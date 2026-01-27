# multi-agent-market-intel-pipeline

Eine produktionsreife, vertragsgesteuerte Multi-Agent-Pipeline für B2B-Unternehmensanalyse, Kunden- und Wettbewerber-Mapping sowie prüfbare Marktforschungsergebnisse.

---

## Was dieses Repository leistet

Dieses Repository implementiert eine **artefaktbasierte, prüfbare Multi-Agent-Pipeline für Marktintelligenz**, die aus einer einzelnen Unternehmenseingabe (Name + Domain) ein strukturiertes, governance-sicheres Ausgabepaket erstellt:

- Verifiziertes Zielunternehmensprofil (Identität, Rechtsform, Standorte, Portfolio)
- Öffentlich belegte Kunden- und Referenzzuordnung
- Peer- / Wettbewerber-Hersteller-Ermittlung (produktbasierte Peers)
- Kunden-von-Herstellern-Mapping (marktweite Käuferlandschaft)
- Vertriebs- und Verhandlungsplaybook aus verifizierbaren Signalen (keine Vermutungen)
- Querverweisindex mit stabilen IDs (deduplizierte Entitäten)
- Maschinenlesbare JSON-Exporte für nachgelagerte Automatisierung

Das System ist für **parallele Domain-Agenten (Fan-Out)** konzipiert und bewahrt gleichzeitig Governance durch **Vertragsvalidierung** und eine zentrale **Entity Registry**.

---

## Zentrale Designziele

- **Prüfbarkeit:** Jeder Durchlauf erzeugt einen vollständigen Artefakt-Trail (Eingaben, Ausgaben, Validierungsergebnisse, Merge-Zustände, Exporte).
- **Vertragsdurchsetzung:** Jeder Schritt muss strikte Ausgabeverträge (Schemas + Regeln) erfüllen oder schlägt schnell fehl.
- **Deterministische Governance:** IDs, Deduplizierung, Merge-Richtlinien und Querverweise sind deterministisch, auch wenn LLM-generierter Text variiert.
- **Referenzielle Integrität:** Querverweissystem stellt sicher, dass alle Entitätsbeziehungen gültig und nachverfolgbar sind.
- **Parallele Ausführung:** Domain-Agenten können parallel laufen; Ergebnisse werden an expliziten Barrieren zusammengeführt.
- **Evidenzbasierte Ausgabe:** Keine erfundenen Fakten. Wenn etwas nicht verifiziert werden kann, wird `n/v` ausgegeben.
- **Recruiter-ready Engineering:** Klare Trennung der Verantwortlichkeiten, versionierte Configs, Tests und Entscheidungsnachverfolgbarkeit (ADRs).

---

## Architekturübersicht

### High-Level-Workflow

Die Pipeline läuft als **DAG** mit expliziten parallelen Batches und Merge-Barrieren:

1. **Intake-Normalisierung** (Bereinigung und Normalisierung der Case-Eingabe)
2. **Parallele Domain-Research-Agenten** (Fan-Out)
3. **Ausgabevertragsvalidierung** nach jedem Schritt (Gatekeeper)
4. **Zentrale Entity-Registry-Merge** (Fan-In-Barriere)
5. **Nachgelagerte Mapping-Schritte** (Peers -> Kunden-von-Peers)
6. **Finale Exporte** (Report, Entities, Index, Querverweismatrix mit Beziehungsanalyse)

### Schlüsselsubsysteme

- **Orchestrator (`src/orchestrator/`)**

  - DAG-Laden und -Auflösung
  - Parallele Planung und Ausführung
  - Barrieren- und Merge-Koordination
  - Retry/Abort-Handling basierend auf Fehlertypen
  - Artefakt-Schreiben (atomare Schreibvorgänge)

- **Domain-Agenten (`src/agents/`)**

  - Einzelverantwortliche Research-Schritte
  - Jeder Agent führt **Selbstvalidierung** seiner Ergebnisse durch
  - Agenten geben nur **Delta-Ausgaben** aus (keine globalen IDs)

- **Validator / Gatekeeper (`src/validator/`)**

  - Schema-Validierung (JSON Schema)
  - Regel-Validierung (Pflichtfelder, Evidence-Policy, ASCII-Policy)
  - Querverweisintegritätsprüfungen (Hard Fail bei defekten Links)
  - Referenzielle Integritätsvalidierung (keine hängenden Entitätsreferenzen)
  - PASS/FAIL-Ergebnisse steuern Orchestrierung

- **Entity Registry (`src/registry/`)**

  - Zentralisierte Deduplizierung (domainbasierte Entity-Keys)
  - Deterministische ID-Zuweisung (TGT/MFR/CUS)
  - Merge-Konfliktauflösung mit Provenance-Tracking
  - Querverweisdiagramm-Konstruktion und Beziehungsmanagement

- **Exporters (`src/exporters/`)**

  - Markdown-Report-Builder (`report.md`)
  - Entity-Export (`entities.json`)
  - Index-Export (`index.json`)
  - Querverweismatrix-Export mit Beziehungsanalyse
  - Adjazenzmatrizen und Beziehungszusammenfassungen

---

## Governance-Prinzipien

### 1) Keine annahmebasierten Inhalte

Die Pipeline darf keine Fakten erfinden.
Wenn Beweise fehlen, muss die Ausgabe **`n/v`** sein.

### 2) Beweise und Quellen sind obligatorisch

Alle wesentlichen Behauptungen müssen durch strukturierte Quellen belegt werden:

- Publisher
- URL
- Titel (falls verfügbar)
- Zugriffszeitstempel

### 3) Ausgabeverträge sind nicht verhandelbar

Jede Schrittausgabe muss konform sein mit:

- `configs/contracts/*.json`
- `configs/pipeline/step_contracts.yml`
- `configs/rules/validator_rules.yml`

Ein fehlgeschlagener Schritt blockiert den nächsten Schritt.

### 4) Zentralisierte ID-Governance (keine parallelen ID-Kollisionen)

IDs werden nur während des Registry-Merge zugewiesen:

- Zielunternehmen: `TGT-001`
- Hersteller/Peers: `MFR-XXX`
- Kunden: `CUS-XXX`

Agenten dürfen keine finalen IDs generieren.

### 5) Fan-Out / Fan-In-Barrieren sind explizit

Parallele Schritte werden nur an expliziten DAG-Knoten zusammengeführt.
Kein Schritt darf teilweise gemergete Registry-Zustände konsumieren.

### 6) Artefaktbasierte Reproduzierbarkeit

Jeder Durchlauf erzeugt ein deterministisches Artefakt-Layout für:

- Debugging
- Review
- Audit-Trails
- Wiederholungen

### 7) Querverweisintegrität ist obligatorisch

Alle Entitätsbeziehungen müssen referenzielle Integrität wahren:

- Keine hängenden Referenzen (Referenzen auf nicht existierende Entitäten)
- Alle Beziehungstypen müssen gültig und evidenzbasiert sein
- Querverweisvalidierung erfolgt an Merge-Barrieren
- Beziehungsmatrizen bieten umfassende Audit-Trails

---

## Repository-Layout

### Top-Level

- `src/` Produktionscode: Orchestrator, Agenten, Registry, Validator, Exporters.
- `configs/` Versionierte Pipeline-Governance:

  - DAG-Definition
  - Verträge (Schemas)
  - Validierungsregeln (ID-Policy, Dedupe, Evidence-Anforderungen)

- `docs/` Architekturdokumentation und Entscheidungsnachverfolgbarkeit:

  - Architektur-Deep-Dives
  - ADRs (Architekturentscheidungen)
  - Beispiele

- `tests/` Unit- und Integrationstests:

  - Vertragsvalidierungstests
  - Registry-Dedupe + ID-Zuweisungstests
  - Pipeline-Smoke-Tests

- `runs/` Laufzeit-Artefakte und Ausgaben (**nicht committed**). Absichtlich von `src/` getrennt.
- `scripts/` Lokale Run- und Validierungs-Hilfsskripte.

---

## Run-Artefakte und Ausgabestruktur

Jede Pipeline-Ausführung erzeugt ein Run-Verzeichnis wie:

```text
runs/<run_id>/
  meta/
    run_meta.json
    dag_resolved.json
    env_snapshot.json

  steps/<AG-XX>/
    input.json
    output.json
    validator.json
    log.txt

  registry/
    registry_v0_init.json
    registry_v1_post_P1.json
    ...

  exports/
    report.md
    entities.json
    index.json
    crossref_matrix.json

  logs/
    pipeline.log
    errors.log
```

### Warum Artefakte wichtig sind

Artefakte ermöglichen:

- Post-Run-Validierung und Review
- Deterministisches Debugging von Fehlern
- Evidence-Nachprüfung
- Reproduzierbare Stakeholder-Berichte

---

## Installation

### Virtuelle Umgebung erstellen und aktivieren

Windows (PowerShell):

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

Git Bash:

```bash
python -m venv venv
source venv/Scripts/activate
```

### Laufzeit-Abhängigkeiten installieren

```bash
pip install -r requirements.txt
```

### Entwicklungs-Abhängigkeiten installieren (optional)

```bash
pip install -r requirements-dev.txt
```

---

## Ausführung

### Streamlit UI (Empfohlen)

```bash
streamlit run ui/app.py
```

Die UI bietet:
- **Intake-Formular** mit Unternehmensdetails (Name, Domain, Adresse, Telefon, Branche)
- **Run-Monitoring** mit Echtzeit-Logs
- **Ergebnis-Viewer** mit professionellen Business-Reports

### CLI-Einstiegspunkt

```bash
python -m src.orchestrator.run_pipeline --case-file case_input.json --run-id my_run
```

Eine typische Case-Eingabe umfasst:

```json
{
  "company_name": "Example Manufacturing GmbH",
  "web_domain": "example-manufacturing.com",
  "city": "München",
  "postal_code": "80331",
  "street_address": "Musterstraße 123",
  "phone_number": "+49 89 123456",
  "industry": "Manufacturing",
  "country": "Germany"
}
```

---

## Testing

### Unit-Tests ausführen

```bash
pytest -q
```

### Vollständige Suite mit Coverage ausführen

```bash
pytest --cov=src --cov-report=term-missing
```

---

## CI/CD-Gates

Der CI-Workflow soll durchsetzen:

- Schema-/Vertragsvalidierungstests
- Unit-Tests
- Optionale statische Prüfungen (ruff, mypy)

Siehe: `.github/workflows/ci.yml`

---

## Entscheidungsnachverfolgbarkeit (ADRs)

Wichtige Architekturentscheidungen werden als ADRs erfasst in:

- `docs/adr/`

Beginnen Sie hier:

- `docs/adr/ADR-000-index.md`

---

## Beitragen / Engineering-Workflow

Dieses Repository folgt einem Contract-First-Entwicklungsprozess:

1. Verträge schreiben/aktualisieren (`configs/contracts/`, `configs/rules/`)
2. Schrittlogik implementieren (`src/agents/`, `src/validator/`, `src/registry/`)
3. Tests hinzufügen/erweitern (`tests/`)
4. Via CI-Gates validieren
5. Änderungen mit klaren Nachrichten committen

---

## Roadmap (Engineering-Meilensteine)

P0 (Must-Have)

- Orchestrator-Skelett + DAG-Loader
- Contract-Validator v1 (Schema + Regeln)
- Zentrale Entity-Registry + deterministische IDs
- Minimale Exporters (`entities.json` + `report.md`)

P1 (Wichtig)

- Paralleler Scheduler + explizite Barrieren
- Merge-Konfliktauflösungsrichtlinie + Provenance-Tracking
- Vollständiger Querverweismatrix-Export

P2 (Nice-to-Have)

- Pre-Commit-Hooks + strikte Linting-Gates
- Rich-Report-Formatierung und optionale Diagramme
- Erweiterte Caching-/Memoization-Schicht

---

## Lizenz

Dieses Projekt ist unter einer Non-Commercial-Lizenz verfügbar. Kommerzielle Lizenzierung ist auf Anfrage erhältlich.

Siehe [LICENSE](LICENSE)
