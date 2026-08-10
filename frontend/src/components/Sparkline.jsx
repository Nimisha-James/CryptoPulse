import { useEffect, useState } from 'react'
import { AreaChart, Area, ResponsiveContainer, YAxis } from 'recharts'
import { api } from '../api'

export default function Sparkline({ asset, refreshKey }) {
  const [series, setSeries] = useState([])

  useEffect(() => {
    let cancelled = false
    api.getSeries(asset).then((data) => {
      if (!cancelled) setSeries(data)
    }).catch(() => { })
    return () => { cancelled = true }
  }, [asset, refreshKey])

  if (series.length === 0) {
    return <div className="sparkline-card muted-text" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>—</div>
  }

  // Tight y-axis domain around the actual data range, not padded to zero —
  // this is the same fix the Streamlit version needed: fill-to-zero on a
  // sparkline swallows small real price swings against a large price base.
  const prices = series.map((d) => d.avg_price)
  const min = Math.min(...prices)
  const max = Math.max(...prices)
  const pad = (max - min) * 0.1 || max * 0.001

  return (
    <div className="sparkline-card">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={series}>
          <defs>
            <linearGradient id={`spark-${asset}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#3f5cf5" stopOpacity={0.28} />
              <stop offset="100%" stopColor="#3f5cf5" stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <YAxis domain={[min - pad, max + pad]} hide />
          <Area
            type="monotone"
            dataKey="avg_price"
            stroke="#3f5cf5"
            strokeWidth={2}
            fill={`url(#spark-${asset})`}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
