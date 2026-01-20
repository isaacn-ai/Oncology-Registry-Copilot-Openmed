import sys
import json
from pathlib import Path
from typing import Dict, Tuple

import pandas as pd

# Ensure the src/ directory is on the Python path so we can import our package
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from oncology_registry_copilot.field_mapping import map_note_to_fields


def load_entities(jsonl_path: Path) -> Dict[Tuple[str, str], dict]:
    """
    Load ner_entities.jsonl into a dict keyed by (case_id, note_id).
    """
    mapping: Dict[Tuple[str, str], dict] = {}
    with jsonl_path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            record = json.loads(line)
            key = (record["case_id"], record["note_id"])
            mapping[key] = record
    return mapping


def main() -> None:
    notes_path = Path("data/raw/synthetic_oncology_notes.csv")
    entities_path = Path("outputs/ner_entities.jsonl")
    output_path = Path("data/processed/preabstract_with_evidence.csv")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not notes_path.exists():
        raise FileNotFoundError(f"Notes CSV not found: {notes_path}")
    if not entities_path.exists():
        raise FileNotFoundError(f"NER output JSONL not found: {entities_path}")

    df_notes = pd.read_csv(notes_path)
    entities_map = load_entities(entities_path)

    records = []
    for _, row in df_notes.iterrows():
        case_id = row["case_id"]
        note_id = row["note_id"]
        note_text = row["note_text"]

        key = (case_id, note_id)
        ent_record = entities_map.get(key, {"entities": []})
        entities = ent_record.get("entities", [])

        field_dict = map_note_to_fields(note_text, entities)

        combined = dict(row)
        combined.update(field_dict)
        records.append(combined)

    df_out = pd.DataFrame(records)
    df_out.to_csv(output_path, index=False)
    print(f"Wrote pre-abstract CSV with {len(df_out)} rows to: {output_path}")


if __name__ == "__main__":
    main()
