export default function AssetSelector({ allAssets, selected, onToggle }) {
  return (
    <div className="asset-selector">
      {allAssets.map((asset) => (
        <button
          key={asset}
          className={`asset-chip ${selected.includes(asset) ? 'active' : ''}`}
          onClick={() => onToggle(asset)}
        >
          {asset}
        </button>
      ))}
    </div>
  )
}
