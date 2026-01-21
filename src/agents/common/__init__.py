"""Backward-compatible shim for shared agent utilities.

Prefer importing from ``src.agent_common``. This package re-exports modules
to avoid breaking legacy imports like ``src.agents.common.base_agent``.
"""

from __future__ import annotations

from importlib import import_module
import sys

_CANONICAL_PACKAGE = "src.agent_common"
_MODULES = (
    "base_agent",
    "env_keys",
    "file_utils",
    "step_meta",
    "text_normalization",
)

for _module in _MODULES:
    _target = import_module(f"{_CANONICAL_PACKAGE}.{_module}")
    _shim_name = f"{__name__}.{_module}"
    sys.modules[_shim_name] = _target
    setattr(sys.modules[__name__], _module, _target)

__all__ = list(_MODULES)
