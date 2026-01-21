# ADR-003: Zentrales Entity‑Registry & ID‑Merge

**Status:** Angenommen

## Hintergrund

Die Pipeline aggregiert Informationen zu denselben realen Entitäten (z. B. Unternehmen, Produkte, Märkte) aus unterschiedlichen Quellen. Ohne zentrale Registry entstehen Duplikate, inkonsistente IDs und spätere Merge‑Konflikte. Ein dedizierter Mechanismus zur Konsolidierung ist notwendig, um konsistente Identitäten über Runs hinweg sicherzustellen.

## Entscheidung

Wir führen ein **zentrales Entity‑Registry** ein:

- **Globale, stabile IDs** für Entitäten über alle Quellen und Runs hinweg.
- **Merge‑Strategie**: Regeln für Deduplikation (z. B. gleiche Domain, Name + Standort, Identifier‑Übereinstimmung).
- **Alias‑/Match‑Historie** zur Nachvollziehbarkeit von Zusammenführungen.

Downstream‑Artefakte referenzieren stets Registry‑IDs.

## Konsequenzen

- **Konsistenz:** alle Artefakte referenzieren eine einheitliche Entitäts‑ID.
- **Nachvollziehbarkeit:** Merge‑Entscheidungen sind dokumentiert und auditierbar.
- **Komplexität:** Matching‑Regeln benötigen Pflege und kontinuierliche Verbesserung.
- **Fehlerauswirkung:** falsche Merges wirken systemweit; daher sind klare Review‑/Rollback‑Mechanismen wichtig.

## Alternativen / Non‑Goals

- **Alternative:** lokale IDs pro Task/Quelle. Abgelehnt wegen Duplikaten und fehlender Konsistenz.
- **Alternative:** rein probabilistische Entitätsauflösung ohne Registry. Abgelehnt wegen fehlender Stabilität über Runs.
- **Non‑Goal:** vollständige, perfekte Entity‑Resolution. Ziel ist robuste, nachvollziehbare Konsolidierung mit klaren Regeln.
