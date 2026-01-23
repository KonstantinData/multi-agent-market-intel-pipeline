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


def tail_log(log_path: Path, max_lines: int = 200) -> str:
    if not log_path.exists():
        return "(no logs yet)"
    lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(lines[-max_lines:])


def archive_run(run_id: str) -> Path:
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


tab_intake, tab_monitor, tab_results = st.tabs(["1) Intake", "2) Run Monitor", "3) Results"])


# =====================================================
# 1) Intake
# =====================================================
with tab_intake:
    st.subheader("Intake (Required)")

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

    st.subheader("Intake (Optional)")
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

    # Live normalization preview (no artifacts written yet)
    company_name_canonical = normalize_whitespace(company_name_raw)
    domain_normalized = normalize_domain(web_domain_raw)
    domain_ok = bool(domain_normalized) and is_valid_domain(domain_normalized)
    entity_key_preview = build_entity_key_from_domain(domain_normalized) if domain_normalized else "domain:n/v"

    st.markdown("### Live Preview (No artifacts created yet)")
    st.code(
        "\n".join(
            [
                f"company_name_canonical: {company_name_canonical or 'n/v'}",
                f"web_domain_normalized: {domain_normalized or 'n/v'}",
                f"entity_key: {entity_key_preview}",
                f"domain_valid: {domain_ok}",
            ]
        )
    )

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
        st.session_state.show_preview = False
        st.session_state.draft_intake = None
        st.experimental_rerun()

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

    if st.session_state.show_preview and st.session_state.draft_intake is not None:
        st.divider()
        st.subheader("Confirmation Step (Artifacts will be created only after confirmation)")

        draft: IntakeCase = st.session_state.draft_intake
        preview_payload = asdict(draft)
        preview_payload["entity_key_preview"] = build_entity_key_from_domain(draft.web_domain)
        preview_payload["created_at_utc_preview"] = utc_now_iso()

        st.json(preview_payload)

        colX, colY = st.columns([1, 1])
        with colX:
            confirm_btn = st.button("Confirm & Create Run", type="primary")
        with colY:
            edit_btn = st.button("Edit")

        if edit_btn:
            st.session_state.show_preview = False
            st.success("Edit the fields above and press START RESEARCH again.")

        if confirm_btn:
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

            st.success(f"Run created: {run_id}")
            st.code(str(case_input_path))
            st.info("Go to Run Monitor -> Start Pipeline")


# =====================================================
# 2) Run Monitor
# =====================================================
with tab_monitor:
    st.subheader("Run Monitor")
    run_id = st.session_state.active_run_id

    if not run_id:
        st.info("No active run yet. Create a run in Intake first.")
    else:
        st.write(f"Active run_id: `{run_id}`")
        run_root = RUNS_DIR / run_id

        colA, colB, colC = st.columns([1, 1, 1])

        with colA:
            start_btn = st.button("Start Pipeline (subprocess)", type="primary")

        with colB:
            rerun_ag00_btn = st.button("Re-run AG-00 (using corrected input if present)")

        with colC:
            archive_btn = st.button("Archive run", type="secondary")

        if archive_btn:
            try:
                archived_path = archive_run(run_id)
                st.success(f"Archived run to: {archived_path}")
                st.session_state.active_run_id = None
                st.experimental_rerun()
            except Exception as e:
                st.error(f"Archive failed: {e}")

        # Start pipeline using case_input.json
        if start_btn:
            case_input_path = run_root / "meta" / "case_input.json"
            if not case_input_path.exists():
                st.error("case_input.json missing. Recreate the run.")
            else:
                try:
                    proc = start_pipeline_subprocess(run_id, case_input_path)
                    st.session_state.pipeline_proc_pid = proc.pid
                    st.success(f"Pipeline started. PID={proc.pid}")
                except FileNotFoundError:
                    st.error("Orchestrator entrypoint not found: src.orchestrator.run_pipeline")

        # Re-run AG-00 using corrected input if present
        if rerun_ag00_btn:
            corrected = run_root / "meta" / "case_corrected.json"
            case_file = corrected if corrected.exists() else (run_root / "meta" / "case_input.json")
            if not case_file.exists():
                st.error("No case file found to run AG-00.")
            else:
                try:
                    proc = start_pipeline_subprocess(run_id, case_file)
                    st.session_state.pipeline_proc_pid = proc.pid
                    st.success(f"AG-00 re-run started. PID={proc.pid} case_file={case_file.name}")
                except Exception as e:
                    st.error(f"Re-run failed: {e}")

        st.markdown("### Run folders")
        st.code(str(run_root))

        # Edit intake (Soft-Fix)
        st.markdown("### Edit Intake (Soft-Fix)")

        meta_dir = run_root / "meta"
        case_input_path = meta_dir / "case_input.json"
        corrected_path = meta_dir / "case_corrected.json"
        intake_history_dir = meta_dir / "intake_history"
        intake_history_dir.mkdir(parents=True, exist_ok=True)

        current_payload = {}
        if case_input_path.exists():
            try:
                current_payload = read_json(case_input_path)
            except Exception:
                current_payload = {}

        # If corrected exists, show it as current
        if corrected_path.exists():
            try:
                current_payload = read_json(corrected_path)
            except Exception:
                pass

        with st.form("edit_intake_form"):
            e_company_name = st.text_input("Company name *", value=str(current_payload.get("company_name", "")))
            e_web_domain = st.text_input("Web domain *", value=str(current_payload.get("web_domain", "")))
            e_city = st.text_input("City", value=str(current_payload.get("city") or ""))
            e_postal = st.text_input("Postal code", value=str(current_payload.get("postal_code") or ""))
            e_street = st.text_input("Street Address", value=str(current_payload.get("street_address") or ""))
            e_phone = st.text_input("Phone Number", value=str(current_payload.get("phone_number") or ""))
            e_industry = st.text_input("Industry", value=str(current_payload.get("industry") or ""))
            e_country = st.text_input("Country", value=str(current_payload.get("country") or ""))
            e_parent = st.text_input("Parent company", value=str(current_payload.get("parent_company") or ""))
            e_child = st.text_input("Child company", value=str(current_payload.get("child_company") or ""))
            
            st.write("**Regional Legal Identity Settings:**")
            col_e1, col_e2, col_e3 = st.columns(3)
            with col_e1:
                e_germany = st.checkbox("🇩🇪 Germany", value=current_payload.get("region_germany", True))
                e_dach = st.checkbox("🇦🇹🇨🇭 DACH", value=current_payload.get("region_dach", False))
            with col_e2:
                e_europe = st.checkbox("🇪🇺 Europe", value=current_payload.get("region_europe", False))
                e_uk = st.checkbox("🇬🇧 UK", value=current_payload.get("region_uk", False))
            with col_e3:
                e_usa = st.checkbox("🇺🇸 USA", value=current_payload.get("region_usa", False))

            save_correction = st.form_submit_button("Save correction (case_corrected.json)")

        if save_correction:
            # Audit trail: snapshot old files with timestamp
            ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            if case_input_path.exists():
                snap = intake_history_dir / f"{ts}__case_input.json"
                shutil.copyfile(case_input_path, snap)

            if corrected_path.exists():
                snap = intake_history_dir / f"{ts}__case_corrected.json"
                shutil.copyfile(corrected_path, snap)

            corrected_payload = {
                "company_name": normalize_whitespace(e_company_name),
                "web_domain": normalize_domain(e_web_domain),
                "city": normalize_whitespace(e_city) or None,
                "postal_code": normalize_whitespace(e_postal) or None,
                "street_address": normalize_whitespace(e_street) or None,
                "phone_number": normalize_whitespace(e_phone) or None,
                "industry": normalize_whitespace(e_industry) or None,
                "country": normalize_whitespace(e_country) or None,
                "parent_company": normalize_whitespace(e_parent) or None,
                "child_company": normalize_whitespace(e_child) or None,
                "region_germany": e_germany,
                "region_dach": e_dach,
                "region_europe": e_europe,
                "region_uk": e_uk,
                "region_usa": e_usa,
                "corrected_at_utc": utc_now_iso(),
            }

            # Validation: require correct domain before saving
            dn = corrected_payload["web_domain"]
            if not corrected_payload["company_name"]:
                st.error("company_name is required.")
            elif not dn or not is_valid_domain(dn):
                st.error("web_domain is invalid. Correction was not saved.")
            else:
                write_json(corrected_path, corrected_payload)
                st.success(f"Saved correction: {corrected_path.name}")
                st.info("Use 'Re-run AG-00' to regenerate normalized artifacts from corrected input.")

        # Logs
        log_path = run_root / "logs" / "pipeline.log"
        st.text_area("pipeline.log (tail)", tail_log(log_path), height=320)


# =====================================================
# 3) Results
# =====================================================
with tab_results:
    st.subheader("Results")
    run_id = st.session_state.active_run_id

    if not run_id:
        st.info("No active run yet.")
    else:
        run_root = RUNS_DIR / run_id
        exports_dir = run_root / "exports"
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
                    st.json(read_json(entities_path))
                except Exception:
                    st.error("entities.json exists but is not valid JSON.")
            else:
                st.info("entities.json not created yet.")
