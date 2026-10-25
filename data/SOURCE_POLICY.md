# Data source policy

Daily Roster's scheduled pipeline is offline-first. It may ingest only source snapshots that have been reviewed, stored in `data/source_snapshots/`, and committed with capture time, effective date, schema version, source name, and a checksum recorded by the loader.

## Approved production input

| Source | Allowed use | Current status |
|---|---|---|
| `stored_daily_roster_fixture` | Reproducible local ingestion, tests, dbt models, puzzle generation, and application export | Approved |

The current fixture contains 250 records, is effective 2026-08-14, and is a frozen input. A stored fixture proves the pipeline's behavior; it does not prove that its basketball facts are current. New snapshots require a documented provenance review before they are committed.

## Not approved for scheduled collection

- NBA2KLab pages and private-looking function endpoints are not scheduled sources. Its [terms](https://www.nba2klab.com/terms) govern access and content use. The legacy `scripts/build-nba2k-top-250.mjs` collector fails closed unless a maintainer explicitly acknowledges that it is unverified.
- ESPN's undocumented site endpoints are not scheduled sources. A public web response is not, by itself, evidence of API permission or a stability contract.
- `nba_api` static identifier data is distributed under its repository's [MIT license](https://github.com/swar/nba_api/blob/master/LICENSE), but it is not fetched by the production pipeline.

No README or resume claim should describe those services as live pipeline sources unless permission, endpoint stability, and an actual successful run are documented.

## Adding a source

1. Confirm its license or API terms permit the intended access, storage, transformation, and redistribution.
2. Add a source-specific adapter with bounded retries, timeouts, structured errors, and an explicit schema version.
3. Save an immutable raw snapshot before normalization. Never silently replace an existing snapshot.
4. Map source identifiers into `core.player_alias`; keep the stable internal `player_id` separate.
5. Quarantine invalid or low-confidence records instead of accepting them.
6. Run the full pipeline, dbt tests, Python tests, and application tests from a clean database.
7. Record only the resulting measured counts in `analytics/pipeline_report.md`.

## Privacy and retention

The dataset contains public professional-basketball attributes and source identifiers, not user data. Raw snapshots are retained for reproducibility. Corrections are added as new dated snapshots so historical values remain auditable.
