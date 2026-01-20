from pathlib import Path
from typing import List, Optional

import pandas as pd


FIELDS_TO_EVALUATE = [
    "primary_site",
    "histology",
    "stage",
    "er_status",
    "pr_status",
    "her2_status",
]


def _norm_str(value) -> Optional[str]:
    if pd.isna(value):
        return None
    s = str(value).strip().lower()
    return s if s else None


def normalize_biomarker(value) -> str:
    """
    Registry-friendly normalization:
    - Treat blank/None as 'unknown'
    - Standardize to: positive / negative / unknown
    """
    s = _norm_str(value)
    if s is None:
        return "unknown"
    if "pos" in s:
        return "positive"
    if "neg" in s:
        return "negative"
    if s in {"unknown", "unk"}:
        return "unknown"
    return s


def normalize_stage(value) -> Optional[str]:
    """
    Normalize stage to a compact form (e.g., ii, iia, iv).

    Handles:
    - 'IV'
    - 'Stage IV (metastatic) non-small cell lung cancer'
    - TNM strings like 'pT3N0M0' -> mapped here to 'ii' for the demo dataset.
    """
    s = _norm_str(value)
    if s is None:
        return None

    import re

    # If string contains 'stage', extract roman numeral + optional letter
    m = re.search(r"\bstage\s+([ivx]{1,3}[ab]?)\b", s)
    if m:
        return m.group(1)

    # Normalize TNM for demo purposes: pT3N0M0 -> stage II
    compact = s.replace(" ", "").lower()
    if "pt3n0m0" in compact or "t3n0m0" in compact:
        return "ii"

    # Simple roman numerals like 'ii', 'iia', 'iv'
    m = re.search(r"\b([ivx]{1,3}[ab]?)\b", s)
    if m:
        return m.group(1)

    return s


def normalize_primary_site(value) -> Optional[str]:
    """
    Normalize primary site to a canonical coarse site class.
    """
    s = _norm_str(value)
    if s is None:
        return None

    if "breast" in s:
        return "breast"
    if "lung" in s or "lobe" in s:
        return "lung"
    if "colon" in s or "sigmoid" in s:
        return "colon"
    return s


def normalize_histology(value) -> Optional[str]:
    """
    Normalize histology by collapsing to key patterns such as:
    - adenocarcinoma
    - invasive ductal carcinoma
    """
    s = _norm_str(value)
    if s is None:
        return None

    if "adenocarcinoma" in s:
        return "adenocarcinoma"
    if "ductal carcinoma" in s or "invasive ductal carcinoma" in s:
        return "invasive ductal carcinoma"
    return s


def normalize_for_field(field: str, value):
    if field in {"er_status", "pr_status", "her2_status"}:
        return normalize_biomarker(value)
    if field == "stage":
        return normalize_stage(value)
    if field == "primary_site":
        return normalize_primary_site(value)
    if field == "histology":
        return normalize_histology(value)
    return _norm_str(value)


def evaluate_field(df: pd.DataFrame, field: str) -> dict:
    gt_col = f"{field}_gt"
    pred_col = f"{field}_pred"

    correct = 0
    total = 0

    for _, row in df.iterrows():
        gt = normalize_for_field(field, row.get(gt_col))
        pred = normalize_for_field(field, row.get(pred_col))

        if gt is None:
            continue

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
        results.append(evaluate_field(df, field))

    results_df = pd.DataFrame(results)

    print("\n=== PRE-ABSTRACT EVALUATION REPORT (NORMALIZED, v2) ===\n")
    print(results_df[["field", "total_cases", "correct", "accuracy"]].to_string(index=False))
    print("\n======================================================\n")


if __name__ == "__main__":
    main()
