# ADR-002: Contract‑Gated Validation

**Status:** Angenommen

## Hintergrund

Pipeline‑Schritte produzieren Artefakte mit unterschiedlichen Strukturen (z. B. Rohdaten, normalisierte Entities, Scores). Ohne klare Contracts entstehen stille Fehler: Downstream‑Steps nehmen falsche Felder oder Formate an. Zusätzlich müssen Datenqualitätsanforderungen (Pflichtfelder, Wertebereiche, Schema‑Versionen) vor dem Übergang geprüft werden.

## Entscheidung

Jedes Artefakt wird vor der Weiterverarbeitung durch einen **Contract‑Gate** geprüft:

- **Schema‑Validierung** (z. B. Pflichtfelder, Typen, Versionen).
- **Inhalts‑Constraints** (z. B. Score‑Ranges, Referenz‑IDs müssen existieren).
- **Versionierung** der Contracts, sodass Breaking Changes explizit und kontrolliert werden.

Nur Artefakte, die den Contract erfüllen, werden downstream weitergegeben; fehlerhafte Artefakte werden markiert und isoliert.

## Konsequenzen

- **Qualitätssicherung:** frühzeitiges Abfangen von fehlerhaften Daten reduziert Folgefehler.
- **Stabilität:** Downstream‑Tasks können sich auf valide Inputs verlassen.
- **Erhöhter Aufwand:** Contracts müssen gepflegt und bei Änderungen versioniert werden.
- **Transparenz:** Validierungsfehler sind nachvollziehbar und können in Monitoring/Reports aufgenommen werden.

## Alternativen / Non‑Goals

- **Alternative:** Validierung nur in Downstream‑Tasks. Abgelehnt, da Fehler später und schwerer debuggt werden.
- **Alternative:** informelle Validierung via unit tests. Abgelehnt, da Runtime‑Validation fehlt.
- **Non‑Goal:** vollständige semantische Korrektheit. Contracts sichern Struktur und grundlegende Constraints, nicht die inhaltliche Wahrheit.
