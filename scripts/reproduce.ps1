# scripts/reproduce.ps1
# Reproducible end-to-end runner for the Oncology Registry Copilot (OpenMed)
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts\reproduce.ps1

$ErrorActionPreference = 'Stop'

Write-Host ''
Write-Host '=== Oncology Registry Copilot (OpenMed) - Reproduce Script ==='
Write-Host ''

# Ensure we're running from repo root even if invoked elsewhere
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

# Basic sanity checks
if (-not (Test-Path '.\.venv\Scripts\python.exe')) {
  Write-Host 'ERROR: Virtual environment not found at .\.venv'
  Write-Host 'Create it and install dependencies first:'
  Write-Host '  python -m venv .venv'
  Write-Host '  .\.venv\Scripts\Activate.ps1'
  Write-Host '  pip install -r requirements.txt'
  exit 1
}

$Py = '.\.venv\Scripts\python.exe'

Write-Host '[0/3] Environment'
& $Py --version
Write-Host ''

Write-Host '[1/3] Running full pipeline'
& $Py 'scripts\run_full_pipeline.py'
Write-Host ''

Write-Host '[2/3] Running detailed evaluation'
& $Py 'scripts\run_detailed_eval.py'
Write-Host ''

Write-Host '[3/3] Done.'
Write-Host 'Artifacts written to:'
Write-Host ' - outputs\ner_entities.jsonl'
Write-Host ' - data\processed\preabstract_with_evidence.csv'
Write-Host ' - outputs\evaluation\eval_metrics.csv'
Write-Host ' - outputs\evaluation\eval_errors.csv'
Write-Host ''
