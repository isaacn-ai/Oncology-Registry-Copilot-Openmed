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
- Baseline normalized evaluation: `src/oncology_registry_copilot/pipeline.py` + `scripts/evaluate_preabstract.py`  
- Detailed metrics + error report: `src/oncology_registry_copilot/evaluation.py` + `scripts/run_detailed_eval.py`

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

---

## 4. Installation and setup (Windows)

### 4.1 Clone the repository

```powershell
git clone https://github.com/isaacn-ai/Oncology-Registry-Copilot-Openmed.git
cd Oncology-Registry-Copilot-Openmed
```

### 4.2 Create and activate a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 4.3 Install dependencies

```powershell
pip install -r requirements.txt
```

---

## 5. Running the full pipeline

### Option A — Direct Python command

```powershell
python scripts/run_full_pipeline.py
```

### Option B — One-command reproducibility (Windows PowerShell)

Runs the full pipeline **and** the detailed evaluation:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/reproduce.ps1
```

### Option C — Windows convenience script

```powershell
scripts\run.bat
```

### Outputs

- `outputs/ner_entities.jsonl`
- `data/processed/preabstract_with_evidence.csv`

---

## 5.1 Evaluation

### Baseline normalized evaluation (accuracy per field)

```powershell
python scripts/evaluate_preabstract.py
```

### Detailed metrics + error report (accuracy / precision / recall / F1)

```powershell
python scripts/run_detailed_eval.py
```

Writes:

- `outputs/evaluation/eval_metrics.csv`
- `outputs/evaluation/eval_errors.csv`

---

## 5.2 Reviewer UI (human-in-the-loop)

This repo includes a lightweight **Streamlit** reviewer UI that lets a user:

- Select a synthetic clinical note (case/note)
- Review predicted registry fields
- See the evidence snippet used for each prediction
- Edit any field values as needed
- Save a structured correction record for QA / audit / future improvement

### Run the UI

First, ensure artifacts exist (run the pipeline once):

```powershell
python scripts/run_full_pipeline.py
```

Then start the app:

```powershell
streamlit run app/app.py
```

Open the URL shown in your terminal (typically `http://localhost:8501`).

### Saved corrections

When you click **Save review record**, the app writes JSON correction files to:

- `outputs/review/`

---

## 6. Synthetic data

The demo dataset lives in:

- `data/raw/synthetic_oncology_notes.csv`

Each row contains:

- `case_id`, `note_id`, `note_type`, `note_date`
- `note_text` (synthetic clinical note)
- Ground truth fields:
  - `primary_site_gt`
  - `histology_gt`
  - `stage_gt`
  - `er_status_gt`, `pr_status_gt`, `her2_status_gt`

The dataset is small by design but structured to resemble registry-relevant documentation:

- Breast pathology report with ER/PR/HER2
- Metastatic lung cancer oncology consult
- Colon cancer discharge summary with TNM (pT3N0M0)

---

## 7. Field mapping and evidence

Core logic:

- `src/oncology_registry_copilot/field_mapping.py`

It implements:

- `map_note_to_fields(note_text, entities)` → dictionary of predicted fields, each with:
  - a `*_pred` value (e.g., `primary_site_pred`)
  - a `*_evidence` snippet (short span around the source text)

The mapping uses a combination of:

- OpenMed entities (labels such as `Cancer`, `Organ`, etc.)
- Regex patterns for:
  - histology phrases (carcinoma, adenocarcinoma, etc.)
  - stage expressions (e.g., `Stage IV ...`, `pT3N0M0`)
  - biomarker patterns (ER, PR, HER2) with local “positive”/“negative” detection

This is deliberately transparent and rule-based, acting as a bridge between NER outputs and registry-style fields.

---

## 8. Evaluation methodology

Evaluation is implemented in:

- `src/oncology_registry_copilot/pipeline.py` (normalized evaluation)
- `src/oncology_registry_copilot/evaluation.py` (detailed metrics + error report)

Normalization (to keep metrics clinically meaningful in this demo):

- Primary site → collapsed to `breast` / `lung` / `colon`
- Histology → collapsed to patterns like `adenocarcinoma`, `invasive ductal carcinoma`
- Stage → normalize:
  - “Stage IV …” → `iv`
  - `pT3N0M0` → `ii` (for this demo dataset)
- Biomarkers → `positive` / `negative` / `unknown`, with blanks treated as `unknown`

---

## 9. Limitations and future work

This repository is intentionally limited:

- Tiny synthetic dataset (3 cases)
- No real NAACCR mapping or full registry schema
- Simple rule-based field mapping; no temporal reasoning
- No EHR connectivity or registry software integration

Possible next steps:

- Expand the synthetic dataset and ground truth coverage
- Add temporal reasoning and richer oncology abstractions
- Improve the reviewer UI (bulk review, export corrections to CSV)
- Add CI (GitHub Actions) to catch metric regressions on every push

---

## 10. Disclaimer

This code is:

- for educational and prototyping purposes
- not validated for clinical use
- not a medical device
- not intended to process real patient data without appropriate safeguards, de-identification, and compliance review

