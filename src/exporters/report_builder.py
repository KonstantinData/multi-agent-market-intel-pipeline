from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

from src.exporters.crossref_matrix_exporter import export_crossref_matrix
from src.exporters.entities_exporter import export_entities
from src.exporters.index_builder import build_index
from src.orchestrator.run_context import RunContext
from src.registry.entity_registry import Entity, EntityRegistry, Relation
from src.registry.merger import merge_registry


@dataclass(frozen=True)
class ReportSection:
    title: str
    lines: List[str]


@dataclass(frozen=True)
class AgentSection:
    step_id: str
    agent_name: str
    findings: List[Dict[str, Any]]
    sources: List[Dict[str, Any]]


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


def _render_findings(findings: List[Dict[str, Any]]) -> List[str]:
    if not findings:
        return ["- n/v"]
    lines: List[str] = []
    for finding in findings:
        summary = str(finding.get("summary", "n/v"))
        lines.append(f"- {summary}")
        for note in finding.get("notes", []) or []:
            lines.append(f"  - {note}")
    return lines


def _render_sources(sources: List[Dict[str, Any]]) -> List[str]:
    if not sources:
        return ["- n/v"]
    lines: List[str] = []
    for source in sources:
        publisher = str(source.get("publisher", "source"))
        url = str(source.get("url", "n/v"))
        accessed = source.get("accessed_at_utc")
        suffix = f" (accessed {accessed})" if accessed else ""
        lines.append(f"- {publisher} — {url}{suffix}")
    return lines


def _load_step_outputs(steps_dir: Path) -> List[Dict[str, Any]]:
    outputs: List[Dict[str, Any]] = []
    if not steps_dir.exists():
        return outputs
    for step_path in sorted(steps_dir.iterdir(), key=lambda path: path.name):
        output_path = step_path / "output.json"
        if not output_path.exists():
            continue
        payload = json.loads(output_path.read_text(encoding="utf-8"))
        outputs.append(payload)
    return outputs


def _normalize_relations(relations_delta: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for rel in relations_delta:
        source_id = rel.get("source_id") or rel.get("from_entity_id")
        target_id = rel.get("target_id") or rel.get("to_entity_id") or rel.get("to_entity_key")
        normalized.append(
            {
                "source_id": str(source_id or ""),
                "relation_type": str(rel.get("relation_type", "")),
                "target_id": str(target_id or ""),
                "evidence": list(rel.get("evidence", [])),
            }
        )
    return normalized


def _build_agent_sections(outputs: List[Dict[str, Any]]) -> List[AgentSection]:
    sections: List[AgentSection] = []
    for output in outputs:
        step_meta = output.get("step_meta", {})
        sections.append(
            AgentSection(
                step_id=str(step_meta.get("step_id", "")),
                agent_name=str(step_meta.get("agent_name", "")),
                findings=list(output.get("findings", []) or []),
                sources=list(output.get("sources", []) or []),
            )
        )
    sections.sort(key=lambda section: section.step_id)
    return sections


def _collect_evidence(outputs: List[Dict[str, Any]], relations: Iterable[Relation]) -> List[Dict[str, str]]:
    evidence_entries: List[Dict[str, str]] = []
    seen_keys: set[str] = set()

    for output in outputs:
        for source in output.get("sources", []) or []:
            url = str(source.get("url", ""))
            key = url or json.dumps(source, sort_keys=True)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            evidence_entries.append(
                {
                    "reference": f"EVD-{len(evidence_entries) + 1:03d}",
                    "detail": f"{source.get('publisher', 'source')} — {url}",
                }
            )

    for rel in relations:
        for ev in rel.evidence:
            key = json.dumps(ev, sort_keys=True)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            detail = str(ev.get("detail") or ev.get("url") or ev)
            evidence_entries.append(
                {
                    "reference": f"EVD-{len(evidence_entries) + 1:03d}",
                    "detail": detail,
                }
            )

    return evidence_entries or [{"reference": "EVD-000", "detail": "n/v"}]


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_csv(path: Path, rows: List[Dict[str, Any]], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            normalized = {
                key: (json.dumps(row[key], ensure_ascii=False) if isinstance(row.get(key), (dict, list)) else row.get(key))
                for key in fieldnames
            }
            writer.writerow(normalized)


def _render_agent_section(agent_section: AgentSection) -> ReportSection:
    title = f"{agent_section.step_id} — {agent_section.agent_name}"
    lines = ["**Findings**"]
    lines.extend(_render_findings(agent_section.findings))
    lines.append("")
    lines.append("**Sources**")
    lines.extend(_render_sources(agent_section.sources))
    return ReportSection(title=title, lines=lines)


def build_report(ctx: RunContext) -> str:
    """Builds a Markdown report derived from validated artifacts in the run context."""
    outputs = _load_step_outputs(ctx.steps_dir)

    registry = EntityRegistry()
    for output in outputs:
        entities_delta = list(output.get("entities_delta", []) or [])
        relations_delta = list(output.get("relations_delta", []) or [])
        merge_registry(
            registry=registry,
            entities_delta=entities_delta,
            relations_delta=_normalize_relations(relations_delta),
        )

    entities = list(registry.entities_by_id.values())
    relations = list(registry.relations)
    entities.sort(key=lambda entity: entity.entity_id)
    relations.sort(key=lambda rel: (rel.source_id, rel.relation_type, rel.target_id))

    exported_entities = export_entities(registry, ctx.exports_dir / "entities.json")
    exported_relations = export_crossref_matrix(registry, ctx.exports_dir / "relations.json")
    index_entries = build_index(registry)
    _write_json(ctx.exports_dir / "index.json", index_entries)

    _write_csv(
        ctx.exports_dir / "entities.csv",
        exported_entities,
        ["entity_id", "entity_type", "entity_name", "domain", "entity_key", "attributes"],
    )
    _write_csv(
        ctx.exports_dir / "relations.csv",
        exported_relations,
        ["source_id", "relation_type", "target_id"],
    )
    _write_csv(
        ctx.exports_dir / "index.csv",
        index_entries,
        ["entity_id", "label", "entity_type", "domain"],
    )

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")

    agent_sections = [_render_agent_section(section) for section in _build_agent_sections(outputs)]
    evidence_entries = _collect_evidence(outputs, relations)

    entities_index_lines = [
        f"- {entry['entity_id']} | {entry['entity_type']} | {entry['label']} | {entry.get('domain', 'n/v')}"
        for entry in index_entries
    ]
    if not entities_index_lines:
        entities_index_lines = ["- n/v"]

    relations_index_lines = [
        f"- {rel.source_id} → {rel.relation_type} → {rel.target_id}"
        for rel in relations
    ]
    if not relations_index_lines:
        relations_index_lines = ["- n/v"]

    crossref_lines = [
        "**Entities Index**",
        *entities_index_lines,
        "",
        "**Relations Index**",
        *relations_index_lines,
        "",
        "**Evidence Index**",
        *[f"- {entry['reference']}: {entry['detail']}" for entry in evidence_entries],
    ]

    sections = [
        ReportSection(
            title="Run Summary",
            lines=[
                f"- Run ID: {ctx.run_id}",
                f"- Generated at (UTC): {now}",
                f"- Entity count: {len(entities)}",
                f"- Relation count: {len(relations)}",
            ],
        ),
        ReportSection(title="Entities", lines=_render_entities(entities)),
        ReportSection(title="Relations", lines=_render_relations(relations)),
        ReportSection(
            title="Cross-Reference Indices",
            lines=crossref_lines,
        ),
        ReportSection(
            title="Structured Exports",
            lines=[
                "- exports/entities.json",
                "- exports/entities.csv",
                "- exports/relations.json",
                "- exports/relations.csv",
                "- exports/index.json",
                "- exports/index.csv",
            ],
        ),
    ]

    sections.extend(agent_sections)

    header = "# Market Intelligence Report\n\n"
    return header + "\n".join(_render_section(section) for section in sections)
