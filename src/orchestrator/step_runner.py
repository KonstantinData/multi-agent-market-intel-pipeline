from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict

from src.agent_common.base_agent import AgentResult
from src.orchestrator.artifact_store import ArtifactStore


@dataclass(frozen=True)
class StepResult:
    step_id: str
    ok: bool
    payload: Dict[str, Any]


class StepRunner:
    """Runs an agent callable and persists output artifacts."""

    def __init__(self, store: ArtifactStore) -> None:
        self.store = store

    def run(
        self,
        *,
        step_id: str,
        agent_callable: Callable[..., AgentResult],
        output_path: str,
        **kwargs: Any,
    ) -> StepResult:
        result = agent_callable(**kwargs)
        if result.ok:
            self.store.write_json(output_path, result.output)
        return StepResult(step_id=step_id, ok=result.ok, payload=result.output)
