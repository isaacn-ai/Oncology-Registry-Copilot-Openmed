from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from openmed import analyze_text

from oncology_registry_copilot.field_mapping import map_note_to_fields


def run_ner_to_jsonl(
    notes_csv: Path,
    output_jsonl: Path,
    model_name: str = "oncology_detection_superclinical",
    confidence_threshold: float = 0.55,
) -> int:
    """
    Read notes CSV and write one JSON record per note with extracted entities.
    Returns number of notes processed.
    """
    if not notes_csv.exists():
        raise FileNotFoundError(f"Notes CSV not found: {notes_csv}")

    df = pd.read_csv(notes_csv)

    output_jsonl.parent.mkdir(parents=True, exist_ok=True)

    with output_jsonl.open("w", encoding="utf-8") as f:
        for _, row in df.iterrows():
            text = row["note_text"]

            result = analyze_text(
                text,
                model_name=model_name,
                confidence_threshold=confidence_threshold,
            )

            entities: List[Dict[str, Any]] = []
            for ent in result.entities:
                entities.append(
                    {
                        "label": ent.label,
                        "text": ent.text,
                        "confidence": float(ent.confidence),
                        "start": int(ent.start),
                        "end": int(ent.end),
                    }
                )

            record = {
                "case_id": row["case_id"],
                "note_id": row["note_id"],
                "note_type": row["note_type"],
                "note_date": row["note_date"],
                "entities": entities,
            }

            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    return len(df)


def load_entities_map(jsonl_path: Path) -> Dict[Tuple[str, str], Dict[str, Any]]:
    """
    Load ner_entities.jsonl into a dict keyed by (case_id, note_id).
    """
    if not jsonl_path.exists():
        raise FileNotFoundError(f"NER JSONL not found: {jsonl_path}")

    mapping: Dict[Tuple[str, str], Dict[str, Any]] = {}
    with jsonl_path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            record = json.loads(line)
            key = (record["case_id"], record["note_id"])
            mapping[key] = record
    return mapping


def generate_preabstract_csv(
    notes_csv: Path,
    ner_jsonl: Path,
    output_csv: Path,
) -> int:
    """
    Combine notes + entities -> predicted fields + evidence and write CSV.
    Returns number of notes processed.
    """
    if not notes_csv.exists():
        raise FileNotFoundError(f"Notes CSV not found: {notes_csv}")
    if not ner_jsonl.exists():
        raise FileNotFoundError(f"NER JSONL not found: {ner_jsonl}")

    df_notes = pd.read_csv(notes_csv)
    entities_map = load_entities_map(ner_jsonl)

    output_csv.parent.mkdir(parents=True, exist_ok=True)

    records: List[Dict[str, Any]] = []
    for _, row in df_notes.iterrows():
        case_id = row["case_id"]
        note_id = row["note_id"]
        note_text = row["note_text"]

        key = (case_id, note_id)
        ent_record = entities_map.get(key, {"entities": []})
        entities = ent_record.get("entities", [])

        mapped = map_note_to_fields(note_text, entities)

        combined = dict(row)
        combined.update(mapped)
        records.append(combined)

    df_out = pd.DataFrame(records)
    df_out.to_csv(output_csv, index=False)

    return len(df_out)


# -----------------------------
# Evaluation (Normalized, v2)
# -----------------------------

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


def evaluate_preabstract(
    preabstract_csv: Path,
    fields: Optional[List[str]] = None,
) -> pd.DataFrame:
    """
    Return a DataFrame with evaluation metrics per field.
    """
    if not preabstract_csv.exists():
        raise FileNotFoundError(f"Missing file: {preabstract_csv}")

    df = pd.read_csv(preabstract_csv)

    if fields is None:
        fields = [
            "primary_site",
            "histology",
            "stage",
            "er_status",
            "pr_status",
            "her2_status",
        ]

    rows: List[Dict[str, Any]] = []
    for field in fields:
        gt_col = f"{field}_gt"
        pred_col = f"{field}_pred"

        correct = 0
        total = 0

        for _, r in df.iterrows():
            gt = normalize_for_field(field, r.get(gt_col))
            pred = normalize_for_field(field, r.get(pred_col))

            if gt is None:
                continue

            total += 1
            if gt == pred:
                correct += 1

        acc = correct / total if total > 0 else 0.0

        rows.append(
            {
                "field": field,
                "total_cases": total,
                "correct": correct,
                "accuracy": round(acc, 3),
            }
        )

    return pd.DataFrame(rows)
