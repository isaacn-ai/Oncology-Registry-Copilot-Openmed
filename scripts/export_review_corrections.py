from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd


FIELDS = ["primary_site", "histology", "stage", "er_status", "pr_status", "her2_status"]


def _read_json(fp: Path) -> dict:
    return json.loads(fp.read_text(encoding="utf-8"))


def _mtime_iso_utc(fp: Path) -> str:
    return datetime.fromtimestamp(fp.stat().st_mtime, tz=timezone.utc).isoformat()


def main() -> int:
    review_dir = Path("outputs/review")
    out_path = review_dir / "review_corrections_export.csv"

    if not review_dir.exists():
        print(f"[export] No review directory found: {review_dir}")
        return 1

    files = sorted(review_dir.glob("correction_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        print(f"[export] No correction JSON files found in: {review_dir}")
        return 1

    rows = []
    for fp in files:
        try:
            d = _read_json(fp)
        except Exception as e:
            print(f"[export] Skipping unreadable JSON: {fp.name} ({e})")
            continue

        row = {
            "file": fp.name,
            "reviewed_at_utc": d.get("reviewed_at_utc") or d.get("reviewed_at") or _mtime_iso_utc(fp),
            "case_id": d.get("case_id"),
            "note_id": d.get("note_id"),
            "note_type": d.get("note_type"),
            "note_date": d.get("note_date"),
            "source_csv": d.get("source_csv"),
            "notes": d.get("notes"),
        }

        orig = d.get("predictions_original") or {}
        edit = d.get("predictions_edited") or {}
        ev = d.get("evidence") or {}

        for f in FIELDS:
            row[f"orig_{f}"] = orig.get(f)
            row[f"edit_{f}"] = edit.get(f)
            row[f"evidence_{f}"] = ev.get(f)

        rows.append(row)

    df = pd.DataFrame(rows)

    # Sort newest first (best-effort)
    df["reviewed_at_sort"] = pd.to_datetime(df["reviewed_at_utc"], errors="coerce")
    df = df.sort_values(by="reviewed_at_sort", ascending=False).drop(columns=["reviewed_at_sort"])

    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)

    print(f"[export] Wrote {len(df)} rows -> {out_path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
