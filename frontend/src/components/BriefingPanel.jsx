import { useEffect, useState } from 'react'
import { api } from '../api'

function renderBullets(text) {
  return text
    .split('\n\n')
    .map((line) => line.replace(/^•\s*/, '').trim())
    .filter(Boolean)
}

function formatIST(isoString) {
  return new Date(isoString).toLocaleString('en-IN', {
    timeZone: 'Asia/Kolkata',
    hour12: false,
  })
}

export default function BriefingPanel({ selectedAssets }) {
  const [briefing, setBriefing] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // On mount: only READ the last saved briefing, never generate a new one.
  useEffect(() => {
    api.getLatestBriefing()
      .then(setBriefing)
      .catch(() => setBriefing(null))
  }, [])

  const handleGenerate = async () => {
    setLoading(true)
    setError(null)
    try {
      // Scoped to whatever's currently selected on the dashboard --
      // this is what makes deselecting an asset actually change the
      // briefing's content instead of always covering everything.
      const result = await api.generateBriefing(selectedAssets)
      setBriefing(result)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const noAssetsSelected = !selectedAssets || selectedAssets.length === 0

  return (
    <>
      <div className="section-label">AI MARKET BRIEFING</div>

      {error && <div className="error-box">Agent service error: {error}</div>}

      {!error && briefing && (
        <div className="briefing-box">
          <div className="briefing-meta">
            GENERATED {formatIST(briefing.created_at)} IST · {briefing.anomaly_count} ANOMALIES DETECTED
          </div>
          <ul>
            {renderBullets(briefing.briefing).map((b, i) => <li key={i}>{b}</li>)}
          </ul>
        </div>
      )}

      {!error && !briefing && (
        <p className="muted-text">No briefing generated yet — click Generate.</p>
      )}

      {noAssetsSelected && (
        <p className="muted-text" style={{ marginTop: '0.5rem' }}>
          Select at least one asset above to generate a briefing.
        </p>
      )}

      <button
        className="btn btn-wide"
        onClick={handleGenerate}
        disabled={loading || noAssetsSelected}
      >
        {loading ? 'Generating…' : `Generate Briefing`}
      </button>
    </>
  )
}