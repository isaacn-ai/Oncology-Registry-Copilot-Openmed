import sys
from pathlib import Path

# Ensure src/ is importable when running from scripts/
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from oncology_registry_copilot.pipeline import (
    evaluate_preabstract,
    generate_preabstract_csv,
    run_ner_to_jsonl,
)


def main() -> None:
    notes_csv = Path("data/raw/synthetic_oncology_notes.csv")
    ner_jsonl = Path("outputs/ner_entities.jsonl")
    preabstract_csv = Path("data/processed/preabstract_with_evidence.csv")

    print("\n=== Oncology Registry Copilot (OpenMed) — Full Pipeline ===\n")

    print("[1/3] Running OpenMed NER -> JSONL")
    n = run_ner_to_jsonl(
        notes_csv=notes_csv,
        output_jsonl=ner_jsonl,
        model_name="oncology_detection_superclinical",
        confidence_threshold=0.55,
    )
    print(f"     Wrote entities for {n} notes -> {ner_jsonl}")

    print("\n[2/3] Generating pre-abstract CSV with evidence")
    m = generate_preabstract_csv(
        notes_csv=notes_csv,
        ner_jsonl=ner_jsonl,
        output_csv=preabstract_csv,
    )
    print(f"     Wrote {m} rows -> {preabstract_csv}")

    print("\n[3/3] Evaluating pre-abstract (normalized, v2)")
    report = evaluate_preabstract(preabstract_csv)
    print("\n=== PRE-ABSTRACT EVALUATION REPORT (NORMALIZED, v2) ===\n")
    print(report.to_string(index=False))
    print("\n======================================================\n")

    print("Outputs:")
    print(f" - NER entities JSONL: {ner_jsonl}")
    print(f" - Pre-abstract CSV:   {preabstract_csv}")
    print("\nDone.\n")


if __name__ == "__main__":
    main()
