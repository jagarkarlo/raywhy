from __future__ import annotations

import json
from collections.abc import Mapping
from urllib.parse import urlparse
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

JOBS_PATH = "/api/jobs/"
CLUSTER_STATUS_PATH = "/api/cluster_status"


class RayApiError(RuntimeError):
    """Raised when a read-only Ray API request cannot be completed."""


def _dashboard_url(address: str) -> str:
    parsed = urlparse(address)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise RayApiError("dashboard address must be an http:// or https:// URL")
    if parsed.username or parsed.password:
        raise RayApiError("dashboard address must not contain credentials")
    return address.rstrip("/")


class RayDashboardClient:
    """Small read-only client for a locally reachable Ray dashboard."""

    def __init__(self, address: str, timeout: float = 5.0):
        self.base_url = _dashboard_url(address)
        self.timeout = timeout

    def _get(self, path: str) -> object:
        request = Request(
            f"{self.base_url}{path}",
            method="GET",
            headers={"Accept": "application/json", "User-Agent": "raywhy/0.1"},
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                payload = json.load(response)
                if not isinstance(payload, (Mapping, list)):
                    raise RayApiError(f"GET {path} returned an unsupported JSON shape")
                return payload
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
            raise RayApiError(f"GET {path} failed: {error}") from error

    def snapshot(self, job_id: str) -> dict[str, object]:
        jobs_payload = self._get(JOBS_PATH)
        cluster_payload = self._get(CLUSTER_STATUS_PATH)
        return normalize_ray_payloads(jobs_payload, cluster_payload, job_id)


def _rows(payload: object) -> list[Mapping[str, object]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, Mapping)]
    if isinstance(payload, Mapping):
        for key in ("data", "jobs", "result"):
            value = payload.get(key)
            if isinstance(value, list):
                return [row for row in value if isinstance(row, Mapping)]
    return []


def _number(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _resource_map(value: object) -> dict[str, float]:
    if isinstance(value, Mapping):
        return {str(name): _number(amount) for name, amount in value.items()}
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return _resource_map(decoded)
    return {}


def _resources(row: Mapping[str, object]) -> dict[str, float]:
    for key in ("resources", "resource_request", "entrypoint_resources"):
        value = row.get(key)
        resources = _resource_map(value)
        if resources:
            return resources
    return {}


def _nodes(cluster_payload: object) -> list[dict[str, object]]:
    raw_nodes: object = cluster_payload
    if isinstance(cluster_payload, Mapping):
        raw_nodes = cluster_payload.get("nodes", cluster_payload.get("data", cluster_payload))
    if not isinstance(raw_nodes, list):
        return []

    normalized: list[dict[str, object]] = []
    for index, raw in enumerate(raw_nodes):
        if not isinstance(raw, Mapping):
            continue
        total = raw.get("total", raw.get("resources_total", {}))
        available = raw.get("available", raw.get("resources_available", {}))
        condition = raw.get("condition", "Ready")
        normalized.append(
            {
                "id": str(raw.get("id", raw.get("node_id", index))),
                "schedulable": bool(raw.get("schedulable", condition == "Ready")),
                "condition": condition,
                "total": dict(total) if isinstance(total, Mapping) else {},
                "available": dict(available) if isinstance(available, Mapping) else {},
            }
        )
    return normalized


def normalize_ray_payloads(jobs_payload: object, cluster_payload: object, job_id: str) -> dict[str, object]:
    """Translate standard Ray responses into raywhy's private snapshot contract."""
    jobs: dict[str, dict[str, object]] = {}
    for row in _rows(jobs_payload):
        identifier = str(row.get("submission_id", row.get("job_id", row.get("id", ""))))
        if not identifier:
            continue
        jobs[identifier] = {
            "state": str(row.get("status", row.get("state", "UNKNOWN"))).upper(),
            "request": {"resources": _resources(row)},
        }

    return {"jobs": jobs, "nodes": _nodes(cluster_payload)}
