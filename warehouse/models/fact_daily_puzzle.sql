select
    puzzle.puzzle_date,
    puzzle.player_id,
    player.game_player_id,
    puzzle.seed,
    puzzle.selection_hash,
    puzzle.generated_at,
    puzzle.dataset_version,
    puzzle.source_run_id
from {{ source('ops', 'daily_puzzle') }} as puzzle
join {{ ref('dim_player') }} as player using (player_id)
