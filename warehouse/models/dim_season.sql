select distinct
    md5(season_label) as season_id,
    season_label,
    try_cast(regexp_extract(season_label, '^[0-9]{4}', 0) as integer) as start_year,
    case
        when regexp_matches(season_label, '^[0-9]{4}-[0-9]{2}$')
        then try_cast(regexp_extract(season_label, '^[0-9]{4}', 0) as integer) + 1
    end as end_year
from {{ source('core', 'roster_history') }}
