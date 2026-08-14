# NBA player database

`players.json` is the local game pool for Guess the NBA Player. It contains the 250 highest-rated active NBA players in the NBA 2K26 roster snapshot.

## Sources

- [NBA2KLab NBA 2K26 player ratings](https://www.nba2klab.com/nba2k-player-ratings): the ranking, NBA 2K overall rating, height, and position for the full player pool.
- [NBA2KLab NBA 2K26 team rosters](https://www.nba2klab.com/teams): the NBA 2K-listed player weights.
- Public roster and player-profile metadata is used only to retain draft year, nationality, and player-photo fallback identifiers when a player was not already in the previous game data. Height, weight, and position always come from the NBA 2K dataset.

## Game rules

- The game pool is exactly 250 active players, sorted by NBA 2K overall rating. Ties are sorted by player name so the daily puzzle order is stable.
- `twoKRating` records the overall rating that selected each player for the pool.
- `height`, `weight`, and `position` are NBA 2K values. Height is stored in inches and weight in pounds.
- `team` and `conference` follow the NBA 2K roster snapshot; `teams` retains the current team as the first entry for compatibility with the game.
- `draftYear` is the NBA draft year. It is `null` for undrafted players, which the game displays as “Undrafted.”
- `active` is always `true` and `rosterSeason` is `2025-26` for this NBA 2K26 snapshot.

Regenerate the file with `node scripts/build-nba2k-top-250.mjs`. The script downloads the public NBA 2K roster feed and supplements only the non-physical game metadata.
