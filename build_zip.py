"""Build a production‑ready zip archive of the repository.

Run this script from the project root to produce `repo_production_ready.zip` containing
all files. It also generates a MANIFEST.json with SHA256 hashes for each file.
"""
import hashlib
import json
import os
from pathlib import Path
import zipfile


def compute_sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def build_manifest_and_zip(root: Path, zip_path: Path) -> None:
    manifest = {"files": {}}
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in root.rglob("*"):
            if file_path.is_file():
                rel_path = file_path.relative_to(root).as_posix()
                zf.write(file_path, rel_path)
                manifest["files"][rel_path] = compute_sha256(file_path)
    # Write manifest into zip
    manifest_json = json.dumps(manifest, indent=2)
    zf.writestr("MANIFEST.json", manifest_json)

    # Also write manifest to disk for inspection
    (root / "MANIFEST.json").write_text(manifest_json)


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent
    zip_path = project_root / "repo_production_ready.zip"
    build_manifest_and_zip(project_root, zip_path)
    print(f"Created zip archive at {zip_path}")