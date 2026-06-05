export interface ClaimDocuments {
  prescription?: Prescription;
  bill: Bill;
}

export interface Prescription {
  doctor_name?: string;
  doctor_reg?: string;
  diagnosis?: string;
  medicines_prescribed?: string[];
  procedures?: string[];
  treatment?: string;
  tests_prescribed?: string[];
}

export interface Bill {
  consultation_fee?: number;
  medicines?: number;
  diagnostic_tests?: number;
  root_canal?: number;
  teeth_whitening?: number;
  mri_scan?: number;
  therapy_charges?: number;
  test_names?: string[];
  additional_items?: Record<string, number>;
}

export interface ClaimInput {
  member_id: string;
  member_name: string;
  treatment_date: string;
  claim_amount: number;
  documents: ClaimDocuments;
  member_join_date?: string;
  previous_claims_same_day?: number;
}

export interface DecisionResult {
  claim_id: string;
  decision: string;
  approved_amount: number;
  rejection_reasons: string[];
  notes: string;
  confidence_score: number;
  next_steps: string;
  flags: string[];
  deductions: Record<string, number>;
  rejected_items: string[];
  uploaded_documents?: Array<{ filename: string; document_type: string; summary: string }>;
  policy_reference?: Record<string, any>;
}

export interface ProcessedDocument {
  filename: string;
  document_type: string;
  extracted_text: string;
  summary: string;
  fields: Record<string, any>;
}

export interface ProcessResult {
  documents: ProcessedDocument[];
}
