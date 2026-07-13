select
    asset_id,
    event_date,
    (array_agg(price_usd order by event_timestamp asc))[1] as open_price,
    max(price_usd) as high_price,
    min(price_usd) as low_price,
    (array_agg(price_usd order by event_timestamp desc))[1] as close_price,
    sum(volume_24h) as total_volume
from {{ ref('fact_price_tick') }}
group by asset_id, event_date
