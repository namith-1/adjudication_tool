from datetime import date
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Prescription(BaseModel):
    doctor_name: Optional[str] = None
    doctor_reg: Optional[str] = None
    diagnosis: Optional[str] = None
    medicines_prescribed: Optional[List[str]] = None
    procedures: Optional[List[str]] = None
    treatment: Optional[str] = None
    tests_prescribed: Optional[List[str]] = None


class Bill(BaseModel):
    consultation_fee: Optional[float] = None
    medicines: Optional[float] = None
    diagnostic_tests: Optional[float] = None
    root_canal: Optional[float] = None
    teeth_whitening: Optional[float] = None
    mri_scan: Optional[float] = None
    therapy_charges: Optional[float] = None
    test_names: Optional[List[str]] = None
    additional_items: Optional[Dict[str, float]] = Field(default_factory=dict)


class Documents(BaseModel):
    prescription: Optional[Prescription] = None
    bill: Optional[Bill] = None


class ClaimInput(BaseModel):
    member_id: str
    member_name: str
    treatment_date: date
    claim_amount: float
    documents: Documents
    member_join_date: Optional[date] = None
    previous_claims_same_day: Optional[int] = 0
    policy_id: Optional[str] = None


class AdjudicationResult(BaseModel):
    claim_id: str
    decision: str
    approved_amount: float
    rejection_reasons: List[str] = Field(default_factory=list)
    notes: Optional[str] = ""
    confidence_score: float = 0.0
    next_steps: Optional[str] = ""
    flags: List[str] = Field(default_factory=list)
    deductions: Optional[Dict[str, float]] = Field(default_factory=dict)
    rejected_items: Optional[List[str]] = Field(default_factory=list)
    uploaded_documents: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    policy_reference: Optional[Dict[str, Any]] = Field(default_factory=dict)
