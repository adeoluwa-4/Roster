select
    history.version_id as snapshot_id,
    history.player_id,
    history.name,
    history.draft_year,
    history.position,
    history.country,
    history.continent,
    history.height_inches,
    history.weight_pounds,
    history.active,
    history.valid_from,
    history.valid_to,
    history.is_current,
    history.content_hash,
    history.source_snapshot_id,
    (
        select roster.membership_id
        from {{ source('core', 'roster_history') }} as roster
        where roster.player_id = history.player_id
          and history.valid_from between roster.valid_from and coalesce(roster.valid_to, date '9999-12-31')
        order by roster.valid_from desc
        limit 1
    ) as membership_id,
    (
        select rating.rating_id
        from {{ source('core', 'rating_history') }} as rating
        where rating.player_id = history.player_id
          and history.valid_from between rating.valid_from and coalesce(rating.valid_to, date '9999-12-31')
        order by rating.valid_from desc
        limit 1
    ) as rating_id
from {{ source('core', 'player_history') }} as history
