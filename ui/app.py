from __future__ import annotations

import json
import os
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import streamlit as st


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNS_DIR = REPO_ROOT / "runs"


@dataclass
class IntakeCase:
    # Required
    company_name: str
    web_domain: str

    # Optional
    city: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    parent_company: Optional[str] = None
    child_company: Optional[str] = None


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_domain(domain: str) -> str:
    d = domain.strip().lower()
    d = d.replace("https://", "").replace("http://", "")
    d = d.split("/")[0]
    return d


def build_run_id(company_name: str, web_domain: str) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    safe = normalize_domain(web_domain).replace(".", "_")
    return f"{ts}__{safe}"


def ensure_run_dirs(run_id: str) -> dict[str, Path]:
    run_root = RUNS_DIR / run_id
    meta_dir = run_root / "meta"
    logs_dir = run_root / "logs"
    exports_dir = run_root / "exports"
    steps_dir = run_root / "steps"

    meta_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    exports_dir.mkdir(parents=True, exist_ok=True)
    steps_dir.mkdir(parents=True, exist_ok=True)

    return {
        "run_root": run_root,
        "meta": meta_dir,
        "logs": logs_dir,
        "exports": exports_dir,
        "steps": steps_dir,
    }


def write_case_input(run_dirs: dict[str, Path], intake: IntakeCase) -> Path:
    case_input_path = run_dirs["meta"] / "case_input.json"
    payload = asdict(intake)

    # Normalize domain early (AG-00 will still do canonical normalization)
    payload["web_domain"] = normalize_domain(payload["web_domain"])
    payload["created_at_utc"] = utc_now_iso()

    case_input_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return case_input_path


def start_pipeline_subprocess(run_id: str, case_input_path: Path) -> subprocess.Popen:
    """
    Starts the orchestrator as a subprocess.

    NOTE:
    This assumes you later implement an entrypoint like:
      python -m src.orchestrator.run_pipeline --run-id <run_id> --case-file <path>

    For now this is a placeholder.
    """
    cmd = [
        "python",
        "-m",
        "src.orchestrator.run_pipeline",
        "--run-id",
        run_id,
        "--case-file",
        str(case_input_path),
    ]

    run_log_path = RUNS_DIR / run_id / "logs" / "pipeline.log"
    log_f = open(run_log_path, "a", encoding="utf-8")  # noqa: SIM115

    proc = subprocess.Popen(
        cmd,
        cwd=str(REPO_ROOT),
        stdout=log_f,
        stderr=log_f,
        env=os.environ.copy(),
    )
    return proc


def tail_log(log_path: Path, max_lines: int = 200) -> str:
    if not log_path.exists():
        return "(no logs yet)"
    lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(lines[-max_lines:])


# -------------------------
# UI
# -------------------------

st.set_page_config(
    page_title="Liquisto Market Intelligence Pipeline",
    page_icon="🔎",
    layout="wide",
)

st.title("Liquisto Market Intelligence Pipeline")

if "active_run_id" not in st.session_state:
    st.session_state.active_run_id = None

if "pipeline_proc_pid" not in st.session_state:
    st.session_state.pipeline_proc_pid = None


tab_intake, tab_monitor, tab_results = st.tabs(["1) Intake", "2) Run Monitor", "3) Results"])

with tab_intake:
    st.subheader("Intake (Required)")
    with st.form("intake_form", clear_on_submit=False):
        company_name = st.text_input("Company name *", placeholder="Liquisto Technologies GmbH")
        web_domain = st.text_input("Web domain *", placeholder="liquisto.com")

        st.subheader("Intake (Optional)")
        col1, col2, col3 = st.columns(3)
        with col1:
            city = st.text_input("City", placeholder="Stuttgart")
            postal_code = st.text_input("Postal code", placeholder="70173")
        with col2:
            country = st.text_input("Country", placeholder="Germany")
            parent_company = st.text_input("Parent company", placeholder="n/v")
        with col3:
            child_company = st.text_input("Child company", placeholder="n/v")

        submitted = st.form_submit_button("START RESEARCH")

    if submitted:
        # Basic intake validation
        if not company_name.strip():
            st.error("company_name is required.")
        elif not web_domain.strip():
            st.error("web_domain is required.")
        else:
            intake = IntakeCase(
                company_name=company_name.strip(),
                web_domain=web_domain.strip(),
                city=city.strip() or None,
                postal_code=postal_code.strip() or None,
                country=country.strip() or None,
                parent_company=parent_company.strip() or None,
                child_company=child_company.strip() or None,
            )

            run_id = build_run_id(intake.company_name, intake.web_domain)
            run_dirs = ensure_run_dirs(run_id)
            case_input_path = write_case_input(run_dirs, intake)

            st.session_state.active_run_id = run_id

            st.success(f"Run created: {run_id}")
            st.code(str(case_input_path))

            st.info("Pipeline start is prepared, but requires src.orchestrator.run_pipeline implementation.")

            st.write("Generated case_input.json:")
            st.json(json.loads(case_input_path.read_text(encoding="utf-8")))


with tab_monitor:
    st.subheader("Run Monitor")
    run_id = st.session_state.active_run_id

    if not run_id:
        st.info("No active run yet. Go to Intake and start a run.")
    else:
        st.write(f"Active run_id: `{run_id}`")

        colA, colB = st.columns([1, 1])
        with colA:
            st.write("Actions")
            start_btn = st.button("Start Pipeline (subprocess)", type="primary")
            refresh_btn = st.button("Refresh Logs")

        with colB:
            st.write("Run folders")
            run_root = RUNS_DIR / run_id
            st.code(str(run_root))

        if start_btn:
            case_input_path = RUNS_DIR / run_id / "meta" / "case_input.json"
            if not case_input_path.exists():
                st.error("case_input.json missing. Recreate the run.")
            else:
                try:
                    proc = start_pipeline_subprocess(run_id, case_input_path)
                    st.session_state.pipeline_proc_pid = proc.pid
                    st.success(f"Pipeline started. PID={proc.pid}")
                except FileNotFoundError:
                    st.error("Orchestrator entrypoint not found. Implement src.orchestrator.run_pipeline first.")

        log_path = RUNS_DIR / run_id / "logs" / "pipeline.log"
        st.text_area("pipeline.log (tail)", tail_log(log_path), height=350)

        st.caption("Once the orchestrator is implemented, this monitor will show real-time progress per step.")


with tab_results:
    st.subheader("Results")
    run_id = st.session_state.active_run_id

    if not run_id:
        st.info("No active run yet. Start a run first.")
    else:
        exports_dir = RUNS_DIR / run_id / "exports"
        report_path = exports_dir / "report.md"
        entities_path = exports_dir / "entities.json"

        col1, col2 = st.columns(2)

        with col1:
            st.write("Report (report.md)")
            if report_path.exists():
                st.markdown(report_path.read_text(encoding="utf-8"))
            else:
                st.info("report.md not created yet.")

        with col2:
            st.write("Entities (entities.json)")
            if entities_path.exists():
                try:
                    st.json(json.loads(entities_path.read_text(encoding="utf-8")))
                except json.JSONDecodeError:
                    st.error("entities.json exists but is not valid JSON.")
            else:
                st.info("entities.json not created yet.")
