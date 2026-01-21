# Repository Inventory and Agent Comparison for `multi-agent-market-intel-pipeline`

## A. Executive summary

This repository contains the skeleton for a market‑intelligence pipeline but is far from complete.  
A full file inventory shows ~65 version‑controlled artefacts. Only the first three research agents (AG‑00, AG‑01, AG‑10, AG‑11) and one enrichment agent (AG‑20) are implemented under `src/agents/`.  
Many directories mentioned in the `setup_repo_tree.py` blueprint (e.g. `src/exporters`, `src/registry`, additional agent folders, ADR docs, etc.) **do not exist** in the current state.  
The pipeline configuration (`configs/pipeline/dag.yml`) only references the first two research agents and AG‑10; AG‑11 and later steps are missing from the DAG, and there is no export logic to produce the required `report.md` and `entities.json` artefacts.  
This inventory provides a complete file tree of the repository and cross‑checks every planned agent against existing implementations and contract definitions.

## B. Full file tree inventory (classified)

Each file is listed with its relative path and classified as Code, Config, Contracts, Docs, Tests, Scripts, CI, or Other.  
Files listed in `setup_repo_tree.py` but missing from the repository are noted as **(missing)**.

| Path | Classification | Notes |
| --- | --- | --- |
| **Root directory** | | |
| `README.md` | Docs | Main project overview and guidelines; emphasises auditability, contract enforcement and export deliverables【247800328128531†L24-L54】. |
| `LICENSE` | Other | MIT license. |
| `requirements.txt` | Config | Python runtime dependencies. |
| `requirements-dev.txt` | Config | Development/testing dependencies. |
| `.streamlit/config.toml` | Config | Streamlit UI configuration. |
| `.github/workflows/ci.yml` | CI | GitHub Actions workflow for CI. |
| `.github/workflows/pipeline_manual_run.yml` | CI | Workflow to trigger the pipeline manually via GitHub. |
| `pytest.ini` | Config/Test | Pytest configuration file. |
| `setup_repo_tree.py` | Scripts | Script enumerating the intended repository structure; many listed files are not present【237031863345122†L35-L195】. |
| **UI directory** | | |
| `ui/app.py` | Code | Streamlit application providing the UI for run creation, monitoring and result display. It generates a `run_id`, ensures run directories and writes `case_input.json` only after user confirmation【805271934015764†L146-L175】. |
| `.streamlit/config.toml` | Config | Streamlit theme settings. |
| **Configuration files (`configs`)** | | |
| `configs/pipeline/dag.yml` | Config | Defines the DAG; currently only includes `AG-00`, `AG-01` and `AG-10` steps【902690364884310†L1-L11】. |
| `configs/pipeline/step_contracts.yml` | Config | Contract definitions and required fields for each agent step. |
| `configs/rules/trusted_domains.json` | Config | List of trusted domains for agents to fetch data from. |
| `configs/contracts/entity_schema.json` | Contracts | JSON schema for entities. |
| `configs/contracts/source_schema.json` | Contracts | JSON schema for sources. |
| `configs/contracts/crossref_schema.json` | Contracts | JSON schema for cross‑reference matrix. |
| `configs/contracts/step_output_schema.json` | Contracts | JSON schema describing generic step outputs. |
| `configs/contracts/report_section_schema.json` | Contracts | JSON schema for report sections (no implementation yet). |
| `configs/contracts/validator_result_schema.json` | Contracts | JSON schema for validator results. |
| *(Expected but missing)* `configs/rules/id_policy.yml` | Config | ID assignment rules referenced in the architecture docs – file not present. |
| *(Expected but missing)* various retry policies and concurrency limit config files mentioned in docs – not present. |
| **Documentation (`docs`)** | | |
| `docs/architecture/00_overview.md` | Docs | Detailed system architecture specification: goals, UI responsibilities, orchestrator responsibilities, agent responsibilities, gatekeeper, registry, cross‑reference model and export layer【955128760861358†L69-L99】【955128760861358†L182-L199】. |
| `docs/architecture/06_formal_definition_of_done.md` | Docs | Formal DoD describing mandatory exports and run invariants. |
| `docs/dod_checklist.yml` | Docs/Contracts | Machine‑enforceable Definition of Done checklist, including mandatory exports (report.md & entities.json)【248644761259551†L111-L119】 and run directory structure【248644761259551†L24-L30】. |
| `docs/how_to_use_dod_checklist_yml.md` | Docs | Explains the enforcement of DoD as acceptance authority【972220847988778†L10-L21】. |
| `docs/planned_agents_overview.md` | Docs | Overview of all planned agent steps (AG‑00 – AG‑90) with expected outputs and gatekeeper rules【517489202949068†L6-L28】【517489202949068†L114-L135】. |
| `docs/agents/AG-00-agent-description.md` | Docs | Step‑specific description for AG‑00; template content. |
| `docs/agents/AG-01-agent-description.md` | Docs | AG‑01 description. |
| `docs/agents/AG-10-agent-description.md` | Docs | AG‑10 description. |
| `docs/agents/AG-11-agent-description.md` | Docs | AG‑11 description. |
| `docs/agents/AG-20-agent-description.md` | Docs | AG‑20 description. |
| `docs/agents/AG-21-agent-description.md` | Docs | AG‑21 description (planned only). |
| `docs/agents/AG-30-agent-description.md` through `AG-90-agent-description.md` | Docs | Descriptions for remaining planned agents (AG‑30, AG‑31, AG‑40, AG‑41, AG‑42, AG‑50, AG‑51, AG‑60, AG‑61, AG‑62, AG‑70, AG‑71, AG‑72, AG‑80, AG‑81, AG‑82, AG‑83, AG‑90). All share generic template text; none have implementation. |
| `docs/prompts/prompt_multi_agent_market_intel_build_v1.0txt` | Docs | Prompt used to generate the repository blueprint. |
| `docs/prompts/prompt_multi_agent_market_intel_build_v1.1.txt` | Docs | Updated prompt describing pipeline requirements. |
| `docs/diagrams/agentic-research-and-enrichement-workflow_v1.0.drawio` | Docs | Diagram file (drawio) for agentic workflow. |
| *(Expected but missing)* `docs/adr/*.md`, `docs/how-tos`, `docs/examples/` | Docs | Mentioned in `setup_repo_tree.py` but not present. |
| **Source code (`src`)** | | |
| `src/agents/common/base_agent.py` | Code | Defines `BaseAgent` and `AgentResult` classes used by all agents【900758601338323†L6-L18】. |
| `src/agents/common/step_meta.py` | Code | Utility to build `step_meta` with timestamp and pipeline version【724545248962537†L14-L55】. |
| `src/agents/common/text_normalization.py` | Code | Functions for normalising domains and validating input【261152085031137†L14-L25】. |
| `src/agents/ag00_intake_normalization/agent.py` | Code | Implementation of AG‑00: normalises the company name/domain, produces `case_normalized`, `target_entity_stub`, `entities_delta`, and step metadata【741439545540675†L80-L99】. |
| `src/agents/ag01_source_registry/agent.py` | Code | Implementation of AG‑01: builds primary and secondary source registry; returns `entities_delta` (empty), `relations_delta` (empty), `findings` and `sources`【796905532618142†L121-L150】. |
| `src/agents/ag01_source_registry/__init__.py` | Code | Package init. |
| `src/agents/ag10_identity_legal/agent.py` | Code | Implementation of AG‑10: fetches legal identity info, uses LLM to extract fields; returns `entities_delta` updates and step meta. |
| `src/agents/ag11_locations_sites/agent.py` | Code | Implementation of AG‑11: extracts location/site information; produces site entities and `operates_at` relations. |
| `src/agents/ag20_company_size/agent.py` | Code | Implementation of AG‑20: scrapes and/or uses LLM to estimate company size; updates `employee_range`, `revenue_band`, `market_scope_signal`【783106215396966†L247-L397】. |
| *(Missing)* All other agent folders under `src/agents/` for AG‑21, AG‑30–AG‑90. |
| `src/orchestrator/run_context.py` | Code | Defines `RunContext` dataclass with run_id and directory paths (meta, steps, logs, exports)【245674676649834†L16-L35】. |
| `src/orchestrator/run_pipeline.py` | Code | Orchestrator entrypoint. Runs AG‑00, AG‑01, AG‑10 and AG‑11 sequentially, validates outputs with gatekeeper, writes step outputs and meta artifacts. Does **not** perform any export step for report or entities files. |
| `src/orchestrator/logger.py` | Code | Simple logger for orchestrator messages. |
| `src/orchestrator/constants.py` | Code | Defines constants such as `PIPELINE_VERSION`. |
| *(Missing)* `src/orchestrator/step_registry.py`, `src/orchestrator/step_runner.py` etc. – referenced in docs but not present. |
| `src/validator/contract_validator.py` | Code | Gatekeeper that validates outputs for AG‑00, AG‑01, AG‑10, AG‑11 and AG‑20 based on the contract, ensuring required fields and invariants. |
| `src/validator/error_codes.py` | Code | Enumerates error codes used by the gatekeeper【394735672714522†L3-L19】. |
| `src/validator/__init__.py` | Code | Package init. |
| *(Missing)* `src/registry/`, `src/exporters/`, `src/index_builder.py` – empty in blueprint or not present. |
| **Tests (`tests/unit`)** | | |
| `tests/unit/test_ag00_gatekeeper.py` | Tests | Unit tests for AG‑00 validation. |
| `tests/unit/test_ag00_normalization.py` | Tests | Tests for AG‑00 normalisation logic. |
| `tests/unit/test_ag01_gatekeeper.py` | Tests | Tests for AG‑01 validation. |
| `tests/unit/test_ag10_gatekeeper.py` | Tests | Tests for AG‑10 validation. |
| *(Missing)* Tests for AG‑11 and AG‑20 (though contract exists). No integration or E2E tests. |

## C. Agents – planned vs. existing

The repository intends to implement a pipeline with numerous agent steps.  
The table below cross‑checks every planned agent from `docs/planned_agents_overview.md` with existing code.  
`Entry point` refers to the expected module/function that runs the agent.  
`Expected outputs` summarise the deliverables defined in the planned agents doc – typically `entities_delta`, `relations_delta`, `findings`, `sources` and `step_meta` (sometimes additional structured artefacts).  
When implementation is missing, the entry points and outputs are marked accordingly.

| Agent ID | Planned description (summary) | Implementation file | Status | Expected outputs / notes |
| --- | --- | --- | --- | --- |
| **AG‑00: Intake Normalisation** | Normalises raw case input (company name and domain) and creates `case_normalized` and `target_entity_stub` along with `entities_delta`. Gatekeeper rules require no relations and only target stub【517489202949068†L6-L28】. | `src/agents/ag00_intake_normalization/agent.py` | **Implemented** | Produces `case_normalized.json`, `target_entity_stub.json`, `entities_delta` containing the stub, empty relations, findings & sources; writes outputs in `steps/ag00/output.json`. |
| **AG‑01: Source Registry** | Builds a registry of primary/secondary sources for the company domain; returns sources and findings; no entities or relations【517489202949068†L6-L28】. | `src/agents/ag01_source_registry/agent.py` | **Implemented** | Returns `source_registry` (entities_delta empty), `relations_delta` empty, `sources` list, `findings`; writes output.json. |
| **AG‑10: Identity – Legal** | Researches legal identity of the target entity; updates name variations, registration info, legal form; may use LLM; returns `entities_delta` for target, findings, sources, and field_sources【517489202949068†L6-L28】. | `src/agents/ag10_identity_legal/agent.py` | **Implemented** | Fetches pages using HTTP, extracts legal identity via regex/LLM, updates target entity attributes; returns `entities_delta`, no relations, findings, sources. |
| **AG‑11: Locations & Sites** | Identifies and extracts information about the company’s office sites; generates site entities with `entity_type` = `SITE` and relations from `TGT-001` to each site via `operates_at`【517489202949068†L6-L28】. | `src/agents/ag11_locations_sites/agent.py` | **Implemented** | Returns `entities_delta` for each site, `relations_delta` linking target to sites, findings, sources. |
| **AG‑20: Company Size** | Estimates company size (employee range, revenue band, market scope). Should update target entity with `employee_range`, `revenue_band`, `market_scope_signal`; gather credible sources【517489202949068†L114-L135】. | `src/agents/ag20_company_size/agent.py` | **Implemented** | Scrapes websites and optionally uses LLM to extract size metrics; returns updated target entity fields, sources, findings【783106215396966†L247-L397】. |
| **AG‑21: Industry Classification** | Should classify the target entity into industry categories. | *Not implemented* | **Missing** | No code under `src/agents/ag21_*`; expected to produce `industry_classification` in entities_delta. |
| **AG‑30: Products & Services** | Should research and extract product/service offerings. | *Not implemented* | **Missing** | Should produce product entities and relations with target. No implementation. |
| **AG‑31: Customers & References** | Research major customers, partners and testimonials. | *Not implemented* | **Missing** | Should update relations and sources. No implementation. |
| **AG‑40: Competitor Landscape** | Should identify competitors and enrich competitor entities. | *Not implemented* | **Missing** | Should produce competitor entities and relations. No implementation. |
| **AG‑41: Differentiators & USPs** | Should research the company’s differentiators and unique selling propositions. | *Not implemented* | **Missing** | No implementation. |
| **AG‑42: Market Opportunity** | Should analyse market opportunity and growth drivers. | *Not implemented* | **Missing** | No implementation. |
| **AG‑50: Technology Stack** | Should identify the technology stack used by the company. | *Not implemented* | **Missing** | No implementation. |
| **AG‑51: Data & AI Maturity** | Should assess data and AI maturity of the company. | *Not implemented* | **Missing** | No implementation. |
| **AG‑60: Investment & Funding** | Should research funding rounds, investors and financial history. | *Not implemented* | **Missing** | No implementation. |
| **AG‑61: Mergers & Acquisitions** | Should extract M&A events involving the company. | *Not implemented* | **Missing** | No implementation. |
| **AG‑62: Management Team** | Should identify key executives and board members. | *Not implemented* | **Missing** | No implementation. |
| **AG‑70: News Summary** | Should summarise recent news articles about the company. | *Not implemented* | **Missing** | No implementation. |
| **AG‑71: Social & Web Sentiment** | Should analyse social media and web sentiment. | *Not implemented* | **Missing** | No implementation. |
| **AG‑72: Innovation Signals** | Should research patents, research projects and innovation signals. | *Not implemented* | **Missing** | No implementation. |
| **AG‑80: Risk & Compliance** | Should check sanctions, compliance and risk factors. | *Not implemented* | **Missing** | No implementation. |
| **AG‑81: ESG & Sustainability** | Should evaluate environmental, social and governance aspects. | *Not implemented* | **Missing** | No implementation. |
| **AG‑82: Employee Insights** | Should extract insights from employee reviews and culture. | *Not implemented* | **Missing** | No implementation. |
| **AG‑83: Hiring Signals** | Should analyse job postings and hiring activity. | *Not implemented* | **Missing** | No implementation. |
| **AG‑90: Executive Summary** | Final narrative synthesis across all findings; should prepare report sections ready for export. | *Not implemented* | **Missing** | No implementation. |

### Summary of agent implementation status

- **Implemented agents:** AG‑00, AG‑01, AG‑10, AG‑11, AG‑20.  
- **Missing agents:** AG‑21, AG‑30, AG‑31, AG‑40, AG‑41, AG‑42, AG‑50, AG‑51, AG‑60, AG‑61, AG‑62, AG‑70, AG‑71, AG‑72, AG‑80, AG‑81, AG‑82, AG‑83, AG‑90.  
- **Partially configured pipeline:** The DAG only includes AG‑00, AG‑01 and AG‑10; AG‑11 is run by orchestrator but not listed in the DAG config. Later steps are absent from DAG.  
- **Export subsystem:** There is no implementation of exporters (report builder, entities exporter, cross‑reference exporter) even though JSON schemas exist in `configs/contracts/`.  
- **Registry and identity model:** No `src/registry/` module exists; there is no central entity registry for deduplication and cross‑step identity resolution despite being described in architecture docs.【955128760861358†L182-L199】.

This inventory establishes the foundation for a gap analysis and future implementation work.  Only after this comprehensive overview is acknowledged can we proceed to design and implement the missing parts needed to achieve a production‑ready, end‑to‑end pipeline with deterministic artefacts and final Exposé report.
