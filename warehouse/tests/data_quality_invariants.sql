with violations as (
    select 'multiple_current_player_versions' as violation_type, player_id as entity_id
    from {{ source('core', 'player_history') }}
    where is_current
    group by player_id
    having count(*) <> 1

    union all

    select 'multiple_current_roster_versions', player_id
    from {{ source('core', 'roster_history') }}
    where is_current
    group by player_id
    having count(*) <> 1

    union all

    select 'multiple_current_rating_versions', player_id || ':' || rating_system
    from {{ source('core', 'rating_history') }}
    where is_current
    group by player_id, rating_system
    having count(*) <> 1

    union all

    select 'overlapping_player_history', left_side.player_id
    from {{ source('core', 'player_history') }} as left_side
    join {{ source('core', 'player_history') }} as right_side
      on left_side.player_id = right_side.player_id
     and left_side.version_id < right_side.version_id
     and left_side.valid_from <= coalesce(right_side.valid_to, date '9999-12-31')
     and right_side.valid_from <= coalesce(left_side.valid_to, date '9999-12-31')

    union all

    select 'overlapping_roster_history', left_side.player_id
    from {{ source('core', 'roster_history') }} as left_side
    join {{ source('core', 'roster_history') }} as right_side
      on left_side.player_id = right_side.player_id
     and left_side.membership_id < right_side.membership_id
     and left_side.valid_from <= coalesce(right_side.valid_to, date '9999-12-31')
     and right_side.valid_from <= coalesce(left_side.valid_to, date '9999-12-31')

    union all

    select 'overlapping_rating_history', left_side.player_id || ':' || left_side.rating_system
    from {{ source('core', 'rating_history') }} as left_side
    join {{ source('core', 'rating_history') }} as right_side
      on left_side.player_id = right_side.player_id
     and left_side.rating_system = right_side.rating_system
     and left_side.rating_id < right_side.rating_id
     and left_side.valid_from <= coalesce(right_side.valid_to, date '9999-12-31')
     and right_side.valid_from <= coalesce(left_side.valid_to, date '9999-12-31')

    union all

    select 'negative_rating', rating_id
    from {{ source('core', 'rating_history') }}
    where rating_value < 0

    union all

    select 'unreasonable_height', version_id
    from {{ source('core', 'player_history') }}
    where height_inches not between 60 and 96

    union all

    select 'invalid_source_lineage', history_id
    from (
        select version_id as history_id, source_snapshot_id from {{ source('core', 'player_history') }}
        union all
        select membership_id, source_snapshot_id from {{ source('core', 'roster_history') }}
        union all
        select rating_id, source_snapshot_id from {{ source('core', 'rating_history') }}
    ) as history
    left join {{ source('raw', 'source_snapshot') }} as snapshot using (source_snapshot_id)
    where snapshot.snapshot_id is null

    union all

    select 'incomplete_puzzle_clues', pool.player_id
    from {{ ref('mart_current_player_pool') }} as pool
    left join {{ ref('mart_daily_puzzle_candidates') }} as candidate using (player_id)
    where candidate.player_id is null

    union all

    select 'quarantine_without_reason', quarantine_id
    from {{ source('core', 'quarantine_player_record') }}
    where reason_code is null or trim(reason_code) = '' or reason_detail is null or trim(reason_detail) = ''
)
select * from violations
