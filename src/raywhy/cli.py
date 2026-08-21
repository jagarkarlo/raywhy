from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .ray_api import RayApiError, RayDashboardClient
from .verdicts import explain_pending_job


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="raywhy", description="Explain why a Ray job is pending.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    job = subparsers.add_parser("job", help="Explain one job from a normalized snapshot.")
    job.add_argument("job_id")
    source = job.add_mutually_exclusive_group(required=True)
    source.add_argument("--snapshot", type=Path, help="Path to a JSON snapshot.")
    source.add_argument("--address", help="Read-only Ray dashboard URL, for example http://127.0.0.1:8265.")
    job.add_argument("--json", action="store_true", dest="as_json", help="Emit machine-readable JSON.")
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
    if args.command == "job":
        try:
            if args.address:
                snapshot = RayDashboardClient(args.address).snapshot(args.job_id)
            else:
                snapshot = json.loads(args.snapshot.read_text())
        except (OSError, json.JSONDecodeError, RayApiError) as error:
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
