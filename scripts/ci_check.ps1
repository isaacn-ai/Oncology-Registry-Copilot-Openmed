$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "=== CI Check: Pipeline + Eval + Artifact Verification ==="
Write-Host ""

# Ensure we're running from repo root
if (-not (Test-Path ".\scripts\run_full_pipeline.py")) {
  throw "Run this from the repo root (where .\scripts exists)."
}

Write-Host "[1/4] Run full pipeline"
python .\scripts\run_full_pipeline.py

Write-Host ""
Write-Host "[2/4] Run detailed evaluation"
python .\scripts\run_detailed_eval.py

Write-Host ""
Write-Host "[3/4] Verify required artifacts exist and are non-empty"
$required = @(
  ".\outputs\ner_entities.jsonl",
  ".\data\processed\preabstract_with_evidence.csv",
  ".\outputs\evaluation\eval_metrics.csv",
  ".\outputs\evaluation\eval_errors.csv"
)

foreach ($p in $required) {
  if (-not (Test-Path $p)) { throw "Missing required artifact: $p" }
  $len = (Get-Item $p).Length
  if ($len -le 0) { throw "Empty artifact: $p" }
  Write-Host ("  OK: {0} ({1} bytes)" -f $p, $len)
}

Write-Host ""
Write-Host "[4/4] Success: CI checks passed."
