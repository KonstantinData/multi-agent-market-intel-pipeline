"""
AG-11 Company Size Profile Builder

Purpose:
- Assemble quantitative and qualitative company size signals for Liquisto's size evaluator (AG-20).
- Output a structured, evidence-aware payload with deterministic defaults ("n/v").

Notes:
- This agent does NOT make authoritative claims. It mirrors provided inputs only.
- It emits a target entity update with an embedded company_size_profile for downstream use.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from src.agents.common.base_agent import AgentResult, BaseAgent
from src.agents.common.step_meta import build_step_meta, utc_now_iso


def _to_ascii(text: str) -> str:
    if text is None:
        return ""
    return str(text).encode("ascii", errors="ignore").decode("ascii")


def _coerce_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned or cleaned.lower() == "n/v":
            return None
        cleaned = cleaned.replace(" ", "").replace(",", "")
        cleaned = re.sub(r"[^0-9.\-]", "", cleaned)
        if not cleaned:
            return None
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def _coerce_int(value: Any) -> Optional[int]:
    as_float = _coerce_float(value)
    if as_float is None:
        return None
    return int(round(as_float))


def _read_nested(source: Dict[str, Any], *keys: str) -> Any:
    current: Any = source
    for key in keys:
        if not isinstance(current, dict):
            return None
        if key not in current:
            return None
        current = current[key]
    return current


def _value_or_nv(value: Any) -> Any:
    if value is None:
        return "n/v"
    if isinstance(value, str) and value.strip() == "":
        return "n/v"
    return value


def _dedupe_sources(sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    deduped: List[Dict[str, Any]] = []
    for source in sources:
        if not isinstance(source, dict):
            continue
        publisher = str(source.get("publisher", "")).strip()
        url = str(source.get("url", "")).strip()
        accessed = str(source.get("accessed_at_utc", "")).strip() or utc_now_iso()
        key = (publisher, url)
        if not publisher or not url or key in seen:
            continue
        seen.add(key)
        deduped.append({"publisher": publisher, "url": url, "accessed_at_utc": accessed})
    return deduped


class AgentAG11CompanySize(BaseAgent):
    step_id = "AG-11"
    agent_name = "ag11_company_size"

    def run(
        self,
        case_input: Dict[str, Any],
        meta_case_normalized: Dict[str, Any],
        meta_target_entity_stub: Dict[str, Any],
    ) -> AgentResult:
        started_at_utc = utc_now_iso()

        company_name = _to_ascii(str(meta_case_normalized.get("company_name_canonical", ""))).strip()
        domain = str(meta_case_normalized.get("web_domain_normalized", "")).strip()
        entity_key = str(meta_case_normalized.get("entity_key", "")).strip()

        if not company_name or not domain or not entity_key:
            return AgentResult(ok=False, output={"error": "missing required meta artifacts"})

        target_company_payload = case_input.get("target_company", {}) if isinstance(case_input, dict) else {}
        quantitative_payload = _read_nested(target_company_payload, "quantitative_metrics") or {}
        qualitative_payload = _read_nested(target_company_payload, "qualitative_context") or {}

        industry = (
            case_input.get("industry")
            or target_company_payload.get("industry")
            or meta_target_entity_stub.get("industry")
        )

        annual_revenue = _coerce_float(
            case_input.get("annual_revenue_eur")
            or quantitative_payload.get("annual_revenue_eur")
        )
        inventory_value = _coerce_float(
            case_input.get("mro_inventory_value_eur")
            or quantitative_payload.get("mro_inventory_value_eur")
        )
        ppe_value = _coerce_float(
            case_input.get("ppe_value_eur")
            or quantitative_payload.get("ppe_value_eur")
        )
        production_sites = _coerce_int(
            case_input.get("number_of_production_sites")
            or quantitative_payload.get("number_of_production_sites")
        )

        inventory_ratio = _coerce_float(
            case_input.get("inventory_to_revenue_ratio")
            or quantitative_payload.get("inventory_to_revenue_ratio")
        )
        if inventory_ratio is None and annual_revenue and inventory_value:
            inventory_ratio = inventory_value / annual_revenue

        maintenance_maturity = (
            case_input.get("maintenance_maturity")
            or qualitative_payload.get("maintenance_maturity")
        )
        erp_system = case_input.get("erp_system") or qualitative_payload.get("erp_system")
        m_and_a_activity = case_input.get("m_and_a_activity") or qualitative_payload.get("m_and_a_activity")
        maintenance_structure = (
            case_input.get("maintenance_structure")
            or qualitative_payload.get("maintenance_structure")
        )
        operational_depth = case_input.get("operational_depth") or qualitative_payload.get("operational_depth")

        quantitative_metrics = {
            "annual_revenue_eur": _value_or_nv(annual_revenue),
            "mro_inventory_value_eur": _value_or_nv(inventory_value),
            "inventory_to_revenue_ratio": _value_or_nv(inventory_ratio),
            "ppe_value_eur": _value_or_nv(ppe_value),
            "number_of_production_sites": _value_or_nv(production_sites),
        }

        qualitative_context = {
            "maintenance_maturity": _value_or_nv(maintenance_maturity),
            "erp_system": _value_or_nv(erp_system),
            "m_and_a_activity": _value_or_nv(m_and_a_activity),
            "maintenance_structure": _value_or_nv(maintenance_structure),
            "operational_depth": _value_or_nv(operational_depth),
        }

        company_size_profile = {
            "agent_source": "AgentAG11CompanySize",
            "target_company": {
                "name": company_name,
                "industry": _value_or_nv(industry),
                "quantitative_metrics": quantitative_metrics,
                "qualitative_context": qualitative_context,
            },
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
        entity_update["attributes"]["company_size_profile"] = company_size_profile

        findings_notes = {
            "company_name_canonical": company_name,
            "web_domain_normalized": domain,
            "entity_key": entity_key,
            "quantitative_metrics": quantitative_metrics,
            "qualitative_context": qualitative_context,
            "data_quality_note": "Values are mirrored from inputs when provided; missing fields remain 'n/v'.",
        }

        sources_input = case_input.get("sources") if isinstance(case_input, dict) else None
        sources = _dedupe_sources(sources_input or [])

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
                    "summary": "Company size profile assembled",
                    "notes": findings_notes,
                }
            ],
            "sources": sources,
            "company_size_profile": company_size_profile,
        }

        return AgentResult(ok=True, output=output)


# NOTE: Wiring-safe alias for dynamic loaders expecting `Agent` symbol in this module.
Agent = AgentAG11CompanySize
