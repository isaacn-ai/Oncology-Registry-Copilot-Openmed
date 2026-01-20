import sys
from pathlib import Path

# Ensure src/ is importable when running from scripts/
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from oncology_registry_copilot.evaluation import (
    compute_metrics,
    generate_error_report,
    load_preabstract_csv,
    write_reports,
)


def main() -> None:
    preabstract_csv = Path("data/processed/preabstract_with_evidence.csv")
    out_dir = Path("outputs/evaluation")

    df = load_preabstract_csv(preabstract_csv)

    metrics_df = compute_metrics(df)
    errors_df = generate_error_report(df)

    print("\n=== DETAILED EVALUATION METRICS ===\n")
    print(metrics_df.to_string(index=False))
    print("\n==================================\n")

    if len(errors_df) == 0:
        print("No errors found after normalization.\n")
    else:
        print("=== ERROR REPORT (first 25 rows) ===\n")
        print(errors_df.head(25).to_string(index=False))
        print("\n===================================\n")

    metrics_path, errors_path = write_reports(metrics_df, errors_df, out_dir)

    print("Wrote reports:")
    print(f" - {metrics_path}")
    print(f" - {errors_path}")
    print("\nDone.\n")


if __name__ == "__main__":
    main()
