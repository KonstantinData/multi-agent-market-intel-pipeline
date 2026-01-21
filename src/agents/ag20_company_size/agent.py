from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from src.agent_common.base_agent import AgentResult, BaseAgent
from src.agent_common.step_meta import build_step_meta, utc_now_iso


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


def _normalize_number(token: str) -> str:
    return token.replace(",", "").strip()


def _has_guess_language(text: str) -> bool:
    return bool(re.search(r"\b(approx|approximately|about|around|estimated|estimate)\b", text, re.IGNORECASE))


def _extract_employee_range(line: str) -> Optional[str]:
    lowered = line.lower()
    if not re.search(r"\b(employees|employee|staff|people|team|headcount)\b", lowered):
        return None
    if _has_guess_language(lowered):
        return None

    range_match = re.search(
        r"(\d{1,3}(?:,\d{3})*)\s*(?:-|to)\s*(\d{1,3}(?:,\d{3})*)\s*(?:employees|staff|people|team|headcount)",
        lowered,
    )
    if range_match:
        start = _normalize_number(range_match.group(1))
        end = _normalize_number(range_match.group(2))
        return f"{start}-{end} employees"

    plus_match = re.search(
        r"(?:over|more than|at least)\s*(\d{1,3}(?:,\d{3})*)\s*(?:employees|staff|people|team|headcount)",
        lowered,
    )
    if plus_match:
        start = _normalize_number(plus_match.group(1))
        return f"{start}+ employees"

    plus_sign_match = re.search(
        r"(\d{1,3}(?:,\d{3})*)\s*\+\s*(?:employees|staff|people|team|headcount)",
        lowered,
    )
    if plus_sign_match:
        start = _normalize_number(plus_sign_match.group(1))
        return f"{start}+ employees"

    single_match = re.search(
        r"(\d{1,3}(?:,\d{3})*)\s*(?:employees|staff|people|team|headcount)",
        lowered,
    )
    if single_match:
        count = _normalize_number(single_match.group(1))
        return f"{count} employees"

    return None


def _extract_revenue_band(line: str) -> Optional[str]:
    lowered = line.lower()
    if not re.search(r"\b(revenue|turnover|sales)\b", lowered):
        return None
    if _has_guess_language(lowered):
        return None

    currency_range = re.search(
        r"([€$£]|eur|usd|gbp)?\s*(\d+(?:[\.,]\d+)?)\s*(m|bn|b|million|billion)?\s*"
        r"(?:-|to)\s*([€$£]|eur|usd|gbp)?\s*(\d+(?:[\.,]\d+)?)\s*(m|bn|b|million|billion)?",
        lowered,
    )
    if currency_range:
        cur = currency_range.group(1) or currency_range.group(4) or ""
        start = currency_range.group(2)
        end = currency_range.group(5)
        unit = currency_range.group(3) or currency_range.group(6) or ""
        unit = unit.replace("million", "m").replace("billion", "b")
        cur = cur.upper() if cur else ""
        if cur and cur.isalpha():
            cur = cur.upper()
        return f"{cur}{start}-{end}{unit}".strip()

    return None


def _extract_market_scope(line: str) -> Optional[str]:
    lowered = line.lower()
    if re.search(r"\b(global|worldwide|international|multinational)\b", lowered):
        return "global"
    if re.search(r"\b(emea|apac|americas|europe|asia|north america|south america)\b", lowered):
        return "regional"
    if re.search(r"\b(national|nationwide)\b", lowered):
        return "national"
    if re.search(r"\b(local|regional)\b", lowered):
        return "local"
    return None


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


def _openai_api_key() -> str:
    return os.getenv("OPENAI_KEY", "").strip() or os.getenv("OPENAI_API_KEY", "").strip()


def _openai_extract_signals(text: str, api_key: str, timeout_s: float = 20.0) -> Dict[str, str]:
    if not text.strip():
        return {
            "employee_range": "n/v",
            "revenue_band": "n/v",
            "market_scope_signal": "n/v",
        }

    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "system",
                "content": (
                    "Extract company size signals only from the provided text. "
                    "Return JSON with keys: employee_range, revenue_band, market_scope_signal. "
                    "Use 'n/v' if the text does not explicitly state the signal. "
                    "No estimates or guesses."
                ),
            },
            {"role": "user", "content": text[:12000]},
        ],
        "temperature": 0,
    }

    headers = {"Authorization": f"Bearer {api_key}"}
    with httpx.Client(timeout=timeout_s) as client:
        resp = client.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    content = (
        data.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
        .strip()
    )
    if not content:
        return {
            "employee_range": "n/v",
            "revenue_band": "n/v",
            "market_scope_signal": "n/v",
        }
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return {
            "employee_range": "n/v",
            "revenue_band": "n/v",
            "market_scope_signal": "n/v",
        }

    return {
        "employee_range": str(parsed.get("employee_range", "n/v")).strip() or "n/v",
        "revenue_band": str(parsed.get("revenue_band", "n/v")).strip() or "n/v",
        "market_scope_signal": str(parsed.get("market_scope_signal", "n/v")).strip() or "n/v",
    }


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
            "/about-us",
            "/company",
            "/profile",
            "/overview",
            "/facts",
            "/facts-and-figures",
            "/company-profile",
            "/careers",
            "/jobs",
        ]

        pages = _fetch_pages(domain=domain, paths=candidate_paths)

        employee_range = "n/v"
        revenue_band = "n/v"
        market_scope_signal = "n/v"
        used_sources: List[Dict[str, str]] = []
        evidence_lines: List[str] = []
        evidence_urls: List[str] = []
        accessed_at = _utc_now_iso()

        for ev in pages:
            contributed = False
            for line in ev.text.split("\n"):
                l = _to_ascii(line.strip())
                if not l:
                    continue

                if re.search(r"\b(employees?|staff|people|team|headcount|revenue|turnover|sales|global|worldwide|international|multinational|national|nationwide|local|regional|emea|apac|americas|europe|asia)\b", l, re.IGNORECASE):
                    evidence_lines.append(f"URL: {ev.url}\nLINE: {l}")
                    if ev.url:
                        evidence_urls.append(ev.url)

                if employee_range == "n/v":
                    candidate = _extract_employee_range(l)
                    if candidate:
                        employee_range = candidate
                        contributed = True

                if revenue_band == "n/v":
                    candidate = _extract_revenue_band(l)
                    if candidate:
                        revenue_band = candidate
                        contributed = True

                if market_scope_signal == "n/v":
                    candidate = _extract_market_scope(l)
                    if candidate:
                        market_scope_signal = candidate
                        contributed = True

                if employee_range != "n/v" and revenue_band != "n/v" and market_scope_signal != "n/v":
                    break

            if ev.url and contributed:
                used_sources.append(
                    {
                        "publisher": company_name or "Official website",
                        "url": ev.url,
                        "accessed_at_utc": accessed_at,
                    }
                )

            if employee_range != "n/v" and revenue_band != "n/v" and market_scope_signal != "n/v":
                break

        api_key = _openai_api_key()
        if api_key and (employee_range == "n/v" or revenue_band == "n/v" or market_scope_signal == "n/v"):
            try:
                llm_text = "\n\n".join(evidence_lines[:200])
                llm_result = _openai_extract_signals(llm_text, api_key=api_key)
                if employee_range == "n/v" and llm_result.get("employee_range") not in ("", "n/v"):
                    employee_range = llm_result["employee_range"]
                if revenue_band == "n/v" and llm_result.get("revenue_band") not in ("", "n/v"):
                    revenue_band = llm_result["revenue_band"]
                if market_scope_signal == "n/v" and llm_result.get("market_scope_signal") not in ("", "n/v"):
                    market_scope_signal = llm_result["market_scope_signal"]
            except Exception:
                pass

        if (employee_range != "n/v" or revenue_band != "n/v" or market_scope_signal != "n/v") and evidence_urls:
            for url in evidence_urls:
                used_sources.append(
                    {
                        "publisher": company_name or "Official website",
                        "url": url,
                        "accessed_at_utc": accessed_at,
                    }
                )

        if used_sources:
            findings_notes = [
                "Size signals extracted from official company pages.",
            ]
        else:
            findings_notes = [
                "No verifiable size signals found; all fields set to n/v.",
            ]

        target_update = {
            "entity_id": "TGT-001",
            "entity_type": "target_company",
            "entity_name": _to_ascii(str(meta_target_entity_stub.get("entity_name", company_name))),
            "domain": str(meta_target_entity_stub.get("domain", domain)),
            "entity_key": str(meta_target_entity_stub.get("entity_key", entity_key)),
            "employee_range": employee_range,
            "revenue_band": revenue_band,
            "market_scope_signal": market_scope_signal,
        }

        finished_at_utc = utc_now_iso()

        output: Dict[str, Any] = {
            "step_meta": build_step_meta(
                case_input=case_input,
                step_id=self.step_id,
                agent_name=self.agent_name,
                started_at_utc=started_at_utc,
                finished_at_utc=finished_at_utc,
            ),
            "entities_delta": [target_update],
            "findings": [
                {
                    "summary": "Company size signals reviewed",
                    "notes": findings_notes,
                }
            ],
            "sources": _dedupe_sources(used_sources),
        }

        return AgentResult(ok=True, output=output)
