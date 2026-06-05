import re
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from fastapi import UploadFile

from .document_processor import (
    calculate_approval_score,
    parse_uploaded_documents,
    simulate_rag_insurance_lookup,
)
from .models import ClaimInput
from .policy import load_policy, is_active_policy


def validate_doctor_registration(reg: str) -> bool:
    if not reg:
        return False
    pattern = r"^[A-Z]{2}/\d{4,6}/\d{4}$"
    return bool(re.match(pattern, reg))


def find_excluded_reason(policy: Dict[str, Any], diagnosis: str, procedures: List[str]) -> Tuple[bool, str]:
    low = diagnosis.lower() if diagnosis else ""
    for exclusion in policy.get("exclusions", []):
        if exclusion.lower() in low:
            return True, "SERVICE_NOT_COVERED"

    for procedure in procedures or []:
        if "cosmetic" in procedure.lower() or "whitening" in procedure.lower():
            return True, "SERVICE_NOT_COVERED"
        if "weight" in procedure.lower() or "bariatric" in procedure.lower():
            return True, "SERVICE_NOT_COVERED"
    return False, ""


def calculate_copay(policy: Dict[str, Any], documents: ClaimInput) -> Tuple[float, Dict[str, float]]:
    deductions: Dict[str, float] = {}
    bill = documents.documents.bill
    total = 0.0
    if bill.consultation_fee:
        total += bill.consultation_fee
    if bill.medicines:
        total += bill.medicines
    if bill.diagnostic_tests:
        total += bill.diagnostic_tests
    if bill.root_canal:
        total += bill.root_canal
    if bill.teeth_whitening:
        total += bill.teeth_whitening
    if bill.mri_scan:
        total += bill.mri_scan
    if bill.therapy_charges:
        total += bill.therapy_charges
    for item_amount in (bill.additional_items or {}).values():
        total += item_amount

    copay = 0.0
    if bill.medicines and policy["coverage_details"]["pharmacy"]["branded_drugs_copay"]:
        copay = round(bill.medicines * policy["coverage_details"]["pharmacy"]["branded_drugs_copay"] / 100, 2)
        deductions["copay"] = copay
    else:
        deductions["copay"] = 0.0

    return copay, deductions


def evaluate_waiting_period(policy: Dict[str, Any], treatment_date: date, join_date: date, diagnosis: str) -> Tuple[bool, str]:
    if not join_date:
        return True, ""
    days_on_policy = (treatment_date - join_date).days
    if days_on_policy < policy["waiting_periods"]["initial_waiting"]:
        return False, "WAITING_PERIOD"
    for condition, days in policy["waiting_periods"].get("specific_ailments", {}).items():
        if condition in (diagnosis or "").lower() and days_on_policy < days:
            return False, "WAITING_PERIOD"
    return True, ""


def adjudicate(claim_input: ClaimInput, uploaded_files: Optional[List[UploadFile]] = None) -> Dict[str, Any]:
    policy = load_policy()
    uploaded_documents = parse_uploaded_documents(claim_input, uploaded_files) if uploaded_files else []
    prescription = claim_input.documents.prescription
    bill = claim_input.documents.bill
    reasons: List[str] = []
    rejected_items: List[str] = []
    flags: List[str] = []
    policy_reference = simulate_rag_insurance_lookup(
        claim_input.policy_id,
        prescription.diagnosis if prescription else None,
    )

    if not prescription:
        reasons.append("MISSING_DOCUMENTS")
        score = calculate_approval_score(claim_input, policy, reasons)
        return build_result(
            claim_input,
            "REJECTED",
            0.0,
            reasons,
            "Prescription required",
            score / 100.0,
            {},
            flags,
            rejected_items,
            uploaded_documents,
            policy_reference,
        )

    if claim_input.claim_amount < policy["claim_requirements"]["minimum_claim_amount"]:
        reasons.append("BELOW_MIN_AMOUNT")
        score = calculate_approval_score(claim_input, policy, reasons)
        return build_result(
            claim_input,
            "REJECTED",
            0.0,
            reasons,
            f"Minimum claim amount is ₹{policy['claim_requirements']['minimum_claim_amount']}",
            score / 100.0,
            {},
            flags,
            rejected_items,
            uploaded_documents,
            policy_reference,
        )

    if not is_active_policy(policy, claim_input.treatment_date):
        reasons.append("POLICY_INACTIVE")

    valid_reg = validate_doctor_registration(prescription.doctor_reg or "")
    if not valid_reg:
        reasons.append("DOCTOR_REG_INVALID")

    if not prescription.diagnosis:
        reasons.append("INVALID_PRESCRIPTION")

    if prescription.doctor_name is None or prescription.doctor_reg is None:
        reasons.append("INVALID_PRESCRIPTION")

    wait_ok, wait_reason = evaluate_waiting_period(
        policy,
        claim_input.treatment_date,
        claim_input.member_join_date or claim_input.treatment_date,
        prescription.diagnosis or "",
    )
    if not wait_ok:
        reasons.append(wait_reason)

    if claim_input.previous_claims_same_day and claim_input.previous_claims_same_day >= 2:
        flags.append("Multiple claims same day")
        score = calculate_approval_score(claim_input, policy, reasons)
        return build_result(
            claim_input,
            "MANUAL_REVIEW",
            0.0,
            [],
            "Potential fraud or unusual pattern detected",
            score / 100.0,
            {},
            flags,
            rejected_items,
            uploaded_documents,
            policy_reference,
        )

    excluded, exclusion_code = find_excluded_reason(
        policy,
        prescription.diagnosis or "",
        prescription.procedures or [],
    )
    if excluded:
        reasons.append(exclusion_code)

    if claim_input.claim_amount > policy["coverage_details"]["per_claim_limit"]:
        reasons.append("PER_CLAIM_EXCEEDED")

    if reasons:
        score = calculate_approval_score(claim_input, policy, reasons)
        return build_result(
            claim_input,
            "REJECTED",
            0.0,
            reasons,
            "; ".join(reasons),
            score / 100.0,
            {},
            flags,
            rejected_items,
            uploaded_documents,
            policy_reference,
        )

    approved = claim_input.claim_amount
    copay, deductions = calculate_copay(policy, claim_input)
    approved = max(0.0, approved - copay)

    if approved > policy["coverage_details"]["annual_limit"]:
        reasons.append("ANNUAL_LIMIT_EXCEEDED")
        score = calculate_approval_score(claim_input, policy, reasons)
        return build_result(
            claim_input,
            "REJECTED",
            0.0,
            reasons,
            "Annual limit exceeded",
            score / 100.0,
            deductions,
            flags,
            rejected_items,
            uploaded_documents,
            policy_reference,
        )

    if prescription.procedures and any("whitening" in p.lower() for p in prescription.procedures):
        rejected_items.append("Teeth whitening - cosmetic procedure")
        approved -= bill.teeth_whitening or 0.0
        score = calculate_approval_score(claim_input, policy, reasons)
        return build_result(
            claim_input,
            "PARTIAL",
            max(0.0, approved),
            [],
            "Cosmetic procedure excluded",
            score / 100.0,
            deductions,
            flags,
            rejected_items,
            uploaded_documents,
            policy_reference,
        )

    score = calculate_approval_score(claim_input, policy, reasons)
    return build_result(
        claim_input,
        "APPROVED",
        approved,
        [],
        "Claim approved",
        score / 100.0,
        deductions,
        flags,
        rejected_items,
        uploaded_documents,
        policy_reference,
    )


def build_result(
    claim_input: ClaimInput,
    decision: str,
    amount: float,
    rejection_reasons: List[str],
    notes: str,
    confidence: float,
    deductions: Dict[str, float],
    flags: List[str],
    rejected_items: List[str],
    uploaded_documents: List[Dict[str, Any]],
    policy_reference: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "claim_id": f"CLM_{claim_input.member_id}_{int(datetime.now().timestamp())}",
        "decision": decision,
        "approved_amount": round(amount, 2),
        "rejection_reasons": rejection_reasons,
        "notes": notes,
        "confidence_score": confidence,
        "next_steps": "Upload supporting documents or contact claims support" if decision != "APPROVED" else "Receive reimbursement within 7 working days",
        "flags": flags,
        "deductions": deductions,
        "rejected_items": rejected_items,
        "uploaded_documents": uploaded_documents,
        "policy_reference": policy_reference or {},
    }
