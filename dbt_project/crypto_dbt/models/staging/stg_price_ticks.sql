with deduped as (
    select
        asset,
        price_usd,
        volume_24h,
        change_24h_pct,
        to_timestamp(event_time) as event_timestamp,
        row_number() over (
            partition by asset, event_time
            order by event_time
        ) as row_num
    from {{ source('raw', 'raw_price_ticks') }}
    where price_usd is not null
)

select
    asset,
    price_usd,
    volume_24h,
    change_24h_pct,
    event_timestamp
from deduped
where row_num = 1
