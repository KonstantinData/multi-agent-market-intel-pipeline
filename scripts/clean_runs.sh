#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: scripts/clean_runs.sh [options]

Options:
  --run-id <id>     Remove a specific run directory and its backups.
  --all             Remove all run directories under artifacts/runs.
  --dry-run         Print what would be removed without deleting.
  --yes             Required to confirm deletion.
  -h, --help        Show this help message.

Examples:
  scripts/clean_runs.sh --run-id local-case-20240101120000 --yes
  scripts/clean_runs.sh --all --yes
USAGE
}

run_id=""
all=false
dry_run=false
confirm=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --run-id)
      run_id="${2:-}"
      shift 2
      ;;
    --all)
      all=true
      shift
      ;;
    --dry-run)
      dry_run=true
      shift
      ;;
    --yes)
      confirm=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ "$all" == true && -n "$run_id" ]]; then
  echo "Use either --all or --run-id, not both." >&2
  exit 1
fi

if [[ "$all" == false && -z "$run_id" ]]; then
  echo "Specify --run-id or --all." >&2
  usage
  exit 1
fi

if [[ "$confirm" == false ]]; then
  echo "Refusing to delete without --yes." >&2
  exit 1
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
runs_root="$repo_root/artifacts/runs"

if [[ ! -d "$runs_root" ]]; then
  echo "Runs directory not found: $runs_root" >&2
  exit 1
fi

paths=()
if [[ "$all" == true ]]; then
  while IFS= read -r -d '' entry; do
    paths+=("$entry")
  done < <(find "$runs_root" -mindepth 1 -maxdepth 1 -print0)
else
  target="$runs_root/$run_id"
  if [[ -e "$target" ]]; then
    paths+=("$target")
  fi
  while IFS= read -r -d '' entry; do
    paths+=("$entry")
  done < <(find "$runs_root" -mindepth 1 -maxdepth 1 -name "${run_id}.bak-*" -print0)
fi

if [[ ${#paths[@]} -eq 0 ]]; then
  echo "No run directories matched." >&2
  exit 0
fi

if [[ "$dry_run" == true ]]; then
  printf '%s\n' "Would remove:" "${paths[@]}"
  exit 0
fi

rm -rf "${paths[@]}"
printf 'Removed %d run directories.\n' "${#paths[@]}"
