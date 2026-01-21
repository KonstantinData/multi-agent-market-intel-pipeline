# ADR-001: Parallel Fan‑out/Fan‑in (Orchestrierung/DAG)

**Status:** Angenommen

## Hintergrund

Die Pipeline verarbeitet heterogene Datenquellen und Aufgaben (Scraping, Klassifikation, Enrichment, Zusammenführung). Diese Aufgaben sind teils unabhängig, teils streng sequentiell. Eine lineare Orchestrierung skaliert schlecht, erhöht die Laufzeit und erschwert Fehlerisolation. Für reproduzierbare Runs müssen Abhängigkeiten explizit und deterministisch sein.

## Entscheidung

Wir orchestrieren die Pipeline als gerichteten azyklischen Graphen (DAG):

- **Fan‑out:** unabhängige Tasks werden parallel ausgeführt, sobald ihre Eingangsartefakte verfügbar sind.
- **Fan‑in:** Ergebnisse werden deterministisch zusammengeführt (z. B. in einem Merge‑ oder Aggregation‑Step).
- **Orchestrierungsschicht** verwaltet Abhängigkeiten, Retry‑Strategien und Artefakt‑Übergaben.

## Konsequenzen

- **Skalierbarkeit:** parallele Ausführung reduziert End‑to‑End‑Laufzeiten.
- **Isolierung:** Fehler betreffen nur die betroffenen Teilzweige; nachgelagerte Tasks warten auf gültige Inputs.
- **Reproduzierbarkeit:** explizite Abhängigkeiten machen Runs nachvollziehbar.
- **Komplexität:** erfordert klar definierte Artefakt‑Contracts und einheitliche IDs für Fan‑in‑Schritte.

## Alternativen / Non‑Goals

- **Alternative:** rein sequenzielle Pipeline. Abgelehnt wegen geringer Parallelisierung und langer Laufzeiten.
- **Alternative:** event‑getriebene, vollständig dynamische Ausführung ohne DAG‑Definition. Abgelehnt wegen schwerer Reproduzierbarkeit.
- **Non‑Goal:** Echtzeit‑Streaming für alle Schritte. Die Pipeline bleibt batch‑orientiert; Streaming kann später ergänzt werden.
