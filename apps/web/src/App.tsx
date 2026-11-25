import { useCallback, useEffect, useState } from 'react'
import { Monitor, Shield, Smartphone } from 'lucide-react'
import { api, type CaseItem } from './api'
import { MobileFieldView } from './components/MobileFieldView'
import { ExpertDesktopView } from './components/ExpertDesktopView'

type ViewMode = 'mobile' | 'desktop'

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

  const loadCases = useCallback(() => {
    void api.listCases().then((list) => {
      setCases(list)
      if (list.length > 0 && !selectedCaseId) {
        setSelectedCaseId(list[0].case_id)
      }
    })
  }, [selectedCaseId])

  useEffect(() => {
    loadCases()
  }, [loadCases])

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      {/* Top Bar with Auto-Detected + 1-Click Role/View Switcher */}
      <header className="sticky top-0 z-20 border-b border-zinc-800 bg-zinc-950/90 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-500/15 text-emerald-400">
              <Shield className="h-4 w-4" />
            </div>
            <div>
              <div className="text-sm font-bold tracking-tight text-white">Attesta</div>
              <div className="text-[10px] text-zinc-400">
                BSA Section 63(4) · Attested. Verified. Sealed.
              </div>
            </div>
          </div>

          <div className="flex items-center rounded-lg border border-zinc-800 bg-zinc-900 p-1">
            <button
              type="button"
              onClick={() => setMode('mobile')}
              className={`flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium transition ${
                mode === 'mobile'
                  ? 'bg-emerald-600 text-white'
                  : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              <Smartphone className="h-3.5 w-3.5" />
              Field Mobile
            </button>
            <button
              type="button"
              onClick={() => setMode('desktop')}
              className={`flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium transition ${
                mode === 'desktop'
                  ? 'bg-sky-600 text-white'
                  : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              <Monitor className="h-3.5 w-3.5" />
              Expert Desktop
            </button>
          </div>
        </div>
      </header>

      {mode === 'mobile' ? (
        <div className="mx-auto my-4 max-w-[420px] rounded-2xl border border-zinc-800 bg-zinc-950 shadow-2xl">
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
      ) : (
        <ExpertDesktopView
          cases={cases}
          selectedCaseId={selectedCaseId}
          onSelectCase={setSelectedCaseId}
          selectedAssetId={selectedAssetId}
          onSelectAsset={setSelectedAssetId}
          refreshKey={refreshKey}
        />
      )}
    </div>
  )
}
