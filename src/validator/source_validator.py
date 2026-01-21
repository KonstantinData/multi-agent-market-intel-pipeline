from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List


@dataclass(frozen=True)
class SourceIssue:
    path: str
    message: str


def _is_http_url(url: str) -> bool:
    return url.startswith("http://") or url.startswith("https://")


def validate_sources(sources: Any, path_prefix: str = "$.sources") -> List[SourceIssue]:
    """Validates source arrays for required fields."""
    issues: List[SourceIssue] = []
    if not isinstance(sources, list):
        return [SourceIssue(path=path_prefix, message="sources must be a list")]

    for idx, entry in enumerate(sources):
        if not isinstance(entry, dict):
            issues.append(
                SourceIssue(
                    path=f"{path_prefix}[{idx}]", message="source must be an object"
                )
            )
            continue
        publisher = str(entry.get("publisher", "")).strip()
        url = str(entry.get("url", "")).strip()
        accessed = str(entry.get("accessed_at_utc", "")).strip()
        if not publisher or not url or not accessed or not _is_http_url(url):
            issues.append(
                SourceIssue(
                    path=f"{path_prefix}[{idx}]",
                    message="source requires publisher, http(s) url, accessed_at_utc",
                )
            )
    return issues
