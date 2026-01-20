from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from src.agent_common.base_agent import AgentResult, BaseAgent
from src.agent_common.step_meta import build_step_meta, utc_now_iso
from src.agent_common.text_normalization import (
    is_valid_domain,
    normalize_domain,
    normalize_whitespace,
)


@dataclass(frozen=True)
class CaseNormalized:
    company_name_canonical: str
    web_domain_normalized: str
    entity_key: str


def build_entity_key_from_domain(domain: str) -> str:
    return f"domain:{domain}"


class AgentAG00IntakeNormalization(BaseAgent):
    step_id = "AG-00"
    agent_name = "ag00_intake_normalization"

    def run(self, case_input: Dict[str, Any]) -> AgentResult:
        started_at_utc = utc_now_iso()
        company_name_raw = str(case_input.get("company_name", "")).strip()
        web_domain_raw = str(case_input.get("web_domain", "")).strip()

        company_name = normalize_whitespace(company_name_raw)
        domain = normalize_domain(web_domain_raw)

        # Agent self-validation (soft). Hard validation happens in Gatekeeper.
        if not company_name:
            return AgentResult(
                ok=False,
                output={
                    "error": "company_name missing",
                },
            )

        if not domain:
            return AgentResult(
                ok=False,
                output={
                    "error": "web_domain missing",
                },
            )

        entity_key = build_entity_key_from_domain(domain)

        case_normalized = CaseNormalized(
            company_name_canonical=company_name,
            web_domain_normalized=domain,
            entity_key=entity_key,
        )

        target_entity_stub = {
            "entity_type": "target_company",
            "entity_name": company_name,
            "domain": domain,
            "entity_key": entity_key,
        }

        finished_at_utc = utc_now_iso()

        output: Dict[str, Any] = {
            "step_meta": build_step_meta(
                case_input=case_input,
                step_id=self.step_id,
                agent_name=self.agent_name,
                started_at_utc=started_at_utc,
                finished_at_utc=finished_at_utc,
            ),
            "case_normalized": {
                "company_name_canonical": case_normalized.company_name_canonical,
                "web_domain_normalized": case_normalized.web_domain_normalized,
                "entity_key": case_normalized.entity_key,
                "domain_valid": is_valid_domain(domain),
            },
            "target_entity_stub": target_entity_stub,
            "entities_delta": [
                target_entity_stub
            ],
            "relations_delta": [],
            "findings": [
                {
                    "summary": "Intake normalized",
                    "notes": [
                        "company_name canonicalized",
                        "web_domain normalized",
                        "entity_key assigned (no final IDs yet)",
                    ],
                }
            ],
            "sources": [],
        }

        return AgentResult(ok=True, output=output)
