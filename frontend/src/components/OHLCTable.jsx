function fmt(n) {
  return `$${Number(n).toLocaleString(undefined, { minimumFractionDigits: 4, maximumFractionDigits: 4 })}`
}

export default function OHLCTable({ rows }) {
  if (rows.length === 0) {
    return <p className="muted-text">No daily summary yet — the Airflow + dbt pipeline hasn't completed a run.</p>
  }
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Asset</th>
            <th>Date</th>
            <th>Open</th>
            <th>High</th>
            <th>Low</th>
            <th>Close</th>
            <th>Volume</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={`${r.asset_id}-${r.event_date}-${i}`}>
              <td>{r.asset_id}</td>
              <td>{r.event_date}</td>
              <td>{fmt(r.open_price)}</td>
              <td>{fmt(r.high_price)}</td>
              <td>{fmt(r.low_price)}</td>
              <td>{fmt(r.close_price)}</td>
              <td>{Number(r.total_volume).toLocaleString(undefined, { maximumFractionDigits: 2 })}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
