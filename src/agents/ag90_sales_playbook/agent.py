from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Tuple
from urllib.parse import quote_plus

import httpx

from src.agent_common.base_agent import AgentResult, BaseAgent
from src.agent_common.step_meta import build_step_meta, utc_now_iso
from src.agent_common.text_normalization import normalize_domain, normalize_whitespace


PROMPT = """Derive sales and negotiation playbook signals from verified sources.
Focus on public pricing, positioning, and procurement signals.
Avoid speculation; only include evidence-backed guidance.
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


def _build_sources(company_name: str, domain: str) -> List[Dict[str, str]]:
    base_url = f"https://{domain}"
    company_paths = [
        "",
        "/pricing",
        "/plans",
        "/quote",
        "/request-quote",
        "/contact",
        "/buy",
        "/shop",
        "/terms",
        "/legal",
        "/procurement",
        "/solutions",
        "/products",
    ]
    company_urls = [f"{base_url}{path}" if path else base_url for path in company_paths]

    company_query = quote_plus(company_name)
    external_urls = [
        ("OpenCorporates", f"https://opencorporates.com/companies?q={company_query}"),
        ("Google News", f"https://news.google.com/search?q={company_query}%20pricing"),
        (
            "PR Newswire",
            f"https://www.prnewswire.com/search/news/?keyword={company_query}%20pricing",
        ),
        (
            "Business Wire",
            f"https://www.businesswire.com/portal/site/home/search/?searchTerm={company_query}%20pricing",
        ),
        ("10times", f"https://10times.com/search?kw={company_query}"),
        ("Eventbrite", f"https://www.eventbrite.com/d/online/{company_query}/"),
    ]

    sources: List[Dict[str, str]] = []
    for url in _dedupe_urls(company_urls):
        sources.append({"publisher": company_name or "Official website", "url": url})

    for publisher, url in external_urls:
        sources.append({"publisher": publisher, "url": url})
    return sources


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


def _extract_sales_lines(text: str) -> List[str]:
    keywords = [
        "pricing",
        "price",
        "quote",
        "request a quote",
        "contact sales",
        "subscription",
        "plan",
        "license",
        "minimum order",
        "moq",
        "lead time",
        "terms",
        "payment",
        "procurement",
        "rfp",
        "trial",
    ]
    lines: List[str] = []
    for line in text.split("\n"):
        line_text = line.strip()
        if not line_text:
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


class AgentAG90SalesPlaybook(BaseAgent):
    step_id = "AG-90"
    agent_name = "ag90_sales_playbook"

    def run(self, case_input: Dict[str, Any]) -> AgentResult:
        started_at_utc = utc_now_iso()

        company_name = normalize_whitespace(
            str(case_input.get("company_name", "")).strip()
        )
        domain_raw = str(case_input.get("web_domain", "")).strip()
        domain = normalize_domain(domain_raw)

        if not company_name or not domain:
            return AgentResult(
                ok=False, output={"error": "missing company_name or web_domain"}
            )

        accessed_at = utc_now_iso()
        sources_catalog = _build_sources(company_name, domain)
        pages = _fetch_pages(sources_catalog)

        signal_lines: List[Tuple[str, str, str]] = []
        for page in pages:
            for line in _extract_sales_lines(page.text):
                signal_lines.append((line, page.url, page.publisher))

        signal_lines = signal_lines[:6]

        used_sources: List[Dict[str, str]] = [
            {
                "publisher": page.publisher or company_name or "Official website",
                "url": page.url,
                "accessed_at_utc": accessed_at,
            }
            for page in pages
        ]
        findings_notes: List[str] = []
        if not signal_lines:
            findings_notes.append(
                "No verifiable pricing, positioning, or procurement signals found in sources reviewed (n/v)."
            )
        else:
            for line, url, _publisher in signal_lines:
                findings_notes.append(f"Sales signal: {line} (source: {url}).")

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
                    "summary": "Sales and negotiation playbook signals",
                    "notes": findings_notes,
                }
            ],
            "sources": _dedupe_sources(used_sources),
        }

        return AgentResult(ok=True, output=output)
