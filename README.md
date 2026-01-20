# Oncology Registry Copilot (OpenMed)

A prototype oncology registry co-pilot built on **OpenMed** clinical NLP to:

- Extract cancer-related signals from unstructured clinical notes (synthetic demo data).
- Map them into a small set of **registry-style fields**:
  - Primary site
  - Histology
  - Stage
  - ER / PR / HER2 status
- Generate a **pre-abstract CSV with evidence snippets** for each field.
- Produce **evaluation reports** (metrics + case-level error analysis).
- Provide a lightweight **human-in-the-loop reviewer UI** to correct outputs and save correction records.

**Important:** This project uses only synthetic, non-patient data. It is a technical prototype, not a production or clinical tool.

---

## 1. Problem and vision

Cancer registries are critical for quality reporting, epidemiology, and research, but registrars often spend significant time manually scanning pathology reports, oncology notes, and discharge summaries to abstract registry fields.

This repository demonstrates a minimal “Registry Copilot” workflow:

- Read clinical notes.
- Pre-fill registry fields with traceable evidence.
- Evaluate performance and surface failures.
- Support human review and correction in a simple UI.

---

## 2. High-level architecture

Data flow:

1) Input synthetic notes + ground truth  
- `data/raw/synthetic_oncology_notes.csv`

2) NER with OpenMed → entities JSONL  
- Script: `scripts/run_ner_to_jsonl.py`  
- Output: `outputs/ner_entities.jsonl`

3) Field mapping + evidence packaging  
- Core mapping: `src/oncology_registry_copilot/field_mapping.py`  
- Script: `scripts/generate_preabstract_csv.py`  
- Output: `data/processed/preabstract_with_evidence.csv`

4) Evaluation  
- Baseline evaluation (shared evaluator, availability-aware stage):  
  - `src/oncology_registry_copilot/evaluation.py`
  - `scripts/evaluate_preabstract.py`
- Detailed metrics + error report:  
  - `src/oncology_registry_copilot/evaluation.py`
  - `scripts/run_detailed_eval.py`

5) Reviewer UI (human-in-the-loop)  
- Streamlit app: `app/app.py`  
- Saves correction records to: `outputs/review/`

---

## 3. Project structure

```text
oncology-registry-copilot-openmed/
├─ app/
│  └─ app.py
├─ configs/
├─ data/
│  ├─ raw/
│  │  └─ synthetic_oncology_notes.csv
│  └─ processed/
│     └─ preabstract_with_evidence.csv
├─ docs/
├─ notebooks/
├─ outputs/
│  ├─ ner_entities.jsonl
│  ├─ review/
│  └─ evaluation/
│     ├─ eval_metrics.csv
│     └─ eval_errors.csv
├─ scripts/
│  ├─ run_basic_ner.py
│  ├─ run_ner_to_jsonl.py
│  ├─ generate_preabstract_csv.py
│  ├─ evaluate_preabstract.py
│  ├─ run_detailed_eval.py
│  ├─ run_full_pipeline.py
│  ├─ ci_check.ps1
│  ├─ reproduce.ps1
│  └─ run.bat
├─ src/
│  └─ oncology_registry_copilot/
│     ├─ __init__.py
│     ├─ field_mapping.py
│     ├─ pipeline.py
│     └─ evaluation.py
├─ tests/
└─ requirements.txt
```

## 4. Installation and setup (Windows)

### 4.1 Clone the repository

```bash
git clone https://github.com/isaacn-ai/Oncology-Registry-Copilot-Openmed.git
cd Oncology-Registry-Copilot-Openmed
```

### 4.2 Create and activate a virtual environment

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 4.3 Install dependencies

```bash
pip install -r requirements.txt
```

## 5. Run the full pipeline

### Option A — Direct Python command

```bash
python scripts/run_full_pipeline.py
```

### Option B — One-command reproducibility (Windows PowerShell)

Runs the full pipeline and the detailed evaluation:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/reproduce.ps1
```

### Option C — Windows convenience script

```powershell
scripts\run.bat
```

Outputs:

- `outputs/ner_entities.jsonl`
- `data/processed/preabstract_with_evidence.csv`

## 6. Evaluation

### 6.1 Baseline evaluation (shared evaluator, availability-aware stage)

This evaluation uses the shared evaluator in `src/oncology_registry_copilot/evaluation.py`, including an “availability-aware” rule for stage: stage is only scored for notes that contain a stage/TNM signal, to avoid penalizing missing evidence.

```bash
python scripts/evaluate_preabstract.py
```

### 6.2 Detailed metrics + error report (accuracy / precision / recall / F1)

```bash
python scripts/run_detailed_eval.py
```

Writes:

- `outputs/evaluation/eval_metrics.csv`
- `outputs/evaluation/eval_errors.csv`

## 7. CI gate (local)

A fast-fail local CI gate script is included:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/ci_check.ps1
```

It runs:

- Unit tests (pytest)
- Full pipeline
- Detailed evaluation
- Artifact existence checks
- Metric regression gate

## 8. Reviewer UI (human-in-the-loop)

This repo includes a lightweight Streamlit reviewer UI that lets a user:

- Select a synthetic clinical note (case/note)
- Review predicted registry fields
- See the evidence snippet used for each prediction
- Edit any field values as needed
- Save a structured correction record for QA / audit / future improvement
- Export saved corrections to CSV (from the sidebar action)

### Run the UI

First, ensure artifacts exist (run the pipeline once):

```bash
python scripts/run_full_pipeline.py
```

Then start the app:

```bash
streamlit run app/app.py
```

Open the URL shown in your terminal (typically http://localhost:8501).

### Saved corrections

When you click Save review record, the app writes JSON correction files to:

- `outputs/review/`

## 9. Synthetic data

The demo dataset lives in:

- `data/raw/synthetic_oncology_notes.csv`

Each row contains:

- `case_id`, `note_id`, `note_type`, `note_date`
- `note_text` (synthetic clinical note)

Ground truth fields:

- `primary_site_gt`
- `histology_gt`
- `stage_gt`
- `er_status_gt`, `pr_status_gt`, `her2_status_gt`

The dataset is small by design but structured to resemble registry-relevant documentation:

- Breast pathology report with ER/PR/HER2
- Metastatic lung cancer oncology consult
- Colon cancer discharge summary with TNM (pT3N0M0)

## 10. Field mapping and evidence

Core logic:

- `src/oncology_registry_copilot/field_mapping.py`

It implements:

- `map_note_to_fields(note_text, entities)` → dictionary of predicted fields, each with:
  - a `*_pred` value (e.g., `primary_site_pred`)
  - a `*_evidence` snippet (short span around the source text)

The mapping uses a combination of:

- OpenMed entities (labels such as Cancer, Organ, etc.)
- Regex patterns for:
  - histology phrases (carcinoma, adenocarcinoma, etc.)
  - stage expressions (e.g., Stage IV ..., pT3N0M0)
  - biomarker patterns (ER, PR, HER2) with local “positive”/“negative” detection

This is deliberately transparent and rule-based, acting as a bridge between NER outputs and registry-style fields.

## 11. Evaluation methodology

Evaluation is implemented in:

- `src/oncology_registry_copilot/evaluation.py` (shared evaluator, detailed metrics, error report)
- `scripts/evaluate_preabstract.py` (baseline report using shared evaluator)
- `scripts/run_detailed_eval.py` (writes metrics + error report CSVs)

Normalization (to keep metrics clinically meaningful in this demo):

- Primary site → collapsed to breast / lung / colon
- Histology → collapsed to patterns like adenocarcinoma, invasive ductal carcinoma
- Stage → normalized to compact forms like ii, iia, iv
- TNM strings like pT3N0M0 map to a demo stage normalization (ii)
- Stage is only scored when the note contains a stage/TNM signal
- Biomarkers → positive / negative / unknown, with blanks treated as unknown

## 12. Limitations and future work

This repository is intentionally limited:

- Tiny synthetic dataset (3 cases)
- No real NAACCR mapping or full registry schema
- Simple rule-based field mapping; no temporal reasoning
- No EHR connectivity or registry software integration

Possible next steps:

- Expand the synthetic dataset and ground truth coverage
- Add temporal reasoning and richer oncology abstractions
- Improve the reviewer UI (bulk review workflows, richer exports)
- Add GitHub Actions CI to run the gate on every push

## 13. Disclaimer

This code is:

- for educational and prototyping purposes
- not validated for clinical use
- not a medical device
- not intended to process real patient data without appropriate safeguards, de-identification, and compliance review

---

## Why this fixes your pain immediately

- You are no longer trying to paste Markdown through PowerShell parsing rules.
- Codex edits the file directly and commits it.
- The replacement uses real Unicode characters (—, →) and a clean directory tree that GitHub renders correctly.
- Sections are renumbered and updated to match your current evaluator/CI pipeline changes.

If you want the README to also mention `.gitattributes` line-ending normalization explicitly, Codex can add a short note under Installation or CI; it is optional and does not affect correctness.
