with aliases as (
    select
        player_id,
        max(case when source_name = 'fixture' then source_player_id end) as game_player_id,
        max(case when source_name = 'nba_id' then try_cast(source_player_id as bigint) end) as nba_id,
        max(case when source_name = 'espn_id' then try_cast(source_player_id as bigint) end) as espn_id
    from {{ source('core', 'player_alias') }}
    group by player_id
)
select
    identity.player_id,
    coalesce(aliases.game_player_id, identity.player_id) as game_player_id,
    aliases.nba_id,
    aliases.espn_id,
    identity.canonical_name,
    identity.normalized_name,
    identity.created_at
from {{ source('core', 'player_identity') }} as identity
left join aliases using (player_id)
