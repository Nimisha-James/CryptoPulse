select distinct
    asset as asset_id,
    asset as asset_name
from {{ ref('stg_price_ticks') }}
