# Daily Roster pipeline report

Generated: 2026-10-25T05:05:29.655217+00:00

## Pipeline health

- Runs recorded: 1
- Successful runs: 1
- Latest completed run: 2026-10-25 00:05:27.433298-05:00
- Source snapshots: 1
- Source records: 250
- Latest source capture: 2026-08-14 13:00:00-05:00
- Mean identity confidence: 1.0
- Quarantined identity events: 0
- Current player pool: 250
- Scheduled puzzles: 90
- Dataset version: `751eed3d78532443`
- Latest runtime (seconds): 12.1668
- Warehouse schema version: 1

## Latest successful run

| Metric | Count |
|---|---:|
| Records fetched | 250 |
| Records added | 250 |
| Records updated | 0 |
| Records unchanged | 0 |
| Duplicates removed | 0 |
| Unresolved identities | 0 |
| Quarantined records | 0 |
| dbt tests passed | 44 |
| dbt tests failed | 0 |

## Source freshness

| Source | Latest capture | Effective date | Snapshots | Records |
|---|---|---|---:|---:|
| stored_daily_roster_fixture | 2026-08-14 13:00:00-05:00 | 2026-08-14 | 1 | 250 |

## Identity resolution confidence

| Match method | Status | Records | Mean confidence |
|---|---|---:|---:|
| new_source_identity | accepted | 250 | 1.0 |

## Roster changes by season

| Season | Membership versions | Closed versions |
|---|---:|---:|
| 2026-27 | 250 | 0 |

## Rating changes over time

| Effective date | Rating versions | Mean rating | Changed ratings |
|---|---:|---:|---:|
| 2026-08-14 | 250 | 80.67 | 0 |

## Players by team

| Team | Players |
|---|---:|
| Atlanta Hawks | 11 |
| Dallas Mavericks | 11 |
| Los Angeles Lakers | 11 |
| Chicago Bulls | 10 |
| Houston Rockets | 10 |
| Indiana Pacers | 10 |
| Milwaukee Bucks | 10 |
| Philadelphia 76ers | 10 |
| Portland Trail Blazers | 10 |
| Utah Jazz | 10 |
| Washington Wizards | 10 |
| Memphis Grizzlies | 9 |
| New York Knicks | 9 |
| Oklahoma City Thunder | 9 |
| San Antonio Spurs | 9 |
| Charlotte Hornets | 8 |
| Detroit Pistons | 8 |
| LA Clippers | 8 |
| New Orleans Pelicans | 8 |
| Orlando Magic | 8 |
| Boston Celtics | 7 |
| Denver Nuggets | 7 |
| Miami Heat | 7 |
| Phoenix Suns | 7 |
| Toronto Raptors | 7 |
| Cleveland Cavaliers | 6 |
| Minnesota Timberwolves | 6 |
| Golden State Warriors | 5 |
| Sacramento Kings | 5 |
| Brooklyn Nets | 4 |

## Players by country

| Country | Players |
|---|---:|
| USA | 200 |
| Canada | 11 |
| Germany | 4 |
| Australia | 3 |
| Cameroon | 3 |
| France | 3 |
| Bahamas | 2 |
| Georgia | 2 |
| Nigeria | 2 |
| Serbia | 2 |
| Switzerland | 2 |
| Austria | 1 |
| Belgium | 1 |
| Bosnia & Herzegovina | 1 |
| England | 1 |
| Finland | 1 |
| Greece | 1 |
| Israel | 1 |
| Japan | 1 |
| Latvia | 1 |
| Lithuania | 1 |
| Montenegro | 1 |
| New Zealand | 1 |
| Slovenia | 1 |
| Spain | 1 |
| Turkey | 1 |
| United Kingdom | 1 |

## Players by position

| Position | Players |
|---|---:|
| Guard | 68 |
| Guard / Forward | 58 |
| Forward | 53 |
| Forward / Center | 38 |
| Center | 33 |

## Daily puzzle coverage

- First scheduled date: 2026-10-25
- Last scheduled date: 2027-01-22
- Scheduled dates: 90
- Distinct featured players: 76

This report is generated from DuckDB only after dbt tests and the application test suite pass.
