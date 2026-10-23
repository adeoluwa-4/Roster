select distinct
    md5(lower(position)) as position_id,
    position as position_name,
    string_split(position, ' / ') as position_components
from {{ source('core', 'player_history') }}
