"""
AG-21 Financial Development

Purpose:
- Assemble historical financial KPIs (Revenue, EBITDA, Net Debt, CAPEX) over 3–5 years.
- Emit structured outputs with explicit sources or "n/v" for unverifiable data.

Notes:
- This agent mirrors provided inputs; it does not invent facts.
- External retrieval is not performed in this implementation.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.agents.common.base_agent import AgentResult, BaseAgent
from src.agents.common.step_meta import build_step_meta, utc_now_iso


def _to_ascii(text: Any) -> str:
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


def _value_or_nv(value: Any) -> Any:
    if value is None:
        return "n/v"
    if isinstance(value, str) and value.strip() == "":
        return "n/v"
    return value


def _normalize_series(entries: Any) -> List[Dict[str, Any]]:
    if not isinstance(entries, list):
        return []
    normalized: List[Dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        year = _coerce_int(entry.get("year"))
        normalized.append(
            {
                "year": _value_or_nv(year),
                "revenue": _value_or_nv(_coerce_float(entry.get("revenue"))),
                "ebitda": _value_or_nv(_coerce_float(entry.get("ebitda"))),
                "net_debt": _value_or_nv(_coerce_float(entry.get("net_debt"))),
                "capex": _value_or_nv(_coerce_float(entry.get("capex"))),
            }
        )
    return normalized


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


class AgentAG21FinancialDevelopment(BaseAgent):
    step_id = "AG-21"
    agent_name = "ag21_financial_development"

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

        financial_payload = {}
        if isinstance(case_input, dict):
            financial_payload = (
                case_input.get("financial_development")
                or case_input.get("financial_profile")
                or case_input.get("financials")
                or {}
            )

        currency = _value_or_nv(financial_payload.get("currency") or case_input.get("currency"))
        equity_ratio = _value_or_nv(
            financial_payload.get("equity_ratio_2024") or case_input.get("equity_ratio_2024")
        )
        trend_summary = _value_or_nv(
            financial_payload.get("trend_summary") or case_input.get("trend_summary")
        )
        working_capital_pressure = _value_or_nv(
            financial_payload.get("working_capital_pressure") or case_input.get("working_capital_pressure")
        )

        time_series = _normalize_series(
            financial_payload.get("time_series") or case_input.get("financial_time_series") or []
        )
        if not time_series:
            time_series = [
                {
                    "year": "n/v",
                    "revenue": "n/v",
                    "ebitda": "n/v",
                    "net_debt": "n/v",
                    "capex": "n/v",
                }
            ]

        financial_profile = {
            "currency": currency,
            "time_series": time_series,
            "equity_ratio_2024": equity_ratio,
            "trend_summary": trend_summary,
            "working_capital_pressure": working_capital_pressure,
            "data_quality_note": "Values are mirrored from inputs when provided; missing fields remain 'n/v'.",
        }

        entity_update = {
            "entity_id": meta_target_entity_stub.get("entity_id", "TGT-001"),
            "entity_type": meta_target_entity_stub.get("entity_type", "company"),
            "entity_name": meta_target_entity_stub.get("entity_name", company_name),
            "entity_key": entity_key,
            "attributes": {
                "financial_development": financial_profile,
            },
        }

        sources_input = []
        if isinstance(case_input, dict):
            sources_input = case_input.get("financial_sources") or case_input.get("sources") or []
        sources = _dedupe_sources(sources_input)

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
                    "summary": "Financial development KPIs assembled",
                    "financial_profile": financial_profile,
                }
            ],
            "sources": sources,
        }

        return AgentResult(ok=True, output=output)


# NOTE: Wiring-safe alias for dynamic loaders expecting `Agent` symbol in this module.
Agent = AgentAG21FinancialDevelopment
