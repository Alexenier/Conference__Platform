from __future__ import annotations

from dataclasses import dataclass, asdict
from enum import Enum
from typing import Any


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"


@dataclass
class ValidationIssue:
    code: str
    severity: Severity
    message: str
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["severity"] = self.severity.value
        return d


@dataclass
class ValidationReport:
    ok: bool
    issues: list[ValidationIssue]

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "issues": [i.to_dict() for i in self.issues],
        }