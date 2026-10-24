select
    player_id,
    game_player_id,
    name,
    draft_year,
    position,
    conference,
    team_name,
    country,
    continent,
    height_inches,
    rating_value,
    rank,
    source_snapshot_id,
    player_content_hash,
    roster_content_hash,
    rating_content_hash
from {{ ref('mart_current_player_pool') }}
where name is not null
  and position is not null
  and conference in ('East', 'West')
  and team_name is not null
  and country is not null
  and continent is not null
  and height_inches between 60 and 96
  and rating_value >= 0
