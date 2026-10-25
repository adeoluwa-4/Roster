# Daily Roster data products

This directory contains the reviewed raw input and the generated JSON consumed by the game. Neither application file is maintained by hand.

## Files

- `source_snapshots/stored_daily_roster_2026-08-14.json` is the immutable, schema-versioned raw fixture currently approved for pipeline runs.
- `players.json` is exported from `mart_current_player_pool` after dbt tests pass.
- `puzzles.json` is exported from `fact_daily_puzzle`; each date is selected deterministically from the eligible player mart.
- `SOURCE_POLICY.md` documents approved and prohibited source use.

The current input has 250 player records. Its 2026-08-14 effective date is source freshness metadata, not a claim that the roster is current today.

## Lineage

```text
stored source snapshot
  -> raw.source_snapshot + raw.player_record
  -> identity resolution + quarantine
  -> SCD player, roster, and rating history
  -> dbt dimensions, facts, and marts
  -> players.json + puzzles.json
  -> Next.js game
```

Every raw snapshot receives a checksum. Player identities use stable internal UUIDs while NBA, ESPN, fixture, and future source identifiers remain aliases. Accepted fuzzy matches retain a confidence score; ambiguous matches go to quarantine.

## Regeneration

From the repository root:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
npm ci
.venv/bin/python -m pipeline.daily_roster run \
  --puzzle-start 2026-10-25 \
  --puzzle-days 90
```

For a bounded historical reload, add `--start YYYY-MM-DD` and/or `--end YYYY-MM-DD`. Reprocessing the same snapshot is idempotent: identical content does not create another history version.

Do not use `scripts/build-nba2k-top-250.mjs` for scheduled production collection. It is a guarded legacy research script whose remote endpoints are not approved pipeline sources.
