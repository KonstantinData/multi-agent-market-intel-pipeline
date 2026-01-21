"""
DESCRIPTION
-----------
BaselineAgent is used for planned steps that do not yet have a specialized implementation.
It produces contract-compliant, deterministic outputs (no TODOs, no stubs), but may return
n/v findings when external evidence is not available.

This ensures:
- the DAG can execute end-to-end,
- every planned step is wired and produces audit artifacts,
- downstream steps can read the cumulative registry snapshot.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from src.agents.common.base_agent import AgentResult, BaseAgent
from src.agents.common.step_meta import build_step_meta, utc_now_iso


#note: A deterministic baseline agent that always returns a contract-valid output payload.
class BaselineAgent(BaseAgent):
    """
    #note: BaselineAgent exists to keep the full DAG executable even when a step has no specialized logic yet.
    """

    #note: Human-readable description injected into findings for traceability.
    baseline_purpose: str = "n/v"

    #note: Run the baseline step and emit a deterministic output structure.
    def run(
        self,
        case_input: Dict[str, Any],
        meta_case_normalized: Optional[Dict[str, Any]] = None,
        meta_target_entity_stub: Optional[Dict[str, Any]] = None,
        registry_snapshot: Optional[Dict[str, Any]] = None,
    ) -> AgentResult:
        started_at_utc = utc_now_iso()
        finished_at_utc = utc_now_iso()

        #note: These fields are propagated from AG-00 to keep step outputs consistent.
        case_norm = meta_case_normalized or {}
        tgt_stub = meta_target_entity_stub or {}

        output: Dict[str, Any] = {
            "step_meta": build_step_meta(
                case_input=case_input,
                step_id=self.step_id,
                agent_name=self.agent_name,
                started_at_utc=started_at_utc,
                finished_at_utc=finished_at_utc,
            ),
            "case_normalized": case_norm,
            "target_entity_stub": tgt_stub,
            "entities_delta": [],
            "relations_delta": [],
            "findings": [
                {
                    "step_id": self.step_id,
                    "finding_type": "baseline",
                    "status": "n/v",
                    "summary": self.baseline_purpose,
                    "details": {
                        "note": "No specialized implementation configured for this step yet. Output is deterministic and contract-compliant.",
                    },
                }
            ],
            "sources": [],
        }

        return AgentResult(ok=True, output=output)
