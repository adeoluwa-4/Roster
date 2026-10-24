import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

import duckdb

from pipeline.daily_roster import (
    Metrics,
    deterministic_puzzles,
    initialize_database,
    load_snapshot,
    merge_scd,
    normalize_country,
    normalize_name,
    normalize_position,
    normalize_team,
    resolve_identity,
)


def player_record(**overrides):
    record = {
        "id": "nikola-jokic",
        "rank": 1,
        "name": "Nikola Jokić Jr.",
        "draftYear": 2014,
        "position": "C",
        "conference": "West",
        "team": "Denver Nuggets",
        "nationality": "Serbia",
        "continent": "Europe",
        "height": 83,
        "weight": 284,
        "nbaId": 203999,
        "espnId": 3112335,
        "twoKRating": 98,
        "active": True,
        "rosterSeason": "2026-27",
    }
    record.update(overrides)
    return record


class DataPipelineTests(unittest.TestCase):
    def setUp(self):
        self.connection = duckdb.connect(":memory:")
        initialize_database(self.connection)

    def tearDown(self):
        self.connection.close()

    def write_snapshot(self, directory: Path, effective: str, records: list[dict]) -> Path:
        path = directory / f"snapshot-{effective}.json"
        path.write_text(json.dumps({
            "schema_version": 1,
            "source_name": "stored_daily_roster_fixture",
            "captured_at": f"{effective}T12:00:00Z",
            "effective_date": effective,
            "source_policy": "stored_fixture_only",
            "records": records,
        }), encoding="utf-8")
        return path

    def test_normalizes_names_suffixes_accents_and_dimensions(self):
        self.assertEqual(normalize_name("Nikola Jokić Jr."), "nikolajokic")
        self.assertEqual(normalize_team("Philadelphia 76ers"), "Philadelphia 76ers")
        self.assertEqual(normalize_position("PF-C"), "Forward / Center")
        self.assertEqual(normalize_country("United States"), "USA")

    def test_source_identifier_wins_before_normalized_name(self):
        self.connection.execute(
            "insert into core.player_identity values ('stable-id', 'Nikola Jokic', 'nikolajokic', current_timestamp)"
        )
        self.connection.execute(
            "insert into core.player_alias values ('alias', 'nba_id', '203999', 'Nikola Jokic', 'nikolajokic', 'stable-id', true, 'manual', current_timestamp)"
        )
        player_id, method, confidence, reason = resolve_identity(
            self.connection, player_record(name="Completely Different")
        )
        self.assertEqual((player_id, method, confidence, reason), ("stable-id", "source_id", 1.0, None))

    def test_low_confidence_fuzzy_match_is_quarantined(self):
        self.connection.execute(
            "insert into core.player_identity values ('known', 'Nikola Jokic', 'nikolajokic', current_timestamp)"
        )
        record = player_record(id=None, nbaId=None, espnId=None, name="Nikola Jovic")
        player_id, method, confidence, reason = resolve_identity(self.connection, record)
        self.assertIsNone(player_id)
        self.assertEqual(method, "fuzzy_quarantine")
        self.assertGreaterEqual(confidence, 0.8)
        self.assertIsNotNone(reason)

    def test_scd_update_closes_previous_version(self):
        keys = {"player_id": "player-1"}
        first = {
            "name": "Player One", "draft_year": 2020, "position": "Guard",
            "country": "USA", "continent": "North America", "height_inches": 75,
            "weight_pounds": 190, "active": True,
        }
        second = {**first, "height_inches": 76}
        self.assertEqual(merge_scd(self.connection, "core.player_history", "version_id", keys, first, date(2026, 1, 1), "snapshot-1"), "added")
        self.assertEqual(merge_scd(self.connection, "core.player_history", "version_id", keys, second, date(2026, 2, 1), "snapshot-2"), "updated")
        rows = self.connection.execute(
            "select height_inches, valid_to, is_current from core.player_history order by valid_from"
        ).fetchall()
        self.assertEqual(rows, [(75, date(2026, 1, 31), False), (76, None, True)])

    def test_incremental_load_and_idempotent_rerun(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = self.write_snapshot(root, "2026-01-01", [player_record()])
            second = self.write_snapshot(root, "2026-02-01", [player_record(team="Dallas Mavericks")])
            initial = Metrics()
            load_snapshot(self.connection, first, initial)
            rerun = Metrics()
            load_snapshot(self.connection, first, rerun)
            changed = Metrics()
            load_snapshot(self.connection, second, changed)
        self.assertEqual(initial.records_added, 1)
        self.assertEqual(rerun.records_unchanged, 1)
        self.assertEqual(changed.records_unchanged, 1)
        roster = self.connection.execute(
            "select team_name, valid_to, is_current from core.roster_history order by valid_from"
        ).fetchall()
        self.assertEqual(roster, [
            ("Denver Nuggets", date(2026, 1, 31), False),
            ("Dallas Mavericks", None, True),
        ])

    def test_invalid_record_enters_quarantine_with_reason(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_snapshot(Path(directory), "2026-01-01", [player_record(height=40)])
            metrics = Metrics()
            load_snapshot(self.connection, path, metrics)
        reason = self.connection.execute(
            "select reason_code, reason_detail from core.quarantine_player_record"
        ).fetchone()
        self.assertEqual(reason[0], "invalid_record")
        self.assertIn("height_out_of_range", reason[1])
        self.assertEqual(metrics.quarantined_records, 1)

    def test_puzzle_selection_is_deterministic_and_date_unique(self):
        self.connection.execute("create schema analytics_analytics")
        self.connection.execute("create table analytics_analytics.mart_daily_puzzle_candidates(player_id varchar)")
        self.connection.executemany(
            "insert into analytics_analytics.mart_daily_puzzle_candidates values (?)",
            [("player-a",), ("player-b",), ("player-c",)],
        )
        deterministic_puzzles(self.connection, date(2026, 10, 24), 10, "seed", "run-1", "v1")
        first = self.connection.execute(
            "select puzzle_date, player_id, selection_hash from ops.daily_puzzle order by puzzle_date"
        ).fetchall()
        deterministic_puzzles(self.connection, date(2026, 10, 24), 10, "seed", "run-2", "v1")
        second = self.connection.execute(
            "select puzzle_date, player_id, selection_hash from ops.daily_puzzle order by puzzle_date"
        ).fetchall()
        self.assertEqual(first, second)
        self.assertEqual(len(second), 10)
        self.assertEqual(len({row[0] for row in second}), 10)


if __name__ == "__main__":
    unittest.main()
