from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

# Ensure src/ is importable when running this script directly (Windows-friendly).
REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from oncology_registry_copilot.evaluation import compute_metrics  # noqa: E402


def main() -> None:
    input_path = REPO_ROOT / "data" / "processed" / "preabstract_with_evidence.csv"
    if not input_path.exists():
        raise FileNotFoundError(
            f"Missing file: {input_path}\n"
            "Run the pipeline first:\n"
            "  python scripts/run_full_pipeline.py\n"
            "or:\n"
            "  powershell -ExecutionPolicy Bypass -File scripts/reproduce.ps1"
        )

    df = pd.read_csv(input_path)

    # Use the shared evaluator (single source of truth)
    metrics_df = compute_metrics(df)

    print("\n=== PRE-ABSTRACT EVALUATION REPORT (NORMALIZED, v3 - shared evaluator) ===\n")
    print(metrics_df[["field", "support", "correct", "accuracy"]].to_string(index=False))
    print("\n======================================================\n")


if __name__ == "__main__":
    main()
