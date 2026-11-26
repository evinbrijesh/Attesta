import { useState } from 'react'
import { QRCodeSVG } from 'qrcode.react'
import { CheckCircle2, FileUp, Fingerprint, QrCode, Send, ShieldCheck } from 'lucide-react'
import { api, computeClientSha256, type CaseItem, type IngestResponse } from '../api'

interface Props {
  cases: CaseItem[]
  selectedCaseId: string
  onSelectCase: (id: string) => void
  onCaseCreated: (c: CaseItem) => void
  onAssetUpdated: (assetId: string) => void
}

export function MobileFieldView({
  cases,
  selectedCaseId,
  onSelectCase,
  onCaseCreated,
  onAssetUpdated,
}: Props) {
  const [newTitle, setNewTitle] = useState('')
  const [custodian, setCustodian] = useState('')
  const [location, setLocation] = useState('')
  const [purpose, setPurpose] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [clientSha, setClientSha] = useState<string>('')
  const [ingestResult, setIngestResult] = useState<IngestResponse | null>(null)
  const [handoffTo, setHandoffTo] = useState('')
  const [handoffStatus, setHandoffStatus] = useState<string>('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function handleFilePick(f: File | null) {
    setFile(f)
    setIngestResult(null)
    setHandoffStatus('')
    setError('')
    if (!f) {
      setClientSha('')
      return
    }
    const sha = await computeClientSha256(f)
    setClientSha(sha)
  }

  async function handleCreateCase() {
    if (!newTitle.trim()) return
    setBusy(true)
    setError('')
    try {
      const created = await api.createCase(newTitle.trim(), 'Field mobile intake')
      onCaseCreated(created)
      onSelectCase(created.case_id)
      setNewTitle('')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to create case')
    } finally {
      setBusy(false)
    }
  }

  async function handleIngest() {
    if (!selectedCaseId || !file) return
    setBusy(true)
    setError('')
    try {
      const res = await api.ingestFile(selectedCaseId, file, custodian, location, purpose)
      setIngestResult(res)
      onAssetUpdated(res.asset_id)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Upload failed')
    } finally {
      setBusy(false)
    }
  }

  async function handleHandoff() {
    if (!ingestResult) return
    setBusy(true)
    setError('')
    try {
      await api.recordHandoff(ingestResult.asset_id, {
        actor_from: custodian,
        actor_to: handoffTo,
        purpose: 'Transfer for BSA Section 63(4) Part B certification',
        location,
        notes: 'Logged from Field Mobile PWA',
      })
      setHandoffStatus(`Handoff sealed to ${handoffTo}`)
      onAssetUpdated(ingestResult.asset_id)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Handoff failed')
    } finally {
      setBusy(false)
    }
  }

  const hashMatches = ingestResult && clientSha && ingestResult.sha256 === clientSha
  const step = ingestResult ? 3 : file ? 2 : 1

  return (
    <div className="space-y-4 p-4 text-[#141413]">
      {/* 3-Step Intake Progress */}
      <div className="flex items-center justify-between border-b border-[#e5dfd3] pb-3 font-mono text-[10px] font-medium">
        <span className={step >= 1 ? 'text-[#0f5132]' : 'text-[#78716c]'}>1. CASE</span>
        <span className="text-[#d6cfc2]" aria-hidden="true">/</span>
        <span className={step >= 2 ? 'text-[#0f5132]' : 'text-[#78716c]'}>2. FINGERPRINT</span>
        <span className="text-[#d6cfc2]" aria-hidden="true">/</span>
        <span className={step >= 3 ? 'text-[#0f5132]' : 'text-[#78716c]'}>3. QR SEAL</span>
      </div>

      <div className="rounded-xl border border-[#b45309]/25 bg-[#fef3c7]/60 px-3 py-2 text-[11px] leading-relaxed text-[#78350f]">
        <span className="font-semibold">Part A Pre-Upload Seal:</span> Evidence is hashed with{' '}
        <code className="font-mono font-semibold">SHA-256</code> on-device before leaving your phone.
      </div>

      {/* Case Selection */}
      <div className="space-y-2 rounded-xl border border-[#ded8cc] bg-white p-3.5">
        <label htmlFor="mobile-case-select" className="block text-[10px] font-semibold uppercase tracking-wider text-[#57534e]">
          Active Case Dossier
        </label>
        <select
          id="mobile-case-select"
          value={selectedCaseId}
          onChange={(e) => onSelectCase(e.target.value)}
          className="min-h-[44px] w-full rounded-lg border border-[#d6cfc2] bg-[#faf8f4] px-3 py-2 text-xs font-medium text-[#141413]"
        >
          <option value="">Select a case</option>
          {cases.map((c) => (
            <option key={c.case_id} value={c.case_id}>
              {c.title} ({c.case_id})
            </option>
          ))}
        </select>
        <div className="flex gap-2">
          <input
            aria-label="New case title"
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
            placeholder="New case title (e.g. Case 2026-BLR-09)"
            className="min-h-[44px] flex-1 rounded-lg border border-[#d6cfc2] bg-[#faf8f4] px-3 py-2 text-xs text-[#141413] placeholder:text-[#78716c]"
          />
          <button
            type="button"
            onClick={handleCreateCase}
            disabled={busy || !newTitle.trim()}
            className="min-h-[44px] rounded-lg bg-[#141413] px-3.5 py-2 text-xs font-medium text-white hover:bg-[#292524] disabled:opacity-40"
          >
            + Case
          </button>
        </div>
      </div>

      {/* Evidence Capture */}
      <div className="space-y-3 rounded-xl border border-[#ded8cc] bg-white p-3.5 shadow-2xs">
        <label className="flex cursor-pointer flex-col items-center justify-center gap-1.5 rounded-xl border border-dashed border-[#c7bfb0] bg-[#faf8f4] p-4 text-center transition hover:border-[#0f5132]">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-[#0f5132]/10 text-[#0f5132]">
            <FileUp className="h-4 w-4" />
          </div>
          <span className="text-xs font-semibold text-[#141413]">
            {file ? file.name : 'Tap to capture or select evidence file'}
          </span>
          <span className="text-[11px] text-[#6b665c]">
            {file ? `${(file.size / 1024).toFixed(1)} KB` : 'Photo, CCTV MP4, audio, PDF, or forensic log'}
          </span>
          <input
            type="file"
            className="hidden"
            onChange={(e) => void handleFilePick(e.target.files?.[0] ?? null)}
          />
        </label>

        {clientSha && (
          <div className="rounded-lg border border-[#0f5132]/25 bg-[#0f5132]/5 p-2.5 text-xs">
            <div className="flex items-center gap-1.5 font-semibold text-[#0f5132]">
              <Fingerprint className="h-3.5 w-3.5" />
              On-Device WebCrypto SHA-256
            </div>
            <p className="mt-1 break-all font-mono text-[10px] text-[#292524]">{clientSha}</p>
          </div>
        )}

        <div className="grid grid-cols-1 gap-2.5">
          <div>
            <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wider text-[#6b665c]">
              Custodian (Part A) *
            </label>
            <input
              value={custodian}
              onChange={(e) => setCustodian(e.target.value)}
              placeholder="Who is in lawful control of this file?"
              className="w-full rounded-lg border border-[#d6cfc2] bg-[#faf8f4] px-3 py-2 text-xs text-[#141413] placeholder:text-[#a8a29e]"
            />
          </div>
          <div>
            <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wider text-[#6b665c]">
              Collection Location
            </label>
            <input
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              placeholder="Where was the evidence collected?"
              className="w-full rounded-lg border border-[#d6cfc2] bg-[#faf8f4] px-3 py-2 text-xs text-[#141413] placeholder:text-[#a8a29e]"
            />
          </div>
          <div>
            <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wider text-[#6b665c]">
              Purpose / Context
            </label>
            <input
              value={purpose}
              onChange={(e) => setPurpose(e.target.value)}
              placeholder="Reason for intake (e.g. seizure, preservation)"
              className="w-full rounded-lg border border-[#d6cfc2] bg-[#faf8f4] px-3 py-2 text-xs text-[#141413] placeholder:text-[#a8a29e]"
            />
          </div>
        </div>

        <button
          type="button"
          onClick={() => void handleIngest()}
          disabled={busy || !selectedCaseId || !file || !custodian.trim()}
          className="flex w-full items-center justify-center gap-2 rounded-lg bg-[#0f5132] px-4 py-2.5 text-xs font-semibold text-white shadow-xs transition hover:bg-[#0c4128] disabled:opacity-40"
        >
          <ShieldCheck className="h-4 w-4" />
          {busy ? 'Sealing...' : 'Seal & Upload Evidence'}
        </button>
      </div>

      {error && (
        <div className="rounded-lg border border-red-600/30 bg-red-50 p-2.5 text-xs text-red-700">
          {error}
        </div>
      )}

      {/* Sealed Confirmation + QR Handoff */}
      {ingestResult && (
        <div className="space-y-3 rounded-xl border border-[#0f5132]/30 bg-white p-3.5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="flex items-center gap-1.5 text-xs font-semibold text-[#0f5132]">
              <CheckCircle2 className="h-4 w-4" />
              {ingestResult.idempotent_hit ? 'Idempotent Match (Already Sealed)' : 'Evidence Sealed'}
            </span>
            {hashMatches && (
              <span className="rounded-full bg-[#0f5132]/10 px-2 py-0.5 font-mono text-[9px] font-semibold text-[#0f5132]">
                CLIENT = SERVER
              </span>
            )}
          </div>

          <div className="flex flex-col items-center gap-2 rounded-lg border border-[#e5dfd3] bg-[#faf8f4] p-3">
            <QRCodeSVG
              size={124}
              value={JSON.stringify({
                asset_id: ingestResult.asset_id,
                sha256: ingestResult.sha256,
                case_id: selectedCaseId,
              })}
            />
            <span className="flex items-center gap-1 font-mono text-[10px] font-medium text-[#57534e]">
              <QrCode className="h-3.5 w-3.5" /> {ingestResult.asset_id}
            </span>
          </div>

          <div className="space-y-2 border-t border-[#e5dfd3] pt-2.5">
            <label className="block text-[10px] font-semibold uppercase tracking-wider text-[#6b665c]">
              Log Custody Handoff
            </label>
            <div className="flex gap-2">
              <input
                value={handoffTo}
                onChange={(e) => setHandoffTo(e.target.value)}
                placeholder="Recipient (e.g. Forensic Lab / Advocate)"
                className="flex-1 rounded-lg border border-[#d6cfc2] bg-[#faf8f4] px-2.5 py-1.5 text-xs text-[#141413] placeholder:text-[#a8a29e]"
              />
              <button
                type="button"
                onClick={() => void handleHandoff()}
                disabled={busy || !handoffTo.trim()}
                className="flex items-center gap-1 rounded-lg bg-[#141413] px-3 py-1.5 text-xs font-semibold text-white hover:bg-[#292524] disabled:opacity-40"
              >
                <Send className="h-3 w-3" /> Send
              </button>
            </div>
            {handoffStatus && <p className="text-xs font-medium text-[#0f5132]">{handoffStatus}</p>}
          </div>
        </div>
      )}
    </div>
  )
}
