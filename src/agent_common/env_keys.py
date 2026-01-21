from __future__ import annotations

import os
from collections.abc import Mapping, MutableMapping

CANONICAL_OPENAI_API_KEY = "OPENAI_API_KEY"
LEGACY_OPENAI_API_KEYS = ("OPENAI_KEY", "OPEN-AI-KEY")


def apply_openai_api_key_compat(env: MutableMapping[str, str]) -> None:
    """Ensure canonical key is populated from legacy keys without overwriting."""
    if env.get(CANONICAL_OPENAI_API_KEY):
        return
    for legacy_key in LEGACY_OPENAI_API_KEYS:
        legacy_value = env.get(legacy_key, "").strip()
        if legacy_value:
            env[CANONICAL_OPENAI_API_KEY] = legacy_value
            return


def resolve_openai_api_key(env: Mapping[str, str] | None = None) -> str:
    """Return the OpenAI API key from canonical or legacy variables."""
    source = env if env is not None else os.environ
    key = source.get(CANONICAL_OPENAI_API_KEY, "").strip()
    if key:
        return key
    for legacy_key in LEGACY_OPENAI_API_KEYS:
        legacy_value = source.get(legacy_key, "").strip()
        if legacy_value:
            return legacy_value
    return ""
