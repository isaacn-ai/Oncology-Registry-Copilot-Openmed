Write-Host ""
Write-Host "=== CI Check: Unit Tests + Pipeline + Eval + Artifact + Metric Regression Gate ==="
Write-Host ""

# [0/5] Unit tests first (fast fail)
Write-Host "[0/5] Run unit tests (pytest)"
python -m pytest -q
if ($LASTEXITCODE -ne 0) {
  Write-Error "Pytest failed."
  exit 1
}
Write-Host ""

# [1/5] Run full pipeline
Write-Host "[1/5] Run full pipeline"
python .\scripts\run_full_pipeline.py
if ($LASTEXITCODE -ne 0) {
  Write-Error "Full pipeline failed."
  exit 1
}
Write-Host ""

# [2/5] Run detailed evaluation
Write-Host "[2/5] Run detailed evaluation"
python .\scripts\run_detailed_eval.py
if ($LASTEXITCODE -ne 0) {
  Write-Error "Detailed evaluation failed."
  exit 1
}
Write-Host ""

# [3/5] Verify required artifacts exist and are non-empty
Write-Host "[3/5] Verify required artifacts exist and are non-empty"

$required = @(
  ".\outputs\ner_entities.jsonl",
  ".\data\processed\preabstract_with_evidence.csv",
  ".\outputs\evaluation\eval_metrics.csv",
  ".\outputs\evaluation\eval_errors.csv"
)

foreach ($p in $required) {
  if (!(Test-Path $p)) {
    Write-Error "Missing artifact: $p"
    exit 1
  }
  $len = (Get-Item $p).Length
  if ($len -le 0) {
    Write-Error "Empty artifact: $p"
    exit 1
  }
  Write-Host ("  OK: {0} ({1} bytes)" -f $p, $len)
}
Write-Host ""

# [4/5] Metric regression gate (fail if accuracy drops below thresholds)
Write-Host "[4/5] Metric regression gate (fail if accuracy drops below thresholds)"

$metricsPath = ".\outputs\evaluation\eval_metrics.csv"
if (!(Test-Path $metricsPath)) {
  Write-Error "Missing metrics file: $metricsPath"
  exit 1
}

$thresholds = @{
  "primary_site" = 0.90
  "histology"    = 0.90
  "stage"        = 0.60
  "er_status"    = 0.90
  "pr_status"    = 0.90
  "her2_status"  = 0.90
}

$rows = Import-Csv $metricsPath
foreach ($field in $thresholds.Keys) {
  $row = $rows | Where-Object { $_.field -eq $field } | Select-Object -First 1
  if ($null -eq $row) {
    Write-Error "Missing field in metrics: $field"
    exit 1
  }

  $acc = [double]$row.accuracy
  $thr = [double]$thresholds[$field]

  if ($acc -lt $thr) {
    Write-Error ("Regression: {0} accuracy {1:N3} < threshold {2:N3}" -f $field, $acc, $thr)
    exit 1
  } else {
    Write-Host ("  OK:   {0} accuracy {1:N3} >= threshold {2:N3}" -f $field, $acc, $thr)
  }
}
Write-Host ""

# [5/5] Success
Write-Host "[5/5] Success: CI checks passed."
