$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "=== CI Check: Pipeline + Eval + Artifact + Metric Regression Gate ==="
Write-Host ""

# Ensure we're running from repo root
if (-not (Test-Path ".\scripts\run_full_pipeline.py")) {
  throw "Run this from the repo root (where .\scripts exists)."
}

Write-Host "[1/5] Run full pipeline"
python .\scripts\run_full_pipeline.py

Write-Host ""
Write-Host "[2/5] Run detailed evaluation"
python .\scripts\run_detailed_eval.py

Write-Host ""
Write-Host "[3/5] Verify required artifacts exist and are non-empty"
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
Write-Host "[4/5] Metric regression gate (fail if accuracy drops below thresholds)"
$thresholds = @{
  "primary_site" = 0.90
  "histology"    = 0.90
  "stage"        = 0.60
  "er_status"    = 0.90
  "pr_status"    = 0.90
  "her2_status"  = 0.90
}

$metricsPath = ".\outputs\evaluation\eval_metrics.csv"
$rows = Import-Csv $metricsPath

# Build lookup: field -> accuracy (as double)
$acc = @{}
foreach ($r in $rows) {
  $f = $r.field
  # Import-Csv reads numbers as strings; convert safely
  $a = [double]$r.accuracy
  $acc[$f] = $a
}

$failed = $false
foreach ($k in $thresholds.Keys) {
  if (-not $acc.ContainsKey($k)) {
    Write-Host ("  FAIL: missing metric row for field '{0}'" -f $k)
    $failed = $true
    continue
  }
  $a = $acc[$k]
  $t = $thresholds[$k]
  if ($a -lt $t) {
    Write-Host ("  FAIL: {0} accuracy {1:N3} < threshold {2:N3}" -f $k, $a, $t)
    $failed = $true
  } else {
    Write-Host ("  OK:   {0} accuracy {1:N3} >= threshold {2:N3}" -f $k, $a, $t)
  }
}

if ($failed) {
  throw "Metric regression gate failed. See messages above."
}

Write-Host ""
Write-Host "[5/5] Success: CI checks passed."
