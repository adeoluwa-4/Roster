# NBA player database

`players.json` is the local game pool for Guess the Athlete. It contains the all-time top 500 NBA/BAA players plus every missing player from the current season's top 150.

## Sources

- [V2 NBA Player Database](https://www.kaggle.com/datasets/flynn28/v2-nba-player-database): career Win Shares, debut, position, height, and games played.
- [NBA Stats (1947-present)](https://www.kaggle.com/datasets/sumitrodatta/nba-aba-baa-stats): season-by-season team and games-played history.
- [NBA Players Dataset](https://www.kaggle.com/datasets/romainmorleghem/nba-players-info-and-headlinestats-up-to-2025): country information sourced from the NBA API.

## Game rules

- The all-time pool includes the 500 eligible NBA/BAA players with the most career Win Shares.
- The current pool ranks the latest NBA season's top 150 by Win Shares, using VORP, games, and name as deterministic tie-breakers. Players already in the all-time 500 are not duplicated.
- `allTimeRank` and `currentRank` show which list or lists include each player.
- `team` is the franchise for which the player appeared in the most regular-season games.
- `teams` preserves every NBA/BAA franchise the player represented, ordered by games played.
- Historical franchise names are grouped into their current franchise, such as Minneapolis and Los Angeles Lakers.
- `conference` follows the current conference of that franchise. Defunct franchises use their historical geography.
- Country values unavailable from the NBA information dataset fall back to USA; the build script reports the fallback count.

Regenerate the file with `scripts/build-player-database.py` after downloading the three source datasets.
