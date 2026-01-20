from oncology_registry_copilot.field_mapping import infer_stage


def test_stage_normalization_explicit_stage():
    note = "Assessment: Stage IIA breast cancer."
    pred = infer_stage(note, entities=[])
    assert pred.value == "IIA"


def test_stage_normalization_colon_format():
    note = "DIAGNOSIS: stage: ii a."
    pred = infer_stage(note, entities=[])
    assert pred.value == "IIA"


def test_stage_tnm_fallback():
    note = "Path: pT3N0M0 noted in the report."
    pred = infer_stage(note, entities=[])
    assert pred.value.lower() == "pt3n0m0"
