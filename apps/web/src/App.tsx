import { useCallback, useEffect, useState } from 'react'
import { AnimatePresence, MotionConfig, motion } from 'motion/react'
import { BookOpen, ExternalLink, Monitor, RefreshCw, Shield, Smartphone, X } from 'lucide-react'
import { api, type CaseItem } from './api'
import { MobileFieldView } from './components/MobileFieldView'
import { ExpertDesktopView } from './components/ExpertDesktopView'

type ViewMode = 'mobile' | 'desktop'

interface LegalRef {
  provider: string
  statute: string
  effective_date: string
  landmark_ruling: string
  requirements: string[]
  sources: string[]
  excerpt?: string
}

function detectInitialMode(): ViewMode {
  if (typeof window !== 'undefined' && window.innerWidth < 768) {
    return 'mobile'
  }
  return 'desktop'
}

export default function App() {
  const [mode, setMode] = useState<ViewMode>(detectInitialMode)
  const [cases, setCases] = useState<CaseItem[]>([])
  const [selectedCaseId, setSelectedCaseId] = useState('')
  const [selectedAssetId, setSelectedAssetId] = useState('')
  const [refreshKey, setRefreshKey] = useState(0)
  const [apiOnline, setApiOnline] = useState<boolean | null>(null)
  const [legalOpen, setLegalOpen] = useState(false)
  const [legalRef, setLegalRef] = useState<LegalRef | null>(null)
  const [loadingLegal, setLoadingLegal] = useState(false)

  const loadCases = useCallback(() => {
    void api
      .listCases()
      .then((list) => {
        setCases(list)
        setApiOnline(true)
        if (list.length > 0 && !selectedCaseId) {
          setSelectedCaseId(list[0].case_id)
        }
      })
      .catch(() => setApiOnline(false))
  }, [selectedCaseId])

  useEffect(() => {
    loadCases()
  }, [loadCases])

  function openLegalDrawer(refresh = false) {
    setLegalOpen(true)
    setLoadingLegal(true)
    void api
      .getLegalReference(refresh)
      .then(setLegalRef)
      .finally(() => setLoadingLegal(false))
  }

  return (
    <MotionConfig reducedMotion="user">
      <div className="min-h-screen bg-zinc-950 text-zinc-100 selection:bg-emerald-500/30">
        {/* Institutional Header */}
        <header className="sticky top-0 z-30 border-b border-zinc-800/80 bg-zinc-950/85 backdrop-blur-md">
          <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-3">
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-emerald-500/30 bg-emerald-500/10 text-emerald-400 shadow-inner">
                <Shield className="h-4 w-4" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold tracking-tight text-white">Attesta</span>
                  <span className="rounded border border-zinc-800 bg-zinc-900 px-1.5 py-0.5 font-mono text-[10px] text-zinc-400">
                    BSA §63(4)
                  </span>
                  <span
                    className={`flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium ${
                      apiOnline === true
                        ? 'bg-emerald-500/10 text-emerald-300'
                        : apiOnline === false
                          ? 'bg-red-500/10 text-red-300'
                          : 'bg-zinc-800 text-zinc-400'
                    }`}
                  >
                    <span
                      className={`h-1.5 w-1.5 rounded-full ${
                        apiOnline === true
                          ? 'bg-emerald-400'
                          : apiOnline === false
                            ? 'bg-red-400'
                            : 'bg-zinc-500'
                      }`}
                    />
                    {apiOnline === true ? 'Ledger Online' : apiOnline === false ? 'API Offline' : 'Connecting'}
                  </span>
                </div>
                <div className="text-[11px] text-zinc-500">
                  Attested. Verified. Sealed. · Zero-Trust Forensic Pipeline
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => openLegalDrawer(false)}
                className="flex items-center gap-1.5 rounded-lg border border-zinc-800 bg-zinc-900/90 px-2.5 py-1.5 text-xs font-medium text-zinc-300 transition hover:border-zinc-700 hover:text-white"
              >
                <BookOpen className="h-3.5 w-3.5 text-amber-400" />
                <span className="hidden sm:inline">BSA §63(4) Legal Ref</span>
                <span className="sm:hidden">§63 Ref</span>
              </button>

              {/* Animated Role / Viewport Switcher */}
              <div className="relative flex items-center rounded-lg border border-zinc-800 bg-zinc-900 p-1">
                <button
                  type="button"
                  onClick={() => setMode('mobile')}
                  className={`relative z-10 flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
                    mode === 'mobile' ? 'text-white' : 'text-zinc-400 hover:text-zinc-200'
                  }`}
                >
                  {mode === 'mobile' && (
                    <motion.span
                      layoutId="mode-pill"
                      transition={{ type: 'spring', stiffness: 420, damping: 32 }}
                      className="absolute inset-0 -z-10 rounded-md bg-emerald-600 shadow-sm"
                    />
                  )}
                  <Smartphone className="h-3.5 w-3.5" />
                  Field Mobile
                </button>
                <button
                  type="button"
                  onClick={() => setMode('desktop')}
                  className={`relative z-10 flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
                    mode === 'desktop' ? 'text-white' : 'text-zinc-400 hover:text-zinc-200'
                  }`}
                >
                  {mode === 'desktop' && (
                    <motion.span
                      layoutId="mode-pill"
                      transition={{ type: 'spring', stiffness: 420, damping: 32 }}
                      className="absolute inset-0 -z-10 rounded-md bg-sky-600 shadow-sm"
                    />
                  )}
                  <Monitor className="h-3.5 w-3.5" />
                  Expert Desktop
                </button>
              </div>
            </div>
          </div>
        </header>

        {/* Main Workspace */}
        <AnimatePresence mode="wait">
          {mode === 'mobile' ? (
            <motion.div
              key="mobile-shell"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.18 }}
              className="mx-auto my-6 max-w-[420px] overflow-hidden rounded-3xl border border-zinc-800 bg-zinc-950 shadow-[0_24px_80px_-24px_rgba(16,185,129,0.22)]"
            >
              <div className="flex items-center justify-between border-b border-zinc-800/80 bg-zinc-900/60 px-4 py-2 text-[10px] font-mono text-zinc-400">
                <span>FIELD CUSTODIAN PWA</span>
                <span>PART A INTAKE</span>
              </div>
              <MobileFieldView
                cases={cases}
                selectedCaseId={selectedCaseId}
                onSelectCase={setSelectedCaseId}
                onCaseCreated={(c) => setCases((prev) => [c, ...prev])}
                onAssetUpdated={(assetId) => {
                  setSelectedAssetId(assetId)
                  setRefreshKey((k) => k + 1)
                }}
              />
            </motion.div>
          ) : (
            <motion.div
              key="desktop-shell"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.18 }}
            >
              <ExpertDesktopView
                cases={cases}
                selectedCaseId={selectedCaseId}
                onSelectCase={setSelectedCaseId}
                selectedAssetId={selectedAssetId}
                onSelectAsset={setSelectedAssetId}
                refreshKey={refreshKey}
              />
            </motion.div>
          )}
        </AnimatePresence>

        {/* BSA Section 63(4) Legal Reference Slide-Over Drawer (Olostep Powered) */}
        <AnimatePresence>
          {legalOpen && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-50 flex justify-end bg-black/65 backdrop-blur-xs"
              onClick={() => setLegalOpen(false)}
            >
              <motion.aside
                initial={{ x: 380 }}
                animate={{ x: 0 }}
                exit={{ x: 380 }}
                transition={{ type: 'spring', stiffness: 360, damping: 34 }}
                onClick={(e) => e.stopPropagation()}
                className="flex h-full w-full max-w-md flex-col border-l border-zinc-800 bg-zinc-950 p-5 shadow-2xl"
              >
                <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
                  <div>
                    <h2 className="text-sm font-semibold text-white">BSA Section 63(4) Reference</h2>
                    <p className="text-[11px] text-zinc-400">
                      Statutory &amp; Supreme Court guidance (Olostep-grounded)
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => setLegalOpen(false)}
                    className="rounded-lg p-1.5 text-zinc-400 hover:bg-zinc-900 hover:text-white"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>

                <div className="mt-4 flex-1 space-y-4 overflow-y-auto text-xs">
                  {loadingLegal ? (
                    <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-4 text-zinc-400">
                      Fetching legal reference...
                    </div>
                  ) : legalRef ? (
                    <>
                      <div className="flex items-center justify-between">
                        <span className="rounded-full border border-amber-500/30 bg-amber-500/10 px-2.5 py-0.5 font-mono text-[10px] text-amber-300">
                          source: {legalRef.provider}
                        </span>
                        <button
                          type="button"
                          onClick={() => openLegalDrawer(true)}
                          className="flex items-center gap-1 rounded-md border border-zinc-800 bg-zinc-900 px-2 py-1 text-[11px] text-zinc-300 hover:text-white"
                        >
                          <RefreshCw className="h-3 w-3" /> Live Olostep Refresh
                        </button>
                      </div>

                      <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-3.5">
                        <div className="font-semibold text-white">{legalRef.statute}</div>
                        <div className="mt-1 text-[11px] text-zinc-400">
                          Effective: {legalRef.effective_date}
                        </div>
                        <p className="mt-2 leading-relaxed text-zinc-300">{legalRef.landmark_ruling}</p>
                      </div>

                      <div className="space-y-2">
                        <div className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400">
                          Mandatory Requirements
                        </div>
                        {legalRef.requirements.map((reqText, i) => (
                          <div
                            key={i}
                            className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-3 text-zinc-300"
                          >
                            {reqText}
                          </div>
                        ))}
                      </div>

                      {legalRef.excerpt && (
                        <div className="space-y-1.5">
                          <div className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400">
                            Live Olostep Excerpt
                          </div>
                          <pre className="whitespace-pre-wrap rounded-lg border border-zinc-800 bg-zinc-900 p-3 font-mono text-[10px] text-zinc-400">
                            {legalRef.excerpt}
                          </pre>
                        </div>
                      )}

                      <div className="space-y-1.5">
                        <div className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400">
                          Citations
                        </div>
                        {legalRef.sources.map((src) => (
                          <a
                            key={src}
                            href={src}
                            target="_blank"
                            rel="noreferrer"
                            className="flex items-center justify-between rounded-lg border border-zinc-800 bg-zinc-900/40 px-3 py-2 text-[11px] text-sky-300 hover:border-zinc-700"
                          >
                            <span className="truncate">{src}</span>
                            <ExternalLink className="ml-2 h-3 w-3 shrink-0" />
                          </a>
                        ))}
                      </div>
                    </>
                  ) : null}
                </div>
              </motion.aside>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </MotionConfig>
  )
}
