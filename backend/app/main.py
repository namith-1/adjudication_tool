import json
from fastapi import Body, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from typing import Any, Dict, List

from .adjudicator import adjudicate
from .document_processor import detect_document_type, extract_text_from_file, process_uploaded_file
from .models import AdjudicationResult, ClaimInput
from .policy import load_json_file

app = FastAPI(title="Plum OPD Adjudication API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

base = Path(__file__).resolve().parents[2]
policy_file = base / "Instruction_files" / "policy_terms (1).json"
test_cases_file = base / "Instruction_files" / "test_cases.json"


@app.get("/api/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "service": "Plum OPD Adjudication"}


@app.get("/api/policy")
def get_policy() -> Any:
    try:
        return load_json_file(policy_file)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/test-cases")
def get_test_cases() -> Any:
    try:
        return load_json_file(test_cases_file)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/documents/extract")
def extract_document_text(file: UploadFile = File(...)) -> Dict[str, Any]:
    extracted_text = extract_text_from_file(file)
    document_type = "unknown"
    try:
        from .document_processor import detect_document_type

        document_type = detect_document_type(file.filename, extracted_text)
    except Exception:
        document_type = "unknown"

    return {
        "filename": file.filename,
        "document_type": document_type,
        "extracted_text": extracted_text,
    }


@app.post("/api/documents/process")
def process_documents(files: List[UploadFile] = File(...)) -> Dict[str, Any]:
    processed = [process_uploaded_file(file) for file in files]
    return {"documents": processed}


@app.post("/api/claims/submit", response_model=AdjudicationResult)
def submit_claim(claim: ClaimInput = Body(...)) -> Dict[str, Any]:
    return adjudicate(claim)


@app.post("/api/claims/submit-with-docs", response_model=AdjudicationResult)
def submit_claim_with_docs(
    claim: str = Form(...),
    files: List[UploadFile] = File(default=[]),
) -> Dict[str, Any]:
    try:
        claim_data = json.loads(claim)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid claim payload: {exc}")

    claim_input = ClaimInput(**claim_data)
    return adjudicate(claim_input, uploaded_files=files)
