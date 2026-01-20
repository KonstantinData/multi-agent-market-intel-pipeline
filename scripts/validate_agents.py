#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import re
import sys


AGENT_DIR_RE = re.compile(r"^ag\\d{2}_.+")


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    agents_dir = repo_root / "src" / "agents"
    if not agents_dir.exists():
        print(f"Agents directory not found: {agents_dir}", file=sys.stderr)
        return 1

    agent_dirs = [
        path
        for path in agents_dir.iterdir()
        if path.is_dir() and AGENT_DIR_RE.match(path.name)
    ]
    invalid = [
        path
        for path in agents_dir.iterdir()
        if path.is_dir() and not AGENT_DIR_RE.match(path.name)
    ]

    if invalid:
        invalid_list = ", ".join(sorted(path.name for path in invalid))
        print(
            "Unexpected non-agent directories in src/agents: " f"{invalid_list}",
            file=sys.stderr,
        )
        return 1

    missing_agent_py = [path.name for path in agent_dirs if not (path / "agent.py").exists()]
    if missing_agent_py:
        missing_list = ", ".join(sorted(missing_agent_py))
        print(f"Missing agent.py in: {missing_list}", file=sys.stderr)
        return 1

    print(f"Validated {len(agent_dirs)} agent directories.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
