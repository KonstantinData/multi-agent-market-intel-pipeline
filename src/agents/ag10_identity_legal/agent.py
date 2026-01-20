from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx

from src.agents.common.base_agent import AgentResult, BaseAgent


@dataclass(frozen=True)
class PageEvidence:
    url: str
    text: str


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _to_ascii(text: str) -> str:
    """Enforce ASCII-only outputs (policy requirement).

    - Preserves common German characters via transliteration.
    - Drops all remaining non-ASCII characters deterministically.
    """
    if text is None:
        return ""
    s = str(text)
    # German transliteration
    s = (s.replace("ä", "ae")
           .replace("ö", "oe")
           .replace("ü", "ue")
           .replace("Ä", "Ae")
           .replace("Ö", "Oe")
           .replace("Ü", "Ue")
           .replace("ß", "ss"))
    # Remove remaining non-ascii deterministically
    s = s.encode("ascii", errors="ignore").decode("ascii")
    return s


def _strip_html(html: str) -> str:
    """Very small, dependency-free HTML-to-text extraction."""
    # Remove scripts/styles
    html = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.IGNORECASE)
    html = re.sub(r"<style[\s\S]*?</style>", " ", html, flags=re.IGNORECASE)
    # Replace breaks with newlines
    html = re.sub(r"<(br|p|div|li|tr|h\d)[^>]*>", "\n", html, flags=re.IGNORECASE)
    # Drop tags
    text = re.sub(r"<[^>]+>", " ", html)
    # Decode common entities minimally
    text = text.replace("&nbsp;", " ")
    text = text.replace("&amp;", "&")
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")
    # Normalize whitespace
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


def _find_first_matching_line(text: str, patterns: List[re.Pattern]) -> Optional[str]:
    # Deterministic: scan top-to-bottom, return first match line
    for line in text.split("\n"):
        l = line.strip()
        if not l:
            continue
        for pat in patterns:
            if pat.search(l):
                return l
    return None


def _extract_registration_signals(text: str) -> str:
    tokens = [
        "Handelsregister",
        "Commercial Register",
        "Registergericht",
        "Amtsgericht",
        "HRB",
        "HRA",
    ]
    lines: List[str] = []
    for line in text.split("\n"):
        l = line.strip()
        if not l:
            continue
        if any(t in l for t in tokens):
            lines.append(l)
        if len(lines) >= 3:
            break
    if not lines:
        return "n/v"
    return "; ".join(lines)


def _extract_founding_year(text: str) -> str:
    # ASCII-only patterns
    patterns = [
        re.compile(r"\bfounded\b\s*(?:in\s*)?(19\d{2}|20\d{2})", re.IGNORECASE),
        re.compile(r"\bestablished\b\s*(?:in\s*)?(19\d{2}|20\d{2})", re.IGNORECASE),
        re.compile(r"\bsince\b\s*(19\d{2}|20\d{2})", re.IGNORECASE),
    ]
    for pat in patterns:
        m = pat.search(text)
        if m:
            return m.group(1)
    return "n/v"


def _extract_legal_name_and_form(text: str) -> Tuple[str, str]:
    forms_ordered = [
        "GmbH & Co. KG",
        "GmbH & Co KG",
        "GmbH",
        "AG",
        "UG",
        "KG",
        "OHG",
        "LLC",
        "Inc",
        "Ltd",
        "Limited",
        "PLC",
        "SE",
        "BV",
        "NV",
    ]
    marker_regex = "|".join([re.escape(x) for x in forms_ordered])
    patterns = [re.compile(rf"\b(?:{marker_regex})\b")]

    match_line = _find_first_matching_line(text, patterns)
    if not match_line:
        return "n/v", "n/v"

    candidate = match_line.strip()
    if len(candidate) > 160:
        candidate = candidate[:160]

    legal_form = "n/v"
    for f in forms_ordered:
        if f in candidate:
            legal_form = f
            break

    return candidate, legal_form


class AgentAG10IdentityLegal(BaseAgent):
    step_id = "AG-10"
    agent_name = "ag10_identity_legal"

    def run(
        self,
        case_input: Dict[str, Any],
        meta_case_normalized: Dict[str, Any],
        meta_target_entity_stub: Dict[str, Any],
    ) -> AgentResult:
        company_name = _to_ascii(str(meta_case_normalized.get("company_name_canonical", ""))).strip()
        domain = str(meta_case_normalized.get("web_domain_normalized", "")).strip()
        entity_key = str(meta_case_normalized.get("entity_key", "")).strip()

        if not company_name or not domain or not entity_key:
            return AgentResult(ok=False, output={"error": "missing required meta artifacts"})

        candidate_paths = [
            "/impressum",
            "/imprint",
            "/legal-notice",
            "/legal",
            "/terms",
            "/about",
        ]

        pages = _fetch_pages(domain=domain, paths=candidate_paths)

        legal_name = "n/v"
        legal_form = "n/v"
        founding_year = "n/v"
        registration_signals = "n/v"
        used_sources: List[Dict[str, str]] = []

        accessed_at = _utc_now_iso()

        for ev in pages:
            before_legal_name = legal_name
            before_legal_form = legal_form
            before_founding_year = founding_year
            before_registration_signals = registration_signals

            if legal_name == "n/v" or legal_form == "n/v":
                ln, lf = _extract_legal_name_and_form(ev.text)
                if ln != "n/v":
                    legal_name = ln
                if lf != "n/v":
                    legal_form = lf

            if founding_year == "n/v":
                fy = _extract_founding_year(ev.text)
                if fy != "n/v":
                    founding_year = fy

            if registration_signals == "n/v":
                rs = _extract_registration_signals(ev.text)
                if rs != "n/v":
                    registration_signals = rs

            contributed = (
                (before_legal_name == "n/v" and legal_name != "n/v")
                or (before_legal_form == "n/v" and legal_form != "n/v")
                or (before_founding_year == "n/v" and founding_year != "n/v")
                or (before_registration_signals == "n/v" and registration_signals != "n/v")
            )

            if ev.url and contributed:
                used_sources.append(
                    {
                        "publisher": company_name,
                        "url": ev.url,
                        "accessed_at_utc": accessed_at,
                    }
                )

            if legal_name != "n/v" and legal_form != "n/v" and founding_year != "n/v" and registration_signals != "n/v":
                break

        # Enforce ASCII-only outputs
        legal_name = _to_ascii(legal_name) if legal_name != "n/v" else "n/v"
        legal_form = _to_ascii(legal_form) if legal_form != "n/v" else "n/v"
        registration_signals = _to_ascii(registration_signals) if registration_signals != "n/v" else "n/v"

        seen = set()
        deduped_sources: List[Dict[str, str]] = []
        for s in used_sources:
            u = s.get("url", "")
            if not u or u in seen:
                continue
            seen.add(u)
            deduped_sources.append(s)

        entity_update = {
            "entity_id": "TGT-001",
            "entity_type": "target_company",
            "entity_name": company_name,
            "domain": domain,
            "entity_key": entity_key,
            "legal_name": legal_name,
            "legal_form": legal_form,
            "founding_year": int(founding_year) if founding_year != "n/v" else "n/v",
            "registration_signals": registration_signals,
        }

        notes: List[str] = []
        if legal_name == "n/v" and legal_form == "n/v" and founding_year == "n/v" and registration_signals == "n/v":
            notes.append("No verifiable legal identity evidence found (n/v).")
        else:
            notes.append("Legal identity fields extracted from publicly available pages.")

        output: Dict[str, Any] = {
            "step_meta": {
                "step_id": self.step_id,
                "agent_name": self.agent_name,
            },
            "entities_delta": [entity_update],
            "relations_delta": [],
            "findings": [
                {
                    "summary": "Identity and legal signals extracted",
                    "notes": notes,
                }
            ],
            "sources": deduped_sources,
        }

        return AgentResult(ok=True, output=output)
