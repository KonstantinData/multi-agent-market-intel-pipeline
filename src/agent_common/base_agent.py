from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class AgentResult:
    ok: bool
    output: Dict[str, Any]


class BaseAgent:
    step_id: str = "n/v"
    agent_name: str = "n/v"

    def run(self, case_input: Dict[str, Any]) -> AgentResult:
        raise NotImplementedError("Agent must implement run()")
