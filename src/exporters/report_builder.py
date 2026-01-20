from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Iterable, List

from src.registry.entity_registry import Entity, EntityRegistry, Relation


@dataclass(frozen=True)
class ReportSection:
    title: str
    lines: List[str]


def _render_section(section: ReportSection) -> str:
    body = "\n".join(section.lines)
    return f"## {section.title}\n\n{body}\n"


def _render_entities(entities: Iterable[Entity]) -> List[str]:
    lines = []
    for entity in entities:
        line = f"- **{entity.entity_id}** ({entity.entity_type}) {entity.entity_name}"
        if entity.domain:
            line += f" — {entity.domain}"
        lines.append(line)
    return lines or ["- n/v"]


def _render_relations(relations: Iterable[Relation]) -> List[str]:
    lines = []
    for rel in relations:
        lines.append(
            f"- {rel.source_id} → {rel.relation_type} → {rel.target_id}"
        )
    return lines or ["- n/v"]


def build_report(
    registry: EntityRegistry | Dict[str, list],
    run_id: str,
) -> str:
    """Builds a minimal Markdown report derived from validated artifacts."""
    if isinstance(registry, EntityRegistry):
        entities = list(registry.entities_by_id.values())
        relations = list(registry.relations)
    else:
        entities = [Entity.from_dict(entry) for entry in registry.get("entities", [])]
        relations = [Relation.from_dict(entry) for entry in registry.get("relations", [])]

    entities.sort(key=lambda entity: entity.entity_id)
    relations.sort(key=lambda rel: (rel.source_id, rel.relation_type, rel.target_id))

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")

    sections = [
        ReportSection(
            title="Run Summary",
            lines=[
                f"- Run ID: {run_id}",
                f"- Generated at (UTC): {now}",
                f"- Entity count: {len(entities)}",
                f"- Relation count: {len(relations)}",
            ],
        ),
        ReportSection(title="Entities", lines=_render_entities(entities)),
        ReportSection(title="Relations", lines=_render_relations(relations)),
    ]

    header = "# Market Intelligence Report\n\n"
    return header + "\n".join(_render_section(section) for section in sections)
