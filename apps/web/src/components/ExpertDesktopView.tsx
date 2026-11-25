import { useEffect, useState } from 'react'
import {
  AlertTriangle,
  Bot,
  CheckCircle2,
  Download,
  FileSearch,
  Link2,
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
  const [custodianName, setCustodianName] = useState('SI Rajesh Kumar')
  const [expertName, setExpertName] = useState('Dr. Ananya Rao')
  const [partAText, setPartAText] = useState('')
  const [partBText, setPartBText] = useState('')
  const [signedCert, setSignedCert] = useState<{ cert_id: string; pdf_sha256: string; signed_at_utc: string } | null>(null)
  const [signing, setSigning] = useState(false)
  const [loading, setLoading] = useState(false)

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
      {/* Left Sidebar: Cases & Assets */}
      <aside className="space-y-4 lg:col-span-4">
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/70 p-4">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
            1. Select Case
          </h2>
          <div className="mt-2 space-y-1.5">
            {cases.length === 0 && (
              <p className="text-xs text-zinc-500">
                No cases yet. Switch to Field Mobile view to create &amp; seal evidence.
              </p>
            )}
            {cases.map((c) => (
              <button
                key={c.case_id}
                type="button"
                onClick={() => onSelectCase(c.case_id)}
                className={`w-full rounded-lg border px-3 py-2 text-left text-xs transition ${
                  c.case_id === selectedCaseId
                    ? 'border-emerald-500/60 bg-emerald-500/10 text-emerald-200'
                    : 'border-zinc-800 bg-zinc-950/60 text-zinc-300 hover:border-zinc-700'
                }`}
              >
                <div className="font-semibold">{c.title}</div>
                <div className="font-mono text-[10px] text-zinc-500">{c.case_id}</div>
              </button>
            ))}
          </div>
        </div>

        <div className="rounded-xl border border-zinc-800 bg-zinc-900/70 p-4">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
            2. Sealed Evidence Assets
          </h2>
          <div className="mt-2 space-y-1.5">
            {assets.length === 0 && (
              <p className="text-xs text-zinc-500">No evidence assets ingested for this case.</p>
            )}
            {assets.map((a) => (
              <button
                key={a.asset_id}
                type="button"
                onClick={() => onSelectAsset(a.asset_id)}
                className={`w-full rounded-lg border px-3 py-2 text-left text-xs transition ${
                  a.asset_id === selectedAssetId
                    ? 'border-sky-500/60 bg-sky-500/10 text-sky-200'
                    : 'border-zinc-800 bg-zinc-950/60 text-zinc-300 hover:border-zinc-700'
                }`}
              >
                <div className="font-semibold">{a.filename}</div>
                <div className="mt-0.5 truncate font-mono text-[10px] text-zinc-400">
                  SHA-256: {a.sha256}
                </div>
              </button>
            ))}
          </div>
        </div>
      </aside>

      {/* Main Panel: Verification, Timeline & Advisory Forensics */}
      <main className="space-y-5 lg:col-span-8">
        {!activeAsset ? (
          <div className="rounded-xl border border-dashed border-zinc-800 p-10 text-center text-sm text-zinc-500">
            Select a case and evidence asset to inspect its cryptographic chain of custody.
          </div>
        ) : (
          <>
            {/* Verification Banner */}
            <div
              className={`flex flex-wrap items-center justify-between gap-4 rounded-xl border p-4 ${
                verify?.valid
                  ? 'border-emerald-500/40 bg-emerald-950/20'
                  : 'border-red-500/40 bg-red-950/20'
              }`}
            >
              <div className="flex items-start gap-3">
                {verify?.valid ? (
                  <ShieldCheck className="mt-0.5 h-6 w-6 text-emerald-400" />
                ) : (
                  <ShieldAlert className="mt-0.5 h-6 w-6 text-red-400" />
                )}
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-semibold text-zinc-100">{activeAsset.filename}</h3>
                    <span
                      className={`rounded-full px-2 py-0.5 text-[10px] font-bold ${
                        verify?.valid
                          ? 'bg-emerald-500/20 text-emerald-300'
                          : 'bg-red-500/20 text-red-300'
                      }`}
                    >
                      {loading ? 'VERIFYING...' : verify?.valid ? 'CHAIN VALID' : 'TAMPER DETECTED'}
                    </span>
                  </div>
                  <p className="mt-1 font-mono text-[11px] text-zinc-400">
                    SHA-256: {activeAsset.sha256}
                  </p>
                  <p className="font-mono text-[11px] text-zinc-500">
                    BLAKE3: {activeAsset.blake3}
                  </p>
                </div>
              </div>

              <a
                href={api.bundleUrl(activeAsset.asset_id)}
                className="flex items-center gap-2 rounded-lg bg-zinc-100 px-3.5 py-2 text-xs font-semibold text-zinc-950 hover:bg-white"
              >
                <Download className="h-3.5 w-3.5" />
                Export Offline .zip Bundle
              </a>
            </div>

            {/* Hash-Chained Custody Timeline */}
            <section className="rounded-xl border border-zinc-800 bg-zinc-900/70 p-4">
              <h3 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-zinc-400">
                <Link2 className="h-4 w-4 text-sky-400" />
                Append-Only Ed25519 Hash-Chained Custody Log ({events.length})
              </h3>
              <div className="mt-3 space-y-3">
                {events.map((ev) => (
                  <div
                    key={ev.event_id}
                    className="rounded-lg border border-zinc-800 bg-zinc-950/80 p-3 text-xs"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="font-semibold text-zinc-100">
                        #{ev.seq} · {ev.event_type}: {ev.actor_from} → {ev.actor_to}
                      </span>
                      <span className="flex items-center gap-1 font-mono text-[11px] text-emerald-400">
                        <CheckCircle2 className="h-3 w-3" /> {ev.occurred_at_utc}
                      </span>
                    </div>
                    <p className="mt-1 text-zinc-400">
                      {ev.purpose} · <span className="text-zinc-500">{ev.location}</span>
                    </p>
                    <div className="mt-2 grid grid-cols-1 gap-1 font-mono text-[10px] text-zinc-500">
                      <div className="truncate">event_hash: {ev.event_hash}</div>
                      <div className="truncate">prev_hash:  {ev.prev_hash}</div>
                    </div>
                  </div>
                ))}
              </div>
            </section>

            {/* TRACE Advisory Forensics */}
            {forensics && (
              <section className="rounded-xl border border-zinc-800 bg-zinc-900/70 p-4">
                <div className="flex items-center justify-between">
                  <h3 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-zinc-400">
                    <FileSearch className="h-4 w-4 text-amber-400" />
                    TRACE Media Metadata &amp; Advisory Flags
                  </h3>
                  <span className="rounded bg-zinc-800 px-2 py-0.5 text-[10px] text-zinc-300">
                    advisory_only: true
                  </span>
                </div>

                <div className="mt-3 grid grid-cols-2 gap-3 text-xs sm:grid-cols-4">
                  <div className="rounded-lg bg-zinc-950 p-2.5">
                    <div className="text-[10px] text-zinc-500">Format</div>
                    <div className="font-mono font-semibold text-zinc-200">
                      {forensics.detected_format}
                    </div>
                  </div>
                  <div className="rounded-lg bg-zinc-950 p-2.5">
                    <div className="text-[10px] text-zinc-500">Dimensions</div>
                    <div className="font-mono font-semibold text-zinc-200">
                      {forensics.width ? `${forensics.width}×${forensics.height}` : 'N/A'}
                    </div>
                  </div>
                  <div className="rounded-lg bg-zinc-950 p-2.5">
                    <div className="text-[10px] text-zinc-500">ELA Mean Diff</div>
                    <div className="font-mono font-semibold text-zinc-200">
                      {forensics.ela_mean_diff ?? 'N/A'}
                    </div>
                  </div>
                  <div className="rounded-lg bg-zinc-950 p-2.5">
                    <div className="text-[10px] text-zinc-500">EXIF Tags</div>
                    <div className="font-mono font-semibold text-zinc-200">
                      {Object.keys(forensics.exif).length}
                    </div>
                  </div>
                </div>

                {forensics.flags.length > 0 && (
                  <div className="mt-3 space-y-2">
                    {forensics.flags.map((flag) => (
                      <div
                        key={flag.code}
                        className="flex items-start gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 p-2.5 text-xs text-amber-200"
                      >
                        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-400" />
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

            {/* AI Forensic Audit Agent & Section 63(4) Grounded Draft */}
            <section className="space-y-3 rounded-xl border border-zinc-800 bg-zinc-900/70 p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h3 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-zinc-400">
                  <Bot className="h-4 w-4 text-emerald-400" />
                  AI Forensic Audit Agent &amp; Section 63(4) Draft
                </h3>
                <label className="flex items-center gap-1.5 text-xs text-zinc-400">
                  <input
                    type="checkbox"
                    checked={notifyN8n}
                    onChange={(e) => setNotifyN8n(e.target.checked)}
                    className="rounded border-zinc-700 bg-zinc-950"
                  />
                  Notify Expert via n8n
                </label>
              </div>

              <textarea
                value={logText}
                onChange={(e) => setLogText(e.target.value)}
                rows={4}
                placeholder="Optional: Paste acquisition log (dd, ewfacquire, Autopsy, ExifTool JSON, or officer seizure notes)..."
                className="w-full rounded-lg border border-zinc-700 bg-zinc-950 p-3 font-mono text-xs text-zinc-200"
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
                className="flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-xs font-semibold text-white hover:bg-emerald-500 disabled:opacity-40"
              >
                <Bot className="h-3.5 w-3.5" />
                {auditing ? 'Auditing & Drafting...' : 'Run AI Audit & Draft Section 63(4)'}
              </button>

              {audit && (
                <div className="space-y-3 border-t border-zinc-800 pt-3 text-xs">
                  <div className="flex flex-wrap items-center gap-2 text-[11px] text-zinc-400">
                    <span className="rounded bg-zinc-800 px-2 py-0.5 font-mono text-zinc-200">
                      drafter: {audit.drafter_mode}
                    </span>
                    {audit.parsed_log && (
                      <span className="rounded bg-zinc-800 px-2 py-0.5 font-mono text-zinc-200">
                        log_format: {audit.parsed_log.format_detected}
                      </span>
                    )}
                    {audit.n8n_notification && (
                      <span className="rounded bg-emerald-500/20 px-2 py-0.5 text-emerald-300">
                        n8n: {audit.n8n_notification.delivered ? 'Telegram Sent' : 'Skipped'}
                      </span>
                    )}
                  </div>

                  {audit.flags.length > 0 && (
                    <div className="space-y-1.5">
                      {audit.flags.map((fl, idx) => (
                        <div
                          key={`${fl.code}-${idx}`}
                          className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-2 text-amber-200"
                        >
                          <span className="font-mono font-semibold">{fl.code}</span>{' '}
                          <span className="font-mono text-[10px] text-amber-300">{fl.citation}</span>
                          <div>{fl.message}</div>
                        </div>
                      ))}
                    </div>
                  )}

                  <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                    <div className="rounded-lg border border-zinc-800 bg-zinc-950 p-3">
                      <div className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-zinc-400">
                        Part A Draft (Custodian)
                      </div>
                      <p className="leading-relaxed text-zinc-200">{audit.part_a_draft}</p>
                    </div>
                    <div className="rounded-lg border border-zinc-800 bg-zinc-950 p-3">
                      <div className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-zinc-400">
                        Part B Draft (Expert)
                      </div>
                      <p className="leading-relaxed text-zinc-200">{audit.part_b_draft}</p>
                    </div>
                  </div>
                  <p className="text-[11px] italic text-zinc-500">{audit.disclaimer}</p>
                </div>
              )}
            </section>

            {/* Human Expert Sign-Off & BSA Section 63(4) PDF */}
            <section className="space-y-3 rounded-xl border border-zinc-800 bg-zinc-900/70 p-4">
              <h3 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-zinc-400">
                <ShieldCheck className="h-4 w-4 text-sky-400" />
                Human Expert Sign-Off &amp; BSA Section 63(4) PDF
              </h3>

              <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                <input
                  value={custodianName}
                  onChange={(e) => setCustodianName(e.target.value)}
                  placeholder="Part A Custodian Name"
                  className="rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-xs text-zinc-100"
                />
                <input
                  value={expertName}
                  onChange={(e) => setExpertName(e.target.value)}
                  placeholder="Part B Certifying Expert Name"
                  className="rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-xs text-zinc-100"
                />
              </div>

              <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                <textarea
                  value={partAText}
                  onChange={(e) => setPartAText(e.target.value)}
                  rows={3}
                  placeholder="Part A Declaration text (auto-filled by AI Audit or edit manually)..."
                  className="rounded-lg border border-zinc-700 bg-zinc-950 p-2.5 text-xs text-zinc-200"
                />
                <textarea
                  value={partBText}
                  onChange={(e) => setPartBText(e.target.value)}
                  rows={3}
                  placeholder="Part B Expert Certification text (auto-filled by AI Audit or edit manually)..."
                  className="rounded-lg border border-zinc-700 bg-zinc-950 p-2.5 text-xs text-zinc-200"
                />
              </div>

              <div className="flex flex-wrap items-center gap-3">
                <button
                  type="button"
                  disabled={signing || partAText.length < 10 || partBText.length < 10}
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
                  className="flex items-center gap-2 rounded-lg bg-sky-600 px-4 py-2 text-xs font-semibold text-white hover:bg-sky-500 disabled:opacity-40"
                >
                  <ShieldCheck className="h-3.5 w-3.5" />
                  {signing ? 'Signing & Sealing PDF...' : 'Sign Part B & Seal Section 63(4) PDF'}
                </button>

                {signedCert && (
                  <a
                    href={api.certificatePdfUrl(activeAsset.asset_id)}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center gap-1.5 rounded-lg border border-emerald-500/40 bg-emerald-500/15 px-3 py-2 text-xs font-semibold text-emerald-300 hover:bg-emerald-500/25"
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
