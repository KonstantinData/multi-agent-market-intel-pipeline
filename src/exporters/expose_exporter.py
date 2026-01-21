"""
    DESCRIPTION
    -----------
    expose_exporter builds the final Exposé artifacts from the aggregated registry snapshot.

Outputs:
- exports/entities.json: deterministic entity + relation list
- exports/report.md: human-readable markdown report

    """

from __future__ import annotations

from typing import Any, Dict, List


#note: Convert the registry snapshot into a stable JSON export payload.
def build_entities_export(registry_snapshot: Dict[str, Any]) -> Dict[str, Any]:
    """
    #note: The export payload is intentionally stable and schema-friendly for CRM ingestion.
    """
    entities = registry_snapshot.get("entities") or []
    relations = registry_snapshot.get("relations") or []

    #note: Ensure deterministic sorting by entity_id if present.
    entities = sorted([e for e in entities if isinstance(e, dict)], key=lambda x: str(x.get("entity_id") or ""))
    relations = sorted([r for r in relations if isinstance(r, dict)], key=lambda x: str(x))

    return {
        "entities": entities,
        "relations": relations,
        "meta": {
            "namespace": registry_snapshot.get("namespace"),
        },
    }


#note: Render a deterministic, human-readable report.md from the registry snapshot.
def build_report_markdown(registry_snapshot: Dict[str, Any]) -> str:
    """
    #note: This is a baseline Exposé renderer. It is deterministic and audit-friendly.
    """
    entities = registry_snapshot.get("entities") or []
    findings = registry_snapshot.get("findings") or []
    sources = registry_snapshot.get("sources") or []

    #note: Identify the target company entity (TGT-001 by convention).
    target = None
    for e in entities:
        if isinstance(e, dict) and str(e.get("entity_id")) == "TGT-001":
            target = e
            break

    company_name = (target or {}).get("entity_name") or (target or {}).get("legal_name") or "n/v"
    domain = (target or {}).get("domain") or "n/v"

    lines: List[str] = []
    lines.append(f"# Exposé – {company_name}")
    lines.append("")
    lines.append("## Target Company")
    lines.append("")
    lines.append(f"- **Company name:** {company_name}")
    lines.append(f"- **Domain:** {domain}")
    lines.append("")

    #note: Entity overview grouped by entity_type.
    lines.append("## Entities")
    lines.append("")
    by_type: Dict[str, List[Dict[str, Any]]] = {}
    for e in entities:
        if not isinstance(e, dict):
            continue
        t = str(e.get("entity_type") or "n/v")
        by_type.setdefault(t, []).append(e)
    for t in sorted(by_type.keys()):
        lines.append(f"### {t}")
        for e in sorted(by_type[t], key=lambda x: str(x.get('entity_id') or '')):
            eid = e.get("entity_id") or "n/v"
            name = e.get("entity_name") or e.get("name") or "n/v"
            lines.append(f"- `{eid}` – {name}")
        lines.append("")

    lines.append("## Findings")
    lines.append("")
    for f in sorted([x for x in findings if isinstance(x, dict)], key=lambda x: str(x)):
        step_id = f.get("step_id") or "n/v"
        summary = f.get("summary") or "n/v"
        lines.append(f"- **{step_id}**: {summary}")

    lines.append("")
    lines.append("## Sources")
    lines.append("")
    for s in sorted([x for x in sources if isinstance(x, dict)], key=lambda x: str(x)):
        title = s.get("title") or s.get("source_name") or "n/v"
        url = s.get("url") or "n/v"
        lines.append(f"- {title} – {url}")

    lines.append("")
    lines.append("## Registry Stats")
    lines.append("")
    lines.append(f"- Entities: {len([e for e in entities if isinstance(e, dict)])}")
    lines.append(f"- Findings: {len([f for f in findings if isinstance(f, dict)])}")
    lines.append(f"- Sources: {len([s for s in sources if isinstance(s, dict)])}")
    lines.append("")

    return "\n".join(lines)
