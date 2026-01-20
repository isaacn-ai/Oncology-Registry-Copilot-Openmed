# Oncology Registry Copilot (OpenMed)

A prototype oncology registry co-pilot that uses **OpenMed** clinical NLP to:

- Extract cancer-related entities from unstructured clinical notes.
- Map them into a small set of **registry-style fields**:
  - Primary site
  - Histology
  - Stage
  - ER / PR / HER2 status
- Generate a **pre-abstract CSV with evidence snippets** for each field.
- Compute **field-level accuracy metrics** against synthetic ground truth.

All of this is runnable end-to-end with a single command:

    python scripts/run_full_pipeline.py

or on Windows:

    scripts\run.bat

> **Important:** This project uses only synthetic, non-patient data.  
> It is a **technical prototype**, not a production or clinical tool.

---

## 1. Problem and vision

Cancer registries are critical for:

- Quality reporting  
- Epidemiology  
- Research and real-world evidence  

But:

- Registrars spend large amounts of time manually scanning pathology reports, oncology notes, and discharge summaries.
- Staffing and workload pressures are well documented.
- Most of the key data elements are present only in **unstructured text**.

The long-term vision is an **Oncology Registry Copilot** that:

- Reads clinical notes.
- Pre-fills registry fields with **traceable evidence**.
- Lets registrars work in **exception-review mode** instead of manual chart mining.

This repository is a **minimal, fully reproducible end-to-end prototype** of that idea, built on top of OpenMed.

---

## 2. High-level architecture

Data flow:

1. **Input**: synthetic clinical notes with ground truth fields  
   - `data/raw/synthetic_oncology_notes.csv`

2. **NER with OpenMed**  
   - Script: `scripts/run_ner_to_jsonl.py`  
   - Output: `outputs/ner_entities.jsonl`  
   - Model: `oncology_detection_superclinical` from OpenMed

3. **Field mapping + evidence packaging**  
   - Module: `src/oncology_registry_copilot/field_mapping.py`  
   - Script: `scripts/generate_preabstract_csv.py`  
   - Output: `data/processed/preabstract_with_evidence.csv`  
   - Fields:
     - `primary_site_pred`, `histology_pred`, `stage_pred`
     - `er_status_pred`, `pr_status_pred`, `her2_status_pred`
     - Each with an associated `*_evidence` snippet from the note text

4. **Evaluation (normalized)**  
   - Module: `src/oncology_registry_copilot/pipeline.py` (`evaluate_preabstract`)  
   - Script: `scripts/evaluate_preabstract.py` (thin wrapper)  
   - Output: printed field-level accuracy report

5. **Orchestration**  
   - Single-command runner: `scripts/run_full_pipeline.py`  
   - Convenience wrapper for Windows: `scripts/run.bat`

---

## 3. Project structure

    oncology-registry-copilot-openmed/
    ├─ configs/
    ├─ data/
    │  ├─ raw/
    │  │  └─ synthetic_oncology_notes.csv
    │  └─ processed/
    │     └─ preabstract_with_evidence.csv
    ├─ docs/
    ├─ notebooks/
    ├─ outputs/
    │  └─ ner_entities.jsonl
    ├─ scripts/
    │  ├─ run_basic_ner.py
    │  ├─ run_ner_to_jsonl.py
    │  ├─ generate_preabstract_csv.py
    │  ├─ evaluate_preabstract.py
    │  ├─ run_full_pipeline.py
    │  └─ run.bat
    ├─ src/
    │  └─ oncology_registry_copilot/
    │     ├─ __init__.py
    │     ├─ field_mapping.py
    │     └─ pipeline.py
    ├─ tests/
    └─ requirements.txt

---

## 4. Installation and setup

### 4.1. Clone the repository

    git clone https://github.com/isaacn-ai/Oncology-Registry-Copilot-Openmed.git
    cd Oncology-Registry-Copilot-Openmed

### 4.2. Create and activate a virtual environment (Windows)

    python -m venv .venv
    .\.venv\Scripts\activate

### 4.3. Install dependencies

    pip install -r requirements.txt

This will install:

- `openmed[hf]` – clinical NLP toolkit and models  
- `pandas`  
- `pydantic` (for future extensions)  

---

## 5. Running the full pipeline

Once dependencies are installed and the virtual environment is active, you can run:

### Option A – Direct Python command

    python scripts/run_full_pipeline.py

### Option B – Windows convenience script

    scripts\run.bat

The pipeline will:

1. Run OpenMed NER over the synthetic notes.
2. Generate the pre-abstract CSV with evidence.
3. Print a normalized evaluation report, for example:

    === PRE-ABSTRACT EVALUATION REPORT (NORMALIZED, v2) ===

           field  total_cases  correct  accuracy
    primary_site            3        3     1.000
       histology            3        3     1.000
           stage            3        2     0.667
       er_status            3        3     1.000
       pr_status            3        3     1.000
     her2_status            3        3     1.000

    ======================================================

Outputs:

- `outputs/ner_entities.jsonl`  
- `data/processed/preabstract_with_evidence.csv`
---

## 5.1 One-command reproducibility (Windows PowerShell)

This project includes a reproducibility script that runs:

1) Full pipeline (NER → pre-abstract → evaluation)  
2) Detailed evaluation (metrics + error report)  

From the repository root:

    powershell -ExecutionPolicy Bypass -File scripts\reproduce.ps1

Artifacts are written locally (and are not committed to git):

- `outputs/ner_entities.jsonl`  
- `data/processed/preabstract_with_evidence.csv`  
- `outputs/evaluation/eval_metrics.csv`  
- `outputs/evaluation/eval_errors.csv`  

---

## 6. Synthetic data

The demo dataset lives in:

- `data/raw/synthetic_oncology_notes.csv`

Each row contains:

- `case_id`, `note_id`, `note_type`, `note_date`  
- `note_text` – synthetic clinical note  
- Ground truth fields:
  - `primary_site_gt`
  - `histology_gt`
  - `stage_gt`
  - `er_status_gt`, `pr_status_gt`, `her2_status_gt`

The dataset is small by design but structured to resemble registry-relevant documentation:

- Breast pathology report with ER/PR/HER2.  
- Metastatic lung cancer oncology consult.  
- Colon cancer discharge summary with TNM (pT3N0M0).  

---

## 7. Field mapping and evidence

The core logic lives in:

- `src/oncology_registry_copilot/field_mapping.py`

It implements:

- `map_note_to_fields(note_text, entities)` → dictionary of predicted fields, each with:
  - A `*_pred` value (e.g., `primary_site_pred`)
  - A `*_evidence` snippet (short span around the source text)

The mapping uses a combination of:

- OpenMed entities (labels such as `Cancer`, `Organ`, etc.).
- Regex patterns for:
  - Histology phrases (carcinoma, adenocarcinoma, etc.).
  - Stage expressions (e.g., `Stage IV ...`, `pT3N0M0`).
  - Biomarker patterns (ER, PR, HER2) with local “positive”/“negative” detection.

This is deliberately transparent and rule-based, acting as a **bridge** between NER outputs and registry-style fields.

---

## 8. Evaluation methodology

Evaluation is implemented in:

- `src/oncology_registry_copilot/pipeline.py` (`evaluate_preabstract`)

Key ideas:

- Compare `_pred` vs `_gt` for each field.
- Use **field-specific normalization** so metrics are clinically meaningful:
  - Primary site → collapsed to `breast` / `lung` / `colon`.
  - Histology → collapsed to patterns like `adenocarcinoma`, `invasive ductal carcinoma`.
  - Stage → normalize:
    - “Stage IV (metastatic) …” → `iv`
    - `pT3N0M0` → `ii` (for this demo dataset)
  - Biomarkers → `positive` / `negative` / `unknown`, with blanks treated as `unknown`.

The result is a table of:

- `field`, `total_cases`, `correct`, `accuracy`

This shows, in a small but honest way, how the prototype would be evaluated and improved in a real registry environment.

---

## 9. Limitations and future work

This repository is intentionally limited:

- Tiny, synthetic dataset (3 cases).  
- No real NAACCR mapping or full registry schema.  
- Simple rule-based field mapping; no temporal reasoning.  
- No EHR connectivity or registry software integration.  

Possible next steps:

- Expand the synthetic dataset and ground truth coverage.  
- Add temporal models or more advanced rules.  
- Introduce site-specific configuration for different cancer centers.  
- Integrate with a simple review UI (web-based evidence viewer).  
- Experiment with fine-tuned OpenMed models for registry-specific tasks.  

---

## 10. Disclaimer

This code is:

- For educational and prototyping purposes.  
- Not validated for clinical use.  
- Not a medical device.  
- Not intended to process real patient data without appropriate safeguards, de-identification, and regulatory/compliance review.
