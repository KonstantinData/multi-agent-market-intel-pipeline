from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx

from src.agents.common.base_agent import AgentResult, BaseAgent
from src.agents.common.step_meta import build_step_meta, utc_now_iso


@dataclass(frozen=True)
class PageEvidence:
    url: str
    text: str


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _to_ascii(text: str) -> str:
    if text is None:
        return ""
    s = str(text)
    s = (s.replace("ä", "ae")
           .replace("ö", "oe")
           .replace("ü", "ue")
           .replace("Ä", "Ae")
           .replace("Ö", "Oe")
           .replace("Ü", "Ue")
           .replace("ß", "ss"))
    s = s.encode("ascii", errors="ignore").decode("ascii")
    return s


def _strip_html(html: str) -> str:
    html = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.IGNORECASE)
    html = re.sub(r"<style[\s\S]*?</style>", " ", html, flags=re.IGNORECASE)
    html = re.sub(r"<(br|p|div|li|tr|h\d)[^>]*>", "\n", html, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", html)
    text = text.replace("&nbsp;", " ")
    text = text.replace("&amp;", "&")
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")
    text = re.sub(r"[\t\r ]+", " ", text)
    text = re.sub(r"\n+", "\n", text)
    return text.strip()


def _fetch_pages(domain: str, paths: List[str], timeout_s: float = 10.0) -> List[PageEvidence]:
    base_url = f"https://{domain}"
    evidences: List[PageEvidence] = []

    with httpx.Client(follow_redirects=True, timeout=timeout_s) as client:
        for p in paths:
            url = f"{base_url}{p}"
            try:
                resp = client.get(url, headers={"User-Agent": "market-intel-pipeline/1.0"})
            except Exception:
                continue

            if resp.status_code != 200:
                continue

            ct = str(resp.headers.get("content-type", "")).lower()
            if "text/html" not in ct and "application/xhtml+xml" not in ct:
                continue

            text = _strip_html(resp.text)
            if not text:
                continue

            evidences.append(PageEvidence(url=url, text=text))

    return evidences


def _site_type_from_line(line: str) -> Optional[str]:
    lowered = line.lower()
    if re.search(r"\b(headquarters|head office|hq)\b", lowered):
        return "hq"
    if re.search(r"\b(manufacturing|production|plant|factory|works)\b", lowered):
        return "production"
    if re.search(r"\b(warehouse|logistics|distribution center|distribution centre)\b", lowered):
        return "warehouse"
    return None


def _extract_location_from_line(line: str) -> Tuple[str, str]:
    candidate = ""
    match = re.search(r"[:\-]\s*(.+)$", line)
    if match:
        candidate = match.group(1).strip()
    else:
        tokens = re.split(r"\b(headquarters|head office|hq|manufacturing|production|plant|factory|works|warehouse|logistics|distribution center|distribution centre)\b",
                          line,
                          flags=re.IGNORECASE)
        if tokens:
            candidate = tokens[-1].strip()

    if not candidate:
        return "n/v", "n/v"

    parts = [p.strip() for p in candidate.split(",") if p.strip()]
    if len(parts) == 1:
        return "n/v", parts[0]
    if len(parts) >= 2:
        city = parts[0]
        country = parts[-1]
        return city, country
    return "n/v", "n/v"


def _slugify(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower())
    return s.strip("-")


def _dedupe_sites(sites: List[Dict[str, str]]) -> List[Dict[str, str]]:
    seen = set()
    deduped: List[Dict[str, str]] = []
    for site in sites:
        key = (site.get("site_type"), site.get("city"), site.get("country_region"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(site)
    return deduped


class AgentAG11LocationsSites(BaseAgent):
    step_id = "AG-11"
    agent_name = "ag11_locations_sites"

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
            "/locations",
            "/contact",
            "/contact-us",
            "/about",
            "/company",
            "/sites",
            "/production",
            "/manufacturing",
            "/plants",
            "/warehouses",
        ]

        pages = _fetch_pages(domain=domain, paths=candidate_paths)

        sites: List[Dict[str, str]] = []
        used_sources: List[Dict[str, str]] = []
        accessed_at = _utc_now_iso()

        for ev in pages:
            contributed = False
            for line in ev.text.split("\n"):
                l = line.strip()
                if not l:
                    continue
                site_type = _site_type_from_line(l)
                if not site_type:
                    continue
                city, country = _extract_location_from_line(l)
                site = {
                    "entity_type": "site",
                    "entity_key": f"{entity_key}#site:{_slugify(site_type)}:{_slugify(city or 'nv')}:{_slugify(country or 'nv')}",
                    "entity_name": _to_ascii(f"{company_name} {site_type} site"),
                    "site_type": site_type,
                    "country_region": _to_ascii(country) if country else "n/v",
                    "city": _to_ascii(city) if city else "n/v",
                }
                sites.append(site)
                contributed = True

            if ev.url and contributed:
                used_sources.append(
                    {
                        "publisher": company_name or "Official website",
                        "url": ev.url,
                        "accessed_at_utc": accessed_at,
                    }
                )

        sites = _dedupe_sites(sites)

        relations: List[Dict[str, str]] = []
        for site in sites:
            relations.append(
                {
                    "from_entity_id": "TGT-001",
                    "relation_type": "operates_at",
                    "to_entity_key": site["entity_key"],
                }
            )

        if not sites:
            findings_notes = ["No verifiable location or site evidence found (n/v)."]
        else:
            findings_notes = ["Site locations extracted from publicly available pages."]

        finished_at_utc = utc_now_iso()

        output: Dict[str, Any] = {
            "step_meta": build_step_meta(
                case_input=case_input,
                step_id=self.step_id,
                agent_name=self.agent_name,
                started_at_utc=started_at_utc,
                finished_at_utc=finished_at_utc,
            ),
            "entities_delta": sites,
            "relations_delta": relations,
            "findings": [
                {
                    "summary": "Locations and sites reviewed",
                    "notes": findings_notes,
                }
            ],
            "sources": _dedupe_sources(used_sources),
        }

        return AgentResult(ok=True, output=output)


def _dedupe_sources(sources: List[Dict[str, str]]) -> List[Dict[str, str]]:
    seen = set()
    deduped: List[Dict[str, str]] = []
    for s in sources:
        url = s.get("url", "")
        if not url or url in seen:
            continue
        seen.add(url)
        deduped.append(s)
    return deduped
