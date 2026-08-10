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
      <div className="brand">
        <svg className="brand-mark" width="28" height="28" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <defs>
            <linearGradient id="brand-mark-gradient" x1="0" y1="0" x2="24" y2="24">
              <stop offset="0%" stopColor="#4f68ff" />
              <stop offset="100%" stopColor="#8b3ff2" />
            </linearGradient>
          </defs>
          <path d="M2 13h4.5l2.5-7 4 14 2.5-9L17.5 13H22" stroke="url(#brand-mark-gradient)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        <h1 className="title">Crypto<span>Pulse</span></h1>
      </div>
      <div className="header-controls">
        <div className="live-pill">
          <span className="pulse-dot"></span>
          LIVE · {time} IST
        </div>
        <button className="btn" onClick={onRefresh} disabled={refreshing}>
          <svg className="btn-icon" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="M20 11A8.1 8.1 0 0 0 4.5 9M4 5v4h4M4 13a8.1 8.1 0 0 0 15.5 2M20 19v-4h-4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          Refresh
        </button>
      </div>
    </div>
  )
}
