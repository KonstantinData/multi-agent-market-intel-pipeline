"""
AG-20 Size Evaluator (Liquisto Fit)

Purpose:
- Evaluate Liquisto lead fit based on AG-13 firmographics signals.
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


def _score_operational_context(operational: Dict[str, Any]) -> float:
    if not operational:
        return 5.0
    
    legal_entities = operational.get("legal_entities", "")
    supply_chain = _normalize_text(operational.get("supply_chain_presence", ""))
    it_landscape = _normalize_text(operational.get("it_landscape", ""))

    score = 3.0
    if isinstance(legal_entities, list) and len(legal_entities) > 2:
        score += 3.0
    if any(term in supply_chain for term in ("multi", "complex", "global", "regional")):
        score += 2.0
    if any(term in it_landscape for term in ("fragmented", "legacy", "multiple", "heterogeneous")):
        score += 2.0

    return min(score, 10.0)


def _industry_bonus(industry: str) -> float:
    text = _normalize_text(industry)
    if any(term in text for term in CORE_INDUSTRY_TERMS):
        return 1.0
    return 0.0


def _extract_firmographics(
    meta_target_entity_stub: Dict[str, Any],
    registry_snapshot: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    if registry_snapshot:
        for entity in registry_snapshot.get("entities", []):
            if not isinstance(entity, dict):
                continue
            if entity.get("entity_id") == "TGT-001" or entity.get("entity_key") == meta_target_entity_stub.get("entity_key"):
                return entity.get("attributes", {})

    return meta_target_entity_stub.get("attributes", {})


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

        attrs = _extract_firmographics(meta_target_entity_stub, registry_snapshot)
        
        headcount = attrs.get("firmographics_headcount", {})
        financial = attrs.get("firmographics_financial", {})
        market = attrs.get("firmographics_market", {})
        operational = attrs.get("firmographics_operational", {})
        classification = attrs.get("industry_classification", {})

        industry = _normalize_text(classification.get("liquisto_class_label"))

        annual_revenue = _coerce_float(financial.get("revenue_last_fy"))
        inventory_ratio = None
        ppe_ratio = None
        
        sites_count = None
        locations = headcount.get("employees_by_location", [])
        if isinstance(locations, list):
            sites_count = len([loc for loc in locations if isinstance(loc, dict)])

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
            "operational_context": _score_operational_context(operational),
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
