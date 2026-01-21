from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import yaml


@dataclass(frozen=True)
class RetryPolicy:
    max_retries: int = 0
    backoff_seconds: float = 0.0

    def can_retry(self, attempt: int) -> bool:
        return attempt < self.max_retries


@dataclass(frozen=True)
class RetryPolicySet:
    policies: Dict[str, RetryPolicy]
    default_policy: RetryPolicy = RetryPolicy()

    def for_step(self, step_id: str) -> RetryPolicy:
        return self.policies.get(step_id, self.default_policy)


def load_retry_policies(path: str) -> RetryPolicySet:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    policies: Dict[str, RetryPolicy] = {}
    for step_id, payload in (data.get("steps") or {}).items():
        policies[step_id] = RetryPolicy(
            max_retries=int(payload.get("max_retries", 0)),
            backoff_seconds=float(payload.get("backoff_seconds", 0.0)),
        )
    default_payload = data.get("default", {}) if isinstance(data, dict) else {}
    default_policy = RetryPolicy(
        max_retries=int(default_payload.get("max_retries", 0)),
        backoff_seconds=float(default_payload.get("backoff_seconds", 0.0)),
    )
    return RetryPolicySet(policies=policies, default_policy=default_policy)
