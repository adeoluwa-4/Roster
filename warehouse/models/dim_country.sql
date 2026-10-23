select distinct
    md5(lower(country)) as country_id,
    country as country_name,
    continent
from {{ source('core', 'player_history') }}
