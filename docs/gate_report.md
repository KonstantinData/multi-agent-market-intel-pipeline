# Gate 2: Agenten-Matrix und Gate 3: DoD‑Compliance

## Agenten‑Matrix (geplant vs. Ist‑Zustand)

Die folgende Tabelle listet alle in `docs/planned_agents_overview.md` sowie `docs/agents/**` definierten Agents und vergleicht sie mit dem im Repository vorgefundenen Zustand (Gate 2). Für jeden Agent werden erwartete Entry‑Points, Inputs/Outputs, und Artefaktpfade auf Basis der Dokumentation zusammengefasst. **Status** beschreibt, ob ein Agent vollständig implementiert ist (alle in der Dokumentation beschriebenen Anforderungen erfüllt), teilweise implementiert ist (Code vorhanden, aber nicht im DAG eingebunden oder Outputs unvollständig) oder völlig fehlt.

| Agent‑ID | Beschreibung / erwartete Deliverables (aus Planung) | Ist‑Entry‑Point | Artefaktpfade (run_id‑basiert) | Status | Evidence |
|---|---|---|---|---|---|
| **AG‑00: Intake Normalization** | Normalisiert Eingaben (Firmenname und Domain), schreibt `case_normalized` und `target_entity_stub`; liefert `entities_delta` mit Zielstub, `relations_delta` leer, `findings` und `sources`【517489202949068†L6-L28】. | `src/agents/ag00_intake_normalization/agent.py` mit Klasse `Agent` und `run()` Funktion | Schreibt `artifacts/runs/<run_id>/steps/ag00/output.json`; orchestrator persistiert zudem `artifacts/runs/<run_id>/meta/case_normalized.json` und `target_entity_stub.json`【741439545540675†L80-L99】. | **Implemented** | Code vorhanden; Orchestrator ruft Agent auf; Gatekeeper validiert; Meta‑Dateien werden erstellt. |
| **AG‑01: Source Registry** | Erstellt Registry aus primären/sekundären Quellen; Rückgabe von `source_registry`, `entities_delta` leer, `relations_delta` leer, `findings`, `sources`【517489202949068†L6-L28】. | `src/agents/ag01_source_registry/agent.py` | `artifacts/runs/<run_id>/steps/ag01/output.json` und `validator.json` | **Implemented** | Code vorhanden und wird vom Orchestrator aufgerufen; Gatekeeper validiert Ausgaben【796905532618142†L121-L150】. |
| **AG‑10: Identity – Legal** | Sammelt Rechtsidentität: Name, Registerinformationen, Rechtsform; nutzt ggf. LLM; produziert `entities_delta`, keine `relations_delta`, `findings`, `sources`, `field_sources`【517489202949068†L6-L28】. | `src/agents/ag10_identity_legal/agent.py` | `artifacts/runs/<run_id>/steps/ag10/output.json` | **Implemented** | Agent implementiert; Orchestrator ruft ihn auf; Validierung vorhanden. |
| **AG‑11: Locations & Sites** | Extrahiert Standort/Site‑Informationen; erzeugt `SITE`‑Entities und `operates_at`‑Relationen; erwartet, dass jede Site eine Quelle hat【517489202949068†L6-L28】. | `src/agents/ag11_locations_sites/agent.py` | `artifacts/runs/<run_id>/steps/ag11/output.json` | **Implemented** | Agent implementiert; Orchestrator ruft ihn auf, obwohl Schritt nicht im DAG steht; Gatekeeper validiert Struktur. |
| **AG‑20: Company Size** | Ermittelt Unternehmensgröße (Mitarbeiterzahl, Umsatzband, Marktumfang); aktualisiert Ziel‑Entity mit `employee_range`, `revenue_band`, `market_scope_signal`; muss Quellen liefern【517489202949068†L114-L135】. | `src/agents/ag20_company_size/agent.py` | `artifacts/runs/<run_id>/steps/ag20/output.json` | **Implemented** (nicht integriert) | Agent‑Code vorhanden, aber nicht in `run_pipeline.py` eingebunden; Step fehlt im DAG; Validierung implementiert. |
| **AG‑21: Industry Classification** | Klassifiziert Ziel‑Entity in Branchenkategorien. | **Fehlt** | Erwartet: `steps/ag21/output.json` | **Missing** | Kein Codeordner `ag21_*`; nur Agent‑Beschreibung im `docs/agents/AG-21-agent-description.md`. |
| **AG‑30: Products & Services** | Sammelt Produkte und Services; sollte Produkt‑Entities und Beziehungen zum Ziel liefern. | **Fehlt** | `steps/ag30/output.json` | **Missing** | Kein Codeordner, nur Dokumentation vorhanden. |
| **AG‑31: Customers & References** | Recherchiert Kunden, Partner, Testimonials. | **Fehlt** | `steps/ag31/output.json` | **Missing** | Kein Code. |
| **AG‑40: Competitor Landscape** | Identifiziert Wettbewerber und legt deren Entities an. | **Fehlt** | `steps/ag40/output.json` | **Missing** | Kein Code. |
| **AG‑41: Differentiators & USPs** | Recherchiert Differenzierungsmerkmale. | **Fehlt** | `steps/ag41/output.json` | **Missing** | Kein Code. |
| **AG‑42: Market Opportunity** | Analysiert Marktchancen und Wachstumstreiber. | **Fehlt** | `steps/ag42/output.json` | **Missing** | Kein Code. |
| **AG‑50: Technology Stack** | Identifiziert verwendete Technologien. | **Fehlt** | `steps/ag50/output.json` | **Missing** | Kein Code. |
| **AG‑51: Data & AI Maturity** | Bewertet Reifegrad in Daten/AI. | **Fehlt** | `steps/ag51/output.json` | **Missing** | Kein Code. |
| **AG‑60: Investment & Funding** | Recherchiert Finanzierungsrunden. | **Fehlt** | `steps/ag60/output.json` | **Missing** | Kein Code. |
| **AG‑61: Mergers & Acquisitions** | Extrahiert M&A‑Ereignisse. | **Fehlt** | `steps/ag61/output.json` | **Missing** | Kein Code. |
| **AG‑62: Management Team** | Identifiziert Management/Board. | **Fehlt** | `steps/ag62/output.json` | **Missing** | Kein Code. |
| **AG‑70: News Summary** | Summiert aktuelle Nachrichtenartikel. | **Fehlt** | `steps/ag70/output.json` | **Missing** | Kein Code. |
| **AG‑71: Social & Web Sentiment** | Analysiert Social‑Media‑Stimmung. | **Fehlt** | `steps/ag71/output.json` | **Missing** | Kein Code. |
| **AG‑72: Innovation Signals** | Recherchiert Patente und F&E‑Signale. | **Fehlt** | `steps/ag72/output.json` | **Missing** | Kein Code. |
| **AG‑80: Risk & Compliance** | Prüft Sanktionen und Compliance. | **Fehlt** | `steps/ag80/output.json` | **Missing** | Kein Code. |
| **AG‑81: ESG & Sustainability** | Bewertet ESG‑Aspekte. | **Fehlt** | `steps/ag81/output.json` | **Missing** | Kein Code. |
| **AG‑82: Employee Insights** | Analysiert Mitarbeiter‑Feedback und Kultur. | **Fehlt** | `steps/ag82/output.json` | **Missing** | Kein Code. |
| **AG‑83: Hiring Signals** | Analysiert Stellenausschreibungen. | **Fehlt** | `steps/ag83/output.json` | **Missing** | Kein Code. |
| **AG‑90: Executive Summary** | Synthetisiert alle Erkenntnisse; bereitet Berichtsabschnitte für den Export vor. | **Fehlt** | `steps/ag90/output.json` | **Missing** | Kein Code; essenziell für finalen Bericht. |

## Gate 3: Definition‑of‑Done‑Compliance

Für jeden Abschnitt der `docs/dod_checklist.yml` wird der derzeitige Status bewertet. **PASS** bedeutet, dass das Repo alle Anforderungen erfüllt. **FAIL** bedeutet, dass das Repo die Anforderung nicht erfüllt; es folgen Begründung und Evidenz sowie ein Hinweis auf notwendige Maßnahmen.

| DoD‑Kategorie/Punkt | PASS/FAIL | Evidence & Begründung |
|---|---|---|
| **repository.structure_integrity.no_folder_renames** | PASS | Aktuelle Struktur folgt dem Blueprint aus `setup_repo_tree.py`; keine umbenannten Ordner festgestellt. |
| **repository.structure_integrity.no_agent_id_renames** | PASS | Agent‑Verzeichnisse besitzen eindeutige IDs (ag00, ag01, ag10, ag11, ag20). |
| **repository.structure_integrity.no_breaking_interface_changes** | PASS | Agent‑Schnittstellen folgen BaseAgent‑Signatur (run returns dict); keine Änderungen festgestellt. |
| **repository.structure_integrity.repo_runs_from_clean_env** | PASS | `requirements.txt` und `requirements-dev.txt` definieren alle Abhängigkeiten; keine globalen Pfade. |
| **repository.structure_integrity.single_schema_system_enforced** | FAIL | Es existieren mehrere Schema‑Dateien in `configs/contracts/`, aber keine zentrale Schema‑Validierung in Pipeline; Gatekeeper nutzt eigene Prüfungen. |
| **configuration_ownership.schemas_only_in configs/contracts, configs/pipeline, configs/rules** | PASS | Schemas liegen in `configs/contracts` und `configs/pipeline`; keine Schemas in Codeordnern. |
| **configuration_ownership.validator_only_in src/validator** | PASS | Gatekeeper‑Code befindet sich ausschließlich unter `src/validator`. |
| **run_execution.run_creation.ui_confirmation_required** | PASS | UI zeigt eine Normalisierungs‑Vorschau und benötigt explizite Bestätigung, bevor `run_id` erzeugt und `case_input.json` geschrieben wird【805271934015764†L146-L175】. |
| **run_execution.run_creation.no_artifacts_before_confirmation** | PASS | `ensure_run_dirs` wird erst nach Bestätigung aufgerufen; vor der Bestätigung werden keine Dateien erzeugt【805271934015764†L146-L175】. |
| **run_execution.run_creation.run_id_unique_and_immutable** | PASS | `build_run_id` erstellt einen Zeitstempel‑basierten Identifier; dieser wird nicht geändert. |
| **run_execution.artifact_layout.required_paths** | PASS | `RunContext` erzeugt `meta`, `steps`, `logs` und `exports` Verzeichnisse für jeden Run【245674676649834†L16-L35】. |
| **run_execution.artifact_layout.no_writes_outside_artifacts** | FAIL | Der Orchestrator schreibt Log‑Dateien im Repository‐Root (`logs` Pfad) statt im `artifacts/runs/<run_id>/logs`; dieser Schritt muss angepasst werden. |
| **ag00_foundation.required_artifacts meta/case_normalized.json & target_entity_stub.json** | PASS | `run_pipeline.py` persistiert diese Dateien nach AG‑00【741439545540675†L80-L99】. |
| **ag00_foundation.normalization_rules.company_name_canonical_non_empty** | PASS | `AG‑00` normalisiert Namen und prüft Nichtleerheit; Validator erzwingt dies. |
| **ag00_foundation.normalization_rules.web_domain_normalized_valid** | PASS | `text_normalization.is_valid_domain` wird im UI zur Vorprüfung verwendet; Gatekeeper validiert ebenfalls. |
| **ag00_foundation.normalization_rules.entity_key_equals_domain_prefixed** | PASS | `AG‑00` erstellt `entity_id` als `TGT-001` (konstant); Regel erfüllt. |
| **ag00_foundation.gatekeeper.status_must_be_pass & warnings_recorded_if_present** | PASS | Validator erstellt `validator.json` mit `status` und `warnings`. |
| **agent_steps.output_artifacts_required (output.json & validator.json pro Schritt)** | PARTIAL | Für AG‑00 bis AG‑11 werden beide Dateien erzeugt. Für AG‑20 existiert keine orchestratorische Einbindung; spätere Schritte fehlen. |
| **agent_steps.output_structure.required_fields (step_id, run_id, timestamp_utc, findings, sources)** | PASS | Alle implementierten Agents füllen `step_meta` und liefern `findings` und `sources` Felder. |
| **agent_steps.output_structure.conditional_fields (entities_delta, relations_delta, report_section)** | PARTIAL | Implementierte Agents liefern `entities_delta`/`relations_delta` korrekt; `report_section` wird von keinem Agent gefüllt (Fehler für AG‑90). |
| **agent_steps.evidence_rules.claims_require_sources** | PASS | Agent‑Implementierungen prüfen, dass Informationen ohne Quelle nicht als Claim ausgegeben werden; Gatekeeper erzwingt dies. |
| **gatekeeper_validation.hard_fail_conditions** | PASS | `contract_validator.py` enthält Prüfungen für fehlende Felder, ungültige IDs, Duplikate und Schema‑Verletzungen. |
| **gatekeeper_validation.warnings_allowed_only_if.explicitly_logged & no_downstream_structural_impact** | PASS | Validator zeichnet Warnungen im `validator.json` auf; Downstream‑Impact wird vom Orchestrator gestoppt. |
| **orchestration.dag_execution_enforced** | FAIL | `configs/pipeline/dag.yml` listet nur AG‑00, AG‑01 und AG‑10; AG‑11 wird im Orchestrator manuell aufgerufen; AG‑20 und spätere Schritte sind nicht eingebunden. |
| **orchestration.no_step_after_fail** | PASS | Orchestrator stoppt die Pipeline, wenn Validatorstatus nicht `PASS`. |
| **orchestration.retry_policy_bounded** | FAIL | Es existiert keine implementierte Retry‑Policy; config `retry_policy.yml` fehlt. |
| **orchestration.orchestrator_does_not_modify_outputs** | PASS | Orchestrator schreibt Agent‑Outputs unverändert weiter; keine Änderungen festgestellt. |
| **orchestration.orchestrator_decision_basis.validator_status_only** | PASS | Orchestrator entscheidet über Fortsetzung ausschließlich basierend auf Validator‑Status. |
| **registry_and_identity.registry_exists meta/entity_registry.json** | FAIL | Es gibt keine Implementierung eines Entity‑Registries; Datei `meta/entity_registry.json` wird nicht erstellt. |
| **registry_and_identity.id_policy.target_id=TGT‑001** | PASS | AG‑00 vergibt `TGT-001` als Ziel-ID. |
| **registry_and_identity.dedupe_rules.primary_key=normalized_domain** | FAIL | Deduplizierungslogik existiert nicht; keine Konfiguration `id_policy.yml` implementiert. |
| **cross_reference_integrity.crossref_graph_exists meta/crossref_graph.json** | FAIL | Es existiert kein Schritt, der Cross‑References aggregiert oder `crossref_graph.json` erzeugt. |
| **exports.mandatory_exports (exports/report.md & exports/entities.json)** | FAIL | Es gibt keine Export‑Logik; `exports` bleibt leer; UI erwartet diese Dateien jedoch. |
| **exports.export_rules.derived_only_from_validated_artifacts & no_additional_inference & all_ids_resolve_to_registry** | FAIL | Mangels Export‑Implementierung können diese Regeln nicht erfüllt werden. |
| **ui.intake_guardrails.invalid_domain_blocks_start & normalization_preview_present & explicit_confirmation_required** | PASS | UI prüft Domains und zeigt eine Normalisierungs-Vorschau; Nutzer muss explizit bestätigen【805271934015764†L146-L175】. |
| **ui.run_controls.step_status_visible** | PARTIAL | UI zeigt Status der implementierten Steps im Run‑Monitor; jedoch werden spätere Steps mangels DAG nicht sichtbar. |
| **ui.run_controls.intake_correction_supported & rerun_supported** | PASS | UI erlaubt Korrektur der Eingabe und erneuten AG‑00‑Run. |
| **ui.run_controls.run_archiving_preserves_audit** | PASS | UI ermöglicht Archivieren von Runs; archivierte Verzeichnisse bleiben erhalten. |
| **testing.pytest_passes** | FAIL | Bestehende Tests decken nur AG‑00, AG‑01 und AG‑10 ab; viele fehlende Komponenten führen zu fehlgeschlagenen E2E Tests. |
| **testing.unit_tests_required_for normalization & validator_logic & dedupe_and_id_policy** | PARTIAL | Tests für Normalisierung und Validator vorhanden (`tests/unit/test_ag00_normalization.py`, `test_ag00_gatekeeper.py`, `test_ag01_gatekeeper.py`, `test_ag10_gatekeeper.py`). Es fehlen Tests für Deduplication/ID‑Policy. |
| **testing.integration_tests.pipeline_smoke_test_produces_exports** | FAIL | Kein E2E‑Test implementiert; Pipeline erzeugt keine Exports. |
| **determinism_and_audit.deterministic_structure_and_ids & nondeterminism_confined_to_content** | PARTIAL | `run_id` garantiert deterministische Verzeichnisse; fehlende Registry/Dedupe führt jedoch zu potentiell nicht deterministischer ID‑Zuordnung bei späteren Agents. |
| **determinism_and_audit.traceability.output_to_step & output_to_source & output_to_run_id** | PASS | Schritt‑Outputs enthalten `step_id`/`run_id` und `sources`. |
| **determinism_and_audit.no_silent_overwrites** | PASS | Orchestrator schreibt Artefakte in neuen Run‑Ordnern; keine Überschreibungen. |
| **documentation.architecture_spec_present & agent_deliverables_documented** | PASS | `docs/architecture/00_overview.md` erklärt die Architektur【955128760861358†L69-L99】; `docs/planned_agents_overview.md` dokumentiert Agent‑Deliverables. |
| **documentation.known_limitations_documented** | FAIL | Es existiert keine Datei mit bekannten Einschränkungen; daher unvollständig. |
| **final_acceptance.no_p0_violations & no_validator_bypasses & full_end_to_end_run_auditable** | FAIL | Da Export‑Schritte, Registry und Crossref fehlen, ist ein voll auditierbarer End‑to‑End‑Run nicht möglich. |

**Zusammenfassung:** Das Repository erfüllt aktuell einige grundlegende Anforderungen (UI‑Bestätigung, Struktur der Artefaktordner, Ausführung der ersten Agents), scheitert jedoch an vielen Punkten des DoD. Insbesondere fehlen:

- Implementierung und Einbindung der meisten geplanten Agents (AG‑21 bis AG‑90),
- eine generische Orchestrierung basierend auf dem DAG,
- eine Registry‑/Deduplication‑Schicht und Cross‑Reference‑Berechnung,
- die Export‑Schicht zur Erstellung von `report.md` und `entities.json`,
- eine Retry‑Policy sowie dedizierte Configs für ID‑Policy und Concurrency,
- umfassende Tests (Deduplication, E2E) und CI‑DoD‑Checks,
- sowie Dokumentation der bekannten Limitationen.

Diese Lücken müssen behoben werden, um einen deterministischen, auditierbaren End‑to‑End‑Pipeline‑Run zu ermöglichen und das Definition‑of‑Done vollständig zu erfüllen.
