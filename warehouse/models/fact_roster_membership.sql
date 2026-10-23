select
    membership_id,
    player_id,
    md5(lower(team_name)) as team_id,
    md5(season_label) as season_id,
    team_name,
    conference,
    season_label,
    active,
    content_hash,
    valid_from,
    valid_to,
    is_current,
    source_snapshot_id
from {{ source('core', 'roster_history') }}
