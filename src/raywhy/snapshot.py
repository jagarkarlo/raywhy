from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class SnapshotError(ValueError):
    """Raised when a normalized raywhy snapshot is structurally invalid."""


def validate_snapshot(snapshot: object) -> dict[str, Any]:
    if not isinstance(snapshot, Mapping):
        raise SnapshotError("snapshot must be a JSON object")

    jobs = snapshot.get("jobs", {})
    nodes = snapshot.get("nodes", [])
    if not isinstance(jobs, Mapping):
        raise SnapshotError("snapshot.jobs must be an object")
    if not isinstance(nodes, list):
        raise SnapshotError("snapshot.nodes must be an array")

    for job_id, job in jobs.items():
        if not isinstance(job_id, str) or not isinstance(job, Mapping):
            raise SnapshotError("each snapshot job must be an object keyed by id")
        if "state" not in job:
            raise SnapshotError(f"job {job_id!r} is missing state")

    for index, node in enumerate(nodes):
        if not isinstance(node, Mapping):
            raise SnapshotError(f"snapshot.nodes[{index}] must be an object")

    return dict(snapshot)
