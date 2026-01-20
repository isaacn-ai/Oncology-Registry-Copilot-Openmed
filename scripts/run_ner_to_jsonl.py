import json
from pathlib import Path

import pandas as pd
from openmed import analyze_text


def main() -> None:
    input_csv = Path("data/raw/synthetic_oncology_notes.csv")
    output_path = Path("outputs/ner_entities.jsonl")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(input_csv)

    with output_path.open("w", encoding="utf-8") as f:
        for _, row in df.iterrows():
            text = row["note_text"]

            result = analyze_text(
                text,
                model_name="oncology_detection_superclinical",
                confidence_threshold=0.55,
            )

            entities = []
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

    print(f"Wrote {len(df)} records to: {output_path}")


if __name__ == "__main__":
    main()
