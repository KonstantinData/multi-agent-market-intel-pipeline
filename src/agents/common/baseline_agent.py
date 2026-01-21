"""
BaselineAgent for missing agents.

Every planned agent that does not yet have a bespoke implementation should inherit from
BaselineAgent. It provides deterministic, contract‑compliant behaviour by emitting
empty `entities_delta` and `relations_delta` lists and including step_meta fields
(run_id, step_id, pipeline_version, timestamp).  
Use this baseline as a starting point for future real implementations.
"""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from .step_meta import build_step_meta, utc_now_iso
from .base_agent import BaseAgent, AgentResult

class BaselineAgent(BaseAgent):
    """A baseline agent that emits empty deltas and placeholder findings/sources."""

    step_id: str

    def __init__(self, run_id: str, config: Optional[Dict[str, Any]] = None) -> None:
        self.run_id = run_id
        self.config = config or {}

    def execute(self, case_normalized: Dict[str, Any], registry: Dict[str, Any]) -> AgentResult:
        """
        Execute the baseline agent.

        :param case_normalized: The normalized case input from previous steps.
        :param registry: The current entity registry. Baseline agents do not modify it.
        :return: AgentResult with empty deltas and placeholder findings/sources.
        """
        step_meta = build_step_meta(
            run_id=self.run_id,
            step_id=self.step_id,
            pipeline_version=self.config.get("pipeline_version", "0.0.0"),
        )
        result: AgentResult = {
            "step_meta": step_meta,
            "case_normalized": case_normalized,
            "entities_delta": [],
            "relations_delta": [],
            "findings": [],
            "sources": [],
        }
        # Insert dummy findings and sources if configured.
        if self.config.get("include_placeholder", False):
            result["findings"].append(
                {
                    "title": f"{self.step_id} baseline executed",
                    "summary": "No implementation yet; baseline returns no data.",
                }
            )
        return result