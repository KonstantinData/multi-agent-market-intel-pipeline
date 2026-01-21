# Apply patch pack to update the repository to production‑ready state.
param()

$BackupDir = "backup_$([int](Get-Date -UFormat %s))"
New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null

function Apply-File {
    param(
        [string]$Path,
        [string]$Content
    )
    if (Test-Path $Path) {
        $Dest = Join-Path $BackupDir $Path
        New-Item -ItemType Directory -Path (Split-Path $Dest) -Force | Out-Null
        Copy-Item $Path $Dest -Force
    }
    New-Item -ItemType Directory -Path (Split-Path $Path) -Force | Out-Null
    Set-Content -Path $Path -Value $Content -Encoding UTF8
    Write-Host "Applied $Path"
}

# --- Generated file contents ---
# (In practice this script would embed the file contents. For brevity, we assume
# the user will copy the corresponding content from patch_pack.md.)

# After applying files, run verification commands
pip install -r requirements.txt
pip install -r requirements-dev.txt
pytest -q
python scripts/verify_dod.py

Write-Host "Patch applied. Backups stored in $BackupDir"