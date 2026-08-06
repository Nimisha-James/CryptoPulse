export default function AssetCard({ metric }) {
  const vol = metric.volatility
  const isCalm = vol === null || vol === undefined || vol === 0
  const state = isCalm ? 'calm' : 'moving'
  const volDisplay = vol === null || vol === undefined ? '—' : vol.toFixed(5)

  return (
    <div className="asset-card">
      <div className="asset-name">
        <span className={`vol-dot ${state}`}></span>
        {metric.asset}
      </div>
      <div className="asset-price">
        ${metric.avg_price.toLocaleString(undefined, { minimumFractionDigits: 4, maximumFractionDigits: 4 })}
      </div>
      <div className="asset-vol">
        VOLATILITY <b className={state}>{volDisplay}</b>
      </div>
    </div>
  )
}
