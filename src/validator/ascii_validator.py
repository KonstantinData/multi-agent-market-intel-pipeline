from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass(frozen=True)
class AsciiIssue:
    path: str
    message: str


def _is_ascii(text: str) -> bool:
    try:
        text.encode("ascii")
        return True
    except UnicodeEncodeError:
        return False


def _walk(value: Any, path: str, issues: List[AsciiIssue]) -> None:
    if isinstance(value, str):
        if not _is_ascii(value):
            issues.append(
                AsciiIssue(path=path, message="Non-ASCII characters detected")
            )
        return
    if isinstance(value, dict):
        for key, item in value.items():
            _walk(item, f"{path}.{key}", issues)
    elif isinstance(value, list):
        for idx, item in enumerate(value):
            _walk(item, f"{path}[{idx}]", issues)


def validate_ascii_payload(payload: Dict[str, Any]) -> List[AsciiIssue]:
    """Returns a list of ASCII validation issues for the payload."""
    issues: List[AsciiIssue] = []
    _walk(payload, "$", issues)
    return issues
