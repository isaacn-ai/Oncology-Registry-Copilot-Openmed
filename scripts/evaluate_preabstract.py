from pathlib import Path
from typing import List

import pandas as pd


FIELDS_TO_EVALUATE = [
    "primary_site",
    "histology",
    "stage",
    "er_status",
    "pr_status",
    "her2_status",
]


def normalize(value):
    """
    Normalize values for fair comparison.
    """
    if pd.isna(value):
        return None
    return str(value).strip().lower()


def evaluate_field(df: pd.DataFrame, field: str) -> dict:
    gt_col = f"{field}_gt"
    pred_col = f"{field}_pred"

    correct = 0
    total = 0

    for _, row in df.iterrows():
        gt = normalize(row.get(gt_col))
        pred = normalize(row.get(pred_col))

        if gt is None:
            continue  # skip cases with no ground truth

        total += 1
        if gt == pred:
            correct += 1

    accuracy = correct / total if total > 0 else 0.0

    return {
        "field": field,
        "total_cases": total,
        "correct": correct,
        "accuracy": round(accuracy, 3),
    }


def main():
    input_path = Path("data/processed/preabstract_with_evidence.csv")

    if not input_path.exists():
        raise FileNotFoundError(f"Missing file: {input_path}")

    df = pd.read_csv(input_path)

    results: List[dict] = []
    for field in FIELDS_TO_EVALUATE:
        metrics = evaluate_field(df, field)
        results.append(metrics)

    results_df = pd.DataFrame(results)

    print("\n=== PRE-ABSTRACT EVALUATION REPORT ===\n")
    print(results_df.to_string(index=False))
    print("\n=====================================\n")


if __name__ == "__main__":
    main()
