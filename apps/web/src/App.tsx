import { useCallback, useEffect, useState } from 'react'
import { AnimatePresence, MotionConfig, motion } from 'motion/react'
import { BookOpen, ExternalLink, Monitor, RefreshCw, Scale, Smartphone, X } from 'lucide-react'
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
      <div className="min-h-screen bg-[#f6f4ef] text-[#141413] selection:bg-[#0f5132]/15">
        {/* Subtle paper grid texture */}
        <div
          className="pointer-events-none fixed inset-0 opacity-[0.35]"
          style={{
            backgroundImage: 'radial-gradient(#c8c1b4 0.75px, transparent 0.75px)',
            backgroundSize: '20px 20px',
          }}
        />

        {/* Editorial Top Bar */}
        <header className="sticky top-0 z-30 border-b border-[#ded8cc] bg-[#f6f4ef]/90 backdrop-blur-md">
          <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-3">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-[#141413]/15 bg-[#141413] text-[#f6f4ef] shadow-xs">
                <Scale className="h-4 w-4" />
              </div>
              <div>
                <div className="flex items-center gap-2.5">
                  <span className="font-serif-display text-2xl leading-none tracking-tight text-[#141413]">
                    Attesta
                  </span>
                  <span className="rounded-md border border-[#d6cfc2] bg-white px-2 py-0.5 font-mono text-[10px] font-medium text-[#57534e]">
                    BSA §63(4)
                  </span>
                  <span
                    className={`flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[10px] font-medium ${
                      apiOnline === true
                        ? 'border-[#0f5132]/25 bg-[#0f5132]/10 text-[#0f5132]'
                        : apiOnline === false
                          ? 'border-red-600/25 bg-red-600/10 text-red-700'
                          : 'border-stone-300 bg-stone-200/60 text-stone-600'
                    }`}
                  >
                    <span
                      className={`h-1.5 w-1.5 rounded-full ${
                        apiOnline === true
                          ? 'bg-[#0f5132]'
                          : apiOnline === false
                            ? 'bg-red-600'
                            : 'bg-stone-500'
                      }`}
                    />
                    {apiOnline === true ? 'Ledger Online' : apiOnline === false ? 'API Offline' : 'Connecting'}
                  </span>
                </div>
                <div className="text-[11px] text-[#6b665c]">
                  Attested. Verified. Sealed. · Cryptographic Evidence &amp; Custody Dossier
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2.5">
              <button
                type="button"
                onClick={() => openLegalDrawer(false)}
                className="flex items-center gap-1.5 rounded-lg border border-[#d6cfc2] bg-white px-3 py-1.5 text-xs font-medium text-[#292524] shadow-2xs transition hover:border-[#141413]/40"
              >
                <BookOpen className="h-3.5 w-3.5 text-[#b45309]" />
                <span className="hidden sm:inline">BSA §63(4) Statute</span>
                <span className="sm:hidden">§63 Ref</span>
              </button>

              {/* Animated Role / Viewport Switcher */}
              <div className="relative flex items-center rounded-lg border border-[#d6cfc2] bg-[#ece8df] p-1">
                <button
                  type="button"
                  onClick={() => setMode('mobile')}
                  className={`relative z-10 flex items-center gap-1.5 rounded-md px-3 py-1 text-xs font-medium transition-colors ${
                    mode === 'mobile' ? 'text-white' : 'text-[#57534e] hover:text-[#141413]'
                  }`}
                >
                  {mode === 'mobile' && (
                    <motion.span
                      layoutId="mode-pill"
                      transition={{ type: 'spring', stiffness: 420, damping: 32 }}
                      className="absolute inset-0 -z-10 rounded-md bg-[#0f5132] shadow-xs"
                    />
                  )}
                  <Smartphone className="h-3.5 w-3.5" />
                  Field Mobile
                </button>
                <button
                  type="button"
                  onClick={() => setMode('desktop')}
                  className={`relative z-10 flex items-center gap-1.5 rounded-md px-3 py-1 text-xs font-medium transition-colors ${
                    mode === 'desktop' ? 'text-white' : 'text-[#57534e] hover:text-[#141413]'
                  }`}
                >
                  {mode === 'desktop' && (
                    <motion.span
                      layoutId="mode-pill"
                      transition={{ type: 'spring', stiffness: 420, damping: 32 }}
                      className="absolute inset-0 -z-10 rounded-md bg-[#141413] shadow-xs"
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
        <div className="relative z-10">
          <AnimatePresence mode="wait">
            {mode === 'mobile' ? (
              <motion.div
                key="mobile-shell"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.18 }}
                className="mx-auto my-8 max-w-[430px] px-3"
              >
                <div className="overflow-hidden rounded-[2rem] border-[6px] border-[#1c1917] bg-[#faf8f4] shadow-[0_30px_80px_-20px_rgba(20,20,19,0.28)]">
                  <div className="flex items-center justify-between border-b border-[#e5dfd3] bg-[#1c1917] px-5 py-2.5 font-mono text-[10px] tracking-wider text-[#d6d3d1]">
                    <span>ATTESTA · FIELD PWA</span>
                    <span className="text-emerald-400">PART A INTAKE</span>
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
                </div>
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
        </div>

        {/* BSA Section 63(4) Legal Reference Slide-Over Drawer (Olostep Powered) */}
        <AnimatePresence>
          {legalOpen && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-50 flex justify-end bg-[#141413]/40 backdrop-blur-xs"
              onClick={() => setLegalOpen(false)}
            >
              <motion.aside
                initial={{ x: 400 }}
                animate={{ x: 0 }}
                exit={{ x: 400 }}
                transition={{ type: 'spring', stiffness: 360, damping: 34 }}
                onClick={(e) => e.stopPropagation()}
                className="flex h-full w-full max-w-md flex-col border-l border-[#ded8cc] bg-[#f6f4ef] p-6 shadow-2xl"
              >
                <div className="flex items-center justify-between border-b border-[#ded8cc] pb-3">
                  <div>
                    <h2 className="font-serif-display text-2xl text-[#141413]">
                      BSA Section 63(4) Statute
                    </h2>
                    <p className="text-[11px] text-[#6b665c]">
                      Mandatory hash &amp; dual-certificate guidance (Olostep-grounded)
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => setLegalOpen(false)}
                    className="rounded-lg p-1.5 text-[#6b665c] hover:bg-[#e7e2d8] hover:text-[#141413]"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>

                <div className="mt-4 flex-1 space-y-4 overflow-y-auto text-xs">
                  {loadingLegal ? (
                    <div className="rounded-xl border border-[#ded8cc] bg-white p-4 text-[#6b665c]">
                      Fetching legal reference...
                    </div>
                  ) : legalRef ? (
                    <>
                      <div className="flex items-center justify-between">
                        <span className="rounded-full border border-[#b45309]/30 bg-[#b45309]/10 px-2.5 py-0.5 font-mono text-[10px] font-medium text-[#b45309]">
                          source: {legalRef.provider}
                        </span>
                        <button
                          type="button"
                          onClick={() => openLegalDrawer(true)}
                          className="flex items-center gap-1 rounded-md border border-[#d6cfc2] bg-white px-2.5 py-1 text-[11px] font-medium text-[#292524] hover:border-[#141413]/40"
                        >
                          <RefreshCw className="h-3 w-3" /> Live Olostep Refresh
                        </button>
                      </div>

                      <div className="rounded-xl border border-[#ded8cc] bg-white p-4 shadow-2xs">
                        <div className="font-semibold text-[#141413]">{legalRef.statute}</div>
                        <div className="mt-1 text-[11px] text-[#6b665c]">
                          Effective: {legalRef.effective_date}
                        </div>
                        <p className="mt-2 leading-relaxed text-[#292524]">{legalRef.landmark_ruling}</p>
                      </div>

                      <div className="space-y-2">
                        <div className="text-[11px] font-semibold uppercase tracking-wider text-[#6b665c]">
                          Mandatory Requirements
                        </div>
                        {legalRef.requirements.map((reqText, i) => (
                          <div
                            key={i}
                            className="rounded-lg border border-[#ded8cc] bg-white p-3 leading-relaxed text-[#292524]"
                          >
                            {reqText}
                          </div>
                        ))}
                      </div>

                      {legalRef.excerpt && (
                        <div className="space-y-1.5">
                          <div className="text-[11px] font-semibold uppercase tracking-wider text-[#6b665c]">
                            Live Olostep Excerpt
                          </div>
                          <pre className="whitespace-pre-wrap rounded-lg border border-[#ded8cc] bg-white p-3 font-mono text-[10px] text-[#57534e]">
                            {legalRef.excerpt}
                          </pre>
                        </div>
                      )}

                      <div className="space-y-1.5">
                        <div className="text-[11px] font-semibold uppercase tracking-wider text-[#6b665c]">
                          Verified Citations
                        </div>
                        {legalRef.sources.map((src) => (
                          <a
                            key={src}
                            href={src}
                            target="_blank"
                            rel="noreferrer"
                            className="flex items-center justify-between rounded-lg border border-[#ded8cc] bg-white px-3 py-2 text-[11px] text-[#1e3a8a] hover:border-[#1e3a8a]/40"
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
