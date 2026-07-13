select
    asset as asset_id,
    price_usd,
    volume_24h,
    change_24h_pct,
    event_timestamp,
    date(event_timestamp) as event_date
from {{ ref('stg_price_ticks') }}
