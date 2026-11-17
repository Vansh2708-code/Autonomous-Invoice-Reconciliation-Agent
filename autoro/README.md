# Autoro

**Autoro** is a local-first, minimalist Python web application that stores purchase orders and invoices, extracts structured data with Google Gemini when configured, checks discrepancies, forecasts invoice spending, and generates downloadable PDF reports.

Built with **FastAPI + vanilla JavaScript/CSS + SQLite + google-genai + scikit-learn + ReportLab**. No React build, Node installation, or hosted database is required for the local MVP.

## Run locally on Windows 11

1. Install **Python 3.10+** and unzip this project into a folder.
2. Open PowerShell in the extracted `autoro` folder:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   Copy-Item .env.example .env
   ```

3. Edit `.env` using Notepad. Replace `APP_SECRET_KEY` with a long random string. Set `GEMINI_API_KEY` **only if you want AI extraction**. Leave it blank to use manual entry and store uploads as pending.
4. Start Autoro:

   ```powershell
   uvicorn main:app --reload
   ```

5. Open **http://127.0.0.1:8000** in your browser. Create an account. To explore all modules without real financial documents, click **Load sample data** in the Overview dashboard.

## Run on macOS/Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env, set APP_SECRET_KEY and optionally GEMINI_API_KEY
uvicorn main:app --reload
```

If the PowerShell activation script is blocked, use `.\.venv\Scripts\python.exe -m pip install -r requirements.txt` and `.\.venv\Scripts\python.exe -m uvicorn main:app --reload` instead.

## Features

| Module | MVP capability |
| --- | --- |
| Accounts | Signup/sign-in, password hashing, user-isolated documents, session and CSRF protection |
| Upload | PDF/JPG/PNG up to 12 MB, file signature checking, Gemini 2.5 Flash JSON schema extraction; fallback to pending/manual entry |
| Manual entry | Create/edit POs or invoices with dynamic line items and optional override totals |
| Document Vault | Vendor/format grouping, chronological sorting, search, filters, original-file download |
| Reconcile | One-to-one PO/invoice matching by SKU or normalized item description; quantity, unit price, tax, total and internal arithmetic checks |
| Batch | Up to one calendar month and up to 200 invoices/POs each; reference-based match; ambiguous/missing references flagged, not silently approved |
| Forecast | 1, 3 and 12-month projections unlocked by the **exact invoice count and historical month rules** below |
| Reporting | Server-generated downloadable PDFs for reconciliation, batch analysis and forecasting |
| Demo | Opt-in generation of **312 synthetic invoices + 312 synthetic POs** over 12 complete historical months |

### Forecast unlocks

- **1 month:** at least **1 distinct month** and **15 invoices**.
- **3 months:** at least **3 distinct months** and **135 invoices**.
- **12 months:** at least **12 distinct months** and **300 invoices**.

Forecasts use invoice totals only, avoiding double-counting POs and invoices. A single-month baseline extrapolates the most recent month's value; longer histories use a regularized trend blended with the recent 3-month average. These are **demonstration forecasts**, not statistically validated financial projections. Mixed-currency invoices intentionally block the forecast instead of being summed incorrectly.

### Gemini API setup

The server reads `GEMINI_API_KEY` from `.env`. A configured key enables multimodal extraction through the official Python `google-genai` SDK with a Pydantic structured-output schema and the `gemini-2.5-flash` model name. You can override the model through `GEMINI_MODEL`.

* Gemini execution requires an active Google AI API key, network access and adequate model quota; it cannot be tested offline by this bundle.
* AI-extracted fields may be inaccurate. **Verify against the original document before approving anything.**
* Real uploaded files are sent to Google for extraction when Gemini is configured. Follow your organization's confidential-data and retention rules.
* The app does **not** use OpenAI keys and does not place API credentials in browser-side JavaScript.

### Reconciliation rules

The comparison engine is deterministic Python logic. The AI extracts document data, but does not decide whether an invoice is payable. A single reconciliation checks vendor, currency, PO number reference, item presence, quantity, unit price, tax rate, subtotal, tax total and grand total, plus internal arithmetic. Matching is conservative: by SKU when present, otherwise by normalized description. Monetary tolerance is 0.01 in the document's currency.

Monthly batches join invoices to POs by explicit PO reference and report missing or ambiguous matches. No fuzzy auto-matching or automatic payment approval is performed.

## Storage and deployment

Data lives under `data/` (or `AUTORO_DATA_DIR` when configured):

- `autoro.sqlite3` — users, document JSON, metadata and reports.
- `uploads/` — original uploaded documents, stored with random opaque file names.
- `reports/` — generated PDFs, accessible only through authenticated endpoints.

For local testing, `.env` loads automatically via `python-dotenv`. In production, use **HTTPS**, persistent storage, `APP_ENV=production`, and a securely generated and stable `APP_SECRET_KEY`. The production flag sets secure session cookies and requires the secret key.

**Before serving real clients**, add password reset and account verification, audit logging and duplicate detection, malware scanning of uploads, database backups and restore checks, request rate limiting, monitoring, automated cloud storage, PostgreSQL migrations, retention policies, organization/team permissions, stricter form and file limits, AI extraction cost controls, structured extraction confidence/verification and compliance review. Real historical forecasts need backtesting and calibration; 12 historical months may not capture annual seasonality robustly.

### Useful commands

```bash
# Development server
uvicorn main:app --reload

# Test the API with a disposable database
python -m pytest -q tests/test_app.py

# API reference while the server is running
# http://127.0.0.1:8000/api/docs
```

## Known MVP limitations

The repository is grouped in the UI by vendor and detected format (not separate filesystem folders). Uploads are extracted sequentially and the UI supports one file per upload; a job queue and multi-file upload interface are future upgrades. Gemini-extracted fields are not confidence-scored. Batch matching relies on an exact PO reference; ambiguous and absent references are explicitly flagged. Forecasting is indicative and not trained on a separately validated dataset. There is no live bank/ERP integration, approval workflow, three-way matching with goods-received notes, or cloud deployment included in this local source bundle.

## Project structure

```text
autoro/
├── main.py                 # FastAPI app, SQLite, Gemini, reconciliation, forecast and PDF
├── static/
│   ├── index.html          # Front-end entry point
│   ├── app.js              # Browser-side interactive app
│   └── styles.css          # Responsive minimalist design
├── tests/
│   └── test_app.py         # Isolated end-to-end API smoke tests
├── .env.example            # Environment variables; no secrets included
├── .gitignore
├── requirements.txt
└── data/.gitkeep           # Runtime data lives here, excluded from git
```

**Disclaimer:** This is an MVP starter, not a production financial-control system. No real payments are made and no financial approvals are automated.
