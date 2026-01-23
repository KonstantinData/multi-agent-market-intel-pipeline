from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import streamlit as st


# -------------------------
# Paths
# -------------------------

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNS_DIR = REPO_ROOT / "artifacts" / "runs"
RUNS_ARCHIVE_DIR = REPO_ROOT / "artifacts" / "runs_archived"
DOTENV_PATH = REPO_ROOT / ".env"


# -------------------------
# Minimal .env loader (no deps, no secret logging)
# -------------------------

def _parse_dotenv_file(path: Path) -> dict[str, str]:
    """
    Parses .env lines like:
      KEY=value
      export KEY=value
      KEY="value"
      KEY='value'
    Ignores comments and blank lines.
    """
    out: dict[str, str] = {}
    if not path.exists() or not path.is_file():
        return out

    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return out

    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue

        if line.lower().startswith("export "):
            line = line[7:].strip()

        if "=" not in line:
            continue

        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip()

        if not k:
            continue

        # Strip surrounding quotes
        if len(v) >= 2 and ((v[0] == v[-1] == '"') or (v[0] == v[-1] == "'")):
            v = v[1:-1]

        out[k] = v

    return out


def _build_subprocess_env() -> dict[str, str]:
    """
    Builds subprocess env by merging:
      - current os.environ
      - REPO_ROOT/.env (only for keys not already present)

    Also mirrors OPEN-AI-KEY -> OPENAI_API_KEY if the latter is missing
    (keeps OPEN-AI-KEY as primary).
    """
    env = os.environ.copy()

    dotenv = _parse_dotenv_file(DOTENV_PATH)
    for k, v in dotenv.items():
        if k not in env:
            env[k] = v

    # Compatibility mirror (do not overwrite)
    if "OPEN-AI-KEY" in env and "OPENAI_API_KEY" not in env:
        env["OPENAI_API_KEY"] = env["OPEN-AI-KEY"]

    return env


# -------------------------
# Intake models
# -------------------------

@dataclass
class IntakeCase:
    # Required
    company_name: str
    web_domain: str

    # Optional
    city: Optional[str] = None
    postal_code: Optional[str] = None
    street_address: Optional[str] = None
    phone_number: Optional[str] = None
    industry: Optional[str] = None
    country: Optional[str] = None
    parent_company: Optional[str] = None
    child_company: Optional[str] = None
    
    # Regional Legal Identity Settings
    region_germany: bool = True
    region_dach: bool = False
    region_europe: bool = False
    region_uk: bool = False
    region_usa: bool = False


# -------------------------
# Helpers (validation + normalization)
# -------------------------

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_whitespace(text: str) -> str:
    return " ".join(text.strip().split())


def normalize_domain(domain: str) -> str:
    d = normalize_whitespace(domain).lower()
    d = d.replace("https://", "").replace("http://", "")
    d = d.split("/")[0]
    d = d.split("?")[0]
    d = d.split("#")[0]
    return d


def is_valid_domain(domain: str) -> bool:
    # Basic domain validation without external dependencies
    # Examples: liquisto.com, www.liquisto.com, sub.domain.co.uk
    import re

    pattern = re.compile(r"^(?=.{1,253}$)([a-z0-9-]{1,63}\.)+[a-z]{2,63}$")
    return bool(pattern.match(domain))


def build_entity_key_from_domain(domain: str) -> str:
    return f"domain:{domain}"


def build_run_id(web_domain: str) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    safe = normalize_domain(web_domain).replace(".", "_")
    return f"{ts}__{safe}"


def ensure_run_dirs(run_id: str) -> dict[str, Path]:
    run_root = RUNS_DIR / run_id
    meta_dir = run_root / "meta"
    logs_dir = run_root / "logs"
    exports_dir = run_root / "exports"
    steps_dir = run_root / "steps"
    intake_history_dir = meta_dir / "intake_history"

    meta_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    exports_dir.mkdir(parents=True, exist_ok=True)
    steps_dir.mkdir(parents=True, exist_ok=True)
    intake_history_dir.mkdir(parents=True, exist_ok=True)

    return {
        "run_root": run_root,
        "meta": meta_dir,
        "logs": logs_dir,
        "exports": exports_dir,
        "steps": steps_dir,
        "intake_history": intake_history_dir,
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def list_existing_domains_from_repo(max_scan: int = 200) -> list[str]:
    """
    Reads prior run domains to warn about typos.
    Scans artifacts/runs/*/meta/case_normalized.json if available,
    otherwise falls back to meta/case_input.json web_domain.
    """
    domains: list[str] = []
    if not RUNS_DIR.exists():
        return domains

    run_folders = sorted([p for p in RUNS_DIR.iterdir() if p.is_dir()], reverse=True)
    run_folders = run_folders[:max_scan]

    for run_root in run_folders:
        meta = run_root / "meta"
        cn = meta / "case_normalized.json"
        ci = meta / "case_input.json"

        try:
            if cn.exists():
                d = read_json(cn).get("web_domain_normalized")
                if isinstance(d, str) and d:
                    domains.append(d)
            elif ci.exists():
                d = read_json(ci).get("web_domain")
                if isinstance(d, str) and d:
                    domains.append(normalize_domain(d))
        except Exception:
            # ignore unreadable artifacts
            continue

    # de-dupe preserving order
    seen = set()
    uniq: list[str] = []
    for d in domains:
        if d not in seen:
            uniq.append(d)
            seen.add(d)
    return uniq


def levenshtein_distance(a: str, b: str) -> int:
    """
    Minimal Levenshtein distance implementation (no dependencies).
    """
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)

    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        curr = [i]
        for j, cb in enumerate(b, start=1):
            ins = curr[j - 1] + 1
            dele = prev[j] + 1
            sub = prev[j - 1] + (0 if ca == cb else 1)
            curr.append(min(ins, dele, sub))
        prev = curr
    return prev[-1]


def find_similar_domain_warning(domain: str) -> dict[str, Any]:
    """
    Domain typo defense:
    - compare against previously used domains in this repo
    - warn if Levenshtein distance <= 1
    """
    domain_n = normalize_domain(domain)
    known = list_existing_domains_from_repo()

    best_match = None
    best_dist = 999

    for d in known:
        dist = levenshtein_distance(domain_n, d)
        if dist < best_dist:
            best_dist = dist
            best_match = d

    if best_match is None:
        return {"warn": False}

    # Do not warn when the domain is identical
    if best_dist == 0:
        return {"warn": False}

    # Warn on very close typos
    if best_dist <= 1:
        return {"warn": True, "closest": best_match, "distance": best_dist}

    return {"warn": False}


def start_pipeline_subprocess(run_id: str, case_file: Path) -> subprocess.Popen:
    """
    Starts the orchestrator as a subprocess.
    Requires module: src.orchestrator.run_pipeline
    """
    cmd = [
        "python",
        "-m",
        "src.orchestrator.run_pipeline",
        "--run-id",
        run_id,
        "--case-file",
        str(case_file),
    ]

    run_log_path = RUNS_DIR / run_id / "logs" / "pipeline.log"
    log_f = open(run_log_path, "a", encoding="utf-8")  # noqa: SIM115

    proc = subprocess.Popen(
        cmd,
        cwd=str(REPO_ROOT),
        stdout=log_f,
        stderr=log_f,
        env=_build_subprocess_env(),
    )
    return proc


def get_pipeline_progress(run_root: Path) -> dict[str, Any]:
    """
    Calculate pipeline progress based on completed steps in the steps directory.
    """
    steps_dir = run_root / "steps"
    manifest_path = run_root / "manifest.json"
    
    # Expected steps from DAG
    expected_steps = [
        "AG-00", "AG-01", "AG-10", "AG-11", "AG-15", "AG-20", "AG-21",
        "AG-30", "AG-31", "AG-40", "AG-41", "AG-42", "AG-50", "AG-51",
        "AG-60", "AG-61", "AG-62", "AG-70", "AG-71", "AG-72", "AG-80",
        "AG-81", "AG-82", "AG-83", "AG-90"
    ]
    
    completed_steps = []
    if steps_dir.exists():
        for step_dir in steps_dir.iterdir():
            if step_dir.is_dir() and (step_dir / "output.json").exists():
                completed_steps.append(step_dir.name)
    
    # Check if pipeline is fully complete (manifest with exports exists)
    pipeline_complete = False
    if manifest_path.exists():
        try:
            manifest = read_json(manifest_path)
            exports = manifest.get("exports", [])
            pipeline_complete = len(exports) > 0
        except Exception:
            pass
    
    total_steps = len(expected_steps)
    completed_count = len(completed_steps)
    
    if pipeline_complete:
        progress = 1.0
        status = "completed"
    elif completed_count > 0:
        progress = completed_count / total_steps
        status = "running"
    else:
        progress = 0.0
        status = "not_started"
    
    return {
        "progress": progress,
        "status": status,
        "completed_steps": completed_count,
        "total_steps": total_steps,
        "completed_step_names": sorted(completed_steps),
        "pipeline_complete": pipeline_complete
    }
    """
    Moves artifacts/runs/<run_id> to artifacts/runs_archived/<run_id>
    """
    src = RUNS_DIR / run_id
    dst = RUNS_ARCHIVE_DIR / run_id
    RUNS_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    if not src.exists():
        raise FileNotFoundError(f"Run not found: {src}")

    if dst.exists():
        raise FileExistsError(f"Archive destination already exists: {dst}")

    shutil.move(str(src), str(dst))
    return dst


# -------------------------
# Streamlit UI
# -------------------------

st.set_page_config(
    page_title="Liquisto Market Intelligence Pipeline",
    page_icon="🔎",
    layout="wide",
)

st.title("Liquisto Market Intelligence Pipeline")


# Session state
if "active_run_id" not in st.session_state:
    st.session_state.active_run_id = None

if "pipeline_proc_pid" not in st.session_state:
    st.session_state.pipeline_proc_pid = None

if "draft_intake" not in st.session_state:
    st.session_state.draft_intake = None

if "show_preview" not in st.session_state:
    st.session_state.show_preview = False

if "pipeline_running" not in st.session_state:
    st.session_state.pipeline_running = False


if "current_tab" not in st.session_state:
    st.session_state.current_tab = "intake"

if "switch_to_monitor" not in st.session_state:
    st.session_state.switch_to_monitor = False

if "switch_to_results" not in st.session_state:
    st.session_state.switch_to_results = False


# Handle automatic tab switching
if st.session_state.switch_to_monitor:
    st.session_state.current_tab = "monitor"
    st.session_state.switch_to_monitor = False
    st.rerun()

if st.session_state.switch_to_results:
    st.session_state.current_tab = "results"
    st.session_state.switch_to_results = False
    st.rerun()

# Create tabs with active indication
if st.session_state.current_tab == "intake":
    tab_intake, tab_monitor, tab_results = st.tabs(["**1) Intake**", "2) Run Monitor", "3) Results"])
elif st.session_state.current_tab == "monitor":
    tab_intake, tab_monitor, tab_results = st.tabs(["1) Intake", "**2) Run Monitor**", "3) Results"])
else:
    tab_intake, tab_monitor, tab_results = st.tabs(["1) Intake", "2) Run Monitor", "**3) Results**"])


# Detect tab clicks and update current_tab
with tab_intake:
    st.session_state.current_tab = "intake"
    st.subheader("Intake (Required)")
    st.markdown("""
    <style>
    .stTextInput > div > div > input {
        font-size: 18px !important;
    }
    .stSelectbox > div > div > div {
        font-size: 18px !important;
    }
    .stCheckbox > label {
        font-size: 16px !important;
    }
    .stButton > button {
        font-size: 16px !important;
    }
    /* Dialog styling */
    .stDialog {
        font-size: 16px !important;
    }
    .stDialog .stJson {
        font-size: 14px !important;
    }
    </style>
    """, unsafe_allow_html=True)

    company_name_raw = st.text_input(
        "Company name *",
        placeholder="Liquisto Technologies GmbH",
        key="intake_company_name",
    )
    web_domain_raw = st.text_input(
        "Web domain *",
        placeholder="liquisto.com",
        key="intake_web_domain",
    )

    st.subheader("Intake (Optional - Wenn Headquarter Informationen bekannt bitte ergänzen)")
    col1, col2, col3 = st.columns(3)
    with col1:
        city = st.text_input("City", placeholder="Stuttgart", key="intake_city")
        postal_code = st.text_input("Postal code", placeholder="70173", key="intake_postal")
        street_address = st.text_input("Street Address", placeholder="Musterstraße 123", key="intake_street")
    with col2:
        country = st.text_input("Country", placeholder="Germany", key="intake_country")
        parent_company = st.text_input("Parent company", placeholder="n/v", key="intake_parent")
        phone_number = st.text_input("Phone Number", placeholder="+49 711 123456", key="intake_phone")
    with col3:
        child_company = st.text_input("Child company", placeholder="n/v", key="intake_child")
        industry = st.text_input("Industry", placeholder="Manufacturing", key="intake_industry")

    st.subheader("Legal Identity Research Regions")
    st.write("Select which regions to search for legal identity information:")
    
    col_reg1, col_reg2, col_reg3 = st.columns(3)
    with col_reg1:
        germany_enabled = st.checkbox("🇩🇪 Germany (AG-10.0)", value=True, key="region_germany", 
                                    help="German Impressum extraction with legal forms (GmbH, AG, SE, etc.)")
        dach_enabled = st.checkbox("🇦🇹🇨🇭 DACH Extension (AG-10.1)", value=False, key="region_dach",
                                 help="Austria & Switzerland legal forms and 4-digit postal codes")
    with col_reg2:
        europe_enabled = st.checkbox("🇪🇺 Europe (AG-10.2)", value=False, key="region_europe",
                                   help="European Union countries (SAS, SpA, BV, etc.)")
        uk_enabled = st.checkbox("🇬🇧 UK (AG-10.3)", value=False, key="region_uk",
                               help="United Kingdom legal forms (Ltd, PLC, LLP) and postcodes")
    with col_reg3:
        usa_enabled = st.checkbox("🇺🇸 USA (AG-10.4)", value=False, key="region_usa",
                                help="United States legal forms (Inc, Corp, LLC) and ZIP codes")

    # Live normalization preview - hidden from UI
    company_name_canonical = normalize_whitespace(company_name_raw)
    domain_normalized = normalize_domain(web_domain_raw)
    domain_ok = bool(domain_normalized) and is_valid_domain(domain_normalized)
    entity_key_preview = build_entity_key_from_domain(domain_normalized) if domain_normalized else "domain:n/v"

    # Hidden preview - no longer shown to user

    # Domain typo defense warning
    typo_info = {"warn": False}
    if domain_ok:
        typo_info = find_similar_domain_warning(domain_normalized)

    if typo_info.get("warn"):
        st.warning(
            f"This domain looks similar to '{typo_info.get('closest')}'. "
            f"Distance={typo_info.get('distance')}. Please confirm it is correct."
        )

    # START RESEARCH should be disabled if required fields invalid
    required_ok = bool(company_name_canonical) and domain_ok

    # If typo warning is present, require explicit confirmation
    confirm_domain_checkbox = False
    if typo_info.get("warn"):
        confirm_domain_checkbox = st.checkbox("I confirm the domain is correct (typo warning acknowledged)")

    start_disabled = (not required_ok) or (typo_info.get("warn") and not confirm_domain_checkbox)

    colA, colB = st.columns([1, 1])
    with colA:
        preview_btn = st.button("START RESEARCH", type="primary", disabled=start_disabled)

    with colB:
        reset_btn = st.button("Reset Intake")

    if reset_btn:
        # Clear all session state
        for key in list(st.session_state.keys()):
            if key.startswith(('intake_', 'region_')):
                del st.session_state[key]
        st.session_state.show_preview = False
        st.session_state.draft_intake = None
        st.rerun()

    # Confirmation step: Preview screen
    if preview_btn:
        draft = IntakeCase(
            company_name=company_name_canonical,
            web_domain=domain_normalized,
            city=normalize_whitespace(city) or None,
            postal_code=normalize_whitespace(postal_code) or None,
            street_address=normalize_whitespace(street_address) or None,
            phone_number=normalize_whitespace(phone_number) or None,
            industry=normalize_whitespace(industry) or None,
            country=normalize_whitespace(country) or None,
            parent_company=normalize_whitespace(parent_company) or None,
            child_company=normalize_whitespace(child_company) or None,
            region_germany=germany_enabled,
            region_dach=dach_enabled,
            region_europe=europe_enabled,
            region_uk=uk_enabled,
            region_usa=usa_enabled,
        )

        st.session_state.draft_intake = draft
        st.session_state.show_preview = True

    # Confirmation dialog trigger
    if st.session_state.show_preview and st.session_state.draft_intake is not None:
        
        @st.dialog("🔍 Confirmation Step (Artifacts)")
        def confirmation_dialog():
            draft: IntakeCase = st.session_state.draft_intake
            preview_payload = asdict(draft)
            
            # Replace None values with "keine Angaben" and boolean values
            for key, value in preview_payload.items():
                if value is None:
                    preview_payload[key] = "keine Angaben"
                elif isinstance(value, bool):
                    preview_payload[key] = "ausgewählt" if value else "nicht ausgewählt"
                    
            preview_payload["entity_key_preview"] = build_entity_key_from_domain(draft.web_domain)
            preview_payload["created_at_utc_preview"] = utc_now_iso()

            st.json(preview_payload)

            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("✅ Confirm & Create Run", type="primary", use_container_width=True):
                    run_id = build_run_id(draft.web_domain)
                    run_dirs = ensure_run_dirs(run_id)

                    # Write raw input as case_input.json
                    case_input_path = run_dirs["meta"] / "case_input.json"
                    raw_payload = asdict(draft)
                    raw_payload["created_at_utc"] = utc_now_iso()
                    write_json(case_input_path, raw_payload)

                    st.session_state.active_run_id = run_id
                    st.session_state.show_preview = False
                    st.session_state.draft_intake = None
                    st.session_state.switch_to_monitor = True

                    st.success(f"✅ Run created: {run_id}")
                    st.rerun()
                    
            with col2:
                if st.button("✏️ Edit", use_container_width=True):
                    st.session_state.show_preview = False
                    st.rerun()
        
        confirmation_dialog()


# =====================================================
# 2) Run Monitor
# =====================================================
with tab_monitor:
    st.session_state.current_tab = "monitor"
    st.subheader("📊 Run Monitor")
    run_id = st.session_state.active_run_id

    if not run_id:
        st.info("No active run yet. Create a run in Intake first.")
    else:
        st.write(f"Active run_id: `{run_id}`")
        run_root = RUNS_DIR / run_id

        # Start Pipeline button
        start_btn = st.button("🚀 Start Pipeline", type="primary")

        if start_btn:
            case_input_path = run_root / "meta" / "case_input.json"
            if not case_input_path.exists():
                st.error("case_input.json missing. Recreate the run.")
            else:
                try:
                    proc = start_pipeline_subprocess(run_id, case_input_path)
                    st.session_state.pipeline_proc_pid = proc.pid
                    st.success(f"✅ Pipeline started. PID={proc.pid}")
                    st.session_state.pipeline_running = True
                except FileNotFoundError:
                    st.error("Orchestrator entrypoint not found: src.orchestrator.run_pipeline")

        # Show loading animation when pipeline is running
        if st.session_state.get('pipeline_running', False):
            # Check if pipeline is actually complete
            progress_info = get_pipeline_progress(run_root)
            if progress_info["pipeline_complete"]:
                st.session_state.pipeline_running = False
            
            # Only show animation if still running
            if st.session_state.get('pipeline_running', False):
                st.markdown("""
                <style>
                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }
                .loading-spinner {
                    border: 4px solid #f3f3f3;
                    border-top: 4px solid #ff4b4b;
                    border-radius: 50%;
                    width: 50px;
                    height: 50px;
                    animation: spin 1s linear infinite;
                    margin: 20px auto;
                }
                .loading-text {
                    text-align: center;
                    font-size: 18px;
                    color: #ff4b4b;
                    margin-top: 10px;
                }
                </style>
                <div class="loading-spinner"></div>
                <div class="loading-text">🚀 Pipeline is running...</div>
                """, unsafe_allow_html=True)

        # Progress bar placeholder
        progress_placeholder = st.empty()
        
        # Check pipeline status and show progress
        progress_info = get_pipeline_progress(run_root)
        
        with progress_placeholder.container():
            if progress_info["pipeline_complete"]:
                st.session_state.pipeline_running = False
                st.progress(1.0, text="Pipeline completed successfully!")
                st.success("✅ Pipeline completed successfully!")
                st.balloons()
                
                # Auto-switch to Results tab
                st.session_state.switch_to_results = True
                st.rerun()
            elif progress_info["status"] == "running":
                progress = progress_info["progress"]
                completed = progress_info["completed_steps"]
                total = progress_info["total_steps"]
                
                st.progress(progress, text=f"Processing steps... ({completed}/{total} completed)")
                st.write(f"**Progress: {progress*100:.1f}% completed**")
                
                # Show last completed step
                if progress_info["completed_step_names"]:
                    last_step = progress_info["completed_step_names"][-1]
                    st.write(f"Last completed: {last_step}")
            else:
                st.info("Pipeline not started yet. Click 'Start Pipeline' to begin.")
        
        # Hidden background info - no longer shown
        # st.markdown("### Run folders")
        # st.code(str(run_root))

        # Logs
        log_path = run_root / "logs" / "pipeline.log"
        with st.expander("📄 View Pipeline Logs"):
            log_content = tail_log(log_path)
            if log_content == "(no logs yet)":
                st.info("No logs available yet. Pipeline may still be starting.")
            else:
                st.text_area("pipeline.log (tail)", log_content, height=320)


# =====================================================
# 3) Results
# =====================================================
with tab_results:
    st.session_state.current_tab = "results"
    st.subheader("📊 Results")
    run_id = st.session_state.active_run_id

    if not run_id:
        st.info("No active run yet.")
    else:
        run_root = RUNS_DIR / run_id
        exports_dir = run_root / "exports"
        report_path = exports_dir / "report.md"
        entities_path = exports_dir / "entities.json"

        # Check if results are available
        if not report_path.exists() and not entities_path.exists():
            st.info("🔄 Pipeline still running. Results will appear here when completed.")
        else:
            st.success("✅ Results are ready!")
            
            # Download buttons at the top
            col_dl1, col_dl2 = st.columns(2)
            
            with col_dl1:
                if report_path.exists():
                    st.download_button(
                        label="📊 Download Report (MD)",
                        data=report_path.read_text(encoding="utf-8"),
                        file_name=f"report_{run_id}.md",
                        mime="text/markdown",
                        type="primary",
                        use_container_width=True
                    )
            
            with col_dl2:
                if entities_path.exists():
                    st.download_button(
                        label="📊 Download Entities (JSON)",
                        data=entities_path.read_text(encoding="utf-8"),
                        file_name=f"entities_{run_id}.json",
                        mime="application/json",
                        use_container_width=True
                    )
            
            st.divider()
            
            # Display results in two columns
            col1, col2 = st.columns([1, 1])

            with col1:
                st.subheader("📄 Business Intelligence Report")
                if report_path.exists():
                    try:
                        report_content = report_path.read_text(encoding="utf-8")
                        st.markdown(report_content)
                    except Exception as e:
                        st.error(f"Error reading report: {e}")
                else:
                    st.info("Report not available yet.")

            with col2:
                st.subheader("📊 Entity Data (JSON)")
                if entities_path.exists():
                    try:
                        entities_data = read_json(entities_path)
                        st.json(entities_data)
                    except Exception as e:
                        st.error(f"Error reading entities: {e}")
                else:
                    st.info("Entity data not available yet.")
