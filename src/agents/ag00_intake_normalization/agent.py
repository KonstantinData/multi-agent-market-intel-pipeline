"""
AG-00 Intake Normalization Agent

Purpose:
- Normalize raw UI-triggered intake input into a deterministic, canonical case payload.
- Provide a stable `entity_key` (domain-based) to anchor downstream steps.
- Produce a contract-friendly step output with `step_meta`, `case_normalized`,
  `entities_delta`, `relations_delta`, `findings`, and `sources`.

Design goals:
- Deterministic output for identical inputs.
- Drift-safe input handling (accepts common synonym keys).
- Wiring-safe agent loading via the `Agent` alias.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from src.agents.common.base_agent import AgentResult, BaseAgent
from src.agents.common.step_meta import build_step_meta, utc_now_iso
from src.agents.common.text_normalization import (
    is_valid_domain,
    normalize_domain,
    normalize_whitespace,
)


#note: Data container for the canonicalized intake fields that downstream agents rely on.
@dataclass(frozen=True)
class CaseNormalized:
    company_name_canonical: str
    web_domain_normalized: str
    entity_key: str


#note: Build a deterministic anchor key for entity identification based on normalized domain.
def build_entity_key_from_domain(domain: str) -> str:
    return f"domain:{domain}"


#note: AG-00 pipeline agent that canonicalizes intake and emits the first entity stub + step artifacts.
class AgentAG00IntakeNormalization(BaseAgent):
    step_id = "AG-00"
    agent_name = "ag00_intake_normalization"

    #note: Execute normalization of raw input into a stable case and a first target entity stub.
    def run(self, case_input: Dict[str, Any]) -> AgentResult:
        #note: Capture deterministic timestamps for step_meta auditability.
        started_at_utc = utc_now_iso()

        #note: Read intake fields in a drift-safe manner (accept common synonyms from UI/handlers).
        company_name_raw = str(
            case_input.get("company_name")
            or case_input.get("legal_name")
            or case_input.get("company")
            or ""
        ).strip()

        web_domain_raw = str(
            case_input.get("web_domain")
            or case_input.get("company_domain")
            or case_input.get("company_web_domain")
            or case_input.get("domain")
            or ""
        ).strip()

        #note: Normalize and canonicalize the core identity attributes.
        company_name = normalize_whitespace(company_name_raw)
        domain = normalize_domain(web_domain_raw)

        #note: Minimal agent self-validation (hard validation belongs to the gatekeeper/validator layer).
        if not company_name:
            return AgentResult(
                ok=False,
                output={"error": "company_name missing"},
            )

        if not domain:
            return AgentResult(
                ok=False,
                output={"error": "web_domain missing"},
            )

        #note: Compute deterministic entity_key to anchor the whole run.
        entity_key = build_entity_key_from_domain(domain)

        #note: Produce canonical case payload for downstream steps.
        case_normalized = CaseNormalized(
            company_name_canonical=company_name,
            web_domain_normalized=domain,
            entity_key=entity_key,
        )

        #note: Build a schema drift-safe entity stub by writing both common naming conventions.
        target_entity_stub = {
            # variant A
            "entity_type": "target_company",
            "entity_name": company_name,
            # variant B
            "type": "target_company",
            "legal_name": company_name,
            # shared
            "domain": domain,
            "entity_key": entity_key,
        }

        #note: Capture end timestamp for run auditability and stable step_meta structure.
        finished_at_utc = utc_now_iso()

        #note: Assemble the canonical step output payload consumed by orchestrator + validator + exporters.
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
            "entities_delta": [target_entity_stub],
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

        #note: Return a successful agent result that downstream orchestration can persist deterministically.
        return AgentResult(ok=True, output=output)


#note: Wiring-safe alias for dynamic loaders expecting `Agent` to exist in the module.
Agent = AgentAG00IntakeNormalization
