from __future__ import annotations

from typing import Any, Dict, List, Sequence, Tuple

from src.agents.common.base_agent import AgentResult, BaseAgent


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

SECONDARY_SOURCES: Tuple[Tuple[str, str], ...] = (
    ("OpenCorporates", "https://opencorporates.com"),
    ("European Business Register", "https://www.ebr.org"),
    ("North Data", "https://www.northdata.com"),
    ("LinkedIn", "https://www.linkedin.com"),
    ("Google News", "https://news.google.com"),
)


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


def _build_primary_sources(domain: str, company_name: str) -> List[Dict[str, str]]:
    base_url = f"https://{domain}"
    urls: List[str] = []
    for path in PRIMARY_PATHS:
        if not path:
            urls.append(base_url)
        else:
            urls.append(f"{base_url}{path}")
    primary = _dedupe_urls(urls)
    if not primary:
        primary = [base_url]
    publisher = company_name or "Official website"
    return [{"publisher": publisher, "url": url} for url in primary]


def _build_secondary_sources() -> List[Dict[str, str]]:
    return [{"publisher": publisher, "url": url} for publisher, url in SECONDARY_SOURCES]


def _build_sources(
    primary: Sequence[Dict[str, str]],
    secondary: Sequence[Dict[str, str]],
) -> List[Dict[str, str]]:
    sources = list(primary) + list(secondary)
    return _dedupe_source_entries(sources)


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


class AgentAG01SourceRegistry(BaseAgent):
    step_id = "AG-01"
    agent_name = "ag01_source_registry"

    def run(
        self,
        case_input: Dict[str, Any],
        meta_case_normalized: Dict[str, Any],
        meta_target_entity_stub: Dict[str, Any],
    ) -> AgentResult:
        company_name = str(meta_case_normalized.get("company_name_canonical", "")).strip()
        domain = str(meta_case_normalized.get("web_domain_normalized", "")).strip()
        entity_key = str(meta_case_normalized.get("entity_key", "")).strip()

        if not company_name or not domain or not entity_key:
            return AgentResult(ok=False, output={"error": "missing required meta artifacts"})

        primary_sources = _build_primary_sources(domain, company_name)
        secondary_sources = _build_secondary_sources()

        source_registry = {
            "primary_sources": primary_sources,
            "secondary_sources": secondary_sources,
            "source_scope_notes": (
                "Primary sources cover official company web properties and legal pages; "
                "secondary sources cover registries, press, and association directories for corroboration."
            ),
        }

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

        sources = _build_sources(primary_sources, secondary_sources)

        output: Dict[str, Any] = {
            "step_meta": {
                "step_id": self.step_id,
                "agent_name": self.agent_name,
            },
            "entities_delta": [],
            "relations_delta": [],
            "source_registry": source_registry,
            "findings": findings,
            "sources": sources,
        }

        return AgentResult(ok=True, output=output)
