from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .ray_api import RayApiError, RayDashboardClient
from .resources import parse_resource_hint
from .verdicts import explain_pending_job


def apply_resource_hint(snapshot: dict[str, Any], job_id: str, hint: str) -> None:
    resources = parse_resource_hint(hint)
    job = snapshot.setdefault("jobs", {}).setdefault(job_id, {})
    request = job.setdefault("request", {})
    request["resources"] = resources


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="raywhy", description="Explain why a Ray job is pending.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    job = subparsers.add_parser("job", help="Explain one job from a normalized snapshot.")
    job.add_argument("job_id")
    source = job.add_mutually_exclusive_group(required=True)
    source.add_argument("--snapshot", type=Path, help="Path to a JSON snapshot.")
    source.add_argument("--address", help="Read-only Ray dashboard URL, for example http://127.0.0.1:8265.")
    job.add_argument("--timeout", type=float, default=5.0, help="HTTP timeout in seconds (default: 5).")
    job.add_argument("--json", action="store_true", dest="as_json", help="Emit machine-readable JSON.")
    job.add_argument("--resources", help="Explicit request hint, for example GPU=1,CPU=4.")
    queue = subparsers.add_parser("queue", help="Classify all pending jobs.")
    queue_source = queue.add_mutually_exclusive_group(required=True)
    queue_source.add_argument("--snapshot", type=Path, help="Path to a JSON snapshot.")
    queue_source.add_argument("--address", help="Read-only Ray dashboard URL.")
    queue.add_argument("--timeout", type=float, default=5.0, help="HTTP timeout in seconds (default: 5).")
    queue.add_argument("--json", action="store_true", dest="as_json", help="Emit machine-readable JSON.")
    return parser


def _human(job_id: str, result: Any) -> str:
    lines = [f"{result.verdict.value}", f"Job       {job_id}", f"Verdict   {result.summary}"]
    for evidence in result.evidence:
        lines.append(f"Evidence  {evidence}")
    if result.fix:
        lines.append(f"Fix       {result.fix}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "queue":
        try:
            if args.address:
                client = RayDashboardClient(args.address, timeout=args.timeout)
                snapshot = client.snapshot("")
            else:
                snapshot = json.loads(args.snapshot.read_text())
        except (OSError, json.JSONDecodeError, RayApiError) as error:
            print(f"raywhy: cannot read Ray data: {error}", file=sys.stderr)
            return 2
        results = []
        for job_id, job in snapshot.get("jobs", {}).items():
            if isinstance(job, dict) and str(job.get("state", "")).upper() == "PENDING":
                results.append({"job_id": job_id, "result": explain_pending_job(snapshot, job_id).to_dict()})
        results.sort(key=lambda item: item["job_id"])
        if args.as_json:
            print(json.dumps(results, indent=2))
        else:
            for item in results:
                print(_human(item["job_id"], explain_pending_job(snapshot, item["job_id"])))
        return 0
    if args.command == "job":
        try:
            if args.address:
                    snapshot = RayDashboardClient(args.address, timeout=args.timeout).snapshot(args.job_id)
            else:
                snapshot = json.loads(args.snapshot.read_text())
            if args.resources:
                apply_resource_hint(snapshot, args.job_id, args.resources)
        except (OSError, ValueError, json.JSONDecodeError, RayApiError) as error:
            print(f"raywhy: cannot read Ray data: {error}", file=sys.stderr)
            return 2
        result = explain_pending_job(snapshot, args.job_id)
        if args.as_json:
            print(json.dumps(result.to_dict(), indent=2))
        else:
            print(_human(args.job_id, result))
        return 0 if result.verdict.value != "UNKNOWN" else 1
    return 2


if __name__ == "__main__":
    main()
