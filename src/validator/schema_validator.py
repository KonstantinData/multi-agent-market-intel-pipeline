from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from jsonschema import Draft7Validator


@dataclass(frozen=True)
class SchemaIssue:
    path: str
    message: str


def validate_schema(payload: Dict[str, Any], schema: Dict[str, Any]) -> List[SchemaIssue]:
    """Validates payload against a JSON schema and returns issues."""
    validator = Draft7Validator(schema)
    issues: List[SchemaIssue] = []
    for error in validator.iter_errors(payload):
        path = "$"
        if error.path:
            path = "$." + ".".join(str(p) for p in error.path)
        issues.append(SchemaIssue(path=path, message=error.message))
    return issues
