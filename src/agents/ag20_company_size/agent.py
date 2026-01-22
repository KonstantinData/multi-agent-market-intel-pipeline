from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx

from src.agents.common.base_agent import AgentResult, BaseAgent
from src.agents.common.step_meta import build_step_meta, utc_now_iso


@dataclass(frozen=True)
class PageEvidence:
    url: str
    text: str


def _to_ascii(text: str) -> str:
    try:
        return text.encode("utf-8", errors="ignore").decode("utf-8")
    except Exception:
        return text


def _dedupe_sources(sources: List[Dict[str, str]]) -> List[Dict[str, str]]:
    seen = set()
    out: List[Dict[str, str]] = []
    for s in sources:
        url = str(s.get("url", "")).strip()
        publisher = str(s.get("publisher", "")).strip()
        key = (publisher, url)
        if url and publisher and key not in seen:
            seen.add(key)
            out.append({"publisher": publisher, "url": url, "accessed_at_utc": s.get("accessed_at_utc", utc_now_iso())})
    return out


def _fetch_text(url: str, timeout_s: float = 15.0) -> Optional[str]:
    try:
        with httpx.Client(timeout=timeout_s, follow_redirects=True) as client:
            r = client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code != 200:
                return None
            ct = r.headers.get("content-type", "")
            if "text/html" not in ct and "text/plain" not in ct and "application/xhtml+xml" not in ct:
                return None
            return r.text
    except Exception:
        return None


def _strip_html_to_text(html: str) -> str:
    # Minimal HTML->text normalization (non-OCR, deterministic)
    text = re.sub(r"(?is)<script.*?>.*?</script>", " ", html)
    text = re.sub(r"(?is)<style.*?>.*?</style>", " ", text)
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _extract_size_signals(text: str) -> Dict[str, Any]:
    """
    Extracts low-stakes "signals" only (no hard claims):
      - employee count pattern hits
      - revenue pattern hits
      - generic size keywords
    """
    t = text.lower()

    employees_hits = []
    revenue_hits = []
    keyword_hits = []

    # Employees patterns (very permissive; treated as "signals")
    emp_patterns = [
        r"\b(\d{2,6})\s*(employees|employee|mitarbeiter|mitarbeitende|mitarbeiterinnen|staff)\b",
        r"\b(employees|employee|mitarbeiter|mitarbeitende|staff)\s*[:\-]?\s*(\d{2,6})\b",
    ]
    for pat in emp_patterns:
        for m in re.finditer(pat, t):
            employees_hits.append(m.group(0))

    # Revenue patterns (signals, not canonical financials)
    rev_patterns = [
        r"\b(revenue|umsatz|turnover)\s*[:\-]?\s*(€|\$|eur|usd)?\s*\d[\d\.,]*\s*(m|mn|million|mio|b|bn|billion|mrd)?\b",
        r"\b(€|\$)\s*\d[\d\.,]*\s*(m|mn|million|mio|b|bn|billion|mrd)\b",
    ]
    for pat in rev_patterns:
        for m in re.finditer(pat, t):
            revenue_hits.append(m.group(0))

    # Generic size keywords (signals)
    size_keywords = [
        "global",
        "worldwide",
        "international",
        "multinational",
        "mid-size",
        "midsize",
        "mittelstand",
        "large",
        "small",
        "startup",
        "family-owned",
        "familienunternehmen",
    ]
    for kw in size_keywords:
        if kw in t:
            keyword_hits.append(kw)

    return {
        "employees_hits": employees_hits[:20],
        "revenue_hits": revenue_hits[:20],
        "keyword_hits": sorted(set(keyword_hits)),
    }


def _build_target_update(meta_target_entity_stub: Dict[str, Any], size_signals: Dict[str, Any]) -> Dict[str, Any]:
    # Non-authoritative enrichment: store signals only
    update = dict(meta_target_entity_stub)

    # Ensure structure fields exist if stub is minimal
    update.setdefault("attributes", {})
    attrs = update["attributes"]
    if not isinstance(attrs, dict):
        attrs = {}
        update["attributes"] = attrs

    attrs["company_size_signals"] = size_signals
    return update


class AgentAG20CompanySize(BaseAgent):
    step_id = "AG-20"
    agent_name = "ag20_company_size"

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

        candidate_paths = [
            "/about",
            "/company",
            "/unternehmen",
            "/about-us",
            "/aboutus",
            "/facts",
            "/facts-and-figures",
            "/facts-figures",
            "/factsfigures",
            "/career",
            "/careers",
            "/karriere",
        ]

        used_sources: List[Dict[str, str]] = []
        evidences: List[PageEvidence] = []

        base_url = f"https://{domain}".rstrip("/")
        used_sources.append({"publisher": company_name, "url": base_url, "accessed_at_utc": utc_now_iso()})

        for p in candidate_paths:
            url = f"{base_url}{p}"
            html = _fetch_text(url)
            if not html:
                continue
            txt = _strip_html_to_text(html)
            if not txt or len(txt) < 80:
                continue
            evidences.append(PageEvidence(url=url, text=txt))
            used_sources.append({"publisher": company_name, "url": url, "accessed_at_utc": utc_now_iso()})

            # Keep it bounded; we only need a few pages for "signals"
            if len(evidences) >= 3:
                break

        combined_text = " ".join([ev.text for ev in evidences]).strip()
        size_signals = _extract_size_signals(combined_text) if combined_text else {
            "employees_hits": [],
            "revenue_hits": [],
            "keyword_hits": [],
        }

        target_update = _build_target_update(meta_target_entity_stub, size_signals)

        finished_at_utc = utc_now_iso()

        findings_notes = {
            "company_name_canonical": company_name,
            "web_domain_normalized": domain,
            "entity_key": entity_key,
            "reviewed_pages": [ev.url for ev in evidences],
            "signals": size_signals,
            "scope_note": "Signals only; no authoritative company size claims are made without corroborating sources.",
        }

        output: Dict[str, Any] = {
            "step_meta": build_step_meta(
                case_input=case_input,
                step_id=self.step_id,
                agent_name=self.agent_name,
                started_at_utc=started_at_utc,
                finished_at_utc=finished_at_utc,
            ),
            "entities_delta": [target_update],
            "relations_delta": [],  # REQUIRED by pipeline output contract (even if empty)
            "findings": [
                {
                    "summary": "Company size signals reviewed",
                    "notes": findings_notes,
                }
            ],
            "sources": _dedupe_sources(used_sources),
        }

        return AgentResult(ok=True, output=output)


# NOTE: Wiring-safe alias for dynamic loaders expecting `Agent` symbol in this module.
Agent = AgentAG20CompanySize
