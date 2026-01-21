"""
DESCRIPTION
-----------
step_validator provides a repo-wide gatekeeper for step outputs.
It enforces minimal invariants while staying backward-compatible with earlier step formats.

Policy:
- Always require: step_meta, entities_delta, relations_delta
- For AG-00 additionally require: case_normalized
- findings/sources/target_entity_stub are recommended but optional (warnings, not errors).
"""


from __future__ import annotations

from typing import Any, Dict, List


#note: Validate that a step output includes required high-level sections and types.
def validate_step_output(step_id: str, output: Dict[str, Any]) -> Dict[str, Any]:
    """
    #note: Returns a validator result payload:
      {
        "ok": bool,
        "errors": [...],
        "warnings": [...]
      }
    """
    errors: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []

    if not isinstance(output, dict):
        return {"ok": False, "errors": [{"code": "OUT-001", "message": "Output is not a dict"}], "warnings": []}

    #note: Minimal contract all steps must satisfy (legacy-compatible).
    required_keys = ["step_meta", "entities_delta", "relations_delta"]
    for k in required_keys:
        if k not in output:
            errors.append({"code": "OUT-002", "message": f"Missing required key: {k}"})

    #note: AG-00 is the foundation step and must emit case_normalized.
    if step_id == "AG-00" and "case_normalized" not in output:
        errors.append({"code": "AG00-001", "message": "AG-00 must emit case_normalized"})

    #note: Recommended keys (warnings only).
    recommended_keys = ["findings", "sources"]
    for k in recommended_keys:
        if k not in output:
            warnings.append({"code": "OUT-W01", "message": f"Recommended key missing: {k}"})

    #note: Type checks for core collections (if present).
    for k in ["entities_delta", "relations_delta", "findings", "sources"]:
        if k in output and not isinstance(output.get(k), list):
            errors.append({"code": "OUT-003", "message": f"Key must be a list: {k}"})

    #note: step_meta must include step_id and agent_name.
    step_meta = output.get("step_meta") or {}
    if not isinstance(step_meta, dict):
        errors.append({"code": "OUT-004", "message": "step_meta must be a dict"})
    else:
        if str(step_meta.get("step_id") or "") != str(step_id):
            errors.append({"code": "OUT-005", "message": "step_meta.step_id must match current step_id"})
        if not str(step_meta.get("agent_name") or "").strip():
            errors.append({"code": "OUT-006", "message": "step_meta.agent_name missing/empty"})

    return {"ok": len(errors) == 0, "errors": errors, "warnings": warnings}
