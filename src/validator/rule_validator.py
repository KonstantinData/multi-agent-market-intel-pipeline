from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass(frozen=True)
class RuleIssue:
    path: str
    message: str


def apply_rule_checks(
    payload: Dict[str, Any], rules: Dict[str, Any]
) -> List[RuleIssue]:
    """Applies lightweight rule checks from rules config."""
    issues: List[RuleIssue] = []
    required_fields = (
        rules.get("required_fields", []) if isinstance(rules, dict) else []
    )
    for field in required_fields:
        if payload.get(field) in (None, "", [], {}):
            issues.append(
                RuleIssue(path=f"$.{field}", message="Missing required field")
            )
    return issues
