import { useEffect, useState } from 'react'
import {
  AlertTriangle,
  Bot,
  Check,
  CheckCircle2,
  Copy,
  Download,
  FileSearch,
  Link2,
  Scale,
  ShieldAlert,
  ShieldCheck,
} from 'lucide-react'
import {
  api,
  type AssetItem,
  type AuditResponse,
  type CaseItem,
  type CustodyEvent,
  type ForensicsResponse,
  type VerifyResponse,
} from '../api'

const SAMPLE_LOGS: Record<string, string> = {
  dd: `[2026-11-24T04:15:00Z] OPERATOR: SI Rajesh Kumar (Cyber PS Whitefield)\n[2026-11-24T04:15:02Z] COMMAND: dd if=/dev/sdb1 of=/mnt/vault/cctv_gate_01.raw bs=4M\n[2026-11-24T04:15:15Z] WRITE_BLOCKER: Tableau T8u USB 3.0 Forensic Bridge\n[2026-11-24T04:15:18Z] SHA256(cctv_gate_01.raw): e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`,
  ewfacquire: `ewfacquire 20230405\nExaminer Name: Dr. Ananya Rao (FSL Bengaluru)\nAcquisition started at: 2026-11-24 10:05:00 IST (UTC+05:30)\nAcquisition completed at: 2026-11-24 04:20:00 UTC\nMedia Type: Fixed Disk (Samsung EVO 512GB)\nNOTE: Device RTC was 15 minutes behind network time.`,
  officer_notes: `Seizure Memo — Synthetic Case #2026-DEL-07\nNote: Shop manager first sent a copy of the video over WhatsApp to IO phone at 11:45 AM before pen drive was sealed.\nSealed pen drive was kept in station malkhana; handed over to FSL courier at 16:30 PM IST (4h 45m gap with no intermediate log entry).`,
}

interface Props {
  cases: CaseItem[]
  selectedCaseId: string
  onSelectCase: (id: string) => void
  selectedAssetId: string
  onSelectAsset: (id: string) => void
  refreshKey: number
}

export function ExpertDesktopView({
  cases,
  selectedCaseId,
  onSelectCase,
  selectedAssetId,
  onSelectAsset,
  refreshKey,
}: Props) {
  const [assets, setAssets] = useState<AssetItem[]>([])
  const [events, setEvents] = useState<CustodyEvent[]>([])
  const [verify, setVerify] = useState<VerifyResponse | null>(null)
  const [forensics, setForensics] = useState<ForensicsResponse | null>(null)
  const [logText, setLogText] = useState('')
  const [notifyN8n, setNotifyN8n] = useState(true)
  const [audit, setAudit] = useState<AuditResponse | null>(null)
  const [auditing, setAuditing] = useState(false)
  const [custodianName, setCustodianName] = useState('')
  const [expertName, setExpertName] = useState('')
  const [partAText, setPartAText] = useState('')
  const [partBText, setPartBText] = useState('')
  const [signedCert, setSignedCert] = useState<{ cert_id: string; pdf_sha256: string; signed_at_utc: string } | null>(null)
  const [signing, setSigning] = useState(false)
  const [loading, setLoading] = useState(false)
  const [copiedHash, setCopiedHash] = useState(false)

  useEffect(() => {
    if (!selectedCaseId) {
      setAssets([])
      return
    }
    void api.listAssets(selectedCaseId).then((list) => {
      setAssets(list)
      if (list.length > 0 && !list.some((a) => a.asset_id === selectedAssetId)) {
        onSelectAsset(list[0].asset_id)
      }
    })
  }, [selectedCaseId, refreshKey, selectedAssetId, onSelectAsset])

  useEffect(() => {
    setAudit(null)
    setPartAText('')
    setPartBText('')
    setSignedCert(null)
    if (!selectedAssetId) {
      setEvents([])
      setVerify(null)
      setForensics(null)
      return
    }
    setLoading(true)
    void Promise.all([
      api.listEvents(selectedAssetId),
      api.verifyAsset(selectedAssetId),
      api.getForensics(selectedAssetId),
    ])
      .then(([ev, ver, fx]) => {
        setEvents(ev)
        setVerify(ver)
        setForensics(fx)
      })
      .finally(() => setLoading(false))
  }, [selectedAssetId, refreshKey])

  const activeAsset = assets.find((a) => a.asset_id === selectedAssetId)

  return (
    <div className="mx-auto grid max-w-6xl grid-cols-1 gap-6 p-6 lg:grid-cols-12">
      {/* Left Dossier Sidebar */}
      <aside className="space-y-4 lg:col-span-4">
        <div className="rounded-2xl border border-[#ded8cc] bg-white p-4 shadow-2xs">
          <div className="flex items-center justify-between">
            <h2 className="text-[11px] font-semibold uppercase tracking-wider text-[#6b665c]">
              1. Case Dossiers
            </h2>
            <span className="font-mono text-[10px] text-[#a8a29e]">{cases.length} total</span>
          </div>
          <div className="mt-3 space-y-2">
            {cases.length === 0 && (
              <p className="rounded-lg border border-dashed border-[#d6cfc2] bg-[#faf8f4] p-3 text-xs text-[#6b665c]">
                No cases yet. Switch to <span className="font-semibold">Field Mobile</span> to create a case &amp; seal evidence.
              </p>
            )}
            {cases.map((c) => (
              <button
                key={c.case_id}
                type="button"
                onClick={() => onSelectCase(c.case_id)}
                className={`w-full rounded-xl border px-3.5 py-2.5 text-left text-xs transition ${
                  c.case_id === selectedCaseId
                    ? 'border-[#0f5132]/40 bg-[#0f5132]/5 text-[#141413] shadow-2xs'
                    : 'border-[#e5dfd3] bg-[#faf8f4] text-[#44403c] hover:border-[#c7bfb0]'
                }`}
              >
                <div className="font-semibold">{c.title}</div>
                <div className="mt-0.5 font-mono text-[10px] text-[#78716c]">{c.case_id}</div>
              </button>
            ))}
          </div>
        </div>

        <div className="rounded-2xl border border-[#ded8cc] bg-white p-4 shadow-2xs">
          <div className="flex items-center justify-between">
            <h2 className="text-[11px] font-semibold uppercase tracking-wider text-[#6b665c]">
              2. Sealed Evidence
            </h2>
            <span className="font-mono text-[10px] text-[#a8a29e]">{assets.length} files</span>
          </div>
          <div className="mt-3 space-y-2">
            {assets.length === 0 && (
              <p className="text-xs text-[#78716c]">No evidence assets ingested for this case.</p>
            )}
            {assets.map((a) => (
              <button
                key={a.asset_id}
                type="button"
                onClick={() => onSelectAsset(a.asset_id)}
                className={`w-full rounded-xl border px-3.5 py-2.5 text-left text-xs transition ${
                  a.asset_id === selectedAssetId
                    ? 'border-[#1e3a8a]/40 bg-[#1e3a8a]/5 text-[#141413] shadow-2xs'
                    : 'border-[#e5dfd3] bg-[#faf8f4] text-[#44403c] hover:border-[#c7bfb0]'
                }`}
              >
                <div className="font-semibold">{a.filename}</div>
                <div className="mt-0.5 truncate font-mono text-[10px] text-[#78716c]">
                  SHA-256: {a.sha256}
                </div>
              </button>
            ))}
          </div>
        </div>
      </aside>

      {/* Main Forensic Dossier Workspace */}
      <main className="space-y-5 lg:col-span-8">
        {!activeAsset ? (
          <div className="rounded-2xl border border-dashed border-[#c7bfb0] bg-white/70 p-12 text-center">
            <Scale className="mx-auto h-8 w-8 text-[#a8a29e]" />
            <h3 className="mt-3 font-serif-display text-2xl text-[#141413]">
              Select an Evidence Asset
            </h3>
            <p className="mt-1 text-xs text-[#6b665c]">
              Inspect its Ed25519 custody chain, run the AI audit agent, and prepare the BSA Section 63(4) certificate.
            </p>
          </div>
        ) : (
          <>
            {/* Verification Dossier Header */}
            <div
              className={`flex flex-wrap items-center justify-between gap-4 rounded-2xl border bg-white p-5 shadow-xs ${
                verify?.valid ? 'border-[#0f5132]/30' : 'border-red-600/40'
              }`}
            >
              <div className="flex items-start gap-3.5">
                <div
                  className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${
                    verify?.valid ? 'bg-[#0f5132]/10 text-[#0f5132]' : 'bg-red-100 text-red-700'
                  }`}
                >
                  {verify?.valid ? (
                    <ShieldCheck className="h-5 w-5" />
                  ) : (
                    <ShieldAlert className="h-5 w-5" />
                  )}
                </div>
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="font-serif-display text-2xl leading-none text-[#141413]">
                      {activeAsset.filename}
                    </h3>
                    <span
                      className={`rounded-full border px-2.5 py-0.5 font-mono text-[10px] font-semibold ${
                        verify?.valid
                          ? 'border-[#0f5132]/25 bg-[#0f5132]/10 text-[#0f5132]'
                          : 'border-red-600/25 bg-red-100 text-red-700'
                      }`}
                    >
                      {loading ? 'VERIFYING...' : verify?.valid ? 'CHAIN VALID' : 'TAMPER DETECTED'}
                    </span>
                  </div>
                  <div className="mt-2 flex items-center gap-2 font-mono text-[11px] text-[#44403c]">
                    <span className="truncate">SHA-256: {activeAsset.sha256}</span>
                    <button
                      type="button"
                      onClick={() => {
                        void navigator.clipboard.writeText(activeAsset.sha256)
                        setCopiedHash(true)
                        setTimeout(() => setCopiedHash(false), 1500)
                      }}
                      className="rounded border border-[#d6cfc2] bg-[#faf8f4] px-1.5 py-0.5 text-[10px] text-[#57534e] hover:text-[#141413]"
                      title="Copy SHA-256"
                    >
                      {copiedHash ? <Check className="h-3 w-3 text-[#0f5132]" /> : <Copy className="h-3 w-3" />}
                    </button>
                  </div>
                  <p className="font-mono text-[11px] text-[#78716c]">
                    BLAKE3: {activeAsset.blake3}
                  </p>
                </div>
              </div>

              <a
                href={api.bundleUrl(activeAsset.asset_id)}
                className="flex items-center gap-2 rounded-lg bg-[#141413] px-4 py-2.5 text-xs font-semibold text-white shadow-xs transition hover:bg-[#292524]"
              >
                <Download className="h-3.5 w-3.5" />
                Export Offline .zip Bundle
              </a>
            </div>

            {/* Vertical Hash-Chained Custody Timeline */}
            <section className="rounded-2xl border border-[#ded8cc] bg-white p-5 shadow-2xs">
              <h3 className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wider text-[#6b665c]">
                <Link2 className="h-4 w-4 text-[#1e3a8a]" />
                Append-Only Ed25519 Custody Ledger ({events.length} events)
              </h3>
              <div className="relative mt-4 space-y-3 pl-5 before:absolute before:bottom-3 before:left-2 before:top-3 before:w-px before:bg-[#ded8cc]">
                {events.map((ev) => (
                  <div
                    key={ev.event_id}
                    className="relative rounded-xl border border-[#e5dfd3] bg-[#faf8f4] p-3.5 text-xs"
                  >
                    <span className="absolute -left-[17px] top-4 h-2.5 w-2.5 rounded-full border-2 border-white bg-[#0f5132]" />
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="font-semibold text-[#141413]">
                        #{ev.seq} · {ev.event_type}: {ev.actor_from} → {ev.actor_to}
                      </span>
                      <span className="flex items-center gap-1 font-mono text-[11px] text-[#0f5132]">
                        <CheckCircle2 className="h-3 w-3" /> {ev.occurred_at_utc}
                      </span>
                    </div>
                    <p className="mt-1 text-[#57534e]">
                      {ev.purpose} · <span className="text-[#78716c]">{ev.location}</span>
                    </p>
                    <div className="mt-2 grid grid-cols-1 gap-0.5 font-mono text-[10px] text-[#78716c]">
                      <div className="truncate">event_hash: {ev.event_hash}</div>
                      <div className="truncate">prev_hash:  {ev.prev_hash}</div>
                    </div>
                  </div>
                ))}
              </div>
            </section>

            {/* TRACE Advisory Forensics */}
            {forensics && (
              <section className="rounded-2xl border border-[#ded8cc] bg-white p-5 shadow-2xs">
                <div className="flex items-center justify-between">
                  <h3 className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wider text-[#6b665c]">
                    <FileSearch className="h-4 w-4 text-[#b45309]" />
                    TRACE Media Metadata &amp; Advisory Flags
                  </h3>
                  <span className="rounded-md border border-[#d6cfc2] bg-[#faf8f4] px-2 py-0.5 font-mono text-[10px] text-[#57534e]">
                    advisory_only: true
                  </span>
                </div>

                <div className="mt-3 grid grid-cols-2 gap-3 text-xs sm:grid-cols-4">
                  <div className="rounded-xl border border-[#e5dfd3] bg-[#faf8f4] p-3">
                    <div className="text-[10px] text-[#78716c]">Format</div>
                    <div className="mt-0.5 font-mono font-semibold text-[#141413]">
                      {forensics.detected_format}
                    </div>
                  </div>
                  <div className="rounded-xl border border-[#e5dfd3] bg-[#faf8f4] p-3">
                    <div className="text-[10px] text-[#78716c]">Dimensions</div>
                    <div className="mt-0.5 font-mono font-semibold text-[#141413]">
                      {forensics.width ? `${forensics.width}×${forensics.height}` : 'N/A'}
                    </div>
                  </div>
                  <div className="rounded-xl border border-[#e5dfd3] bg-[#faf8f4] p-3">
                    <div className="text-[10px] text-[#78716c]">ELA Mean Diff</div>
                    <div className="mt-0.5 font-mono font-semibold text-[#141413]">
                      {forensics.ela_mean_diff ?? 'N/A'}
                    </div>
                  </div>
                  <div className="rounded-xl border border-[#e5dfd3] bg-[#faf8f4] p-3">
                    <div className="text-[10px] text-[#78716c]">EXIF Tags</div>
                    <div className="mt-0.5 font-mono font-semibold text-[#141413]">
                      {Object.keys(forensics.exif).length}
                    </div>
                  </div>
                </div>

                {forensics.flags.length > 0 && (
                  <div className="mt-3 space-y-2">
                    {forensics.flags.map((flag) => (
                      <div
                        key={flag.code}
                        className="flex items-start gap-2 rounded-xl border border-[#b45309]/25 bg-[#fef3c7]/60 p-3 text-xs text-[#78350f]"
                      >
                        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-[#b45309]" />
                        <div>
                          <span className="font-mono font-semibold">{flag.code}:</span>{' '}
                          {flag.message}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </section>
            )}

            {/* AI Forensic Audit Agent */}
            <section className="space-y-3 rounded-2xl border border-[#ded8cc] bg-white p-5 shadow-2xs">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h3 className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wider text-[#6b665c]">
                  <Bot className="h-4 w-4 text-[#0f5132]" />
                  AI Forensic Audit Agent &amp; Grounded Draft
                </h3>
                <label className="flex items-center gap-1.5 text-xs text-[#57534e]">
                  <input
                    type="checkbox"
                    checked={notifyN8n}
                    onChange={(e) => setNotifyN8n(e.target.checked)}
                    className="rounded border-[#c7bfb0]"
                  />
                  Notify Expert via n8n
                </label>
              </div>

              <div className="flex flex-wrap items-center gap-1.5 text-[11px]">
                <span className="text-[#6b665c]">Load sample log:</span>
                {Object.entries(SAMPLE_LOGS).map(([key, val]) => (
                  <button
                    key={key}
                    type="button"
                    onClick={() => setLogText(val)}
                    className="rounded-md border border-[#d6cfc2] bg-[#faf8f4] px-2.5 py-0.5 font-mono text-[10px] font-medium text-[#292524] transition hover:border-[#0f5132] hover:text-[#0f5132]"
                  >
                    {key}
                  </button>
                ))}
              </div>

              <textarea
                value={logText}
                onChange={(e) => setLogText(e.target.value)}
                rows={4}
                placeholder="Optional: Paste acquisition log (dd, ewfacquire, Autopsy, ExifTool JSON, or officer seizure notes)..."
                className="w-full rounded-xl border border-[#d6cfc2] bg-[#faf8f4] p-3 font-mono text-xs text-[#141413] placeholder:text-[#a8a29e]"
              />

              <button
                type="button"
                disabled={auditing}
                onClick={() => {
                  setAuditing(true)
                  void api
                    .runAudit(activeAsset.asset_id, logText, notifyN8n)
                    .then((res) => {
                      setAudit(res)
                      setPartAText(res.part_a_draft)
                      setPartBText(res.part_b_draft)
                    })
                    .finally(() => setAuditing(false))
                }}
                className="flex items-center gap-2 rounded-lg bg-[#0f5132] px-4 py-2.5 text-xs font-semibold text-white shadow-xs transition hover:bg-[#0c4128] disabled:opacity-40"
              >
                <Bot className="h-3.5 w-3.5" />
                {auditing ? 'Auditing & Drafting...' : 'Run AI Audit & Draft Section 63(4)'}
              </button>

              {audit && (
                <div className="space-y-3 border-t border-[#e5dfd3] pt-3 text-xs">
                  <div className="flex flex-wrap items-center gap-2 text-[11px]">
                    <span className="rounded-md border border-[#d6cfc2] bg-[#faf8f4] px-2 py-0.5 font-mono text-[#292524]">
                      drafter: {audit.drafter_mode}
                    </span>
                    {audit.parsed_log && (
                      <span className="rounded-md border border-[#d6cfc2] bg-[#faf8f4] px-2 py-0.5 font-mono text-[#292524]">
                        log_format: {audit.parsed_log.format_detected}
                      </span>
                    )}
                    {audit.n8n_notification && (
                      <span className="rounded-md border border-[#0f5132]/25 bg-[#0f5132]/10 px-2 py-0.5 font-medium text-[#0f5132]">
                        n8n: {audit.n8n_notification.delivered ? 'Telegram Sent' : 'Skipped'}
                      </span>
                    )}
                  </div>

                  {audit.flags.length > 0 && (
                    <div className="space-y-1.5">
                      {audit.flags.map((fl, idx) => (
                        <div
                          key={`${fl.code}-${idx}`}
                          className="rounded-xl border border-[#b45309]/25 bg-[#fef3c7]/60 p-2.5 text-[#78350f]"
                        >
                          <span className="font-mono font-semibold">{fl.code}</span>{' '}
                          <span className="font-mono text-[10px] text-[#92400e]">{fl.citation}</span>
                          <div className="mt-0.5">{fl.message}</div>
                        </div>
                      ))}
                    </div>
                  )}

                  <p className="text-[11px] italic text-[#78716c]">{audit.disclaimer}</p>
                </div>
              )}
            </section>

            {/* Statutory Section 63(4) Instrument & Human Sign-Off */}
            <section className="space-y-4 rounded-2xl border border-[#ded8cc] bg-white p-5 shadow-2xs">
              <div className="flex items-center justify-between border-b border-[#e5dfd3] pb-3">
                <div>
                  <h3 className="font-serif-display text-xl text-[#141413]">
                    Statutory Certificate — BSA Section 63(4)
                  </h3>
                  <p className="text-[11px] text-[#6b665c]">
                    Review grounded drafts, edit if required, and apply human expert sign-off.
                  </p>
                </div>
                <span className="rounded-md border border-[#1e3a8a]/25 bg-[#1e3a8a]/5 px-2.5 py-1 font-mono text-[10px] font-semibold text-[#1e3a8a]">
                  HUMAN SIGN-OFF REQUIRED
                </span>
              </div>

              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <input
                  value={custodianName}
                  onChange={(e) => setCustodianName(e.target.value)}
                  placeholder="Part A Custodian Name"
                  className="rounded-lg border border-[#d6cfc2] bg-[#faf8f4] px-3 py-2 text-xs text-[#141413]"
                />
                <input
                  value={expertName}
                  onChange={(e) => setExpertName(e.target.value)}
                  placeholder="Part B Certifying Expert Name"
                  className="rounded-lg border border-[#d6cfc2] bg-[#faf8f4] px-3 py-2 text-xs text-[#141413]"
                />
              </div>

              <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                <div className="space-y-1">
                  <div className="text-[10px] font-semibold uppercase tracking-wider text-[#b45309]">
                    Part A · Custodian Declaration
                  </div>
                  <textarea
                    value={partAText}
                    onChange={(e) => setPartAText(e.target.value)}
                    rows={4}
                    placeholder="Part A Declaration text (auto-filled by AI Audit or edit manually)..."
                    className="w-full rounded-xl border border-[#d6cfc2] bg-[#faf8f4] p-3 text-xs leading-relaxed text-[#141413]"
                  />
                </div>
                <div className="space-y-1">
                  <div className="text-[10px] font-semibold uppercase tracking-wider text-[#1e3a8a]">
                    Part B · Expert Certification
                  </div>
                  <textarea
                    value={partBText}
                    onChange={(e) => setPartBText(e.target.value)}
                    rows={4}
                    placeholder="Part B Expert Certification text (auto-filled by AI Audit or edit manually)..."
                    className="w-full rounded-xl border border-[#d6cfc2] bg-[#faf8f4] p-3 text-xs leading-relaxed text-[#141413]"
                  />
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-3 pt-1">
                <button
                  type="button"
                  disabled={
                    signing ||
                    !custodianName.trim() ||
                    !expertName.trim() ||
                    partAText.length < 10 ||
                    partBText.length < 10
                  }
                  onClick={() => {
                    setSigning(true)
                    void api
                      .signSection63(activeAsset.asset_id, {
                        custodian_name: custodianName,
                        custodian_designation: 'Custodian / Investigating Officer',
                        expert_name: expertName,
                        expert_designation: 'Forensic / Technical Expert',
                        part_a_text: partAText,
                        part_b_text: partBText,
                        notify_n8n: notifyN8n,
                      })
                      .then((res) => {
                        setSignedCert(res)
                        void api.listEvents(activeAsset.asset_id).then(setEvents)
                      })
                      .finally(() => setSigning(false))
                  }}
                  className="flex items-center gap-2 rounded-lg bg-[#1e3a8a] px-4 py-2.5 text-xs font-semibold text-white shadow-xs transition hover:bg-[#172e6e] disabled:opacity-40"
                >
                  <ShieldCheck className="h-3.5 w-3.5" />
                  {signing ? 'Signing & Sealing PDF...' : 'Sign Part B & Seal Section 63(4) PDF'}
                </button>

                {signedCert && (
                  <a
                    href={api.certificatePdfUrl(activeAsset.asset_id)}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center gap-1.5 rounded-lg border border-[#0f5132]/30 bg-[#0f5132]/10 px-3.5 py-2.5 text-xs font-semibold text-[#0f5132] hover:bg-[#0f5132]/15"
                  >
                    <Download className="h-3.5 w-3.5" />
                    Download Section 63(4) PDF ({signedCert.cert_id})
                  </a>
                )}
              </div>
            </section>
          </>
        )}
      </main>
    </div>
  )
}
