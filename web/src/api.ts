import { ClaimInput, DecisionResult, ProcessResult } from './types'

const BASE_URL = (import.meta as any).env?.VITE_API_BASE_URL ?? 'http://localhost:8000'

export async function fetchPolicy() {
  const response = await fetch(`${BASE_URL}/api/policy`)
  return response.json()
}

export async function submitClaim(claim: ClaimInput, files: File[] = []): Promise<DecisionResult> {
  if (files.length === 0) {
    const response = await fetch(`${BASE_URL}/api/claims/submit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(claim),
    })
    if (!response.ok) {
      throw new Error(`Claim submission failed: ${response.statusText}`)
    }
    return response.json()
  }

  const formData = new FormData()
  formData.append('claim', JSON.stringify(claim))
  files.forEach((file) => formData.append('files', file))

  const response = await fetch(`${BASE_URL}/api/claims/submit-with-docs`, {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    throw new Error(`Claim submission failed: ${response.statusText}`)
  }

  return response.json()
}

export async function processDocuments(files: File[]): Promise<ProcessResult> {
  const formData = new FormData()
  files.forEach((file) => formData.append('files', file))

  const response = await fetch(`${BASE_URL}/api/documents/process`, {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    throw new Error(`Document processing failed: ${response.statusText}`)
  }

  return response.json()
}
