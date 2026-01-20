from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class FieldPrediction:
    value: Optional[str]
    evidence_start: Optional[int]
    evidence_end: Optional[int]

    def evidence_span(self, note_text: str, max_len: int = 160) -> Optional[str]:
        """
        Return a short evidence snippet from the note text.

        Clinical QA requirements:
        - Evidence must be traceable (verbatim) and not start mid-word.
        - Evidence should be display-friendly (single-line) but derived from note text.
        """
        if self.evidence_start is None or self.evidence_end is None:
            return None

        # Base window around the evidence span
        start = max(0, self.evidence_start - 40)
        end = min(len(note_text), self.evidence_end + 40)

        # Expand to word boundaries so we don't cut tokens like "breast" -> "ast"
        # Move start left until boundary (or max 80 chars)
        left_limit = max(0, self.evidence_start - 80)
        while start > left_limit and start < len(note_text) and note_text[start].isalnum():
            start -= 1

        # Move end right until boundary (or max 80 chars)
        right_limit = min(len(note_text), self.evidence_end + 80)
        while end < right_limit and end > 0 and end <= len(note_text) and end - 1 < len(note_text) and note_text[end - 1].isalnum():
            end += 1

        snippet_raw = note_text[start:end]

        # Normalize Windows line endings and collapse whitespace to single spaces
        s = snippet_raw.replace("\r\n", "\n").replace("\r", "\n")
        s = re.sub(r"\n\s*", " ", s)          # join lines cleanly
        s = re.sub(r"[ \t]+", " ", s).strip() # collapse spaces

        if len(s) > max_len:
            s = s[: max_len - 3].rstrip() + "..."
        return s


def _pick_best(
    entities: List[Dict[str, Any]],
    condition,
) -> Optional[Dict[str, Any]]:
    candidates = [e for e in entities if condition(e)]
    if not candidates:
        return None
    return max(candidates, key=lambda e: e.get("confidence", 0.0))


# ---------------------------
# Primary site
# ---------------------------


def infer_primary_site(note_text: str, entities: List[Dict[str, Any]]) -> FieldPrediction:
    """
    Heuristic primary site inference.

    Strategy:
    - Prefer Cancer / Organ entities that contain organ/site keywords.
    - Fallback: search raw text for those keywords.
    """
    site_keywords = [
        "left breast",
        "right breast",
        "breast",
        "right upper lobe",
        "lung",
        "sigmoid colon",
        "sigmoid",
        "colon",
    ]

    def has_site_keyword(ent: Dict[str, Any]) -> bool:
        if ent.get("label") not in {"Cancer", "Organ"}:
            return False
        lower = ent.get("text", "").lower()
        return any(kw in lower for kw in site_keywords)

    best = _pick_best(entities, has_site_keyword)
    if best:
        return FieldPrediction(
            value=best["text"],
            evidence_start=best["start"],
            evidence_end=best["end"],
        )

    # Fallback: direct keyword search in the note
    lower_text = note_text.lower()
    for kw in site_keywords:
        idx = lower_text.find(kw)
        if idx != -1:
            return FieldPrediction(
                value=kw,
                evidence_start=idx,
                evidence_end=idx + len(kw),
            )

    return FieldPrediction(value=None, evidence_start=None, evidence_end=None)


# ---------------------------
# Histology
# ---------------------------


def infer_histology(note_text: str, entities: List[Dict[str, Any]]) -> FieldPrediction:
    """
    Histology inference.

    Strategy:
    - Look for Cancer entities containing carcinoma/adenocarcinoma/lymphoma etc.
    """
    histology_terms = ["carcinoma", "adenocarcinoma", "sarcoma", "lymphoma"]

    def is_histology(ent: Dict[str, Any]) -> bool:
        if ent.get("label") != "Cancer":
            return False
        lower = ent.get("text", "").lower()
        return any(term in lower for term in histology_terms)

    best = _pick_best(entities, is_histology)
    if best:
        return FieldPrediction(
            value=best["text"],
            evidence_start=best["start"],
            evidence_end=best["end"],
        )

    # Fallback: regex in raw text
    pattern = re.compile(
        r"\b(\w+\s+(carcinoma|adenocarcinoma|sarcoma|lymphoma))\b",
        re.IGNORECASE,
    )
    m = pattern.search(note_text)
    if m:
        return FieldPrediction(
            value=m.group(0),
            evidence_start=m.start(),
            evidence_end=m.end(),
        )

    return FieldPrediction(value=None, evidence_start=None, evidence_end=None)


# ---------------------------
# Stage
# ---------------------------


def infer_stage(note_text: str, entities: List[Dict[str, Any]]) -> FieldPrediction:
    """
    Stage inference.

    Strategy:
    - Prefer Cancer entities starting with 'Stage'.
    - Also look for TNM-like strings such as pT3N0M0.
    """
    def is_stage_entity(ent: Dict[str, Any]) -> bool:
        if ent.get("label") != "Cancer":
            return False
        text = ent.get("text", "")
        return text.strip().lower().startswith("stage")

    best = _pick_best(entities, is_stage_entity)
    if best:
        return FieldPrediction(
            value=best["text"],
            evidence_start=best["start"],
            evidence_end=best["end"],
        )

    # TNM style, e.g. pT3N0M0
    tnm_pattern = re.compile(r"\bp?[Tt]\d+[Nn]\d+M\d+\b")
    m = tnm_pattern.search(note_text)
    if m:
        return FieldPrediction(
            value=m.group(0),
            evidence_start=m.start(),
            evidence_end=m.end(),
        )

    # Simple stage codes like II, IIA, IV
    simple_stage_pattern = re.compile(r"\b[IVX]{1,3}[AB]?\b")
    m = simple_stage_pattern.search(note_text)
    if m:
        return FieldPrediction(
            value=m.group(0),
            evidence_start=m.start(),
            evidence_end=m.end(),
        )

    return FieldPrediction(value=None, evidence_start=None, evidence_end=None)


# ---------------------------
# Biomarkers
# ---------------------------


def _find_marker_status(note_text: str, marker_patterns: List[str]) -> FieldPrediction:
    """
    Find biomarker status by looking just AFTER the marker name
    for 'positive' or 'negative'. This avoids windows that
    include other markers with opposite polarity.
    """
    text = note_text
    lower = text.lower()

    marker_regex = re.compile("|".join(marker_patterns), re.IGNORECASE)
    m = marker_regex.search(text)
    if not m:
        return FieldPrediction(value=None, evidence_start=None, evidence_end=None)

    # Look in a window AFTER the marker mention
    window_after = lower[m.end() : m.end() + 120]

    status = None

    pos_index = window_after.find("positive")
    neg_index = window_after.find("negative")

    # Determine which term appears first, if any
    if pos_index != -1 and (neg_index == -1 or pos_index < neg_index):
        status = "positive"
    elif neg_index != -1:
        status = "negative"

    return FieldPrediction(
        value=status,
        evidence_start=m.start(),
        evidence_end=m.end(),
    )


def infer_er_status(note_text: str) -> FieldPrediction:
    patterns = [r"estrogen receptor", r"\bER\b"]
    return _find_marker_status(note_text, patterns)


def infer_pr_status(note_text: str) -> FieldPrediction:
    patterns = [r"progesterone receptor", r"\bPR\b"]
    return _find_marker_status(note_text, patterns)


def infer_her2_status(note_text: str) -> FieldPrediction:
    patterns = [r"\bHER2\b"]
    return _find_marker_status(note_text, patterns)


# ---------------------------
# Main mapping entry point
# ---------------------------


def map_note_to_fields(note_text: str, entities: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Given note text + entities, return predicted fields with evidence.
    """
    primary_site = infer_primary_site(note_text, entities)
    histology = infer_histology(note_text, entities)
    stage = infer_stage(note_text, entities)

    er = infer_er_status(note_text)
    pr = infer_pr_status(note_text)
    her2 = infer_her2_status(note_text)

    return {
        "primary_site_pred": primary_site.value,
        "primary_site_evidence": primary_site.evidence_span(note_text),
        "histology_pred": histology.value,
        "histology_evidence": histology.evidence_span(note_text),
        "stage_pred": stage.value,
        "stage_evidence": stage.evidence_span(note_text),
        "er_status_pred": er.value,
        "er_status_evidence": er.evidence_span(note_text),
        "pr_status_pred": pr.value,
        "pr_status_evidence": pr.evidence_span(note_text),
        "her2_status_pred": her2.value,
        "her2_status_evidence": her2.evidence_span(note_text),
    }
