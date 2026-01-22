"""
DESCRIPTION
-----------
Agent AG-10 (Identity / Legal) extracts evidence-bound legal identity signals AND
basic contact/location/social discovery signals for the target company.

Why we enrich more fields already in AG-10:
- Downstream agents can search better if they already have:
  - structured address signals (street/city/zip)
  - phone signal
  - social links (LinkedIn/Facebook/Twitter)

IMPORTANT:
- This is NOT the CRM export step. HubSpot sync happens at the very end of the full run.
- Evidence-only policy: if not explicitly present in evidence -> "n/v"
- Deterministic behavior: stable parsing rules, stable output structure
- No secret leakage: OPEN-AI-KEY is read from environment only

Output structure (contract-friendly):
- step_meta
- entities_delta / relations_delta
- findings
- sources / field_sources
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx

from src.agents.common.base_agent import AgentResult, BaseAgent
from src.agents.common.step_meta import build_step_meta, utc_now_iso


# NOTE: Minimal evidence container used to anchor extracted text to its originating URL.
@dataclass(frozen=True)
class PageEvidence:
    url: str
    text: str


# NOTE: Generates a UTC timestamp in ISO-8601 format (Z suffix) deterministically for metadata fields.
def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


# NOTE: Enforces ASCII-only output by transliterating German characters and stripping remaining non-ASCII chars.
def _to_ascii(text: str) -> str:
    """Enforce ASCII-only outputs (policy requirement)."""
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
    s = s.encode("ascii", errors="ignore").decode("ascii")
    return s


# NOTE: Dependency-free HTML-to-text conversion for basic evidence extraction.
def _strip_html(html: str) -> str:
    """Small, dependency-free HTML-to-text extraction."""
    html = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.IGNORECASE)
    html = re.sub(r"<style[\s\S]*?</style>", " ", html, flags=re.IGNORECASE)
    html = re.sub(r"<(br|p|div|li|tr|h\d)[^>]*>", "\n", html, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", html)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = re.sub(r"[\t\r ]+", " ", text)
    text = re.sub(r"\n+", "\n", text)
    return text.strip()


# NOTE: Fetches HTML pages from well-known paths under the target domain and returns extracted plain-text evidences.
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


# NOTE: Scans text line-by-line and returns the first line matching any pattern (deterministic order).
def _find_first_matching_line(text: str, patterns: List[re.Pattern]) -> Optional[str]:
    for line in text.split("\n"):
        l = line.strip()
        if not l:
            continue
        for pat in patterns:
            if pat.search(l):
                return l
    return None


# NOTE: Extracts up to 3 registration-related lines from text.
def _extract_registration_signals(text: str) -> str:
    tokens = ["Handelsregister", "Commercial Register", "Registergericht", "Amtsgericht", "HRB", "HRA"]
    lines: List[str] = []
    for line in text.split("\n"):
        l = line.strip()
        if not l:
            continue
        if any(t in l for t in tokens):
            lines.append(l)
        if len(lines) >= 3:
            break
    return "n/v" if not lines else "; ".join(lines)


# NOTE: Attempts to extract a founding year using deterministic regex patterns; otherwise returns "n/v".
def _extract_founding_year(text: str) -> str:
    patterns = [
        re.compile(r"\bfounded\b\s*(?:in\s*)?(19\d{2}|20\d{2})", re.IGNORECASE),
        re.compile(r"\bestablished\b\s*(?:in\s*)?(19\d{2}|20\d{2})", re.IGNORECASE),
        re.compile(r"\bsince\b\s*(19\d{2}|20\d{2})", re.IGNORECASE),
        re.compile(r"\bgegruendet\b\s*(?:im\s*)?(19\d{2}|20\d{2})", re.IGNORECASE),
        re.compile(r"\bseit\b\s*(19\d{2}|20\d{2})", re.IGNORECASE),
    ]
    for pat in patterns:
        m = pat.search(text)
        if m:
            return m.group(1)
    return "n/v"


# NOTE: Tries to find plausible legal name and legal form from a line containing known legal-form tokens.
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


# NOTE: Extracts phone number deterministically from common patterns (Tel/Phone).
def _extract_phone_number(text: str) -> str:
    phone_markers = ["tel", "telefon", "phone", "mobile", "fax"]
    for line in text.split("\n"):
        l = _to_ascii(line).strip()
        if not l:
            continue
        low = l.lower()
        if any(m in low for m in phone_markers):
            # simple phone normalization: keep digits, +, spaces, /, -
            m = re.search(r"(\+?\d[\d\s\/\-()]{6,}\d)", l)
            if m:
                cand = m.group(1).strip()
                if len(cand) > 40:
                    cand = cand[:40]
                return cand
    return "n/v"


# NOTE: Extracts postal code + city from German-style patterns: "12345 City".
def _extract_postal_city(text: str) -> Tuple[str, str]:
    for line in text.split("\n"):
        l = _to_ascii(line).strip()
        if not l:
            continue
        m = re.search(r"\b(\d{5})\s+([A-Za-z][A-Za-z \-]{1,40})\b", l)
        if m:
            postal = m.group(1).strip()
            city = m.group(2).strip()
            if len(city) > 60:
                city = city[:60]
            return postal, city
    return "n/v", "n/v"


# NOTE: Extracts a best-effort street line (evidence-only) using common street tokens.
def _extract_street_address(text: str) -> str:
    street_tokens = [
        "strasse", "straße", "street", "st.", "weg", "allee", "platz", "ring", "gasse", "damm",
    ]
    for line in text.split("\n"):
        raw = line.strip()
        l = _to_ascii(raw).strip()
        if not l:
            continue
        low = l.lower()
        if any(tok in low for tok in street_tokens):
            # requires at least one number in the line (house number)
            if re.search(r"\b\d{1,4}\b", l):
                if len(l) > 120:
                    l = l[:120]
                return l
    return "n/v"


# NOTE: Extracts social URLs/handles deterministically from evidence text (no guessing).
def _extract_socials(text: str) -> Dict[str, str]:
    t = _to_ascii(text)
    facebook = "n/v"
    linkedin = "n/v"
    twitter_handle = "n/v"
    google_plus = "n/v"

    # Facebook URL
    m = re.search(r"(https?://(www\.)?facebook\.com/[A-Za-z0-9.\-_/]+)", t, re.IGNORECASE)
    if m:
        facebook = m.group(1)[:200]

    # LinkedIn company page URL
    m = re.search(r"(https?://(www\.)?linkedin\.com/company/[A-Za-z0-9.\-_/]+)", t, re.IGNORECASE)
    if m:
        linkedin = m.group(1)[:200]

    # Twitter/X: detect handle or URL
    m = re.search(r"(https?://(www\.)?(twitter\.com|x\.com)/[A-Za-z0-9_]+)", t, re.IGNORECASE)
    if m:
        url = m.group(1)[:200]
        # store as handle if possible
        hm = re.search(r"/([A-Za-z0-9_]+)$", url)
        twitter_handle = f"@{hm.group(1)}" if hm else url

    # Google Plus URL (historical)
    m = re.search(r"(https?://plus\.google\.com/[A-Za-z0-9.\-_/]+)", t, re.IGNORECASE)
    if m:
        google_plus = m.group(1)[:200]

    return {
        "facebook_company_page": facebook,
        "linkedin_company_page": linkedin,
        "twitter_handle": twitter_handle,
        "google_plus_page": google_plus,
    }


# NOTE: Internal guard to avoid re-loading .env multiple times across calls.
_DOTENV_LOADED = False


# NOTE: Minimal .env loader (no dependencies). Loads only if values are not already present in os.environ.
def _load_dotenv_if_present() -> None:
    global _DOTENV_LOADED
    if _DOTENV_LOADED:
        return
    _DOTENV_LOADED = True

    candidates: List[Path] = [Path.cwd() / ".env"]
    here = Path(__file__).resolve()
    for i, parent in enumerate(here.parents):
        if i > 8:
            break
        candidates.append(parent / ".env")

    dotenv_path = next((p for p in candidates if p.is_file()), None)
    if not dotenv_path:
        return

    try:
        for raw in dotenv_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.lower().startswith("export "):
                line = line[7:].strip()
            if "=" not in line:
                continue

            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip()

            if len(v) >= 2 and ((v[0] == v[-1] == '"') or (v[0] == v[-1] == "'")):
                v = v[1:-1]

            if k and k not in os.environ:
                os.environ[k] = v
    except Exception:
        return


# NOTE: Fetches the OpenAI API key from env; primary required name is OPEN-AI-KEY (fallback: OPENAI_API_KEY).
def _openai_api_key() -> str:
    key = os.getenv("OPEN-AI-KEY", "").strip() or os.getenv("OPENAI_API_KEY", "").strip()
    if key:
        return key
    _load_dotenv_if_present()
    return os.getenv("OPEN-AI-KEY", "").strip() or os.getenv("OPENAI_API_KEY", "").strip()


# NOTE: Normalizes text for contains-checks by reducing to lowercase alphanumerics and collapsing whitespace.
def _normalize_for_contains(s: str) -> str:
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


# NOTE: Collects compact, URL-anchored evidence lines for deterministic extraction and auditability.
def _collect_evidence_lines(pages: List[PageEvidence], max_lines: int = 180) -> Tuple[str, List[str]]:
    keyword_re = re.compile(
        r"\b("
        r"handelsregister|commercial register|registergericht|amtsgericht|hrb|hra|"
        r"impressum|imprint|legal|terms|register|registration|incorporated|"
        r"founded|established|since|gegruendet|seit|"
        r"gmbh|ag|ug|kg|ohg|llc|inc\b|ltd\b|limited\b|plc\b|se\b|bv\b|nv\b|"
        r"tel|telefon|phone|contact|kontakt|address|adresse|"
        r"linkedin|facebook|twitter|x\.com|plus\.google\.com"
        r")\b",
        re.IGNORECASE,
    )

    out: List[str] = []
    urls: List[str] = []

    for ev in pages:
        lines = [(_to_ascii(l).strip()) for l in ev.text.split("\n")]
        lines = [l for l in lines if l]
        if not lines:
            continue

        hit_idxs: List[int] = []
        for i, l in enumerate(lines):
            if keyword_re.search(l):
                hit_idxs.append(i)

        picked: List[int] = []
        for i in hit_idxs:
            for j in (i - 1, i, i + 1):
                if 0 <= j < len(lines) and j not in picked:
                    picked.append(j)

        if not picked:
            picked = list(range(min(25, len(lines))))

        for idx in picked:
            if len(out) >= max_lines:
                break
            l = lines[idx]
            if len(l) > 240:
                l = l[:240]
            out.append(f"URL: {ev.url}\nLINE: {l}")
            if ev.url:
                urls.append(ev.url)

        if len(out) >= max_lines:
            break

    evidence_text = "\n\n".join(out).strip()

    seen = set()
    deduped_urls: List[str] = []
    for u in urls:
        if u and u not in seen:
            seen.add(u)
            deduped_urls.append(u)

    return evidence_text, deduped_urls


# NOTE: Calls OpenAI Chat Completions with strict instructions to extract ONLY evidence-bound JSON fields (legal identity).
def _openai_extract_legal_identity(evidence_text: str, api_key: str, timeout_s: float = 25.0) -> Dict[str, Any]:
    user_content = evidence_text.strip() or "NO_EVIDENCE"

    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a strict information extractor. Extract ONLY from the provided evidence. "
                    "Return JSON ONLY (no markdown, no commentary) with keys: "
                    "legal_name, legal_form, founding_year, registration_signals. "
                    "Rules: "
                    "- If a field is not explicitly stated in evidence, output 'n/v'. "
                    "- Do NOT guess or infer. "
                    "- Do NOT invent registration numbers or identifiers. "
                    "- registration_signals must be copied from evidence lines and should include a register marker "
                    "  like Handelsregister/Registergericht/Amtsgericht/HRB/HRA if present; otherwise 'n/v'. "
                    "- founding_year must be a 4-digit year (e.g., 1998) or 'n/v'."
                ),
            },
            {"role": "user", "content": user_content[:12000]},
        ],
        "temperature": 0,
    }

    headers = {"Authorization": f"Bearer {api_key}"}
    with httpx.Client(timeout=timeout_s) as client:
        resp = client.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    content = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
    if not content:
        raise ValueError("empty OpenAI response")

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError("OpenAI response is not valid JSON") from e

    if not isinstance(parsed, dict):
        raise ValueError("OpenAI response JSON is not an object")

    return parsed


# NOTE: Sanitizes LLM outputs by verifying that extracted values are explicitly contained in evidence text.
def _sanitize_llm_outputs(parsed: Dict[str, Any], evidence_text: str) -> Tuple[str, str, str, str]:
    ev_norm = _normalize_for_contains(evidence_text)

    raw_legal_name = _to_ascii(str(parsed.get("legal_name", "n/v"))).strip() or "n/v"
    raw_legal_form = _to_ascii(str(parsed.get("legal_form", "n/v"))).strip() or "n/v"
    raw_founding_year = _to_ascii(str(parsed.get("founding_year", "n/v"))).strip() or "n/v"
    raw_registration = _to_ascii(str(parsed.get("registration_signals", "n/v"))).strip() or "n/v"

    if raw_legal_name != "n/v" and _normalize_for_contains(raw_legal_name) not in ev_norm:
        raw_legal_name = "n/v"

    if raw_legal_form != "n/v" and _normalize_for_contains(raw_legal_form) not in ev_norm:
        raw_legal_form = "n/v"

    if raw_founding_year != "n/v":
        m = re.search(r"\b(18\d{2}|19\d{2}|20\d{2})\b", raw_founding_year)
        year = m.group(1) if m else None
        if not year or year not in evidence_text:
            raw_founding_year = "n/v"
        else:
            raw_founding_year = year

    if raw_registration != "n/v":
        markers = ("handelsregister", "commercial register", "registergericht", "amtsgericht", "hrb", "hra")
        lowered = raw_registration.lower()
        if not any(marker in lowered for marker in markers):
            raw_registration = "n/v"
        if raw_registration != "n/v" and _normalize_for_contains(raw_registration) not in ev_norm:
            raw_registration = "n/v"

    if raw_legal_name != "n/v" and len(raw_legal_name) > 160:
        raw_legal_name = raw_legal_name[:160]
    if raw_registration != "n/v" and len(raw_registration) > 400:
        raw_registration = raw_registration[:400]

    return raw_legal_name, raw_legal_form, raw_founding_year, raw_registration


# NOTE: De-duplicates sources deterministically by URL (first-seen wins).
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


# NOTE: Builds per-field source mapping so validators and exporters can attribute values to URLs.
def _build_field_sources(values: Dict[str, Any], evidence_urls: List[str]) -> Dict[str, List[Dict[str, str]]]:
    def _sources_for(value: Any) -> List[Dict[str, str]]:
        if value in (None, "", "n/v"):
            return []
        return [{"url": url} for url in evidence_urls if url]

    out: Dict[str, List[Dict[str, str]]] = {}
    for k, v in values.items():
        out[k] = _sources_for(v)
    return out


# NOTE: AG-10 agent implementation; produces entities_delta enrichment for legal identity + contact/social signals.
class AgentAG10IdentityLegal(BaseAgent):
    step_id = "AG-10"
    agent_name = "ag10_identity_legal"

    # NOTE: Executes the AG-10 step using normalized case metadata, evidence extraction, and strict parsing.
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

        api_key = _openai_api_key()
        if not api_key:
            return AgentResult(
                ok=False,
                output={"error": "missing OPEN-AI-KEY in environment (.env) - AG-10 requires LLM access"},
            )

        candidate_paths = [
            "/impressum",
            "/imprint",
            "/legal-notice",
            "/legal",
            "/terms",
            "/about",
            "/kontakt",
            "/contact",
        ]

        pages = _fetch_pages(domain=domain, paths=candidate_paths)
        evidence_text, evidence_urls = _collect_evidence_lines(pages)

        # --- Legal extraction via OpenAI (evidence-bound) ---
        try:
            parsed = _openai_extract_legal_identity(evidence_text=evidence_text, api_key=api_key)
        except Exception as e:
            return AgentResult(ok=False, output={"error": f"openai_extraction_failed: {type(e).__name__}"})

        legal_name, legal_form, founding_year_s, registration_signals = _sanitize_llm_outputs(
            parsed=parsed,
            evidence_text=evidence_text,
        )

        # --- Deterministic fallbacks from raw evidence text if LLM returns n/v ---
        if pages and (legal_name == "n/v" or legal_form == "n/v"):
            for ev in pages:
                ln, lf = _extract_legal_name_and_form(ev.text)
                if legal_name == "n/v" and ln != "n/v":
                    legal_name = _to_ascii(ln).strip()
                if legal_form == "n/v" and lf != "n/v":
                    legal_form = _to_ascii(lf).strip()
                if legal_name != "n/v" and legal_form != "n/v":
                    break

        if pages and founding_year_s == "n/v":
            for ev in pages:
                fy = _extract_founding_year(ev.text)
                if fy != "n/v":
                    founding_year_s = fy
                    break

        if pages and registration_signals == "n/v":
            for ev in pages:
                rs = _extract_registration_signals(ev.text)
                if rs != "n/v":
                    registration_signals = _to_ascii(rs).strip()
                    break

        founding_year: Any
        if founding_year_s != "n/v":
            try:
                founding_year = int(founding_year_s)
            except Exception:
                founding_year = "n/v"
        else:
            founding_year = "n/v"

        # --- NEW: contact/location/social extraction (deterministic, evidence-only) ---
        full_text = "\n".join([p.text for p in pages]) if pages else ""
        street_address = _extract_street_address(full_text)
        postal_code, city = _extract_postal_city(full_text)
        phone_number = _extract_phone_number(full_text)
        socials = _extract_socials(full_text)

        # Fields typically not reliably extractable in AG-10 without dedicated research steps
        state_region = "n/v"
        parent_company_id = "n/v"
        industry = "n/v"
        description = "n/v"

        # If we produce any claimed fields, ensure we have at least one evidence URL anchor.
        claimed_values = [
            legal_name, legal_form, founding_year, registration_signals,
            street_address, city, postal_code, phone_number,
            socials.get("facebook_company_page", "n/v"),
            socials.get("linkedin_company_page", "n/v"),
            socials.get("twitter_handle", "n/v"),
            socials.get("google_plus_page", "n/v"),
        ]
        has_claim = any(v not in (None, "", "n/v") for v in claimed_values)

        accessed_at = _utc_now_iso()
        if has_claim and not evidence_urls:
            evidence_urls = [f"https://{domain}/"]

        used_sources: List[Dict[str, str]] = []
        if has_claim:
            for url in evidence_urls:
                used_sources.append({"publisher": company_name, "url": url, "accessed_at_utc": accessed_at})

        # --- Entity enrichment for downstream agents (NOT CRM export) ---
        entity_update = {
            "entity_id": "TGT-001",
            "entity_type": "target_company",
            "entity_name": company_name,
            "domain": domain,
            "entity_key": entity_key,
            "legal_name": legal_name,
            "legal_form": legal_form,
            "founding_year": founding_year,
            "registration_signals": registration_signals,

            # NEW: contact/location (downstream search helper fields)
            "street_address": street_address,
            "city": city,
            "postal_code": postal_code,
            "state_region": state_region,
            "phone_number": phone_number,

            # NEW: corporate parent pointer (not evidence-extracted here)
            "parent_company_id": parent_company_id,

            # NEW: industry/description baseline placeholders (to be filled in later steps)
            "industry": industry,
            "description": description,

            # NEW: socials
            "facebook_company_page": socials.get("facebook_company_page", "n/v"),
            "google_plus_page": socials.get("google_plus_page", "n/v"),
            "linkedin_company_page": socials.get("linkedin_company_page", "n/v"),
            "twitter_handle": socials.get("twitter_handle", "n/v"),
        }

        # --- Field sources for auditability ---
        field_source_values = {
            "legal_name": legal_name,
            "legal_form": legal_form,
            "founding_year": founding_year,
            "registration_signals": registration_signals,
            "street_address": street_address,
            "city": city,
            "postal_code": postal_code,
            "state_region": state_region,
            "phone_number": phone_number,
            "parent_company_id": parent_company_id,
            "industry": industry,
            "description": description,
            "facebook_company_page": socials.get("facebook_company_page", "n/v"),
            "google_plus_page": socials.get("google_plus_page", "n/v"),
            "linkedin_company_page": socials.get("linkedin_company_page", "n/v"),
            "twitter_handle": socials.get("twitter_handle", "n/v"),
        }
        field_sources = _build_field_sources(values=field_source_values, evidence_urls=evidence_urls)

        # --- Findings summary ---
        notes: List[str] = []
        if not has_claim:
            notes.append("No verifiable identity/contact evidence found (n/v).")
        else:
            notes.append("Legal identity and contact/social signals extracted from publicly available pages.")

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
            "findings": [{"summary": "Identity/legal + contact/social signals extracted", "notes": notes}],
            "sources": _dedupe_sources(used_sources),
            "field_sources": field_sources,
        }

        return AgentResult(ok=True, output=output)


# NOTE: Wiring-safe alias for dynamic loaders expecting `Agent` symbol in this module.
Agent = AgentAG10IdentityLegal

