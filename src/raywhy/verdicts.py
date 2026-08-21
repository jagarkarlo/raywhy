from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .models import Verdict, VerdictResult


def _resources(job: Mapping[str, Any]) -> dict[str, float]:
    request = job.get("request", {})
    return {name: float(value) for name, value in request.get("resources", {}).items()}


def _fits(request: Mapping[str, float], capacity: Mapping[str, Any]) -> bool:
    return all(float(capacity.get(name, 0)) >= amount for name, amount in request.items())


def _total_available(nodes: list[Mapping[str, Any]]) -> dict[str, float]:
    totals: dict[str, float] = {}
    for node in nodes:
        for name, value in node.get("available", {}).items():
            totals[name] = totals.get(name, 0) + float(value)
    return totals


def explain_pending_job(snapshot: Mapping[str, Any], job_id: str) -> VerdictResult:
    """Classify a pending job from a normalized, read-only cluster snapshot.

    Snapshot shape is intentionally small and adapter-independent. API adapters
    can translate Ray and Kubernetes responses into this contract later.
    """
    jobs = snapshot.get("jobs", {})
    job = jobs.get(job_id)
    if not isinstance(job, Mapping):
        return VerdictResult(
            Verdict.UNKNOWN,
            f"Job {job_id} was not found in the snapshot.",
            fix="Refresh the snapshot and check the submission id.",
        )

    state = str(job.get("state", "UNKNOWN")).upper()
    if state != "PENDING":
        return VerdictResult(
            Verdict.UNKNOWN,
            f"Job {job_id} is {state}, not PENDING.",
            fix="Inspect the job's current state instead of applying a pending verdict.",
        )

    request = _resources(job)
    nodes = [node for node in snapshot.get("nodes", []) if isinstance(node, Mapping)]
    schedulable = [node for node in nodes if node.get("schedulable", True)]
    capacity = snapshot.get("capacity", {})
    if not isinstance(capacity, Mapping):
        capacity = {}

    autoscaler = snapshot.get("autoscaler", {})
    if isinstance(autoscaler, Mapping) and autoscaler.get("blocked"):
        reason = str(autoscaler.get("reason", "the autoscaler reported a block"))
        return VerdictResult(
            Verdict.AUTOSCALER_BLOCKED,
            "The request could fit, but the autoscaler is preventing capacity from being added.",
            [reason],
            "Inspect autoscaler limits, quotas, cooldowns, and worker-group max replicas.",
        )

    unavailable = [node for node in nodes if node.get("condition") not in (None, "Ready")]
    if not nodes or not schedulable:
        return VerdictResult(
            Verdict.NODES_UNAVAILABLE,
            "The snapshot reports no schedulable nodes for this request.",
            [f"Unavailable nodes: {len(unavailable) or len(nodes)}"],
            "Restore node readiness, remove the cordon, or inspect node taints and image state.",
        )

    if not any(_fits(request, node.get("total", {})) for node in schedulable):
        return VerdictResult(
            Verdict.UNSATISFIABLE,
            "No schedulable node shape can satisfy this job's resource request.",
            [f"Requested resources: {request or 'none'}"],
            "Change the resource request or add a node type that can host it.",
        )

    available = _total_available(schedulable)
    return VerdictResult(
        Verdict.CONTENDED,
        "The request is valid, but resources are currently held by other work.",
        [f"Available resources: {available or 'none'}"],
        "Wait for resources to be released or inspect the jobs currently holding them.",
    )
