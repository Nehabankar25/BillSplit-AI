# BillSplit AI

Upload a bill photograph → AI extracts line items → human review → assign items to people → **exact proportional split**.

---

## Quick Start

```bash
# 1. Clone and enter the project
cd billsplit-ai/backend

# 2. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set your API key
copy .env.example .env
# Edit .env and paste your Gemini API key

# 5. Run the server
uvicorn main:app --reload --port 8000
```

Open **http://localhost:8000** for the app, **http://localhost:8000/docs** for Swagger.

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
    ├── index.html                   4-screen SPA (no framework)
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

`test_data/bills/` — Place your 12 test photographs here (gitignored by default).
`test_data/ground_truth.json` — Template with fields for all 12 required scenarios:

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
- The two-photo long-bill scenario is represented in the evaluation template and requires manual combination during review.
