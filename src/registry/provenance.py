from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class FieldProvenance:
    """Tracks evidence for an entity field."""

    field_name: str
    sources: List[Dict[str, str]] = field(default_factory=list)
    last_updated_step: str = "n/v"

    def add_sources(self, new_sources: List[Dict[str, str]], step_id: str) -> None:
        self.sources.extend(new_sources)
        self.last_updated_step = step_id
