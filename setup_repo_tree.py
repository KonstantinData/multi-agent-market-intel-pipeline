from __future__ import annotations

from pathlib import Path
from typing import Iterable

REPO_NAME = "multi-agent-market-intel-pipeline"


# Files that should be created as binary placeholders (empty bytes).
BINARY_PLACEHOLDERS = {".png", ".jpg", ".jpeg", ".webp", ".pdf"}


def touch_file(path: Path) -> None:
    """
    Create an empty file if it does not exist.
    Uses binary mode for known binary placeholders to avoid invalid text encoding.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        return

    if path.suffix.lower() in BINARY_PLACEHOLDERS:
        path.write_bytes(b"")
    else:
        path.write_text("", encoding="utf-8")


def touch_files(repo_root: Path, relative_paths: Iterable[str]) -> None:
    for rel in relative_paths:
        touch_file(repo_root / rel)


def create_repo_tree(repo_root: Path) -> None:
    # ---------------------------------------------------------------------
    # Top-level files
    # ---------------------------------------------------------------------
    top_files = [
        "README.md",
        "LICENSE",
        "CHANGELOG.md",
        ".env.example",
        "pyproject.toml",
        "requirements.txt",
        "requirements-dev.txt",
    ]
    touch_files(repo_root, top_files)

    # ---------------------------------------------------------------------
    # .github workflows and governance templates
    # ---------------------------------------------------------------------
    github_files = [
        ".github/workflows/ci.yml",
        ".github/workflows/pipeline_manual_run.yml",
        ".github/pull_request_template.md",
        ".github/ISSUE_TEMPLATE/feature_request.yml",
        ".github/ISSUE_TEMPLATE/bug_report.yml",
        ".github/ISSUE_TEMPLATE/governance_finding.yml",
        ".github/ISSUE_TEMPLATE/config.yml",
    ]
    touch_files(repo_root, github_files)

    # ---------------------------------------------------------------------
    # docs
    # ---------------------------------------------------------------------
    docs_files = [
        # Architecture docs
        "docs/architecture/00_overview.md",
        "docs/architecture/01_workflow_parallel_dag.md",
        "docs/architecture/02_output_contracts.md",
        "docs/architecture/03_entity_registry_and_id_policy.md",
        "docs/architecture/04_validation_and_gatekeeping.md",
        "docs/architecture/05_run_artifacts_and_auditability.md",
        # ADRs (Governance / decision traceability)
        "docs/adr/ADR-000-index.md",
        "docs/adr/ADR-001-parallel-fanout-fanin.md",
        "docs/adr/ADR-002-contract-gated-validation.md",
        "docs/adr/ADR-003-central-entity-registry-and-ids.md",
        "docs/adr/ADR-004-run-artifact-model.md",
        # Diagrams
        "docs/diagrams/workflow_parallel.drawio",
        "docs/diagrams/workflow_parallel.png",
        # Examples
        "docs/examples/example_input_case.json",
        "docs/examples/example_step_output.json",
        "docs/examples/example_validator_result.json",
        "docs/examples/example_entity_registry.json",
    ]
    touch_files(repo_root, docs_files)

    # ---------------------------------------------------------------------
    # configs (pipeline + contracts + rules)
    # ---------------------------------------------------------------------
    configs_files = [
        # pipeline configs
        "configs/pipeline/dag.yml",
        "configs/pipeline/step_contracts.yml",
        "configs/pipeline/retry_policy.yml",
        "configs/pipeline/output_paths.yml",
        "configs/pipeline/concurrency_limits.yml",
        # contracts
        "configs/contracts/entity_schema.json",
        "configs/contracts/step_output_schema.json",
        "configs/contracts/validator_result_schema.json",
        "configs/contracts/source_schema.json",
        "configs/contracts/crossref_schema.json",
        "configs/contracts/report_section_schema.json",
        # rules
        "configs/rules/id_policy.yml",
        "configs/rules/normalization_rules.yml",
        "configs/rules/dedupe_rules.yml",
        "configs/rules/validator_rules.yml",
        "configs/rules/ascii_policy.yml",
    ]
    touch_files(repo_root, configs_files)

    # ---------------------------------------------------------------------
    # src structure
    # ---------------------------------------------------------------------
    src_files = [
        "src/__init__.py",
        # orchestrator
        "src/orchestrator/__init__.py",
        "src/orchestrator/run_pipeline.py",
        "src/orchestrator/dag_loader.py",
        "src/orchestrator/batch_scheduler.py",
        "src/orchestrator/step_runner.py",
        "src/orchestrator/barrier_manager.py",
        "src/orchestrator/retry_manager.py",
        "src/orchestrator/artifact_store.py",
        "src/orchestrator/run_context.py",
        "src/orchestrator/logger.py",
        # agents common
        "src/agents/__init__.py",
        "src/agents/common/__init__.py",
        "src/agents/common/base_agent.py",
        "src/agents/common/agent_types.py",
        "src/agents/common/io_models.py",
        "src/agents/common/self_validation.py",
        "src/agents/common/evidence.py",
        "src/agents/common/source_capture.py",
        "src/agents/common/text_normalization.py",
        # registry
        "src/registry/__init__.py",
        "src/registry/entity_registry.py",
        "src/registry/id_allocator.py",
        "src/registry/entity_key.py",
        "src/registry/deduper.py",
        "src/registry/merger.py",
        "src/registry/provenance.py",
        "src/registry/crossref_graph.py",
        # validator
        "src/validator/__init__.py",
        "src/validator/contract_validator.py",
        "src/validator/schema_validator.py",
        "src/validator/rule_validator.py",
        "src/validator/crossref_validator.py",
        "src/validator/source_validator.py",
        "src/validator/ascii_validator.py",
        "src/validator/error_codes.py",
        # exporters
        "src/exporters/__init__.py",
        "src/exporters/report_builder.py",
        "src/exporters/entities_exporter.py",
        "src/exporters/index_builder.py",
        "src/exporters/crossref_matrix_exporter.py",
    ]
    touch_files(repo_root, src_files)

    # ---------------------------------------------------------------------
    # Agents folders (clear function naming stays intact)
    # ---------------------------------------------------------------------
    agent_dirs = [
        "ag00_intake_normalization",
        "ag10_identity_legal",
        "ag11_company_size",
        "ag20_Size_Evaluator",
        "ag21_financial_development",
        "ag30_portfolio",
        "ag31_markets_focus",
        "ag40_target_customers",
        "ag41_peer_discovery",
        "ag42_customers_of_intake_company",
        "ag70_supply_chain_tech",
        "ag71_supply_chain_risks",
        "ag72_sustainability_circular",
        "ag81_industry_trends",
        "ag82_trade_fairs_events",
        "ag83_associations_memberships",
        "ag90_sales_playbook",
    ]

    for d in agent_dirs:
        touch_file(repo_root / f"src/agents/{d}/__init__.py")
        touch_file(repo_root / f"src/agents/{d}/agent.py")

    # AG-42 extras (Map-Reduce)
    touch_file(repo_root / "src/agents/ag42_customers_of_intake_company/map_tasks.py")
    touch_file(repo_root / "src/agents/ag42_customers_of_intake_company/reduce_merge.py")

    # ---------------------------------------------------------------------
    # scripts
    # ---------------------------------------------------------------------
    script_files = [
        "scripts/run_local.sh",
        "scripts/run_local.ps1",
        "scripts/validate_run.sh",
        "scripts/clean_runs.sh",
    ]
    touch_files(repo_root, script_files)

    # ---------------------------------------------------------------------
    # runs + assets (NOT in src; runtime outputs / placeholders)
    # ---------------------------------------------------------------------
    (repo_root / "runs").mkdir(parents=True, exist_ok=True)
    touch_file(repo_root / "runs/.gitkeep")

    (repo_root / "assets").mkdir(parents=True, exist_ok=True)
    touch_file(repo_root / "assets/.gitkeep")

    # ---------------------------------------------------------------------
    # tests
    # ---------------------------------------------------------------------
    test_files = [
        "tests/__init__.py",
        "tests/unit/test_id_allocator.py",
        "tests/unit/test_dedupe_by_domain.py",
        "tests/unit/test_registry_merge_policy.py",
        "tests/unit/test_contract_validator_schema.py",
        "tests/unit/test_crossref_integrity.py",
        "tests/integration/test_pipeline_smoke.py",
    ]
    touch_files(repo_root, test_files)


def main() -> None:
    # If user is already inside the repo folder, do not nest it again.
    cwd = Path.cwd()

    if cwd.name == REPO_NAME:
        repo_root = cwd
    else:
        repo_root = cwd / REPO_NAME
        repo_root.mkdir(parents=True, exist_ok=True)

    create_repo_tree(repo_root)

    print(f"OK: Repo tree created/updated at: {repo_root}")


if __name__ == "__main__":
    main()
