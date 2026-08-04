# NBA player database

`players.json` is the local game pool for Guess the NBA Player. It contains the all-time top 200 NBA/BAA players plus every missing player from the current season's top 150.

## Sources

- [V2 NBA Player Database](https://www.kaggle.com/datasets/flynn28/v2-nba-player-database): career Win Shares, position, height, and games played.
- [NBA Stats (1947-present)](https://www.kaggle.com/datasets/sumitrodatta/nba-aba-baa-stats): season-by-season team and games-played history.
- [NBA Players Dataset](https://www.kaggle.com/datasets/romainmorleghem/nba-players-info-and-headlinestats-up-to-2025): country and official draft-year information sourced from the NBA API `CommonPlayerInfo` records.
- [NBA League Roster](https://www.nba.com/players): official current team, position, height, and country for active players. The current snapshot is for the 2026-27 season.

## Game rules

- The all-time pool includes the 200 eligible NBA/BAA players with the most career Win Shares.
- The current pool ranks the latest NBA season's top 150 by Win Shares, using VORP, games, and name as deterministic tie-breakers. Players already in the all-time 200 are not duplicated.
- `allTimeRank` and `currentRank` show which list or lists include each player.
- For an active player, `team` is the player’s current team on the official NBA league roster. For an inactive player, it is the franchise for which the player appeared in the most regular-season games.
- `teams` preserves every NBA/BAA franchise the player represented. An active player’s current team is first, followed by career teams ordered by games played; a newly joined team may have zero recorded games before the season begins.
- `active` and `rosterSeason` identify records updated from the current official roster.
- `draftYear` is the NBA draft year. It is `null` for players the NBA identifies as undrafted, which the game displays as “Undrafted.”
- Historical franchise names are grouped into their current franchise, such as Minneapolis and Los Angeles Lakers.
- `conference` follows the current conference of that franchise. Defunct franchises use their historical geography.
- Country values unavailable from the NBA information dataset fall back to USA; the build script reports the fallback count.

Regenerate the file with `scripts/build-player-database.py` after downloading the source datasets and the official NBA league roster page. Pass the saved roster page with `--roster` and its season with `--roster-season`.
