select
    membership.membership_id,
    membership.player_id,
    team.team_id,
    season.season_id,
    membership.team_name,
    membership.conference,
    membership.season_label,
    membership.active,
    membership.valid_from,
    membership.valid_to,
    membership.is_current,
    membership.source_snapshot_id
from {{ source('core', 'roster_history') }} as membership
join {{ ref('dim_team') }} as team
  on membership.team_name = team.team_name
 and membership.conference = team.conference
join {{ ref('dim_season') }} as season
  on membership.season_label = season.season_label
