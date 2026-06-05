# Backend — Plum OPD Adjudication API

This directory contains a FastAPI service that reads policy and claim rules from the provided assignment files and evaluates claim submissions.

## Run locally

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Endpoints

- `GET /api/health` — health check
- `GET /api/policy` — returns the loaded policy terms
- `GET /api/test-cases` — returns test case JSON data
- `POST /api/claims/submit` — adjudicates a claim and returns a decision

## How it works

- `app/adjudicator.py` implements the core claim decision logic
- `Instruction_files/policy_terms (1).json` and `Instruction_files/test_cases.json` are used as the reference data
- The API uses CORS to allow connections from the frontend running on port `5173`
