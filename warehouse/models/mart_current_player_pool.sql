with latest_payload as (
    select
        resolution.player_id,
        record.payload,
        row_number() over (
            partition by resolution.player_id
            order by snapshot.effective_date desc, snapshot.captured_at desc
        ) as recency
    from {{ source('core', 'identity_resolution_event') }} as resolution
    join {{ source('raw', 'player_record') }} as record
      on resolution.snapshot_id = record.snapshot_id
     and resolution.row_number = record.row_number
    join {{ source('raw', 'source_snapshot') }} as snapshot
      on record.snapshot_id = snapshot.snapshot_id
    where resolution.resolution_status = 'accepted'
), current_players as (
    select * from {{ source('core', 'player_history') }} where is_current
), current_rosters as (
    select * from {{ source('core', 'roster_history') }} where is_current
), current_ratings as (
    select * from {{ source('core', 'rating_history') }} where is_current and rating_system = 'NBA 2K'
)
select
    player.player_id,
    player.game_player_id,
    player.nba_id,
    player.espn_id,
    metadata.name,
    metadata.draft_year,
    metadata.position,
    roster.conference,
    roster.team_name,
    metadata.country,
    metadata.continent,
    metadata.height_inches,
    metadata.weight_pounds,
    metadata.active,
    roster.season_label,
    cast(coalesce(rating.rank_value, row_number() over (order by rating.rating_value desc, metadata.name)) as integer) as rank,
    rating.rating_value,
    coalesce(try_cast(payload.payload ->> 'games' as integer), 0) as games,
    coalesce(try_cast(payload.payload ->> 'winShares' as double), 0) as win_shares,
    try_cast(payload.payload ->> 'currentWinShares' as double) as current_win_shares,
    metadata.source_snapshot_id,
    metadata.content_hash as player_content_hash,
    roster.content_hash as roster_content_hash,
    rating.content_hash as rating_content_hash
from current_players as metadata
join {{ ref('dim_player') }} as player using (player_id)
join current_rosters as roster using (player_id)
join current_ratings as rating using (player_id)
join latest_payload as payload
  on metadata.player_id = payload.player_id
 and payload.recency = 1
where metadata.active and roster.active
