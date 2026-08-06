import { useEffect, useState } from 'react'

// Client-side ticking clock in IST — updates every second on its own via
// setInterval, no server round-trip needed just to display the time.
function useISTClock() {
  const [time, setTime] = useState('')
  useEffect(() => {
    const format = () =>
      new Date().toLocaleTimeString('en-IN', {
        timeZone: 'Asia/Kolkata',
        hour12: false,
      })
    setTime(format())
    const id = setInterval(() => setTime(format()), 1000)
    return () => clearInterval(id)
  }, [])
  return time
}

export default function Header({ onRefresh, refreshing }) {
  const time = useISTClock()
  return (
    <div className="header-row">
      <h1 className="title">◈ CRYPTO<span>MARKET</span>INTEL</h1>
      <div className="header-controls">
        <div className="live-pill">
          <span className="pulse-dot"></span>
          LIVE · {time} IST
        </div>
        <button className="btn" onClick={onRefresh} disabled={refreshing}>
          ⟳ Refresh
        </button>
      </div>
    </div>
  )
}
