from __future__ import annotations

from datetime import datetime, timezone
import os
from typing import Any, Dict


ISO_UTC_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime(ISO_UTC_FORMAT)


def _resolve_run_id(case_input: Dict[str, Any]) -> str:
    run_id = case_input.get("run_id")
    if isinstance(run_id, str) and run_id.strip():
        return run_id.strip()
    env_run_id = os.getenv("RUN_ID")
    if env_run_id:
        return env_run_id
    return "n/v"


def _resolve_pipeline_version(case_input: Dict[str, Any]) -> str:
    pipeline_version = case_input.get("pipeline_version")
    if isinstance(pipeline_version, str) and pipeline_version.strip():
        return pipeline_version.strip()
    git_sha = case_input.get("git_sha")
    if isinstance(git_sha, str) and git_sha.strip():
        return git_sha.strip()
    env_pipeline_version = os.getenv("PIPELINE_VERSION")
    if env_pipeline_version:
        return env_pipeline_version
    env_git_sha = os.getenv("GIT_SHA")
    if env_git_sha:
        return env_git_sha
    return "n/v"


def build_step_meta(
    *,
    case_input: Dict[str, Any],
    step_id: str,
    agent_name: str,
    started_at_utc: str,
    finished_at_utc: str,
) -> Dict[str, str]:
    return {
        "step_id": step_id,
        "agent_name": agent_name,
        "run_id": _resolve_run_id(case_input),
        "started_at_utc": started_at_utc,
        "finished_at_utc": finished_at_utc,
        "pipeline_version": _resolve_pipeline_version(case_input),
    }
