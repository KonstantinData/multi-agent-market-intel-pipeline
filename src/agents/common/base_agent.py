"""
DESCRIPTION
-----------
BaseAgent defines the minimal, repo-wide interface for pipeline steps.
Each agent returns an AgentResult containing an `ok` flag and an `output` payload.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


#note: Standard return type for all agents (ok flag + output payload).
@dataclass(frozen=True)
class AgentResult:
    ok: bool
    output: Dict[str, Any]


#note: Common base class for all step agents.
class BaseAgent:
    """
    #note: Agents should override `step_id` and `agent_name` and implement run().
    """

    step_id: str = "n/v"
    agent_name: str = "n/v"

    #note: Agents may receive a config dict from orchestrator/registry.
    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.config: Dict[str, Any] = config or {}

    #note: The run signature is intentionally flexible; orchestrator adapts invocation by inspection.
    def run(
        self,
        case_input: Dict[str, Any],
        meta_case_normalized: Optional[Dict[str, Any]] = None,
        meta_target_entity_stub: Optional[Dict[str, Any]] = None,
        registry_snapshot: Optional[Dict[str, Any]] = None,
    ) -> AgentResult:
        raise NotImplementedError("Agent must implement run()")
