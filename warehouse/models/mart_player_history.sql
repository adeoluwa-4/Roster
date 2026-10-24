select
    player.player_id,
    player.game_player_id,
    history.valid_from as changed_at,
    'player_metadata' as change_type,
    history.name as value_label,
    history.content_hash,
    history.valid_to,
    history.is_current,
    history.source_snapshot_id
from {{ source('core', 'player_history') }} as history
join {{ ref('dim_player') }} as player using (player_id)

union all

select
    player.player_id,
    player.game_player_id,
    history.valid_from as changed_at,
    'roster_membership' as change_type,
    history.team_name || ' (' || history.season_label || ')' as value_label,
    history.content_hash,
    history.valid_to,
    history.is_current,
    history.source_snapshot_id
from {{ source('core', 'roster_history') }} as history
join {{ ref('dim_player') }} as player using (player_id)

union all

select
    player.player_id,
    player.game_player_id,
    history.valid_from as changed_at,
    'rating' as change_type,
    history.rating_system || ': ' || cast(history.rating_value as varchar) as value_label,
    history.content_hash,
    history.valid_to,
    history.is_current,
    history.source_snapshot_id
from {{ source('core', 'rating_history') }} as history
join {{ ref('dim_player') }} as player using (player_id)
