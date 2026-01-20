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
        """Return a short evidence snippet from the note text."""
        if self.evidence_start is None or self.evidence_end is None:
            return None
        start = max(0, self.evidence_start - 40)
        end = min(len(note_text), self.evidence_end + 40)
        snippet = note_text[start:end].replace("\n", " ")
        if len(snippet) > max_len:
            snippet = snippet[: max_len - 3] + "..."
        return snippet


def _pick_best(
    entities: List[Dict[str, Any]],
    condition,
) -> Optional[Dict[str, Any]]:
    candidates = [e for e in entities if condition(e)]
    if not candidates:
        return None
    return max(candidates, key=lambda e: e.get("confidence", 0.0))


def infer_primary_site(note_text: str, entities: List[Dict[str, Any]]) -> FieldPrediction:
    """
    Heuristic primary site inference.

    Strategy:
    - Prefer Cancer entities whose text contains organ/site keywords.
    - Fallback: search raw text for those keywords.
    """
    site_keywords = [
        "breast",
        "lung",
        "colon",
        "sigmoid",
        "right upper lobe",
        "left breast",
        "sigmoid colon",
    ]

    def has_site_keyword(ent: Dict[str, Any]) -> bool:
        if ent.get("label") != "Cancer":
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


def infer_histology(note_text: str, entities: List[Dict[str, Any]]) -> FieldPrediction:
    """
    Histology inference.

    Strategy:
    - Look for Cancer entities containing carcinoma/adenocarcinoma/lymphoma/etc.
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
    pattern = re.compile(r"\b(\w+\s+(carcinoma|adenocarcinoma|sarcoma|lymphoma))\b", re.IGNORECASE)
    m = pattern.search(note_text)
    if m:
        return FieldPrediction(
            value=m.group(0),
            evidence_start=m.start(),
            evidence_end=m.end(),
        )

    return FieldPrediction(value=None, evidence_start=None, evidence_end=None)


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
        return text.strip().startswith("Stage")

    best = _pick_best(entities, is_stage_entity)
    if best:
        return FieldPrediction(
            value=best["text"],
            evidence_start=best["start"],
            evidence_end=best["end"],
        )

    # TNM style, e.g. pT3N0M0
    tnm_pattern = re.compile(r"\bp?[Tt]\d+[AN]\d+M\d+\b")
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


def _find_marker_status(note_text: str, marker_patterns: List[str]) -> FieldPrediction:
    """
    Find biomarker status by looking near the marker name for 'positive' or 'negative'.
    """
    text = note_text
    lower = text.lower()

    # Find marker occurrence
    marker_regex = re.compile("|".join(marker_patterns), re.IGNORECASE)
    m = marker_regex.search(text)
    if not m:
        return FieldPrediction(value=None, evidence_start=None, evidence_end=None)

    # Define a window around the marker
    start = max(0, m.start() - 80)
    end = min(len(text), m.end() + 80)
    window = lower[start:end]

    status = None
    if "negative" in window:
        status = "negative"
    elif "positive" in window or "strongly positive" in window:
        status = "positive"

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


def map_note_to_fields(note_text: str, entities: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Main entry point: given note text + entities, return predicted fields with evidence.
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
