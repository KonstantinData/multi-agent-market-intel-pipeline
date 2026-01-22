"""
AG-20 Size Evaluator (Liquisto Fit)

Purpose:
- Evaluate Liquisto lead fit based on AG-11 company size profile signals.
- Emit a weighted priority score, tier, rationale, and outreach hook.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

from src.agents.common.base_agent import AgentResult, BaseAgent
from src.agents.common.step_meta import build_step_meta, utc_now_iso


CORE_INDUSTRY_TERMS = {
    "medtech",
    "medical technology",
    "medical",
    "mechanical engineering",
    "mechanical",
    "electrical engineering",
    "electrical",
}


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def _coerce_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def _score_ratio(ratio: Optional[float], thresholds: List[Tuple[float, float]]) -> float:
    if ratio is None or math.isnan(ratio):
        return 5.0
    for threshold, score in thresholds:
        if ratio >= threshold:
            return score
    return 1.0


def _score_sites(count: Optional[int]) -> float:
    if count is None:
        return 5.0
    if count >= 4:
        return 10.0
    if count == 3:
        return 7.0
    if count == 2:
        return 4.0
    return 1.0


def _score_operational_context(context: Dict[str, Any]) -> float:
    if not context:
        return 5.0
    m_and_a = _normalize_text(context.get("m_and_a_activity"))
    erp = _normalize_text(context.get("erp_system"))
    maintenance = _normalize_text(context.get("maintenance_structure"))

    score = 3.0
    if m_and_a and m_and_a not in {"n/v", "none", "no", "nein"}:
        score += 3.0
    if any(term in erp for term in ("fragmented", "legacy", "multiple", "mix", "hybrid")):
        score += 2.0
    if any(term in maintenance for term in ("decentral", "local", "plant", "regional")):
        score += 2.0

    return min(score, 10.0)


def _industry_bonus(industry: str) -> float:
    text = _normalize_text(industry)
    if any(term in text for term in CORE_INDUSTRY_TERMS):
        return 1.0
    return 0.0


def _extract_profile(
    case_input: Dict[str, Any],
    meta_target_entity_stub: Dict[str, Any],
    registry_snapshot: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    if isinstance(case_input.get("company_size_profile"), dict):
        return case_input.get("company_size_profile")  # type: ignore[return-value]

    if registry_snapshot:
        for entity in registry_snapshot.get("entities", []):
            if not isinstance(entity, dict):
                continue
            if entity.get("entity_id") == "TGT-001" or entity.get("entity_key") == meta_target_entity_stub.get("entity_key"):
                attrs = entity.get("attributes")
                if isinstance(attrs, dict) and isinstance(attrs.get("company_size_profile"), dict):
                    return attrs.get("company_size_profile")  # type: ignore[return-value]

    attrs = meta_target_entity_stub.get("attributes")
    if isinstance(attrs, dict) and isinstance(attrs.get("company_size_profile"), dict):
        return attrs.get("company_size_profile")  # type: ignore[return-value]

    return {}


class AgentAG20SizeEvaluator(BaseAgent):
    step_id = "AG-20"
    agent_name = "ag20_size_evaluator"

    def run(
        self,
        case_input: Dict[str, Any],
        meta_case_normalized: Dict[str, Any],
        meta_target_entity_stub: Dict[str, Any],
        registry_snapshot: Optional[Dict[str, Any]] = None,
    ) -> AgentResult:
        started_at_utc = utc_now_iso()

        company_name = str(meta_case_normalized.get("company_name_canonical", "")).strip()
        domain = str(meta_case_normalized.get("web_domain_normalized", "")).strip()
        entity_key = str(meta_case_normalized.get("entity_key", "")).strip()

        if not company_name or not domain or not entity_key:
            return AgentResult(ok=False, output={"error": "missing required meta artifacts"})

        profile = _extract_profile(case_input, meta_target_entity_stub, registry_snapshot)
        target_company = profile.get("target_company", {}) if isinstance(profile, dict) else {}
        quantitative = target_company.get("quantitative_metrics", {}) if isinstance(target_company, dict) else {}
        qualitative = target_company.get("qualitative_context", {}) if isinstance(target_company, dict) else {}

        industry = _normalize_text(target_company.get("industry"))

        annual_revenue = _coerce_float(quantitative.get("annual_revenue_eur"))
        inventory_value = _coerce_float(quantitative.get("mro_inventory_value_eur"))
        inventory_ratio = _coerce_float(quantitative.get("inventory_to_revenue_ratio"))
        if inventory_ratio is None and annual_revenue and inventory_value:
            inventory_ratio = inventory_value / annual_revenue

        ppe_value = _coerce_float(quantitative.get("ppe_value_eur"))
        ppe_ratio = None
        if ppe_value is not None and annual_revenue:
            ppe_ratio = ppe_value / annual_revenue

        production_sites = _coerce_float(quantitative.get("number_of_production_sites"))
        sites_count = int(round(production_sites)) if production_sites is not None else None

        scores = {
            "mro_inventory_intensity": _score_ratio(
                inventory_ratio,
                [(0.04, 10.0), (0.02, 7.0), (0.01, 4.0)],
            ),
            "asset_intensity_ppe": _score_ratio(
                ppe_ratio,
                [(0.3, 10.0), (0.15, 7.0), (0.05, 4.0)],
            ),
            "site_fragmentation": _score_sites(sites_count),
            "operational_context": _score_operational_context(qualitative),
            "industry_core_fit": 10.0 if _industry_bonus(industry) > 0 else 5.0,
        }

        weights = {
            "mro_inventory_intensity": 35,
            "asset_intensity_ppe": 25,
            "site_fragmentation": 20,
            "operational_context": 10,
            "industry_core_fit": 10,
        }

        weighted_sum = sum(scores[key] * weights[key] for key in scores)
        priority_score = round(weighted_sum / 100, 1)
        priority_score = min(priority_score + _industry_bonus(industry), 10.0)

        if priority_score >= 8.0:
            tier = "Tier A"
        elif priority_score >= 5.0:
            tier = "Tier B"
        else:
            tier = "Tier C"

        rationale = [
            f"Inventory intensity score: {scores['mro_inventory_intensity']}/10",
            f"Asset intensity score: {scores['asset_intensity_ppe']}/10",
            f"Site fragmentation score: {scores['site_fragmentation']}/10",
        ]
        if _industry_bonus(industry):
            rationale.append("Industry bonus applied for core Liquisto sectors.")
        if scores["operational_context"] >= 7:
            rationale.append("Operational complexity suggests consolidation potential.")

        outreach_hook = ""
        if tier == "Tier A":
            outreach_hook = "CFO-level working capital release pitch with MRO consolidation focus."
        elif tier == "Tier B":
            outreach_hook = "Plant manager and procurement hook around inventory visibility gains."
        else:
            outreach_hook = "Deprioritize: insufficient inventory pressure signals."

        evaluation = {
            "priority_score": priority_score,
            "priority_tier": tier,
            "scores": scores,
            "strategic_rationale": " ".join(rationale),
            "outreach_hook": outreach_hook,
        }

        entity_update = dict(meta_target_entity_stub)
        entity_update.update(
            {
                "entity_id": "TGT-001",
                "entity_type": "target_company",
                "entity_name": company_name,
                "domain": domain,
                "entity_key": entity_key,
            }
        )
        entity_update.setdefault("attributes", {})
        if not isinstance(entity_update["attributes"], dict):
            entity_update["attributes"] = {}
        entity_update["attributes"]["liquisto_fit"] = evaluation

        finished_at_utc = utc_now_iso()

        output: Dict[str, Any] = {
            "step_meta": build_step_meta(
                case_input=case_input,
                step_id=self.step_id,
                agent_name=self.agent_name,
                started_at_utc=started_at_utc,
                finished_at_utc=finished_at_utc,
            ),
            "entities_delta": [entity_update],
            "relations_delta": [],
            "findings": [
                {
                    "summary": "Liquisto fit evaluation completed",
                    "notes": {
                        "priority_score": priority_score,
                        "priority_tier": tier,
                        "outreach_hook": outreach_hook,
                    },
                }
            ],
            "sources": [],
            "evaluation": evaluation,
        }

        return AgentResult(ok=True, output=output)


# NOTE: Wiring-safe alias for dynamic loaders expecting `Agent` symbol in this module.
Agent = AgentAG20SizeEvaluator
