import json
import subprocess
import sys
import unittest
from pathlib import Path

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
