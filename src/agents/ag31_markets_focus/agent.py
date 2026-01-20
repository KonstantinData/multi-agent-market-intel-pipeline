from __future__ import annotations

import os
from typing import Any, Dict

from src.agent_common.base_agent import AgentResult, BaseAgent
from src.agent_common.step_meta import build_step_meta, utc_now_iso


PROMPT = """Determine industries, markets, and segments the company targets.
Capture geographic focus and vertical specialization.
Only include sourced claims; mark unknowns as n/v.
"""


def _openai_api_key() -> str:
    return os.getenv("OPEN-AI-KEY", "").strip() or os.getenv("OPENAI_API_KEY", "").strip()


class AgentAG31MarketsFocus(BaseAgent):
    step_id = "AG-31"
    agent_name = "ag31_markets_focus"

    def run(self, case_input: Dict[str, Any]) -> AgentResult:
        api_key = _openai_api_key()
        if not api_key:
            return AgentResult(ok=False, output={"error": "OPEN-AI-KEY missing"})

        started_at_utc = utc_now_iso()

        output: Dict[str, Any] = {
            "step_meta": build_step_meta(
                case_input=case_input,
                step_id=self.step_id,
                agent_name=self.agent_name,
                started_at_utc=started_at_utc,
                finished_at_utc=utc_now_iso(),
            ),
            "prompt": PROMPT,
            "entities_delta": [],
            "relations_delta": [],
            "findings": [
                {
                    "summary": "AG-31 markets and industry focus",
                    "notes": [
                        "determine industries and markets served",
                        "record geographic and vertical focus signals",
                        "OPEN-AI-KEY configured",
                    ],
                }
            ],
            "sources": [],
        }

        return AgentResult(ok=True, output=output)
