# BillSplit AI

Upload a bill photograph → AI extracts line items → human review → assign items to people → **exact proportional split**.

---

## Quick Start

### PowerShell

```powershell
cd "C:\Users\<you>\OneDrive\Desktop\BillSplit\billsplit-ai"
python -m venv backend\venv
& .\backend\venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
Copy-Item backend\.env.example backend\.env
# Edit backend\.env and add your local Gemini API key
python -m uvicorn backend.main:app --reload --port 8000
```

Open **http://127.0.0.1:8000** for the app and **http://127.0.0.1:8000/docs** for Swagger. Stop the server with `Ctrl+C`.

### macOS / Linux

```bash
# 1. Enter the project
cd billsplit-ai

# 2. Create and activate a virtual environment
python -m venv backend/venv
source backend/venv/bin/activate

# 3. Install dependencies
pip install -r backend/requirements.txt

# 4. Set your API key
cp backend/.env.example backend/.env
# Edit .env and paste your Gemini API key

# 5. Run the server
python -m uvicorn backend.main:app --reload --port 8000
```

## What Is Real vs Mocked

- **Real:** receipt upload, FastAPI routing, Gemini Vision extraction, Pydantic validation, human edits, stable item IDs, participant assignment, Decimal calculations, proportional tax/service-charge allocation, mismatch warnings, and penny reconciliation.
- **Real:** one or two receipt photos can be sent to Gemini as one combined bill through `POST /api/bills/analyze-multiple`.
- **Mocked/demo:** **Try Sample Bill** calls `GET /api/bills/demo`, which returns a fixed in-memory sample bill. It does not call Gemini and exists for a no-key demonstration.
- **Local-only:** participants and recent split history are not saved to a backend database or shared across users.
- No login, database, payments, cloud deployment, or authentication is included in this MVP.

### Past Bills

Completed splits are stored locally in browser `localStorage` under `billsplit_past_bills`. The history contains structured bill and final split data only; it does not store receipt images, Gemini keys, or other secrets. History is not persisted in a backend database and is not shared between users or devices. The 12-bill evaluation dataset remains separate under `test_data/bills/` with labels in `test_data/ground_truth.json`.

---

## What It Does

```
Upload Bill Photo
      │
      ▼
Gemini Vision (gemini-2.5-flash)
  • Image understanding
  • OCR across scripts and lighting conditions
  • Schema-constrained JSON output
      │
      ▼
Structured Bill (Pydantic v2)
  • BillItem: name, quantity, unit_price, total, confidence
  • Charges: subtotal, tax, service_charge, discount
  • printed_total (Optional — null if unreadable)
  • calculated_total (Python-computed, never from LLM)
  • total_mismatch flag
      │
      ▼
Human Review Screen
  • Edit any mis-extracted value
  • Confidence badges (High/Medium/Low)
  • Mismatch warning if printed ≠ calculated
  • Illegible-total notice if printed_total is null
      │
      ▼
Add Participants + Assign Items
  • Each item → specific people, or Everyone
  • Unassigned items block the Calculate button
      │
      ▼
Proportional Split Calculation
  • Tax / Service Charge / Discount distributed by food share
  • NOT divided equally by headcount
  • Penny reconciliation: sum of splits == bill total exactly
      │
      ▼
Per-Person Summary Cards
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `GEMINI_API_KEY` | *(required)* | Get one free at [aistudio.google.com](https://aistudio.google.com) |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Any Gemini model supporting `response_schema` |

---

## Architecture

```
billsplit-ai/
├── backend/
│   ├── main.py                      FastAPI app, CORS, static serving
│   ├── models/
│   │   ├── bill.py                  BillItem, BillExtract, Bill (Pydantic v2)
│   │   └── split.py                 Person, ItemAssignment, SplitRequest, SplitResult
│   └── services/
│       ├── gemini_service.py        Image → schema-constrained JSON via Gemini
│       ├── extraction_service.py    Python computes calculated_total + mismatch
│       └── calculation_service.py   Proportional split + penny reconciliation
└── frontend/
    ├── index.html                   6-step SPA (no framework)
    ├── style.css                    Dark navy design system
    └── app.js                       BillSplitApp class
```

---

## Key Engineering Decisions

### 1. Decimal arithmetic
All money uses Python's `decimal.Decimal`. Float arithmetic (e.g. `0.1 + 0.2 == 0.30000000000000004`) is never used for financial calculations. Pydantic v2 constructs Decimals via `str()` internally when validating JSON, avoiding binary float noise.

### 2. Schema-constrained Gemini output
```python
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=[image_part, prompt],
    config={"response_mime_type": "application/json", "response_schema": BillExtract},
)
```
The model is constrained to the `BillExtract` shape rather than relying on prompt wording alone. This eliminates the entire class of "Gemini added a markdown fence" parse failures.

### 3. Python owns `calculated_total`
The LLM extracts raw fields only. `calculated_total = subtotal + tax + service_charge - discount` is always computed in Python. This means even if Gemini mis-extracts a field, the frontend always shows a consistent arithmetic result.

### 4. `printed_total: Optional[Decimal]`
When the receipt total is illegible, Gemini returns `null`. The mismatch check is skipped entirely, preventing false-positive "mismatch" warnings on every bill with a smudged total.

### 5. Proportional tax distribution
```
person_tax = bill.tax × (person_food / total_food)
```
Not `bill.tax / n_people`. If Neha ate ₹500 worth of food and Rahul ₹300 (₹800 total) and GST is ₹40:
- Neha pays ₹40 × (500/800) = **₹25.00**
- Rahul pays ₹40 × (300/800) = **₹15.00**

### 6. Penny reconciliation
```
remainder = calculated_total - sum(round(grand_total, 2) for each person)
first_person.grand_total += remainder
```
The remainder is always < ₹0.01 × number of people (a few paise). Assigning it to the first person guarantees `sum(splits) == calculated_total` exactly — no floating ₹0.01 discrepancy in the summary.

### 7. `ItemAssignment.everyone` flag
An explicit `everyone: bool` distinguishes "split among all" from "not yet assigned". An empty `person_ids` with `everyone=False` triggers a `422` from the Pydantic validator with the specific item names listed — it never silently splits to everyone.

---

## Tax Order-of-Operations Assumption

```
calculated_total = subtotal + tax + service_charge − discount
```

**Assumed:**
- Tax/GST is computed on the **full pre-discount subtotal**
- Discount is a bill-level reduction applied **after** all charges

Bills that compute tax on the post-discount subtotal will show a small `total_mismatch`. This is a modeling assumption difference, not an extraction error — the UI explains this context.

---

## Test Data

The test-data folders have intentionally separate roles:

- `test_data/bills/` — the official 12 real bills personally photographed for the assignment. These are not currently included because they must be real photographs and manually labeled.
- `test_data/online_samples/` — supplemental development/testing receipts downloaded from an explicitly licensed source. Source and license details are recorded beside the files. Online samples do **not** satisfy or replace the 12-bill requirement.
- `test_data/ground_truth.json` — manually verified expected values for the official 12 assignment bills. Participant assignments are not part of extraction ground truth.

### Developer Evaluation Utility

The developer-only evaluator uses the same Gemini extraction service as the application and reports field-level differences when a matching ground-truth entry exists. It does not affect the production flow:

```powershell
& ".\backend\venv\Scripts\python.exe" tools\evaluate_receipts.py test_data\online_samples\cord_sample.png
```

For official bills, use a filename that exists in `ground_truth.json`. The utility requires the local `backend/.env` Gemini configuration and never stores credentials or writes to browser history.

The official 12-bill evaluation scenarios are:

| # | Scenario |
|---|---|
| 1 | Normal clear receipt |
| 2 | Small receipt |
| 3 | Long receipt |
| 4 | Dim photograph |
| 5 | Crumpled receipt |
| 6 | Steep angle |
| 7 | Faded thermal print |
| 8 | Handwritten annotations |
| 9 | Two scripts (e.g. English + Hindi) |
| 10 | Two-photo long bill |
| 11 | Shared-item-heavy bill |
| 12 | **Wrong printed total** |

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Liveness probe |
| `POST` | `/api/bills/analyze` | Upload image → `Bill` JSON |
| `POST` | `/api/bills/analyze-multiple` | Upload one or two consecutive images → one merged `Bill` JSON |
| `POST` | `/api/bills/validate` | Re-validate edited bill → `Bill` JSON |
| `POST` | `/api/split/calculate` | `SplitRequest` → `SplitResult` |
| `GET` | `/docs` | Swagger UI |

## Security Notes

- Gemini credentials stay on the FastAPI backend in `backend/.env`.
- Never commit `.env`, API keys, tokens, passwords, or machine-specific configuration.
- `backend/.env.example` contains placeholders only.
- The frontend communicates with FastAPI and never calls Gemini directly.

## Testing

Run the backend tests from the repository root:

```bash
python -m pytest backend/tests -q
```

The suite covers health checks, bill re-validation, stable item IDs, unassigned-item validation, proportional charges, and penny reconciliation.

## Demo Instructions

1. Start the backend with `uvicorn backend.main:app --reload --port 8000`.
2. Open `http://127.0.0.1:8000`.
3. Select **Try Sample Bill** to demonstrate the review, participant, assignment, and summary flow without a Gemini key.
4. For real photographs, copy `backend/.env.example` to `backend/.env` and add the local Gemini key.

## Known Limitations

- This MVP has no login, database, payments, or cloud deployment.
- Participants and recent split history are local to the current browser session/device.
- The two-photo long-bill scenario supports two consecutive images and depends on Gemini correctly combining the pages; human review remains available for corrections.
