import pandas as pd
from openmed import analyze_text


def run_basic_ner() -> None:
    """
    Load synthetic oncology notes and run OpenMed NER on each note.

    This is our first end-to-end smoke test:
    - Read CSV
    - Call OpenMed's analyze_text
    - Print entities for inspection
    """
    # Load the CSV file
    df = pd.read_csv("data/raw/synthetic_oncology_notes.csv")

    # Loop over each note
    for _, row in df.iterrows():
        case_id = row["case_id"]
        note_id = row["note_id"]
        note_type = row["note_type"]
        text = row["note_text"]

        print("=" * 80)
        print(f"Case {case_id} | Note {note_id} | Type: {note_type}")
        print("-" * 80)

        # Call OpenMed NER – we use an oncology-focused model
        result = analyze_text(
            text,
            model_name="oncology_detection_superclinical",
            confidence_threshold=0.55,  # ignore very low-confidence hits
        )

        if not result.entities:
            print("No entities found.")
        else:
            for ent in result.entities:
                # Each entity has label, text, confidence, start, end, etc.
                print(f"{ent.label:<18} {ent.text:<45} {ent.confidence:.2f}")

        print()  # blank line between notes


if __name__ == "__main__":
    run_basic_ner()
