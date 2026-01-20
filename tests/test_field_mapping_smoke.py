import pandas as pd
from pathlib import Path


def test_preabstract_has_expected_columns():
    """
    Clinical QA rationale:
    - If these columns disappear, downstream reviewers/evaluators silently break.
    - This is a schema regression guardrail.
    """
    path = Path("data/processed/preabstract_with_evidence.csv")
    assert path.exists(), "Expected pre-abstract CSV missing. Run pipeline first."

    df = pd.read_csv(path)

    # Minimal schema contract for this project
    required_cols = [
        "case_id",
        "note_id",
        "note_type",
        "note_date",
        "note_text",
        "primary_site_pred",
        "histology_pred",
        "stage_pred",
        "er_status_pred",
        "pr_status_pred",
        "her2_status_pred",
    ]

    missing = [c for c in required_cols if c not in df.columns]
    assert not missing, f"Missing required columns: {missing}"

    # Basic sanity: we should have at least 1 row
    assert len(df) >= 1, "Pre-abstract CSV has zero rows."
