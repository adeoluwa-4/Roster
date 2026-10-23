select
    rating_id,
    player_id,
    rating_system,
    rating_value,
    rank_value,
    content_hash,
    valid_from,
    valid_to,
    is_current,
    source_snapshot_id,
    rating_value - lag(rating_value) over (
        partition by player_id, rating_system order by valid_from
    ) as rating_change
from {{ source('core', 'rating_history') }}
