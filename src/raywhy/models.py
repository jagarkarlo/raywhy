from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class Verdict(StrEnum):
    UNSATISFIABLE = "UNSATISFIABLE"
    CONTENDED = "CONTENDED"
    AUTOSCALER_BLOCKED = "AUTOSCALER_BLOCKED"
    NODES_UNAVAILABLE = "NODES_UNAVAILABLE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class VerdictResult:
    verdict: Verdict
    summary: str
    evidence: list[str] = field(default_factory=list)
    fix: str = ""

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["verdict"] = self.verdict.value
        return result
