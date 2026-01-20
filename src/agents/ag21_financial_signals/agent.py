from __future__ import annotations

import os
from typing import Any, Dict

from src.agent_common.base_agent import AgentResult, BaseAgent
from src.agent_common.step_meta import build_step_meta, utc_now_iso


PROMPT = """Extract verifiable financial development signals for the target company.
Focus on revenue, funding, profitability, and financial momentum.
Only return claims backed by sources; use n/v when evidence is missing.
"""


def _openai_api_key() -> str:
    return os.getenv("OPEN-AI-KEY", "").strip() or os.getenv("OPENAI_API_KEY", "").strip()


class AgentAG21FinancialSignals(BaseAgent):
    step_id = "AG-21"
    agent_name = "ag21_financial_signals"

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
                    "summary": "AG-21 financial development signals",
                    "notes": [
                        "collect revenue, funding, and profitability indicators",
                        "require sourced evidence for each financial claim",
                        "OPEN-AI-KEY configured",
                    ],
                }
            ],
            "sources": [],
        }

        return AgentResult(ok=True, output=output)
