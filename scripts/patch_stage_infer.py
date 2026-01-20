from pathlib import Path
import re

path = Path("src/oncology_registry_copilot/field_mapping.py")
t = path.read_text(encoding="utf-8", errors="replace")

pattern = re.compile(
    r"def infer_stage\(note_text: str, entities: List\[Dict\[str, Any\]\]\) -> FieldPrediction:.*?return FieldPrediction\(value=None, evidence_start=None, evidence_end=None\)\n",
    re.S,
)

new_fn = '''def infer_stage(note_text: str, entities: List[Dict[str, Any]]) -> FieldPrediction:
    """
    Stage inference.

    Clinical intent:
    - Prefer explicit stage mentions (e.g., "Stage IIA", "stage: II").
    - Otherwise, capture TNM strings (e.g., pT3N0M0).
    - Avoid false positives from stray roman numerals by requiring context.

    Normalization:
    - If we capture "Stage <X>", return just the code (e.g., "IIA").
    """

    # 1) Prefer explicit "Stage ..." mentions in the raw note text.
    stage_kw = re.compile(r"\\bstage\\b\\s*[:\\-]?\\s*([0-9]{1,2}|[IVX]{1,4})(\\s*[AB])?\\b", re.IGNORECASE)
    m = stage_kw.search(note_text)
    if m:
        code = (m.group(1) + (m.group(2) or "")).replace(" ", "").upper()
        return FieldPrediction(value=code, evidence_start=m.start(), evidence_end=m.end())

    # 2) If the NER produced a stage-like Cancer entity, use it.
    def is_stage_entity(ent: Dict[str, Any]) -> bool:
        if ent.get("label") != "Cancer":
            return False
        text = (ent.get("text") or "").strip()
        return text.lower().startswith("stage")

    best = _pick_best(entities, is_stage_entity)
    if best:
        raw = (best.get("text") or "").strip()
        m2 = re.search(r"\\bstage\\b\\s*[:\\-]?\\s*([0-9]{1,2}|[IVX]{1,4})(\\s*[AB])?\\b", raw, flags=re.IGNORECASE)
        if m2:
            code = (m2.group(1) + (m2.group(2) or "")).replace(" ", "").upper()
        else:
            code = raw
        return FieldPrediction(value=code, evidence_start=best.get("start"), evidence_end=best.get("end"))

    # 3) TNM style, e.g. pT3N0M0
    tnm_pattern = re.compile(r"\\bp?[Tt]\\d+[Nn]\\d+M\\d+\\b")
    m3 = tnm_pattern.search(note_text)
    if m3:
        return FieldPrediction(value=m3.group(0), evidence_start=m3.start(), evidence_end=m3.end())

    # 4) Contextual roman stage: require "stage" or "stg" prefix
    contextual = re.compile(r"(stage|stg)\\s*[:\\-]?\\s*([IVX]{1,4})(\\s*[AB])?\\b", re.IGNORECASE)
    m4 = contextual.search(note_text)
    if m4:
        code = (m4.group(2) + (m4.group(3) or "")).replace(" ", "").upper()
        return FieldPrediction(value=code, evidence_start=m4.start(), evidence_end=m4.end())

    return FieldPrediction(value=None, evidence_start=None, evidence_end=None)
'''

def _repl(_m: re.Match) -> str:
    # Insert literal text (no backslash-template interpretation)
    return new_fn + "\n"

t2, n = pattern.subn(_repl, t, count=1)
if n != 1:
    raise SystemExit(f"ERROR: Expected to replace 1 infer_stage block, replaced {n}")

path.write_text(t2, encoding="utf-8", newline="\n")
print("patched infer_stage OK")
