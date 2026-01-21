from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Tuple
from urllib.parse import quote_plus

import httpx

from src.agent_common.base_agent import AgentResult, BaseAgent
from src.agent_common.step_meta import build_step_meta, utc_now_iso
from src.agent_common.text_normalization import normalize_domain, normalize_whitespace


PROMPT = """Map target customer segments and named reference customers.
Capture customer evidence from press releases or case studies.
Do not infer; include only sourced customer claims.
"""


@dataclass(frozen=True)
class PageEvidence:
    url: str
    publisher: str
    text: str


def _to_ascii(text: str) -> str:
    if text is None:
        return ""
    s = str(text)
    s = (
        s.replace("ä", "ae")
        .replace("ö", "oe")
        .replace("ü", "ue")
        .replace("Ä", "Ae")
        .replace("Ö", "Oe")
        .replace("Ü", "Ue")
        .replace("ß", "ss")
    )
    return s.encode("ascii", errors="ignore").decode("ascii")


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


def _dedupe_urls(urls: Iterable[str]) -> List[str]:
    seen = set()
    deduped: List[str] = []
    for url in urls:
        u = url.strip()
        if not u or u in seen:
            continue
        seen.add(u)
        deduped.append(u)
    return deduped


def _build_sources(company_name: str, domain: str) -> List[Dict[str, str]]:
    base_url = f"https://{domain}"
    company_paths = [
        "",
        "/customers",
        "/customer",
        "/clients",
        "/case-studies",
        "/case-study",
        "/references",
        "/success-stories",
        "/stories",
        "/news",
        "/press",
    ]
    company_urls = [f"{base_url}{path}" if path else base_url for path in company_paths]

    company_query = quote_plus(company_name)
    external_urls = [
        ("OpenCorporates", f"https://opencorporates.com/companies?q={company_query}"),
        ("Google News", f"https://news.google.com/search?q={company_query}%20case%20study"),
        ("PR Newswire", f"https://www.prnewswire.com/search/news/?keyword={company_query}"),
        ("Business Wire", f"https://www.businesswire.com/portal/site/home/search/?searchTerm={company_query}"),
        ("10times", f"https://10times.com/search?kw={company_query}"),
        ("Eventbrite", f"https://www.eventbrite.com/d/online/{company_query}/"),
    ]

    sources: List[Dict[str, str]] = []
    for url in _dedupe_urls(company_urls):
        sources.append({"publisher": company_name or "Official website", "url": url})

    for publisher, url in external_urls:
        sources.append({"publisher": publisher, "url": url})
    return sources


def _fetch_pages(sources: List[Dict[str, str]], timeout_s: float = 10.0) -> List[PageEvidence]:
    evidences: List[PageEvidence] = []
    with httpx.Client(follow_redirects=True, timeout=timeout_s) as client:
        for src in sources:
            url = src["url"]
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
            evidences.append(
                PageEvidence(url=url, publisher=src.get("publisher", "source"), text=text)
            )
    return evidences


def _split_names(value: str) -> List[str]:
    cleaned = re.sub(r"\s+(and|&)\s+", ",", value, flags=re.IGNORECASE)
    cleaned = cleaned.replace("•", ",")
    parts = [p.strip() for p in re.split(r"[;,|]", cleaned) if p.strip()]
    names: List[str] = []
    for part in parts:
        part = re.sub(r"\s+[-–—]\s+.*$", "", part).strip()
        part = re.sub(r"\(.*?\)", "", part).strip()
        if not part:
            continue
        names.append(part)
    return names


def _extract_customer_names(text: str) -> List[str]:
    patterns = [
        re.compile(r"\b(?:Case Study|Customer Story|Client Story|Success Story)\b\s*[:\-]\s*(.+)", re.IGNORECASE),
        re.compile(r"\b(?:Customer|Client|Reference)\b\s*[:\-]\s*(.+)", re.IGNORECASE),
        re.compile(r"\b(?:Trusted by|Customers include|Clients include)\b\s*[:\-]?\s*(.+)", re.IGNORECASE),
    ]
    names: List[str] = []
    for line in text.split("\n"):
        line_text = line.strip()
        if not line_text:
            continue
        for pat in patterns:
            match = pat.search(line_text)
            if not match:
                continue
            for name in _split_names(match.group(1)):
                if len(name) < 2 or len(name) > 80:
                    continue
                lowered = name.lower()
                if any(token in lowered for token in ("customer", "client", "case study", "success story")):
                    continue
                names.append(name)
    return names


def _slugify(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower())
    return s.strip("-") or "nv"


def _dedupe_customers(customers: List[Tuple[str, str, str]]) -> List[Tuple[str, str, str]]:
    seen = set()
    deduped: List[Tuple[str, str, str]] = []
    for name, source, publisher in customers:
        key = (name.lower(), source)
        if key in seen:
            continue
        seen.add(key)
        deduped.append((name, source, publisher))
    return deduped


def _dedupe_sources(sources: List[Dict[str, str]]) -> List[Dict[str, str]]:
    seen = set()
    deduped: List[Dict[str, str]] = []
    for src in sources:
        url = src.get("url", "").strip()
        if not url or url in seen:
            continue
        seen.add(url)
        deduped.append(src)
    return deduped


class AgentAG40TargetCustomers(BaseAgent):
    step_id = "AG-40"
    agent_name = "ag40_target_customers"

    def run(self, case_input: Dict[str, Any]) -> AgentResult:
        started_at_utc = utc_now_iso()

        company_name = normalize_whitespace(str(case_input.get("company_name", "")).strip())
        domain_raw = str(case_input.get("web_domain", "")).strip()
        domain = normalize_domain(domain_raw)

        if not company_name or not domain:
            return AgentResult(ok=False, output={"error": "missing company_name or web_domain"})

        accessed_at = utc_now_iso()
        sources_catalog = _build_sources(company_name, domain)
        pages = _fetch_pages(sources_catalog)

        customer_evidence: List[Tuple[str, str, str]] = []
        for page in pages:
            names = _extract_customer_names(page.text)
            for name in names:
                customer_evidence.append((_to_ascii(name), page.url, page.publisher))

        customer_evidence = _dedupe_customers(customer_evidence)

        entities_delta: List[Dict[str, str]] = []
        relations_delta: List[Dict[str, str]] = []
        used_sources: List[Dict[str, str]] = [
            {
                "publisher": page.publisher or company_name or "Official website",
                "url": page.url,
                "accessed_at_utc": accessed_at,
            }
            for page in pages
        ]

        for name, source_url, _publisher in customer_evidence:
            entity_key = f"customer:{_slugify(name)}"
            entities_delta.append(
                {
                    "entity_key": entity_key,
                    "entity_type": "customer",
                    "entity_name": name,
                    "domain": "n/v",
                }
            )
            relations_delta.append(
                {
                    "relation_type": "supplies_to",
                    "source_id": "TGT-001",
                    "target_id": entity_key,
                }
            )

        if not customer_evidence:
            findings_notes = [
                "No verifiable customer references found in company sites, registries, publications, or event listings (n/v)."
            ]
        else:
            findings_notes = [
                f"Customer reference: {name} (source: {url})."
                for name, url, _publisher in customer_evidence
            ]

        output: Dict[str, Any] = {
            "step_meta": build_step_meta(
                case_input=case_input,
                step_id=self.step_id,
                agent_name=self.agent_name,
                started_at_utc=started_at_utc,
                finished_at_utc=utc_now_iso(),
            ),
            "prompt": PROMPT,
            "entities_delta": entities_delta,
            "relations_delta": relations_delta,
            "findings": [
                {
                    "summary": "Target customer evidence review",
                    "notes": findings_notes,
                }
            ],
            "sources": _dedupe_sources(used_sources),
        }

        return AgentResult(ok=True, output=output)
