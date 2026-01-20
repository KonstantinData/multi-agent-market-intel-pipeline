from __future__ import annotations

import os
from typing import Any, Dict

from src.agents.common.base_agent import AgentResult, BaseAgent
from src.agents.common.step_meta import build_step_meta, utc_now_iso


PROMPT = """Identify the company portfolio: products, services, and solution lines.
Prefer official sources (website, brochures, catalogs).
Return only evidence-backed claims; use n/v when unknown.
"""


def _openai_api_key() -> str:
    return os.getenv("OPEN-AI-KEY", "").strip() or os.getenv("OPENAI_API_KEY", "").strip()


class AgentAG30Portfolio(BaseAgent):
    step_id = "AG-30"
    agent_name = "ag30_portfolio"

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
                    "summary": "AG-30 portfolio discovery",
                    "notes": [
                        "identify product and service offerings",
                        "capture portfolio evidence with sources",
                        "OPEN-AI-KEY configured",
                    ],
                }
            ],
            "sources": [],
        }

        return AgentResult(ok=True, output=output)
