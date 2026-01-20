from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import re


DEFAULT_FIELDS = [
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
    s = _norm_str(value)
    if s is None:
        return None

    import re

    m = re.search(r"\bstage\s+([ivx]{1,3}[ab]?)\b", s)
    if m:
        return m.group(1)

    compact = s.replace(" ", "").lower()
    if "pt3n0m0" in compact or "t3n0m0" in compact:
        return "ii"

    m = re.search(r"\b([ivx]{1,3}[ab]?)\b", s)
    if m:
        return m.group(1)

    return s



def stage_signal_present(note_text) -> bool:
    """Return True if the note likely contains stage information.

    Clinical rationale:
    Do not score stage for notes that do not mention stage or TNM, to avoid
    incentivizing hallucinated stage.
    """
    if note_text is None:
        return False
    # pandas may give NaN floats
    try:
        import pandas as pd
        if pd.isna(note_text):
            return False
    except Exception:
        pass

    s = str(note_text).lower()
    if "stage" in s or re.search(r"\bstg\b", s):
        return True
    if re.search(r"\bp?[Tt]\d+[Nn]\d+M\d+\b", s):
        return True
    return False

def normalize_primary_site(value) -> Optional[str]:
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


@dataclass
class FieldMetrics:
    field: str
    support: int
    correct: int
    accuracy: float
    precision: float
    recall: float
    f1: float


def compute_metrics(df: pd.DataFrame, fields: Optional[List[str]] = None) -> pd.DataFrame:
    """
    Compute accuracy, precision, recall, and F1 per field.

    For multi-class fields, we compute micro-averaged precision/recall/F1
    across all non-null ground truth cases:
      - true positives = gt == pred
      - false positives = gt != pred AND pred not null
      - false negatives = gt != pred AND pred is null

    Note: This is a pragmatic, pipeline-level metric, not a token-level NER metric.
    """
    if fields is None:
        fields = DEFAULT_FIELDS

    rows: List[Dict[str, Any]] = []

    for field in fields:
        gt_col = f"{field}_gt"
        pred_col = f"{field}_pred"

        tp = 0
        fp = 0
        fn = 0
        total = 0
        correct = 0

        for _, r in df.iterrows():
            note_text = r.get("note_text")
            if field == "stage" and not stage_signal_present(note_text):
                continue

            gt = normalize_for_field(field, r.get(gt_col))
            pred = normalize_for_field(field, r.get(pred_col))

            if gt is None:
                continue

            total += 1

            if gt == pred:
                tp += 1
                correct += 1
            else:
                # Wrong prediction cases
                if pred is None:
                    fn += 1
                else:
                    fp += 1

        accuracy = (correct / total) if total else 0.0
        precision = (tp / (tp + fp)) if (tp + fp) else 0.0
        recall = (tp / (tp + fn)) if (tp + fn) else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0

        rows.append(
            {
                "field": field,
                "support": total,
                "correct": correct,
                "accuracy": round(accuracy, 3),
                "precision": round(precision, 3),
                "recall": round(recall, 3),
                "f1": round(f1, 3),
            }
        )

    return pd.DataFrame(rows)


def generate_error_report(df: pd.DataFrame, fields: Optional[List[str]] = None) -> pd.DataFrame:
    """
    Generate a case-level error report:
      - case_id, note_id, field
      - gt_value, pred_value
      - evidence snippet (if available)
    Only includes rows where gt is present and gt != pred (after normalization).
    """
    if fields is None:
        fields = DEFAULT_FIELDS

    errors: List[Dict[str, Any]] = []

    for _, r in df.iterrows():
        case_id = r.get("case_id")
        note_id = r.get("note_id")
        note_type = r.get("note_type")
        note_date = r.get("note_date")

        for field in fields:
            gt_col = f"{field}_gt"
            pred_col = f"{field}_pred"
            ev_col = f"{field}_evidence"

            note_text = r.get("note_text")

            if field == "stage" and not stage_signal_present(note_text):
                continue

            gt_norm = normalize_for_field(field, r.get(gt_col))
            pred_norm = normalize_for_field(field, r.get(pred_col))

            if gt_norm is None:
                continue

            if gt_norm != pred_norm:
                errors.append(
                    {
                        "case_id": case_id,
                        "note_id": note_id,
                        "note_type": note_type,
                        "note_date": note_date,
                        "field": field,
                        "gt_value_raw": r.get(gt_col),
                        "pred_value_raw": r.get(pred_col),
                        "gt_value_norm": gt_norm,
                        "pred_value_norm": pred_norm,
                        "evidence": r.get(ev_col),
                    }
                )

    return pd.DataFrame(errors)


def load_preabstract_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")
    return pd.read_csv(path)


def write_reports(
    metrics_df: pd.DataFrame,
    errors_df: pd.DataFrame,
    out_dir: Path,
) -> Tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)

    metrics_path = out_dir / "eval_metrics.csv"
    errors_path = out_dir / "eval_errors.csv"

    metrics_df.to_csv(metrics_path, index=False)
    errors_df.to_csv(errors_path, index=False)

    return metrics_path, errors_path
