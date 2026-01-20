from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

import pandas as pd
import streamlit as st

APP_TITLE = "Oncology Registry Copilot (OpenMed) — Reviewer UI"

DATA_PATH = Path("data/processed/preabstract_with_evidence.csv")
CORRECTIONS_DIR = Path("outputs/review")
CORRECTIONS_DIR.mkdir(parents=True, exist_ok=True)


FIELDS = [
    ("primary_site", "Primary site"),
    ("histology", "Histology"),
    ("stage", "Stage"),
    ("er_status", "ER status"),
    ("pr_status", "PR status"),
    ("her2_status", "HER2 status"),
]


def load_data() -> pd.DataFrame:
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Missing {DATA_PATH}. Run the pipeline first:\n"
            "  python scripts/run_full_pipeline.py\n"
            "or:\n"
            "  powershell -ExecutionPolicy Bypass -File scripts/reproduce.ps1"
        )
    df = pd.read_csv(DATA_PATH)
    return df


def safe_str(x) -> str:
    if pd.isna(x):
        return ""
    return str(x)


def save_correction(payload: Dict[str, Any]) -> Path:
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    case_id = payload.get("case_id", "unknown")
    note_id = payload.get("note_id", "unknown")
    path = CORRECTIONS_DIR / f"correction_{case_id}_{note_id}_{ts}.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, layout="wide")
    st.title(APP_TITLE)
    st.caption(
        "Review predicted registry fields with evidence, optionally correct them, and export corrections. "
        "Synthetic demo only."
    )

    df = load_data()

    # Sidebar: pick a case
    st.sidebar.header("Select a note")
    options = [
        f"{row.case_id} | {row.note_id} | {row.note_type} | {row.note_date}"
        for row in df.itertuples(index=False)
    ]
    selected = st.sidebar.selectbox("Case / Note", options, index=0)
    idx = options.index(selected)
    row = df.iloc[idx]

    # Main: show note context
    left, right = st.columns([2, 1], gap="large")

    with left:
        st.subheader("Clinical note (synthetic)")
        st.code(safe_str(row.get("note_text")), language="text")

    with right:
        st.subheader("Pre-abstract fields (review)")

        st.markdown("**Legend:** predicted value + evidence snippet; edit if needed.")
        st.write("")

        # Build an editable review form
        with st.form("review_form", clear_on_submit=False):
            edited: Dict[str, str] = {}
            evidence: Dict[str, str] = {}

            for field_key, field_label in FIELDS:
                pred_col = f"{field_key}_pred"
                ev_col = f"{field_key}_evidence"
                gt_col = f"{field_key}_gt"

                pred_val = safe_str(row.get(pred_col))
                ev_val = safe_str(row.get(ev_col))
                gt_val = safe_str(row.get(gt_col))

                st.markdown(f"### {field_label}")

                c1, c2 = st.columns([1, 1])
                with c1:
                    edited[field_key] = st.text_input(
                        f"{field_label} (editable)",
                        value=pred_val,
                        key=f"edit_{field_key}",
                        help="Edit the predicted value if needed.",
                    )
                with c2:
                    st.text_input(
                        f"{field_label} ground truth (demo only)",
                        value=gt_val,
                        key=f"gt_{field_key}",
                        disabled=True,
                    )

                st.caption("Evidence snippet")
                st.text_area(
                    f"Evidence for {field_label}",
                    value=ev_val,
                    key=f"ev_{field_key}",
                    height=70,
                    disabled=True,
                )

                evidence[field_key] = ev_val
                st.divider()

            accept = st.checkbox(
                "I confirm the edited values above (save correction record).",
                value=False,
            )
            submitted = st.form_submit_button("Save review record")

        if submitted:
            if not accept:
                st.error("Please check the confirmation box before saving.")
            else:
                payload = {
                    "case_id": safe_str(row.get("case_id")),
                    "note_id": safe_str(row.get("note_id")),
                    "note_type": safe_str(row.get("note_type")),
                    "note_date": safe_str(row.get("note_date")),
                    "source_csv": str(DATA_PATH),
                    "reviewed_at_utc": datetime.utcnow().isoformat(timespec="seconds") + "Z",
                    "predictions_original": {
                        k: safe_str(row.get(f"{k}_pred")) for k, _ in FIELDS
                    },
                    "predictions_edited": edited,
                    "evidence": evidence,
                    "notes": "Synthetic demo review record. Not clinical use.",
                }
                out_path = save_correction(payload)
                st.success(f"Saved: {out_path}")

        st.subheader("Export / Next steps")
        st.write(
            "Saved corrections are written locally to `outputs/review/` as JSON. "
            "In a real system, these would feed a human-in-the-loop training loop or QA process."
        )

    st.sidebar.divider()
    st.sidebar.subheader("Run instructions")
    st.sidebar.code(
        "streamlit run app/app.py\n\n"
        "If data is missing, run:\n"
        "python scripts/run_full_pipeline.py\n"
        "or:\n"
        "powershell -ExecutionPolicy Bypass -File scripts/reproduce.ps1",
        language="text",
    )


if __name__ == "__main__":
    main()
