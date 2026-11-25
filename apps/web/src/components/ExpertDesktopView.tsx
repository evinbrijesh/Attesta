import { useEffect, useState } from 'react'
import {
  AlertTriangle,
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
          </>
        )}
      </main>
    </div>
  )
}
