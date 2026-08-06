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

export default function BriefingPanel() {
  const [briefing, setBriefing] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // On mount: only READ the last saved briefing, never generate a new one.
  // Generation is strictly gated behind the button click below.
  useEffect(() => {
    api.getLatestBriefing()
      .then(setBriefing)
      .catch(() => setBriefing(null)) // 404 == no briefing yet, not an error state
  }, [])

  const handleGenerate = async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await api.generateBriefing()
      setBriefing(result)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <div className="section-label">AI MARKET BRIEFING</div>
      <div style={{ display: 'flex', gap: '1rem', alignItems: 'flex-start' }}>
        <div style={{ flex: 1 }}>
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
        </div>
        <button className="btn" onClick={handleGenerate} disabled={loading}>
          {loading ? 'Generating…' : 'Generate'}
        </button>
      </div>
    </>
  )
}
