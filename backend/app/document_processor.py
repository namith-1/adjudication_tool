import io
import re
from typing import Any, Dict, List, Optional

import numpy as np
from docx import Document as DocxDocument
from easyocr import Reader
from fastapi import UploadFile
from PIL import Image

try:
    from pdf2image import convert_from_bytes
except ImportError:
    convert_from_bytes = None

from .models import Bill, ClaimInput, Prescription

_OCR_READER: Optional[Reader] = None


def get_ocr_reader() -> Reader:
    global _OCR_READER
    if _OCR_READER is None:
        _OCR_READER = Reader(["en"], gpu=False)
    return _OCR_READER


def extract_text_from_docx(uploaded_file: UploadFile) -> str:
    try:
        uploaded_file.file.seek(0)
        document = DocxDocument(uploaded_file.file)
        return "\n".join([paragraph.text for paragraph in document.paragraphs if paragraph.text.strip()])
    except Exception:
        return ""


def extract_text_from_image_bytes(data: bytes) -> str:
    try:
        image = Image.open(io.BytesIO(data)).convert("RGB")
        reader = get_ocr_reader()
        results = reader.readtext(np.array(image))
        return "\n".join([entry[1] for entry in results if entry[1].strip()])
    except Exception:
        return ""


def extract_text_from_file(uploaded_file: UploadFile) -> str:
    try:
        filename = uploaded_file.filename.lower()
        if filename.endswith(".docx"):
            return extract_text_from_docx(uploaded_file)

        if filename.endswith((".txt", ".md", ".csv", ".json", ".xml", ".html", ".htm")):
            uploaded_file.file.seek(0)
            data = uploaded_file.file.read()
            if isinstance(data, bytes):
                return data.decode("utf-8", errors="ignore")
            return str(data)

        if filename.endswith((".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif")):
            uploaded_file.file.seek(0)
            return extract_text_from_image_bytes(uploaded_file.file.read())

        if filename.endswith(".pdf") and convert_from_bytes is not None:
            uploaded_file.file.seek(0)
            pages = convert_from_bytes(uploaded_file.file.read())
            page_texts = []
            for page in pages:
                buf = io.BytesIO()
                page.save(buf, format="PNG")
                page_texts.append(extract_text_from_image_bytes(buf.getvalue()))
            return "\n\n".join([text for text in page_texts if text])

        return ""
    except Exception:
        return ""


def detect_document_type(filename: str, text: str) -> str:
    lower_name = filename.lower()
    if "prescription" in lower_name or "rx" in lower_name:
        return "prescription"
    if "bill" in lower_name or "invoice" in lower_name or "receipt" in lower_name:
        return "bill"
    if "test" in lower_name or "report" in lower_name:
        return "test_report"
    if "doctor" in lower_name or "slip" in lower_name:
        return "doctor_slip"
    if text and ("diagnosis" in text.lower() or "doctor" in text.lower()):
        return "prescription"
    return "unknown"


def parse_list_field(value: str) -> List[str]:
    cleaned = re.split(r"[,;]\s*", value.strip())
    return [item.strip() for item in cleaned if item.strip()]


def extract_prescription_fields(text: str) -> Dict[str, Any]:
    prescription: Dict[str, Any] = {}
    patterns = {
        "doctor_name": r"(?:Doctor|Dr\.?)(?:\s+Name)?\s*[:\-]?\s*(.+)",
        "doctor_reg": r"(?:Reg(?:istration)?(?:\s*No\.?|\s*#)?)(?:\s*[:\-])\s*([A-Z]{2}/\d{4,6}/\d{4})",
        "diagnosis": r"(?:Diagnosis|Dx)\s*[:\-]?\s*(.+)",
        "medicines_prescribed": r"(?:Medicines|Drugs|Rx)\s*[:\-]?\s*(.+)",
        "procedures": r"(?:Procedure|Procedures)\s*[:\-]?\s*(.+)",
        "tests_prescribed": r"(?:Tests|Investigations)\s*[:\-]?\s*(.+)",
    }

    for field, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            if field in ("medicines_prescribed", "procedures", "tests_prescribed"):
                prescription[field] = parse_list_field(value)
            else:
                prescription[field] = value

    if "diagnosis" not in prescription:
        match = re.search(r"(?:fever|pain|infection|fracture|allergy)", text, re.IGNORECASE)
        if match:
            prescription["diagnosis"] = match.group(0).title()

    return prescription


def extract_bill_fields(text: str) -> Dict[str, Any]:
    bill: Dict[str, Any] = {}
    amount_patterns = {
        "consultation_fee": r"Consultation(?: Fee)?\s*[:\-]?\s*₹?\s*(\d+(?:\.\d+)?)",
        "medicines": r"Medicines\s*[:\-]?\s*₹?\s*(\d+(?:\.\d+)?)",
        "diagnostic_tests": r"Diagnostic Tests\s*[:\-]?\s*₹?\s*(\d+(?:\.\d+)?)",
        "root_canal": r"Root Canal\s*[:\-]?\s*₹?\s*(\d+(?:\.\d+)?)",
        "teeth_whitening": r"Teeth Whitening\s*[:\-]?\s*₹?\s*(\d+(?:\.\d+)?)",
        "mri_scan": r"MRI Scan\s*[:\-]?\s*₹?\s*(\d+(?:\.\d+)?)",
        "therapy_charges": r"Therapy Charges\s*[:\-]?\s*₹?\s*(\d+(?:\.\d+)?)",
    }

    for field, pattern in amount_patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            bill[field] = float(match.group(1))

    additional_items: Dict[str, float] = {}
    for match in re.finditer(r"([A-Za-z ]+?)\s*[:\-]?\s*₹?\s*(\d+(?:\.\d+)?)", text):
        label = match.group(1).strip()
        amount = float(match.group(2))
        normalized = label.lower()
        if normalized not in (
            "consultation",
            "consultation fee",
            "medicines",
            "diagnostic tests",
            "root canal",
            "teeth whitening",
            "mri scan",
            "therapy charges",
        ):
            additional_items[label] = amount

    if additional_items:
        bill["additional_items"] = additional_items

    return bill


def summarize_document_content(doc_type: str, text: str, filename: str) -> str:
    if doc_type == "prescription":
        prescription = extract_prescription_fields(text)
        summary_parts = []
        if prescription.get("doctor_name"):
            summary_parts.append(f"Doctor: {prescription['doctor_name']}")
        if prescription.get("doctor_reg"):
            summary_parts.append(f"Reg: {prescription['doctor_reg']}")
        if prescription.get("diagnosis"):
            summary_parts.append(f"Diagnosis: {prescription['diagnosis']}")
        if prescription.get("medicines_prescribed"):
            summary_parts.append(f"Medicines: {', '.join(prescription['medicines_prescribed'])}")
        return summary_parts[0:3] and "; ".join(summary_parts) or f"Prescription found in {filename}."

    if doc_type == "bill":
        bill = extract_bill_fields(text)
        summary_parts = []
        for key, label in (
            ("consultation_fee", "Consultation"),
            ("medicines", "Medicines"),
            ("diagnostic_tests", "Diagnostic tests"),
            ("root_canal", "Root canal"),
            ("teeth_whitening", "Teeth whitening"),
            ("mri_scan", "MRI scan"),
            ("therapy_charges", "Therapy charges"),
        ):
            if bill.get(key) is not None:
                summary_parts.append(f"{label}: ₹{bill[key]:.2f}")
        if bill.get("additional_items"):
            summary_parts.append(f"Additional items: {', '.join(bill['additional_items'].keys())}")
        return summary_parts[0:3] and "; ".join(summary_parts) or f"Bill found in {filename}."

    if text:
        snippet = " ".join(text.strip().split()[:20])
        return f"Parsed {doc_type or 'document'} content: {snippet}..."

    return f"Uploaded {filename} but no readable content was extracted."


def merge_extracted_data_into_claim(claim_input: ClaimInput, extracted: Dict[str, Dict[str, Any]]) -> None:
    prescription_data = extracted.get("prescription", {})
    bill_data = extracted.get("bill", {})

    if prescription_data:
        existing = claim_input.documents.prescription.dict() if claim_input.documents.prescription else {}
        merged = {**existing, **{k: v for k, v in prescription_data.items() if v}}
        claim_input.documents.prescription = Prescription(**merged)

    if bill_data:
        existing = claim_input.documents.bill.dict() if claim_input.documents.bill else {}
        merged = {**existing, **{k: v for k, v in bill_data.items() if v is not None}}
        claim_input.documents.bill = Bill(**merged)


def process_uploaded_file(uploaded_file: UploadFile) -> Dict[str, Any]:
    text = extract_text_from_file(uploaded_file)
    document_type = detect_document_type(uploaded_file.filename, text)
    extracted_fields: Dict[str, Any] = {}
    if document_type == "prescription":
        extracted_fields = extract_prescription_fields(text)
    elif document_type == "bill":
        extracted_fields = extract_bill_fields(text)
    else:
        extracted_fields = {
            **extract_prescription_fields(text),
            **extract_bill_fields(text),
        }

    return {
        "filename": uploaded_file.filename,
        "document_type": document_type,
        "extracted_text": text,
        "summary": summarize_document_content(document_type, text, uploaded_file.filename),
        "fields": extracted_fields,
    }


def parse_uploaded_documents(claim_input: ClaimInput, uploaded_files: Optional[List[UploadFile]] = None) -> List[Dict[str, Any]]:
    if not uploaded_files:
        return []

    extracted: Dict[str, Dict[str, Any]] = {"prescription": {}, "bill": {}}
    uploaded_documents: List[Dict[str, Any]] = []

    for uploaded_file in uploaded_files:
        document_data = process_uploaded_file(uploaded_file)
        text = document_data["extracted_text"]
        document_type = document_data["document_type"]

        if document_type == "prescription":
            extracted["prescription"].update(extract_prescription_fields(text))
        elif document_type == "bill":
            extracted["bill"].update(extract_bill_fields(text))
        else:
            extracted["prescription"].update(extract_prescription_fields(text))
            extracted["bill"].update(extract_bill_fields(text))

        uploaded_documents.append(
            {
                "filename": uploaded_file.filename,
                "document_type": document_type,
                "summary": document_data["summary"],
            }
        )

    merge_extracted_data_into_claim(claim_input, extracted)
    return uploaded_documents


def simulate_rag_insurance_lookup(policy_id: Optional[str], diagnosis: Optional[str]) -> Dict[str, Any]:
    return {
        "policy_id": policy_id or "unknown",
        "matched_terms": [t for t in [diagnosis] if t],
        "reference_excerpt": "Checked policy coverage, waiting period, exclusions, and claim limits against current policy terms.",
        "rule_notes": [
            "Minimum claim amount must meet policy requirement.",
            "Doctor registration number is validated against policy format.",
            "Cosmetic, excluded, and waiting period conditions are checked.",
        ],
    }


def calculate_approval_score(claim_input: ClaimInput, policy: Dict[str, Any], reasons: List[str]) -> float:
    score = 95.0
    score -= len(reasons) * 12.0
    if claim_input.documents.prescription is not None:
        score += 3.0
    if claim_input.documents.bill is not None:
        score += 2.0
    return max(0.0, min(100.0, score))
