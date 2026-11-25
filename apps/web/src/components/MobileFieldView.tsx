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
  const [custodian, setCustodian] = useState('SI Rajesh Kumar (Cyber PS)')
  const [location, setLocation] = useState('Whitefield, Bengaluru')
  const [purpose, setPurpose] = useState('Initial field seizure & BSA S.63 Part A')
  const [file, setFile] = useState<File | null>(null)
  const [clientSha, setClientSha] = useState<string>('')
  const [ingestResult, setIngestResult] = useState<IngestResponse | null>(null)
  const [handoffTo, setHandoffTo] = useState('FSL Forensic Examiner')
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

  return (
    <div className="space-y-4 p-4">
      <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-200">
        <span className="font-semibold">Field Custodian Mode (Part A):</span> Evidence is fingerprinted
        with <code className="font-mono">SHA-256</code> on-device before upload.
      </div>

      {/* Case Selection */}
      <div className="space-y-2 rounded-xl border border-zinc-800 bg-zinc-900/70 p-3">
        <label className="block text-xs font-medium uppercase tracking-wider text-zinc-400">
          Active Case
        </label>
        <select
          value={selectedCaseId}
          onChange={(e) => onSelectCase(e.target.value)}
          className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100"
        >
          <option value="">-- Select a case --</option>
          {cases.map((c) => (
            <option key={c.case_id} value={c.case_id}>
              {c.title} ({c.case_id})
            </option>
          ))}
        </select>
        <div className="flex gap-2">
          <input
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
            placeholder="New case title (e.g. Case 2026-BLR-09)"
            className="flex-1 rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-1.5 text-xs text-zinc-100"
          />
          <button
            type="button"
            onClick={handleCreateCase}
            disabled={busy || !newTitle.trim()}
            className="rounded-lg bg-zinc-800 px-3 py-1.5 text-xs font-medium text-zinc-100 hover:bg-zinc-700 disabled:opacity-40"
          >
            + Case
          </button>
        </div>
      </div>

      {/* Evidence Capture */}
      <div className="space-y-3 rounded-xl border border-zinc-800 bg-zinc-900/70 p-3">
        <label className="flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-zinc-700 bg-zinc-950/60 p-4 text-center hover:border-emerald-500/60">
          <FileUp className="h-6 w-6 text-emerald-400" />
          <span className="text-sm font-medium text-zinc-200">
            {file ? file.name : 'Tap to capture or select evidence file'}
          </span>
          <span className="text-[11px] text-zinc-500">
            {file ? `${(file.size / 1024).toFixed(1)} KB` : 'Photo, CCTV MP4, audio, PDF, or log'}
          </span>
          <input
            type="file"
            className="hidden"
            onChange={(e) => void handleFilePick(e.target.files?.[0] ?? null)}
          />
        </label>

        {clientSha && (
          <div className="rounded-lg border border-zinc-800 bg-zinc-950 p-2.5 text-xs">
            <div className="flex items-center gap-1.5 font-medium text-emerald-400">
              <Fingerprint className="h-3.5 w-3.5" />
              On-Device WebCrypto SHA-256
            </div>
            <p className="mt-1 break-all font-mono text-[11px] text-zinc-300">{clientSha}</p>
          </div>
        )}

        <div className="grid grid-cols-1 gap-2">
          <input
            value={custodian}
            onChange={(e) => setCustodian(e.target.value)}
            placeholder="Custodian Name / Rank"
            className="rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-xs text-zinc-100"
          />
          <input
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            placeholder="Seizure Location"
            className="rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-xs text-zinc-100"
          />
          <input
            value={purpose}
            onChange={(e) => setPurpose(e.target.value)}
            placeholder="Purpose"
            className="rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-xs text-zinc-100"
          />
        </div>

        <button
          type="button"
          onClick={() => void handleIngest()}
          disabled={busy || !selectedCaseId || !file}
          className="flex w-full items-center justify-center gap-2 rounded-lg bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-emerald-500 disabled:opacity-40"
        >
          <ShieldCheck className="h-4 w-4" />
          {busy ? 'Sealing...' : 'Seal & Upload Evidence'}
        </button>
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/40 bg-red-500/10 p-2.5 text-xs text-red-300">
          {error}
        </div>
      )}

      {/* Sealed Confirmation + QR Handoff */}
      {ingestResult && (
        <div className="space-y-3 rounded-xl border border-emerald-500/40 bg-emerald-950/20 p-3">
          <div className="flex items-center justify-between">
            <span className="flex items-center gap-1.5 text-xs font-semibold text-emerald-400">
              <CheckCircle2 className="h-4 w-4" />
              {ingestResult.idempotent_hit ? 'Idempotent Match (Already Sealed)' : 'Evidence Sealed'}
            </span>
            {hashMatches && (
              <span className="rounded-full bg-emerald-500/20 px-2 py-0.5 text-[10px] font-semibold text-emerald-300">
                CLIENT = SERVER SHA-256
              </span>
            )}
          </div>

          <div className="flex flex-col items-center gap-2 rounded-lg bg-white p-3 text-zinc-900">
            <QRCodeSVG
              size={128}
              value={JSON.stringify({
                asset_id: ingestResult.asset_id,
                sha256: ingestResult.sha256,
                case_id: selectedCaseId,
              })}
            />
            <span className="flex items-center gap-1 text-[11px] font-medium text-zinc-700">
              <QrCode className="h-3.5 w-3.5" /> Custody QR · {ingestResult.asset_id}
            </span>
          </div>

          <div className="space-y-2 border-t border-emerald-500/20 pt-2">
            <label className="block text-[11px] font-medium text-zinc-300">
              Log Handoff to Forensic Expert
            </label>
            <div className="flex gap-2">
              <input
                value={handoffTo}
                onChange={(e) => setHandoffTo(e.target.value)}
                className="flex-1 rounded-lg border border-zinc-700 bg-zinc-950 px-2.5 py-1.5 text-xs text-zinc-100"
              />
              <button
                type="button"
                onClick={() => void handleHandoff()}
                disabled={busy}
                className="flex items-center gap-1 rounded-lg bg-zinc-100 px-3 py-1.5 text-xs font-semibold text-zinc-950 hover:bg-white"
              >
                <Send className="h-3 w-3" /> Send
              </button>
            </div>
            {handoffStatus && <p className="text-xs text-emerald-300">{handoffStatus}</p>}
          </div>
        </div>
      )}
    </div>
  )
}
