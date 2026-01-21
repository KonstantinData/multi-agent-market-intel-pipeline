from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Tuple
from urllib.parse import quote_plus

import httpx

from src.agent_common.base_agent import AgentResult, BaseAgent
from src.agent_common.step_meta import build_step_meta, utc_now_iso
from src.agent_common.text_normalization import normalize_whitespace


PROMPT = """Map customers of peer manufacturers identified in AG-41.
Capture evidence linking customers to peers.
Only include customer claims with sources.
"""


@dataclass(frozen=True)
class PageEvidence:
    url: str
    publisher: str
    text: str


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


def _collect_peer_names(case_input: Dict[str, Any], fallback_name: str) -> List[str]:
    candidates = []
    for key in ("peer_manufacturers", "peer_companies", "competitors", "peers"):
        value = case_input.get(key)
        if isinstance(value, list):
            candidates.extend([str(v).strip() for v in value if str(v).strip()])
    if fallback_name:
        candidates.append(fallback_name)
    seen = set()
    deduped: List[str] = []
    for name in candidates:
        if name.lower() in seen:
            continue
        seen.add(name.lower())
        deduped.append(name)
    return deduped


def _build_sources(peer_names: List[str]) -> List[Dict[str, str]]:
    sources: List[Dict[str, str]] = []
    for peer in peer_names:
        query = quote_plus(peer)
        sources.extend(
            [
                {
                    "publisher": "Google News",
                    "url": f"https://news.google.com/search?q={query}%20customer",
                },
                {
                    "publisher": "PR Newswire",
                    "url": f"https://www.prnewswire.com/search/news/?keyword={query}%20customer",
                },
                {
                    "publisher": "Business Wire",
                    "url": f"https://www.businesswire.com/portal/site/home/search/?searchTerm={query}%20customer",
                },
            ]
        )
    return _dedupe_sources(sources)


def _fetch_pages(
    sources: List[Dict[str, str]], timeout_s: float = 10.0
) -> List[PageEvidence]:
    evidences: List[PageEvidence] = []
    with httpx.Client(follow_redirects=True, timeout=timeout_s) as client:
        for src in sources:
            url = src["url"]
            try:
                resp = client.get(
                    url, headers={"User-Agent": "market-intel-pipeline/1.0"}
                )
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
                PageEvidence(
                    url=url, publisher=src.get("publisher", "source"), text=text
                )
            )
    return evidences


def _extract_customer_lines(text: str) -> List[str]:
    keywords = [
        "customer",
        "client",
        "case study",
        "success story",
        "selected by",
        "trusted by",
        "partners with",
    ]
    lines: List[str] = []
    for line in text.split("\n"):
        line_text = line.strip()
        if not line_text:
            continue
        if len(line_text) < 40 or len(line_text) > 260:
            continue
        if any(k in line_text.lower() for k in keywords):
            lines.append(line_text)
        if len(lines) >= 6:
            break
    return lines


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


class AgentAG42CustomersOfManufacturers(BaseAgent):
    step_id = "AG-42"
    agent_name = "ag42_customers_of_manufacturers"

    def run(self, case_input: Dict[str, Any]) -> AgentResult:
        started_at_utc = utc_now_iso()

        company_name = normalize_whitespace(
            str(case_input.get("company_name", "")).strip()
        )
        if not company_name:
            return AgentResult(ok=False, output={"error": "missing company_name"})

        peer_names = _collect_peer_names(case_input, company_name)
        accessed_at = utc_now_iso()
        sources_catalog = _build_sources(peer_names)
        pages = _fetch_pages(sources_catalog)

        customer_lines: List[Tuple[str, str, str]] = []
        for page in pages:
            for line in _extract_customer_lines(page.text):
                customer_lines.append((line, page.url, page.publisher))

        customer_lines = customer_lines[:6]

        used_sources: List[Dict[str, str]] = [
            {
                "publisher": page.publisher or "source",
                "url": page.url,
                "accessed_at_utc": accessed_at,
            }
            for page in pages
        ]

        findings_notes: List[str] = []
        if not customer_lines:
            findings_notes.append(
                "No verifiable downstream customer references found for peer manufacturers in public sources (n/v)."
            )
        else:
            for line, url, _publisher in customer_lines:
                findings_notes.append(f"Customer evidence: {line} (source: {url}).")

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
                    "summary": "Customers of peer manufacturers",
                    "notes": findings_notes,
                }
            ],
            "sources": _dedupe_sources(used_sources),
        }

        return AgentResult(ok=True, output=output)
