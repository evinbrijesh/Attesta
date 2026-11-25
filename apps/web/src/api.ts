export interface CaseItem {
  case_id: string
  title: string
  description: string
  created_at: string
}

export interface AssetItem {
  asset_id: string
  case_id: string
  filename: string
  media_type: string
  sha256: string
  blake3: string
  size_bytes: number
  ingested_at: string
}

export interface IngestResponse {
  asset_id: string
  sha256: string
  blake3: string
  size_bytes: number
  idempotent_hit: boolean
  intake_event_id: string
}

export interface CustodyEvent {
  event_id: string
  case_id: string
  asset_id: string
  seq: number
  event_type: string
  actor_from: string
  actor_to: string
  purpose: string
  location: string
  occurred_at_utc: string
  prev_hash: string
  event_hash: string
  signer_public_key: string
  signature: string
  notes: string
}

export interface VerifyResponse {
  valid: boolean
  asset_id: string
  event_count: number
  file_hash_match: boolean
  errors: string[]
}

export interface AdvisoryFlag {
  code: string
  severity: string
  message: string
  advisory_only: boolean
}

export interface ForensicsResponse {
  asset_id: string
  is_image: boolean
  detected_format: string
  width: number | null
  height: number | null
  exif: Record<string, string>
  ela_mean_diff: number | null
  ela_max_diff: number | null
  advisory_only: boolean
  flags: AdvisoryFlag[]
}

export async function computeClientSha256(file: File): Promise<string> {
  const buf = await file.arrayBuffer()
  const hashBuf = await crypto.subtle.digest('SHA-256', buf)
  return Array.from(new Uint8Array(hashBuf))
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('')
}

async function req<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init)
  if (!res.ok) {
    const msg = await res.text()
    throw new Error(msg || `HTTP ${res.status}`)
  }
  return res.json() as Promise<T>
}

export interface AuditFlag {
  code: string
  severity: string
  message: string
  citation: string
}

export interface AuditResponse {
  asset_id: string
  parsed_log: {
    format_detected: string
    operator_or_examiner: string | null
    device_or_source: string | null
    declared_sha256: string | null
  } | null
  flags: AuditFlag[]
  part_a_draft: string
  part_b_draft: string
  drafter_mode: string
  disclaimer: string
  n8n_notification: { delivered: boolean; status_code?: number; reason?: string } | null
}

export const api = {
  listCases: () => req<CaseItem[]>('/api/cases'),
  createCase: (title: string, description: string) =>
    req<CaseItem>('/api/cases', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, description }),
    }),
  listAssets: (caseId: string) => req<AssetItem[]>(`/api/cases/${caseId}/assets`),
  ingestFile: (caseId: string, file: File, custodian: string, location: string, purpose: string) => {
    const fd = new FormData()
    fd.append('file', file)
    fd.append('custodian', custodian)
    fd.append('location', location)
    fd.append('purpose', purpose)
    return req<IngestResponse>(`/api/cases/${caseId}/ingest`, { method: 'POST', body: fd })
  },
  listEvents: (assetId: string) => req<CustodyEvent[]>(`/api/assets/${assetId}/events`),
  recordHandoff: (
    assetId: string,
    payload: { actor_from: string; actor_to: string; purpose: string; location: string; notes: string },
  ) =>
    req<CustodyEvent>(`/api/assets/${assetId}/handoff`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),
  verifyAsset: (assetId: string) => req<VerifyResponse>(`/api/assets/${assetId}/verify`),
  getForensics: (assetId: string) => req<ForensicsResponse>(`/api/assets/${assetId}/forensics`),
  runAudit: (assetId: string, logText: string, notifyN8n: boolean) =>
    req<AuditResponse>(`/api/assets/${assetId}/audit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ log_text: logText, notify_n8n: notifyN8n }),
    }),
  signSection63: (
    assetId: string,
    payload: {
      custodian_name: string
      custodian_designation: string
      expert_name: string
      expert_designation: string
      part_a_text: string
      part_b_text: string
      notify_n8n: boolean
    },
  ) =>
    req<{
      cert_id: string
      asset_id: string
      signed_at_utc: string
      pdf_sha256: string
      head_event_hash: string
      n8n_notification: { delivered: boolean } | null
    }>(`/api/assets/${assetId}/sign-s63`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),
  certificatePdfUrl: (assetId: string) => `/api/assets/${assetId}/certificate.pdf`,
  bundleUrl: (assetId: string) => `/api/assets/${assetId}/bundle`,
}
