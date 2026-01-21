"""
AG-01 Source Registry Agent

Purpose:
- Assemble a deterministic, offline-safe registry of primary and secondary source URLs
  that can be used by downstream research/enrichment agents.
- This step MUST NOT perform network requests or make factual company claims.

Key outputs:
- source_registry.primary_sources
- source_registry.secondary_sources
- sources (deduplicated, stable order)

Design goals:
- Deterministic ordering and deduplication.
- Contract-friendly step output: step_meta, entities_delta, relations_delta, findings, sources.
- Wiring-safe loading via `Agent` alias.
"""

from __future__ import annotations

from typing import Any, Dict, List, Sequence, Tuple

from src.agents.common.base_agent import AgentResult, BaseAgent
from src.agents.common.step_meta import build_step_meta, utc_now_iso


#note: Static list of primary URL paths to cover typical corporate/legal pages.
PRIMARY_PATHS: Tuple[str, ...] = (
    "",
    "/impressum",
    "/imprint",
    "/legal",
    "/legal-notice",
    "/terms",
    "/privacy",
    "/about",
    "/contact",
)

#note: Static list of secondary reference sources (no calls performed; URLs are candidates only).
SECONDARY_SOURCES: Tuple[Tuple[str, str], ...] = (
    ("OpenCorporates", "https://opencorporates.com"),
    ("European Business Register", "https://www.ebr.org"),
    ("North Data", "https://www.northdata.com"),
    ("LinkedIn", "https://www.linkedin.com"),
    ("Google News", "https://news.google.com"),
)


#note: Deterministically deduplicate a list of URLs while preserving first-seen order.
def _dedupe_urls(urls: Sequence[str]) -> List[str]:
    seen = set()
    deduped: List[str] = []
    for url in urls:
        u = url.strip()
        if not u or u in seen:
            continue
        seen.add(u)
        deduped.append(u)
    return deduped


#note: Build primary source entries from the target company's official domain and known legal/info paths.
def _build_primary_sources(
    domain: str,
    company_name: str,
    accessed_at_utc: str,
) -> List[Dict[str, str]]:
    base_url = f"https://{domain}"
    urls: List[str] = []
    for path in PRIMARY_PATHS:
        if not path:
            urls.append(base_url)
        else:
            urls.append(f"{base_url}{path}")

    primary = _dedupe_urls(urls)

    #note: Ensure we always have at least one primary source entry.
    if not primary:
        primary = [base_url]

    publisher = company_name or "Official website"

    return [
        {"publisher": publisher, "url": url, "accessed_at_utc": accessed_at_utc}
        for url in primary
    ]


#note: Build secondary source entries from predefined public registries and indexes.
def _build_secondary_sources(accessed_at_utc: str) -> List[Dict[str, str]]:
    return [
        {"publisher": publisher, "url": url, "accessed_at_utc": accessed_at_utc}
        for publisher, url in SECONDARY_SOURCES
    ]


#note: Merge primary and secondary sources and deduplicate them by URL deterministically.
def _build_sources(
    primary: Sequence[Dict[str, str]],
    secondary: Sequence[Dict[str, str]],
) -> List[Dict[str, str]]:
    sources = list(primary) + list(secondary)
    return _dedupe_source_entries(sources)


#note: Deduplicate source entry objects by URL while preserving stable ordering.
def _dedupe_source_entries(entries: Sequence[Dict[str, str]]) -> List[Dict[str, str]]:
    seen = set()
    deduped: List[Dict[str, str]] = []
    for entry in entries:
        url = entry.get("url", "").strip()
        if not url or url in seen:
            continue
        seen.add(url)
        deduped.append(entry)
    return deduped


#note: AG-01 agent that produces an offline-safe registry of candidate verification sources.
class AgentAG01SourceRegistry(BaseAgent):
    step_id = "AG-01"
    agent_name = "ag01_source_registry"

    #note: Execute source registry assembly using meta artifacts from AG-00 (normalized case + entity stub).
    def run(
        self,
        case_input: Dict[str, Any],
        meta_case_normalized: Dict[str, Any],
        meta_target_entity_stub: Dict[str, Any],
    ) -> AgentResult:
        #note: Capture start timestamp for audit-friendly step_meta.
        started_at_utc = utc_now_iso()

        #note: Read normalized values produced by AG-00 (this is a hard dependency for stable execution).
        company_name = str(meta_case_normalized.get("company_name_canonical", "")).strip()
        domain = str(meta_case_normalized.get("web_domain_normalized", "")).strip()
        entity_key = str(meta_case_normalized.get("entity_key", "")).strip()

        #note: Minimal self-validation; orchestration must treat this as a hard failure.
        if not company_name or not domain or not entity_key:
            return AgentResult(ok=False, output={"error": "missing required meta artifacts"})

        #note: "Accessed at" is a deterministic timestamp captured at step runtime.
        accessed_at_utc = utc_now_iso()

        #note: Build deterministic primary and secondary source sets.
        primary_sources = _build_primary_sources(domain, company_name, accessed_at_utc)
        secondary_sources = _build_secondary_sources(accessed_at_utc)

        #note: Assemble the structured registry payload consumed by downstream steps.
        source_registry = {
            "primary_sources": primary_sources,
            "secondary_sources": secondary_sources,
            "source_scope_notes": (
                "Primary sources cover official company web properties and legal pages; "
                "secondary sources cover registries, press, and association directories for corroboration."
            ),
        }

        #note: Provide non-assertive findings describing what was produced (not company facts).
        findings = [
            {
                "summary": "Source registry assembled",
                "notes": [
                    "Primary sources focus on official web properties suitable for authoritative details.",
                    "Secondary sources include registries and press indexes to corroborate public signals.",
                    "No factual company assertions are made; sources are recommended verification targets.",
                ],
            }
        ]

        #note: Build deduplicated sources array (stable ordering by first-seen URL).
        sources = _build_sources(primary_sources, secondary_sources)

        #note: Capture end timestamp for step_meta completeness.
        finished_at_utc = utc_now_iso()

        #note: Build contract-friendly output (no entities/relations emitted by this step).
        output: Dict[str, Any] = {
            "step_meta": build_step_meta(
                case_input=case_input,
                step_id=self.step_id,
                agent_name=self.agent_name,
                started_at_utc=started_at_utc,
                finished_at_utc=finished_at_utc,
            ),
            "entities_delta": [],
            "relations_delta": [],
            "source_registry": source_registry,
            "findings": findings,
            "sources": sources,
        }

        #note: Return success so orchestrator can persist artifacts deterministically.
        return AgentResult(ok=True, output=output)


#note: Wiring-safe alias for dynamic loaders expecting `Agent` symbol in this module.
Agent = AgentAG01SourceRegistry
