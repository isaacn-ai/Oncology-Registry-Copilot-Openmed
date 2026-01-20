import re
import pandas as pd
from pathlib import Path


def _norm(text: str) -> str:
    """
    Normalize text for robust evidence containment checks:
    - normalize line endings
    - normalize bullet formatting
    - collapse ALL whitespace (including newlines) to single spaces
    """
    s = str(text or "")
    s = s.replace("\r\n", "\n").replace("\r", "\n")

    # Normalize bullets: "\n - foo" and "\n-foo" -> "\n- foo"
    s = re.sub(r"\n\s*-\s*", "\n- ", s)

    # Collapse all whitespace (spaces, tabs, newlines) to single spaces
    s = re.sub(r"\s+", " ", s)

    return s.strip()


def test_evidence_snippets_are_substrings_of_note_text_normalized():
    """
    Clinical QA rationale:
    Evidence must be traceable. If we show an evidence snippet, it must appear
    in the actual note text after harmless formatting normalization.
    """
    path = Path("data/processed/preabstract_with_evidence.csv")
    assert path.exists(), "Expected pre-abstract CSV missing. Run pipeline first."

    df = pd.read_csv(path)

    evidence_cols = [c for c in df.columns if c.endswith("_evidence")]
    assert evidence_cols, "No evidence columns found (expected *_evidence columns)."

    for idx, row in df.iterrows():
        note_text = _norm(row.get("note_text", ""))

        for col in evidence_cols:
            ev = row.get(col, "")
            if pd.isna(ev) or ev is None:
                continue

            ev = str(ev).strip()
            if not ev:
                continue

            evn = _norm(ev)

            assert evn in note_text, (
                f"Evidence integrity failure at row={idx}, col={col}:\n"
                f"Evidence snippet not found in normalized note_text.\n"
                f"Evidence(norm): {evn!r}\n"
            )
