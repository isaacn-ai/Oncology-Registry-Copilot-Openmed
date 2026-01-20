from pathlib import Path
import re

path = Path("src/oncology_registry_copilot/evaluation.py")
t = path.read_text(encoding="utf-8", errors="replace")

# 1) Ensure we have `import re` at top-level (needed by stage_signal_present)
if not re.search(r"^\s*import re\s*$", t, flags=re.M):
    # Insert after pandas import
    t = t.replace("import pandas as pd\n", "import pandas as pd\nimport re\n")

# 2) Insert stage_signal_present() if missing (just before normalize_primary_site)
if "def stage_signal_present(" not in t:
    insert_point = "def normalize_primary_site"
    helper = '''
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
    if "stage" in s or re.search(r"\\bstg\\b", s):
        return True
    if re.search(r"\\bp?[Tt]\\d+[Nn]\\d+M\\d+\\b", s):
        return True
    return False

'''
    if insert_point not in t:
        raise SystemExit("ERROR: Could not find insertion point for helper.")
    t = t.replace(insert_point, helper + insert_point)

# 3) Patch compute_metrics(): skip stage rows without stage signal
needle_cm = "for _, r in df.iterrows():\n            gt = normalize_for_field(field, r.get(gt_col))"
if needle_cm in t:
    repl_cm = (
        "for _, r in df.iterrows():\n"
        "            note_text = r.get(\"note_text\")\n"
        "            if field == \"stage\" and not stage_signal_present(note_text):\n"
        "                continue\n\n"
        "            gt = normalize_for_field(field, r.get(gt_col))"
    )
    t = t.replace(needle_cm, repl_cm, 1)
else:
    raise SystemExit("ERROR: Could not find compute_metrics needle.")

# 4) Patch generate_error_report(): skip stage rows without stage signal
needle_er = "gt_norm = normalize_for_field(field, r.get(gt_col))"
if needle_er in t:
    repl_er = (
        "note_text = r.get(\"note_text\")\n\n"
        "            if field == \"stage\" and not stage_signal_present(note_text):\n"
        "                continue\n\n"
        "            gt_norm = normalize_for_field(field, r.get(gt_col))"
    )
    t = t.replace(needle_er, repl_er, 1)
else:
    raise SystemExit("ERROR: Could not find error_report needle.")

path.write_text(t, encoding="utf-8", newline="\n")
print("patched evaluation.py (stage scorable rule) OK")
