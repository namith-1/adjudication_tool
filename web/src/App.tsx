import { useState } from 'react'
import { ClaimInput, DecisionResult, ProcessResult, ProcessedDocument } from './types'
import { submitClaim, processDocuments } from './api'

const initialClaim: ClaimInput = {
  member_id: 'EMP001',
  member_name: 'Rajesh Kumar',
  treatment_date: new Date().toISOString().slice(0, 10),
  claim_amount: 1500,
  documents: {
    prescription: {
      doctor_name: 'Dr. Sharma',
      doctor_reg: 'KA/45678/2015',
      diagnosis: 'Viral fever',
      medicines_prescribed: ['Paracetamol 650mg', 'Vitamin C'],
    },
    bill: {
      consultation_fee: 1000,
      diagnostic_tests: 500,
    },
  },
}

function App() {
  const [claim, setClaim] = useState<ClaimInput>(initialClaim)
  const [documentFiles, setDocumentFiles] = useState<File[]>([])
  const [result, setResult] = useState<DecisionResult | null>(null)
  const [pipelineResult, setPipelineResult] = useState<ProcessResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [processingDocuments, setProcessingDocuments] = useState(false)

  const mergeExtractedFields = (claimData: ClaimInput, documents: ProcessedDocument[]) => {
    const prescriptionKeys = new Set([
      'doctor_name',
      'doctor_reg',
      'diagnosis',
      'medicines_prescribed',
      'procedures',
      'treatment',
      'tests_prescribed',
    ])
    const billKeys = new Set([
      'consultation_fee',
      'medicines',
      'diagnostic_tests',
      'root_canal',
      'teeth_whitening',
      'mri_scan',
      'therapy_charges',
      'test_names',
      'additional_items',
    ])

    const prescription = { ...claimData.documents.prescription }
    const bill = { ...claimData.documents.bill }

    documents.forEach((doc) => {
      Object.entries(doc.fields || {}).forEach(([key, value]) => {
        if (prescriptionKeys.has(key)) {
          ;(prescription as any)[key] = value
        } else if (billKeys.has(key)) {
          ;(bill as any)[key] = value
        }
      })
    })

    return {
      ...claimData,
      documents: {
        ...claimData.documents,
        prescription,
        bill,
      },
    }
  }

  const handleProcessDocuments = async () => {
    if (documentFiles.length === 0) {
      setError('Upload documents first to process them.')
      return
    }

    setProcessingDocuments(true)
    setError(null)
    try {
      const pipeline = await processDocuments(documentFiles)
      setPipelineResult(pipeline)
      const mergedClaim = mergeExtractedFields(claim, pipeline.documents)
      setClaim(mergedClaim)
    } catch (err: any) {
      const message = err?.message || 'Document processing failed'
      setError(message)
    } finally {
      setProcessingDocuments(false)
    }
  }

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const response = await submitClaim(claim, documentFiles)
      setResult(response)
    } catch (err: any) {
      const message = err?.message || 'Unable to submit claim'
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  const updateField = (field: string, value: string | number) => {
    setClaim((current) => ({ ...current, [field]: value }))
  }

  const updateBillField = (field: string, value: number) => {
    setClaim((current) => ({
      ...current,
      documents: {
        ...current.documents,
        bill: { ...current.documents.bill, [field]: value },
      },
    }))
  }

  const handleDocumentFiles = (files: FileList | null) => {
    setDocumentFiles(files ? Array.from(files) : [])
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-5xl py-10 px-4 sm:px-6 lg:px-8">
        <header className="mb-8 rounded-3xl bg-white p-8 shadow-sm ring-1 ring-slate-200">
          <h1 className="text-3xl font-semibold">Plum OPD Claim Adjudication</h1>
          <p className="mt-3 text-slate-600">
            Submit claim details, extract document fields, and get an approval decision using FastAPI backend logic.
          </p>
        </header>

        <main className="grid gap-8 lg:grid-cols-[1.2fr_0.8fr]">
          <section className="rounded-3xl bg-white p-8 shadow-sm ring-1 ring-slate-200">
            <h2 className="text-xl font-semibold">Claim submission</h2>
            <form className="space-y-6 mt-6" onSubmit={handleSubmit}>
              <div className="grid gap-4 sm:grid-cols-2">
                <label className="block">
                  <span className="text-sm font-medium text-slate-700">Member ID</span>
                  <input
                    value={claim.member_id}
                    onChange={(event) => updateField('member_id', event.target.value)}
                    className="mt-1 w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-100"
                  />
                </label>
                <label className="block">
                  <span className="text-sm font-medium text-slate-700">Member name</span>
                  <input
                    value={claim.member_name}
                    onChange={(event) => updateField('member_name', event.target.value)}
                    className="mt-1 w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-100"
                  />
                </label>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <label className="block">
                  <span className="text-sm font-medium text-slate-700">Treatment date</span>
                  <input
                    type="date"
                    value={claim.treatment_date}
                    onChange={(event) => updateField('treatment_date', event.target.value)}
                    className="mt-1 w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-100"
                  />
                </label>
                <label className="block">
                  <span className="text-sm font-medium text-slate-700">Claim amount</span>
                  <input
                    type="number"
                    value={claim.claim_amount}
                    onChange={(event) => updateField('claim_amount', Number(event.target.value))}
                    className="mt-1 w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-100"
                  />
                </label>
              </div>

              <div className="rounded-2xl bg-slate-50 p-6">
                <h3 className="text-lg font-semibold">Upload supporting documents</h3>
                <p className="mt-2 text-sm text-slate-600">
                  Upload prescription, bill, test report, or doctor slip files. The backend will parse text fields and apply policy checks.
                </p>
                <label className="mt-4 block">
                  <span className="text-sm font-medium text-slate-700">Documents</span>
                  <input
                    type="file"
                    multiple
                    onChange={(event) => handleDocumentFiles(event.target.files)}
                    className="mt-1 w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-slate-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-100"
                  />
                </label>
                <div className="mt-4 space-y-1 text-sm text-slate-600">
                  {documentFiles.length > 0 ? (
                    documentFiles.map((file) => (
                      <p key={file.name}>{file.name}</p>
                    ))
                  ) : (
                    <p>No documents selected yet.</p>
                  )}
                </div>
              </div>

              <div className="rounded-2xl bg-slate-50 p-6">
                <h3 className="text-lg font-semibold">Prescription details</h3>
                <div className="grid gap-4 sm:grid-cols-2 mt-4">
                  <label className="block">
                    <span className="text-sm font-medium text-slate-700">Doctor name</span>
                    <input
                      value={claim.documents.prescription?.doctor_name ?? ''}
                      onChange={(event) =>
                        setClaim((current) => ({
                          ...current,
                          documents: {
                            ...current.documents,
                            prescription: {
                              ...current.documents.prescription,
                              doctor_name: event.target.value,
                            },
                          },
                        }))
                      }
                      className="mt-1 w-full rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-100"
                    />
                  </label>
                  <label className="block">
                    <span className="text-sm font-medium text-slate-700">Doctor reg.</span>
                    <input
                      value={claim.documents.prescription?.doctor_reg ?? ''}
                      onChange={(event) =>
                        setClaim((current) => ({
                          ...current,
                          documents: {
                            ...current.documents,
                            prescription: {
                              ...current.documents.prescription,
                              doctor_reg: event.target.value,
                            },
                          },
                        }))
                      }
                      className="mt-1 w-full rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-100"
                    />
                  </label>
                </div>
                <label className="block mt-4">
                  <span className="text-sm font-medium text-slate-700">Diagnosis</span>
                  <input
                    value={claim.documents.prescription?.diagnosis ?? ''}
                    onChange={(event) =>
                      setClaim((current) => ({
                        ...current,
                        documents: {
                          ...current.documents,
                          prescription: {
                            ...current.documents.prescription,
                            diagnosis: event.target.value,
                          },
                        },
                      }))
                    }
                    className="mt-1 w-full rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-100"
                  />
                </label>
              </div>

              <div className="rounded-2xl bg-slate-50 p-6">
                <h3 className="text-lg font-semibold">Bill details</h3>
                <div className="grid gap-4 sm:grid-cols-2 mt-4">
                  <label className="block">
                    <span className="text-sm font-medium text-slate-700">Consultation fee</span>
                    <input
                      type="number"
                      value={claim.documents.bill.consultation_fee ?? 0}
                      onChange={(event) => updateBillField('consultation_fee', Number(event.target.value))}
                      className="mt-1 w-full rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-100"
                    />
                  </label>
                  <label className="block">
                    <span className="text-sm font-medium text-slate-700">Medicines</span>
                    <input
                      type="number"
                      value={claim.documents.bill.medicines ?? 0}
                      onChange={(event) => updateBillField('medicines', Number(event.target.value))}
                      className="mt-1 w-full rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-100"
                    />
                  </label>
                </div>

                <div className="grid gap-4 sm:grid-cols-2 mt-4">
                  <label className="block">
                    <span className="text-sm font-medium text-slate-700">Diagnostic tests</span>
                    <input
                      type="number"
                      value={claim.documents.bill.diagnostic_tests ?? 0}
                      onChange={(event) => updateBillField('diagnostic_tests', Number(event.target.value))}
                      className="mt-1 w-full rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-100"
                    />
                  </label>
                  <label className="block">
                    <span className="text-sm font-medium text-slate-700">Previous same-day claims</span>
                    <input
                      type="number"
                      value={claim.previous_claims_same_day ?? 0}
                      onChange={(event) => updateField('previous_claims_same_day', Number(event.target.value))}
                      className="mt-1 w-full rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-100"
                    />
                  </label>
                </div>
              </div>

              <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
                <button
                  type="button"
                  disabled={processingDocuments}
                  onClick={handleProcessDocuments}
                  className="inline-flex items-center justify-center rounded-2xl border border-indigo-600 bg-white px-6 py-3 text-indigo-600 transition hover:bg-indigo-50 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {processingDocuments ? 'Processing…' : 'Process Documents'}
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="inline-flex items-center justify-center rounded-2xl bg-indigo-600 px-6 py-3 text-white transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {loading ? 'Submitting…' : 'Submit Claim'}
                </button>
                <p className="text-sm text-slate-500">Example claim uses policy rules from the assignment.</p>
              </div>
            </form>
          </section>

          <aside className="space-y-6">
            <div className="rounded-3xl bg-white p-8 shadow-sm ring-1 ring-slate-200">
              <h2 className="text-xl font-semibold">Decision output</h2>
              {error ? (
                <p className="mt-4 rounded-2xl bg-rose-50 p-4 text-rose-700">{error}</p>
              ) : result ? (
                <div className="mt-4 space-y-4">
                  <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <p className="text-sm font-semibold text-slate-600">Decision</p>
                        <p className="text-2xl font-bold text-slate-900">{result.decision}</p>
                      </div>
                      <div className="rounded-2xl bg-white px-3 py-2 text-sm font-medium text-slate-700 ring-1 ring-slate-200">
                        {result.confidence_score * 100}% confidence
                      </div>
                    </div>
                    <p className="mt-3 text-sm text-slate-600">{result.notes}</p>
                  </div>

                  <div className="rounded-2xl border border-slate-200 bg-white p-4">
                    <p className="text-sm font-semibold text-slate-700">Approved amount</p>
                    <p className="mt-2 text-3xl font-semibold text-indigo-600">₹{result.approved_amount}</p>
                    {result.rejection_reasons.length > 0 && (
                      <div className="mt-4 space-y-2">
                        <p className="text-sm font-semibold text-slate-700">Rejection reasons</p>
                        <ul className="list-disc pl-5 text-sm text-slate-600">
                          {result.rejection_reasons.map((reason) => (
                            <li key={reason}>{reason}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {result.rejected_items.length > 0 && (
                      <div className="mt-4 space-y-2">
                        <p className="text-sm font-semibold text-slate-700">Rejected items</p>
                        <ul className="list-disc pl-5 text-sm text-slate-600">
                          {result.rejected_items.map((item) => (
                            <li key={item}>{item}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {result.uploaded_documents?.length ? (
                      <div className="mt-4 space-y-2 rounded-2xl border border-slate-200 bg-slate-50 p-4">
                        <p className="text-sm font-semibold text-slate-700">Parsed documents</p>
                        <ul className="space-y-2 text-sm text-slate-600">
                          {result.uploaded_documents.map((doc) => (
                            <li key={doc.filename}>
                              <span className="font-medium">{doc.filename}</span>: {doc.summary}
                            </li>
                          ))}
                        </ul>
                      </div>
                    ) : null}
                    {result.policy_reference ? (
                      <div className="mt-4 space-y-2 rounded-2xl border border-slate-200 bg-slate-50 p-4">
                        <p className="text-sm font-semibold text-slate-700">Policy reference</p>
                        <p className="text-sm text-slate-600">{result.policy_reference.policy_name}</p>
                        <p className="text-sm text-slate-600">{result.policy_reference.diagnosis_reference}</p>
                      </div>
                    ) : null}
                  </div>
                </div>
              ) : (
                <p className="mt-4 text-slate-600">Submit a claim to see the adjudication decision here.</p>
              )}
            </div>

            {pipelineResult ? (
              <div className="rounded-3xl bg-white p-8 shadow-sm ring-1 ring-slate-200">
                <h2 className="text-xl font-semibold">Document processing pipeline</h2>
                <p className="mt-2 text-sm text-slate-600">These files were sent to `/api/documents/process` and merged into the claim data before submission.</p>
                <div className="mt-4 space-y-4">
                  {pipelineResult.documents.map((doc) => (
                    <div key={doc.filename} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                      <p className="text-sm font-semibold text-slate-700">{doc.filename}</p>
                      <p className="text-sm text-slate-600">Type: {doc.document_type}</p>
                      <p className="mt-2 text-sm text-slate-600">{doc.summary}</p>
                      {doc.extracted_text ? (
                        <details className="mt-2 text-sm text-slate-600">
                          <summary className="cursor-pointer font-medium text-slate-700">Extracted text preview</summary>
                          <p className="mt-2 whitespace-pre-wrap">{doc.extracted_text.slice(0, 300)}{doc.extracted_text.length > 300 ? '...' : ''}</p>
                        </details>
                      ) : null}
                    </div>
                  ))}
                </div>
              </div>
            ) : null}

            <div className="rounded-3xl bg-white p-8 shadow-sm ring-1 ring-slate-200">
              <h2 className="text-xl font-semibold">Assignment scope</h2>
              <ul className="mt-4 space-y-2 text-sm text-slate-600">
                <li>• Document processing / OCR can be mocked during MVP stage.</li>
                <li>• Policy validation uses instruction file rules and limits.</li>
                <li>• Decision engine returns approve/partial/reject/manual review.</li>
                <li>• Backend and frontend are connected through `/api/claims/submit` and `/api/claims/submit-with-docs`.</li>
              </ul>
            </div>
          </aside>
        </main>
      </div>
    </div>
  )
}

export default App
