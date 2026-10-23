select
    md5(lower(team_name)) as team_id,
    team_name,
    conference,
    min(valid_from) as first_observed_at,
    max(coalesce(valid_to, valid_from)) as last_observed_at,
    bool_or(is_current) as is_current
from {{ source('core', 'roster_history') }}
group by team_name, conference
