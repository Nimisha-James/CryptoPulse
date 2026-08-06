import { useEffect, useState, useCallback } from 'react'
import Header from './components/Header'
import AssetSelector from './components/AssetSelector'
import AssetCard from './components/AssetCard'
import Sparkline from './components/Sparkline'
import OHLCTable from './components/OHLCTable'
import BriefingPanel from './components/BriefingPanel'
import { api } from './api'

const POLL_INTERVAL_MS = 5000

export default function App() {
  const [allAssets, setAllAssets] = useState([])
  const [selected, setSelected] = useState([])
  const [liveMetrics, setLiveMetrics] = useState([])
  const [dailySummary, setDailySummary] = useState([])
  const [tick, setTick] = useState(0)          // bumps to force a manual refresh
  const [error, setError] = useState(null)

  const fetchAll = useCallback(async () => {
    try {
      const [metrics, daily] = await Promise.all([
        api.getLiveMetrics(),
        api.getDailySummary(),
      ])
      setLiveMetrics(metrics)
      setDailySummary(daily)
      setError(null)
    } catch (e) {
      setError(e.message)
    }
  }, [])

  // Load the asset list once on mount.
  useEffect(() => {
    api.getAssets()
      .then((assets) => {
        setAllAssets(assets)
        setSelected(assets.slice(0, 5)) // default to first 5, same as the Streamlit version
      })
      .catch((e) => setError(e.message))
  }, [])

  // Poll live data every 5 seconds — this is the REST-polling equivalent
  // of streamlit-autorefresh, chosen deliberately over WebSockets for
  // this project's scope.
  useEffect(() => {
    fetchAll()
    const id = setInterval(fetchAll, POLL_INTERVAL_MS)
    return () => clearInterval(id)
  }, [fetchAll, tick])

  const handleManualRefresh = () => {
    setTick((t) => t + 1)
    fetchAll()
  }

  const toggleAsset = (asset) => {
    setSelected((prev) =>
      prev.includes(asset) ? prev.filter((a) => a !== asset) : [...prev, asset]
    )
  }

  const filteredMetrics = liveMetrics.filter((m) => selected.includes(m.asset))

  return (
    <div className="container">
      <Header onRefresh={handleManualRefresh} refreshing={false} />

      {error && <div className="error-box">Could not reach the API — retrying automatically. ({error})</div>}

      <div className="section-label">ASSETS</div>
      <AssetSelector allAssets={allAssets} selected={selected} onToggle={toggleAsset} />

      <BriefingPanel />

      <div className="section-label">LIVE · 5-MIN ROLLING METRICS</div>
      <div className="cards-grid">
        {filteredMetrics.map((m) => <AssetCard key={m.asset} metric={m} />)}
      </div>

      <div className="section-label">PRICE TREND · LAST WINDOWS</div>
      <div className="cards-grid">
        {filteredMetrics.map((m) => (
          <Sparkline key={m.asset} asset={m.asset} refreshKey={tick} />
        ))}
      </div>

      <div className="section-label">HISTORICAL · DAILY OHLC (DBT)</div>
      <OHLCTable rows={dailySummary} />
    </div>
  )
}