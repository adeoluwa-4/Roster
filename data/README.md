# NBA player database

`players.json` is the local game pool for Guess the NBA Player. It contains the 250 highest-rated active NBA players in the NBA 2K26 roster snapshot.

## Sources

- [NBA2KLab NBA 2K26 player ratings](https://www.nba2klab.com/nba2k-player-ratings): the ranking, NBA 2K overall rating, and position for the full player pool.
- [NBA2KLab NBA 2K26 team rosters](https://www.nba2klab.com/teams): the NBA 2K-listed player weights.
- [ESPN NBA team rosters](https://www.espn.com/nba/teams): the current player pool, height, and current team. Public player-profile metadata also retains draft year, nationality, and player-photo fallback identifiers.

## Game rules

- The game pool is exactly 250 players on ESPN’s current NBA rosters, sorted by NBA 2K overall rating. Ties are sorted by player name so the daily puzzle order is stable.
- `twoKRating` records the overall rating that selected each player for the pool.
- `height` and `team` are ESPN current-roster values. `position` and `weight` are NBA 2K values. Height is stored in inches and weight in pounds.
- `conference` follows the player’s ESPN current team; `teams` retains that current team as the first entry for compatibility with the game.
- `draftYear` is the NBA draft year. It is `null` for undrafted players, which the game displays as “Undrafted.”
- `active` is always `true` and `rosterSeason` records the ESPN roster season used by the build.

Regenerate the file with `node scripts/build-nba2k-top-250.mjs`. The script downloads the public NBA 2K roster feed and supplements only the non-physical game metadata.
