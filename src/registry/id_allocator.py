from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict

from src.registry.entity_registry import EntityRegistry


_PREFIXES = {
    "target_company": "TGT",
    "manufacturer": "MFR",
    "customer": "CUS",
    "location_site": "LOC",
    "subsidiary": "SUB",
}


@dataclass
class IdAllocator:
    counters: Dict[str, int] = field(default_factory=dict)

    def _seed_from_registry(self, registry: EntityRegistry) -> None:
        for entity_id in registry.entities_by_id:
            parts = entity_id.split("-")
            if len(parts) != 2:
                continue
            prefix, number = parts
            if not number.isdigit():
                continue
            current = self.counters.get(prefix, 0)
            self.counters[prefix] = max(current, int(number))

    def allocate(self, entity_type: str, registry: EntityRegistry) -> str:
        if not self.counters:
            self._seed_from_registry(registry)

        if entity_type == "target_company":
            return "TGT-001"

        prefix = _PREFIXES.get(entity_type, "ENT")
        current = self.counters.get(prefix, 0) + 1
        self.counters[prefix] = current
        return f"{prefix}-{current:03d}"
