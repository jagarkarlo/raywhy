import json
import subprocess
import sys
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Thread

from raywhy.ray_api import RayApiError, RayDashboardClient, normalize_ray_payloads
from raywhy.models import Verdict
from raywhy.verdicts import explain_pending_job


FIXTURES = Path(__file__).parent / "fixtures"


class VerdictTests(unittest.TestCase):
    def test_classifies_known_pending_causes(self):
        cases = {
            "unsatisfiable.json": Verdict.UNSATISFIABLE,
            "contended.json": Verdict.CONTENDED,
            "autoscaler-blocked.json": Verdict.AUTOSCALER_BLOCKED,
            "nodes-unavailable.json": Verdict.NODES_UNAVAILABLE,
        }
        for fixture, expected in cases.items():
            with self.subTest(fixture=fixture):
                snapshot = json.loads((FIXTURES / fixture).read_text())
                result = explain_pending_job(snapshot, "job-1")
                self.assertIs(result.verdict, expected)
                self.assertTrue(result.summary)
                self.assertTrue(result.fix)

    def test_unknown_job_is_explicit(self):
        result = explain_pending_job({"jobs": {}}, "missing")
        self.assertIs(result.verdict, Verdict.UNKNOWN)

    def test_zero_node_snapshot_is_not_unsatisfiable(self):
        snapshot = {
            "jobs": {"job-1": {"state": "PENDING", "request": {"resources": {"GPU": 1}}}},
            "nodes": [],
        }
        result = explain_pending_job(snapshot, "job-1")
        self.assertIs(result.verdict, Verdict.NODES_UNAVAILABLE)

    def test_missing_request_is_not_guessed(self):
        snapshot = {
            "jobs": {"job-1": {"state": "PENDING"}},
            "nodes": [{"total": {"GPU": 4}, "available": {"GPU": 4}}],
        }
        result = explain_pending_job(snapshot, "job-1")
        self.assertIs(result.verdict, Verdict.UNKNOWN)

    def test_normalizes_ray_payloads(self):
        snapshot = normalize_ray_payloads(
            [{"submission_id": "job-1", "status": "pending", "resources": {"GPU": 1}}],
            {"nodes": [{"node_id": "node-a", "resources_total": {"GPU": 2}, "resources_available": {"GPU": 1}}]},
            "job-1",
        )
        self.assertEqual(snapshot["jobs"]["job-1"]["request"]["resources"]["GPU"], 1.0)
        self.assertEqual(snapshot["nodes"][0]["id"], "node-a")

    def test_normalizes_encoded_resource_requests(self):
        snapshot = normalize_ray_payloads(
            [{"submission_id": "job-1", "status": "PENDING", "resource_request": '{"GPU": "2", "CPU": 4}'}],
            [],
            "job-1",
        )
        self.assertEqual(snapshot["jobs"]["job-1"]["request"]["resources"], {"GPU": 2.0, "CPU": 4.0})

    def test_live_client_reads_only_get_endpoints(self):
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                payload = (
                    [{"submission_id": "job-1", "status": "PENDING", "resources": {"GPU": 1}}]
                    if self.path == "/api/jobs/"
                    else {"nodes": [{"node_id": "node-a", "resources_total": {"GPU": 2}, "resources_available": {"GPU": 1}}]}
                )
                encoded = json.dumps(payload).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)

            def do_POST(self):
                self.send_response(405)
                self.end_headers()

            def log_message(self, *_):
                return

        server = HTTPServer(("127.0.0.1", 0), Handler)
        Thread(target=server.serve_forever, daemon=True).start()
        try:
            snapshot = RayDashboardClient(f"http://127.0.0.1:{server.server_port}").snapshot("job-1")
            result = explain_pending_job(snapshot, "job-1")
            self.assertIs(result.verdict, Verdict.CONTENDED)
        finally:
            server.shutdown()
            server.server_close()

    def test_dashboard_address_rejects_credentials(self):
        with self.assertRaises(RayApiError):
            RayDashboardClient("http://user:password@127.0.0.1:8265")

    def test_dashboard_address_requires_http_scheme(self):
        with self.assertRaises(RayApiError):
            RayDashboardClient("ray://127.0.0.1:8265")

    def test_live_client_rejects_scalar_json(self):
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                encoded = b"42"
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)

            def log_message(self, *_):
                return

        server = HTTPServer(("127.0.0.1", 0), Handler)
        Thread(target=server.serve_forever, daemon=True).start()
        with self.assertRaises(RayApiError):
            RayDashboardClient(f"http://127.0.0.1:{server.server_port}").snapshot("job-1")
        server.shutdown()
        server.server_close()

    def test_cli_json_output(self):
        process = subprocess.run(
            [
                sys.executable,
                "-m",
                "raywhy.cli",
                "job",
                "job-1",
                "--snapshot",
                str(FIXTURES / "unsatisfiable.json"),
                "--json",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn('"verdict": "UNSATISFIABLE"', process.stdout)


if __name__ == "__main__":
    unittest.main()
