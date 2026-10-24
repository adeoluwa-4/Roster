#!/usr/bin/env python3
"""Reproducible DuckDB/dbt pipeline that powers the Daily Roster game."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import subprocess
import sys
import time
import unicodedata
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Callable, Iterable

import duckdb


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "warehouse" / "daily_roster.duckdb"
DEFAULT_PLAYERS = ROOT / "data" / "players.json"
DEFAULT_PUZZLES = ROOT / "data" / "puzzles.json"
DEFAULT_REPORT = ROOT / "analytics" / "pipeline_report.md"
NAMESPACE = uuid.UUID("ad8f2148-ec68-4ca2-a29c-e1c63fe7f62e")
SCHEMA_VERSION = 1

TEAM_ALIASES = {
    "la clippers": "LA Clippers",
    "los angeles clippers": "LA Clippers",
    "philadelphia 76ers": "Philadelphia 76ers",
    "philadelphia sixers": "Philadelphia 76ers",
    "philly 76ers": "Philadelphia 76ers",
    "portland trailblazers": "Portland Trail Blazers",
}
POSITION_ALIASES = {
    "pg": "Guard", "sg": "Guard", "g": "Guard",
    "sf": "Forward", "pf": "Forward", "f": "Forward", "c": "Center",
}
COUNTRY_ALIASES = {
    "united states": "USA", "u.s.a.": "USA", "us": "USA",
    "bosnia and herzegovina": "Bosnia & Herzegovina",
    "democratic republic of the congo": "DR Congo", "congo": "DR Congo",
}
VALID_TEAMS = {
    "Atlanta Hawks", "Boston Celtics", "Brooklyn Nets", "Charlotte Hornets",
    "Chicago Bulls", "Cleveland Cavaliers", "Dallas Mavericks", "Denver Nuggets",
    "Detroit Pistons", "Golden State Warriors", "Houston Rockets", "Indiana Pacers",
    "LA Clippers", "Los Angeles Lakers", "Memphis Grizzlies", "Miami Heat",
    "Milwaukee Bucks", "Minnesota Timberwolves", "New Orleans Pelicans",
    "New York Knicks", "Oklahoma City Thunder", "Orlando Magic", "Philadelphia 76ers",
    "Phoenix Suns", "Portland Trail Blazers", "Sacramento Kings", "San Antonio Spurs",
    "Toronto Raptors", "Utah Jazz", "Washington Wizards",
}
VALID_POSITIONS = {
    "Guard", "Forward", "Center", "Guard / Forward", "Forward / Guard",
    "Forward / Center", "Center / Forward",
}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "event": record.getMessage(),
        }, sort_keys=True)


LOG = logging.getLogger("daily_roster_pipeline")
if not LOG.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    LOG.addHandler(handler)
LOG.setLevel(logging.INFO)


@dataclass
class Metrics:
    records_fetched: int = 0
    records_added: int = 0
    records_updated: int = 0
    records_unchanged: int = 0
    duplicates_removed: int = 0
    unresolved_identities: int = 0
    quarantined_records: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    dataset_version: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        values = {
            "records_fetched": self.records_fetched,
            "records_added": self.records_added,
            "records_updated": self.records_updated,
            "records_unchanged": self.records_unchanged,
            "duplicates_removed": self.duplicates_removed,
            "unresolved_identities": self.unresolved_identities,
            "quarantined_records": self.quarantined_records,
            "tests_passed": self.tests_passed,
            "tests_failed": self.tests_failed,
            "dataset_version": self.dataset_version,
        }
        values.update(self.extra)
        return values


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def content_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def normalize_name(value: str) -> str:
    folded = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode()
    folded = re.sub(r"\b(jr|sr|ii|iii|iv)\b\.?", "", folded, flags=re.IGNORECASE)
    return re.sub(r"[^a-z0-9]", "", folded.casefold())


def normalize_team(value: str) -> str:
    compact = " ".join((value or "").replace(".", "").split()).casefold()
    if compact in TEAM_ALIASES:
        return TEAM_ALIASES[compact]
    return " ".join(word.upper() if word in {"la", "okc"} else word.title() for word in compact.split())


def normalize_country(value: str) -> str:
    compact = " ".join((value or "").split())
    return COUNTRY_ALIASES.get(compact.casefold(), compact)


def normalize_position(value: str) -> str:
    raw = re.split(r"[/|,-]", value or "")
    labels: list[str] = []
    for item in raw:
        key = item.strip().casefold()
        label = POSITION_ALIASES.get(key, item.strip().title())
        if label and label not in labels:
            labels.append(label)
    order = {"Guard": 0, "Forward": 1, "Center": 2}
    labels.sort(key=lambda item: order.get(item, 99))
    return " / ".join(labels)


def retry(operation: Callable[[], Any], source: str, attempts: int = 3) -> Any:
    for attempt in range(1, attempts + 1):
        try:
            return operation()
        except (OSError, json.JSONDecodeError) as error:
            LOG.error(canonical_json({"source": source, "attempt": attempt, "error": str(error)}))
            if attempt == attempts:
                raise
            time.sleep(0.25 * attempt)
    raise RuntimeError("unreachable")


def create_snapshot(input_path: Path, output_path: Path, captured_at: str, effective_date: str) -> None:
    records = retry(lambda: json.loads(input_path.read_text(encoding="utf-8")), str(input_path))
    if not isinstance(records, list) or not records:
        raise ValueError("snapshot input must be a non-empty JSON array")
    payload = {
        "schema_version": SCHEMA_VERSION,
        "source_name": "stored_daily_roster_fixture",
        "captured_at": captured_at,
        "effective_date": effective_date,
        "source_policy": "stored_fixture_only",
        "records": records,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    LOG.info(canonical_json({"event": "snapshot_created", "path": str(output_path), "records": len(records), "checksum": content_hash(payload)}))


def initialize_database(connection: duckdb.DuckDBPyConnection) -> None:
    connection.execute("CREATE SCHEMA IF NOT EXISTS raw")
    connection.execute("CREATE SCHEMA IF NOT EXISTS core")
    connection.execute("CREATE SCHEMA IF NOT EXISTS ops")
    connection.execute("""
        CREATE TABLE IF NOT EXISTS raw.source_snapshot (
            snapshot_id VARCHAR PRIMARY KEY, source_name VARCHAR NOT NULL,
            captured_at TIMESTAMPTZ NOT NULL, effective_date DATE NOT NULL,
            checksum VARCHAR NOT NULL, schema_version INTEGER NOT NULL,
            source_path VARCHAR NOT NULL, record_count INTEGER NOT NULL,
            loaded_at TIMESTAMPTZ NOT NULL,
            UNIQUE(source_name, checksum, schema_version)
        )
    """)
    connection.execute("""
        CREATE TABLE IF NOT EXISTS raw.player_record (
            snapshot_id VARCHAR NOT NULL, row_number INTEGER NOT NULL,
            source_name VARCHAR NOT NULL, source_player_id VARCHAR,
            normalized_name VARCHAR NOT NULL, payload JSON NOT NULL,
            record_hash VARCHAR NOT NULL, loaded_at TIMESTAMPTZ NOT NULL,
            PRIMARY KEY(snapshot_id, row_number)
        )
    """)
    connection.execute("""
        CREATE TABLE IF NOT EXISTS core.player_identity (
            player_id VARCHAR PRIMARY KEY, canonical_name VARCHAR NOT NULL,
            normalized_name VARCHAR NOT NULL, created_at TIMESTAMPTZ NOT NULL
        )
    """)
    connection.execute("""
        CREATE TABLE IF NOT EXISTS core.player_alias (
            alias_id VARCHAR PRIMARY KEY, source_name VARCHAR NOT NULL,
            source_player_id VARCHAR, alias_name VARCHAR NOT NULL,
            normalized_name VARCHAR NOT NULL, player_id VARCHAR NOT NULL,
            is_manual BOOLEAN NOT NULL DEFAULT FALSE, notes VARCHAR,
            created_at TIMESTAMPTZ NOT NULL,
            UNIQUE(source_name, source_player_id)
        )
    """)
    connection.execute("""
        CREATE TABLE IF NOT EXISTS core.identity_resolution_event (
            event_id VARCHAR PRIMARY KEY, snapshot_id VARCHAR NOT NULL,
            row_number INTEGER NOT NULL, player_id VARCHAR,
            match_method VARCHAR NOT NULL, confidence DOUBLE NOT NULL,
            resolution_status VARCHAR NOT NULL, reason VARCHAR,
            created_at TIMESTAMPTZ NOT NULL
        )
    """)
    connection.execute("""
        CREATE TABLE IF NOT EXISTS core.quarantine_player_record (
            quarantine_id VARCHAR PRIMARY KEY, snapshot_id VARCHAR NOT NULL,
            row_number INTEGER NOT NULL, source_player_id VARCHAR,
            normalized_name VARCHAR, reason_code VARCHAR NOT NULL,
            reason_detail VARCHAR NOT NULL, payload JSON NOT NULL,
            quarantined_at TIMESTAMPTZ NOT NULL, resolved_at TIMESTAMPTZ
        )
    """)
    connection.execute("""
        CREATE TABLE IF NOT EXISTS core.player_history (
            version_id VARCHAR PRIMARY KEY, player_id VARCHAR NOT NULL,
            name VARCHAR NOT NULL, draft_year INTEGER, position VARCHAR NOT NULL,
            country VARCHAR NOT NULL, continent VARCHAR NOT NULL,
            height_inches INTEGER NOT NULL, weight_pounds INTEGER,
            active BOOLEAN NOT NULL, content_hash VARCHAR NOT NULL,
            valid_from DATE NOT NULL, valid_to DATE, is_current BOOLEAN NOT NULL,
            source_snapshot_id VARCHAR NOT NULL,
            UNIQUE(player_id, valid_from)
        )
    """)
    connection.execute("""
        CREATE TABLE IF NOT EXISTS core.roster_history (
            membership_id VARCHAR PRIMARY KEY, player_id VARCHAR NOT NULL,
            team_name VARCHAR NOT NULL, conference VARCHAR NOT NULL,
            season_label VARCHAR NOT NULL, active BOOLEAN NOT NULL,
            content_hash VARCHAR NOT NULL, valid_from DATE NOT NULL,
            valid_to DATE, is_current BOOLEAN NOT NULL,
            source_snapshot_id VARCHAR NOT NULL,
            UNIQUE(player_id, valid_from)
        )
    """)
    connection.execute("""
        CREATE TABLE IF NOT EXISTS core.rating_history (
            rating_id VARCHAR PRIMARY KEY, player_id VARCHAR NOT NULL,
            rating_system VARCHAR NOT NULL, rating_value DOUBLE NOT NULL,
            rank_value INTEGER, content_hash VARCHAR NOT NULL,
            valid_from DATE NOT NULL, valid_to DATE, is_current BOOLEAN NOT NULL,
            source_snapshot_id VARCHAR NOT NULL,
            UNIQUE(player_id, rating_system, valid_from)
        )
    """)
    connection.execute("""
        CREATE TABLE IF NOT EXISTS ops.daily_puzzle (
            puzzle_date DATE PRIMARY KEY, player_id VARCHAR NOT NULL,
            seed VARCHAR NOT NULL, selection_hash VARCHAR NOT NULL,
            generated_at TIMESTAMPTZ NOT NULL, dataset_version VARCHAR NOT NULL,
            source_run_id VARCHAR NOT NULL
        )
    """)
    connection.execute("""
        CREATE TABLE IF NOT EXISTS ops.pipeline_run (
            run_id VARCHAR PRIMARY KEY, started_at TIMESTAMPTZ NOT NULL,
            completed_at TIMESTAMPTZ, status VARCHAR NOT NULL,
            source_name VARCHAR NOT NULL, snapshot_id VARCHAR,
            metrics JSON NOT NULL, dataset_version VARCHAR,
            error_message VARCHAR, runtime_seconds DOUBLE,
            schema_version INTEGER NOT NULL
        )
    """)


def validate_record(record: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    required = ("id", "name", "position", "team", "nationality", "height")
    reasons.extend(f"missing_{field}" for field in required if record.get(field) in (None, ""))
    height = record.get("height")
    rating = record.get("twoKRating")
    if not isinstance(height, int) or not 60 <= height <= 96:
        reasons.append("height_out_of_range")
    if rating is not None and (not isinstance(rating, (int, float)) or rating < 0):
        reasons.append("negative_or_invalid_rating")
    if normalize_team(str(record.get("team", ""))) not in VALID_TEAMS:
        reasons.append("unrecognized_team")
    if normalize_position(str(record.get("position", ""))) not in VALID_POSITIONS:
        reasons.append("unrecognized_position")
    return reasons


def source_identifiers(record: dict[str, Any]) -> list[tuple[str, str]]:
    identifiers: list[tuple[str, str]] = []
    if record.get("nbaId") is not None:
        identifiers.append(("nba_id", str(record["nbaId"])))
    if record.get("espnId") is not None:
        identifiers.append(("espn_id", str(record["espnId"])))
    if record.get("id") not in (None, ""):
        identifiers.append(("fixture", str(record["id"])))
    return [(source, value) for source, value in identifiers if value]


def resolve_identity(connection: duckdb.DuckDBPyConnection, record: dict[str, Any]) -> tuple[str | None, str, float, str | None]:
    for source, identifier in source_identifiers(record):
        row = connection.execute(
            "SELECT player_id FROM core.player_alias WHERE source_name = ? AND source_player_id = ?",
            [source, identifier],
        ).fetchone()
        if row:
            return str(row[0]), "source_id", 1.0, None

    normalized = normalize_name(str(record.get("name", "")))
    exact = connection.execute(
        "SELECT player_id FROM core.player_identity WHERE normalized_name = ? ORDER BY player_id",
        [normalized],
    ).fetchall()
    if len(exact) == 1:
        return str(exact[0][0]), "normalized_exact", 0.99, None
    if len(exact) > 1:
        return None, "ambiguous_exact", 0.5, "multiple players share normalized name"

    identifiers = source_identifiers(record)
    if identifiers:
        source, identifier = identifiers[0]
        player_id = str(uuid.uuid5(NAMESPACE, f"player:{source}:{identifier}"))
        return player_id, "new_source_identity", 1.0, None

    candidates = connection.execute("SELECT player_id, normalized_name FROM core.player_identity").fetchall()
    if not candidates:
        player_id = str(uuid.uuid5(NAMESPACE, f"player:{normalized}:{record.get('draftYear')}"))
        return player_id, "new_identity", 1.0, None
    scored = sorted(
        ((SequenceMatcher(None, normalized, str(name)).ratio(), str(player_id)) for player_id, name in candidates),
        reverse=True,
    )
    best_score, best_id = scored[0]
    margin = best_score - (scored[1][0] if len(scored) > 1 else 0.0)
    if best_score >= 0.94 and margin >= 0.05:
        return best_id, "fuzzy", round(best_score, 4), None
    if best_score >= 0.80:
        return None, "fuzzy_quarantine", round(best_score, 4), f"best fuzzy match margin {margin:.4f}"
    player_id = str(uuid.uuid5(NAMESPACE, f"player:{normalized}:{record.get('draftYear')}"))
    return player_id, "new_identity", 1.0, None


def quarantine(connection: duckdb.DuckDBPyConnection, snapshot_id: str, row_number: int, record: dict[str, Any], code: str, detail: str) -> None:
    key = str(uuid.uuid5(NAMESPACE, f"quarantine:{snapshot_id}:{row_number}:{code}"))
    connection.execute("""
        INSERT OR REPLACE INTO core.quarantine_player_record VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
    """, [key, snapshot_id, row_number, str(record.get("id", "")), normalize_name(str(record.get("name", ""))), code, detail, canonical_json(record), utc_now()])


def record_resolution(connection: duckdb.DuckDBPyConnection, snapshot_id: str, row_number: int, player_id: str | None, method: str, confidence: float, status: str, reason: str | None) -> None:
    event_id = str(uuid.uuid5(NAMESPACE, f"resolution:{snapshot_id}:{row_number}"))
    connection.execute("""
        INSERT OR REPLACE INTO core.identity_resolution_event VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [event_id, snapshot_id, row_number, player_id, method, confidence, status, reason, utc_now()])


def upsert_aliases(connection: duckdb.DuckDBPyConnection, player_id: str, record: dict[str, Any]) -> None:
    for source, identifier in source_identifiers(record):
        alias_id = str(uuid.uuid5(NAMESPACE, f"alias:{source}:{identifier}"))
        connection.execute("""
            INSERT INTO core.player_alias VALUES (?, ?, ?, ?, ?, ?, FALSE, ?, ?)
            ON CONFLICT(source_name, source_player_id) DO UPDATE SET
                alias_name = excluded.alias_name,
                normalized_name = excluded.normalized_name,
                player_id = excluded.player_id
        """, [alias_id, source, identifier, record["name"], normalize_name(record["name"]), player_id, "pipeline source alias", utc_now()])


def merge_scd(connection: duckdb.DuckDBPyConnection, table: str, id_column: str, natural_keys: dict[str, Any], attributes: dict[str, Any], effective_date: date, snapshot_id: str) -> str:
    where = " AND ".join(f"{column} = ?" for column in natural_keys)
    current = connection.execute(
        f"SELECT {id_column}, content_hash, valid_from FROM {table} WHERE {where} AND is_current = TRUE",
        list(natural_keys.values()),
    ).fetchone()
    row_hash = content_hash(attributes)
    if current and current[1] == row_hash:
        return "unchanged"
    if current:
        if effective_date <= current[2]:
            raise ValueError(f"out_of_order_scd:{table}:{natural_keys}:{effective_date}")
        connection.execute(
            f"UPDATE {table} SET valid_to = ?, is_current = FALSE WHERE {id_column} = ?",
            [effective_date - timedelta(days=1), current[0]],
        )
    version_key = canonical_json({"table": table, **natural_keys, "valid_from": effective_date.isoformat()})
    version_id = str(uuid.uuid5(NAMESPACE, version_key))
    columns = [id_column, *natural_keys, *attributes, "content_hash", "valid_from", "valid_to", "is_current", "source_snapshot_id"]
    values = [version_id, *natural_keys.values(), *attributes.values(), row_hash, effective_date, None, True, snapshot_id]
    placeholders = ", ".join("?" for _ in columns)
    connection.execute(f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})", values)
    return "updated" if current else "added"


def load_snapshot(connection: duckdb.DuckDBPyConnection, snapshot_path: Path, metrics: Metrics) -> tuple[str, str, date]:
    payload = retry(lambda: json.loads(snapshot_path.read_text(encoding="utf-8")), str(snapshot_path))
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"unsupported snapshot schema version: {payload.get('schema_version')}")
    if payload.get("source_policy") != "stored_fixture_only":
        raise ValueError("only policy-approved stored fixtures may enter the default pipeline")
    records = payload.get("records")
    if not isinstance(records, list):
        raise ValueError("snapshot records must be an array")
    checksum = content_hash(payload)
    source_name = str(payload["source_name"])
    effective_date = date.fromisoformat(payload["effective_date"])
    snapshot_id = str(uuid.uuid5(NAMESPACE, f"snapshot:{source_name}:{checksum}:{SCHEMA_VERSION}"))
    captured_at = datetime.fromisoformat(str(payload["captured_at"]).replace("Z", "+00:00"))
    exists = connection.execute("SELECT 1 FROM raw.source_snapshot WHERE snapshot_id = ?", [snapshot_id]).fetchone()
    if not exists:
        try:
            source_path = str(snapshot_path.resolve().relative_to(ROOT))
        except ValueError:
            source_path = str(snapshot_path.resolve())
        connection.execute("""
            INSERT INTO raw.source_snapshot VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [snapshot_id, source_name, captured_at, effective_date, checksum, SCHEMA_VERSION, source_path, len(records), utc_now()])

    seen: set[str] = set()
    metrics.records_fetched += len(records)
    for row_number, original in enumerate(records, start=1):
        record = dict(original)
        record["name"] = " ".join(str(record.get("name", "")).split())
        record["team"] = normalize_team(str(record.get("team", "")))
        record["position"] = normalize_position(str(record.get("position", "")))
        record["nationality"] = normalize_country(str(record.get("nationality", "")))
        record_key = str(record.get("nbaId") or record.get("espnId") or record.get("id") or normalize_name(record["name"]))
        if record_key in seen:
            metrics.duplicates_removed += 1
            quarantine(connection, snapshot_id, row_number, record, "duplicate_source_record", record_key)
            continue
        seen.add(record_key)
        record_hash = content_hash(record)
        connection.execute("""
            INSERT OR IGNORE INTO raw.player_record VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, [snapshot_id, row_number, source_name, str(record.get("id", "")), normalize_name(record["name"]), canonical_json(record), record_hash, utc_now()])
        reasons = validate_record(record)
        if reasons:
            metrics.quarantined_records += 1
            quarantine(connection, snapshot_id, row_number, record, "invalid_record", ",".join(reasons))
            record_resolution(connection, snapshot_id, row_number, None, "validation", 0.0, "quarantined", ",".join(reasons))
            continue
        player_id, method, confidence, reason = resolve_identity(connection, record)
        if player_id is None:
            metrics.unresolved_identities += 1
            metrics.quarantined_records += 1
            quarantine(connection, snapshot_id, row_number, record, "unresolved_identity", reason or method)
            record_resolution(connection, snapshot_id, row_number, None, method, confidence, "quarantined", reason)
            continue
        identity = connection.execute("SELECT 1 FROM core.player_identity WHERE player_id = ?", [player_id]).fetchone()
        if not identity:
            connection.execute("INSERT INTO core.player_identity VALUES (?, ?, ?, ?)", [player_id, record["name"], normalize_name(record["name"]), utc_now()])
        upsert_aliases(connection, player_id, record)
        record_resolution(connection, snapshot_id, row_number, player_id, method, confidence, "accepted", reason)

        player_state = merge_scd(connection, "core.player_history", "version_id", {"player_id": player_id}, {
            "name": record["name"], "draft_year": record.get("draftYear"), "position": record["position"],
            "country": record["nationality"], "continent": record.get("continent") or "Other",
            "height_inches": record["height"], "weight_pounds": record.get("weight"),
            "active": bool(record.get("active", True)),
        }, effective_date, snapshot_id)
        merge_scd(connection, "core.roster_history", "membership_id", {"player_id": player_id}, {
            "team_name": record["team"], "conference": record.get("conference") or "",
            "season_label": record.get("rosterSeason") or str(effective_date.year),
            "active": bool(record.get("active", True)),
        }, effective_date, snapshot_id)
        if record.get("twoKRating") is not None:
            merge_scd(connection, "core.rating_history", "rating_id", {"player_id": player_id, "rating_system": "NBA 2K"}, {
                "rating_value": float(record["twoKRating"]), "rank_value": record.get("rank"),
            }, effective_date, snapshot_id)
        if player_state == "added":
            metrics.records_added += 1
        elif player_state == "updated":
            metrics.records_updated += 1
        else:
            metrics.records_unchanged += 1
    return snapshot_id, source_name, effective_date


def run_command(command: list[str], label: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    LOG.info(canonical_json({"event": "command_started", "label": label, "command": command}))
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, env=env)
    if result.returncode:
        LOG.error(canonical_json({"event": "command_failed", "label": label, "stdout": result.stdout[-4000:], "stderr": result.stderr[-4000:]}))
        raise RuntimeError(f"{label} failed with exit code {result.returncode}")
    LOG.info(canonical_json({"event": "command_completed", "label": label}))
    return result


def run_dbt(db_path: Path, select: str | None = None) -> dict[str, int]:
    command = [str(ROOT / ".venv" / "bin" / "dbt"), "build", "--project-dir", "warehouse", "--profiles-dir", "warehouse"]
    if select:
        command.extend(["--select", select])
    environment = os.environ.copy()
    environment["DAILY_ROSTER_DB_PATH"] = str(db_path.resolve())
    run_command(command, f"dbt_build{':' + select if select else ''}", environment)
    run_results = json.loads((ROOT / "warehouse" / "target" / "run_results.json").read_text(encoding="utf-8"))
    statuses = [item.get("status") for item in run_results.get("results", [])]
    return {"passed": sum(status in {"success", "pass"} for status in statuses), "failed": sum(status in {"error", "fail"} for status in statuses)}


def deterministic_puzzles(connection: duckdb.DuckDBPyConnection, start: date, days: int, seed: str, run_id: str, dataset_version: str) -> None:
    candidates = connection.execute("SELECT player_id FROM analytics_analytics.mart_daily_puzzle_candidates ORDER BY player_id").fetchall()
    player_ids = [str(row[0]) for row in candidates]
    if not player_ids:
        raise ValueError("no eligible puzzle candidates")
    generated_at = utc_now()
    for offset in range(days):
        puzzle_date = start + timedelta(days=offset)
        digest, player_id = min((hashlib.sha256(f"{seed}:{puzzle_date}:{candidate}".encode()).hexdigest(), candidate) for candidate in player_ids)
        connection.execute("""
            INSERT INTO ops.daily_puzzle VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(puzzle_date) DO UPDATE SET
                player_id = excluded.player_id, seed = excluded.seed,
                selection_hash = excluded.selection_hash,
                generated_at = excluded.generated_at,
                dataset_version = excluded.dataset_version,
                source_run_id = excluded.source_run_id
        """, [puzzle_date, player_id, seed, digest, generated_at, dataset_version, run_id])


def export_products(connection: duckdb.DuckDBPyConnection, players_path: Path, puzzles_path: Path, report_path: Path) -> str:
    rows = connection.execute("SELECT * FROM analytics_analytics.mart_current_player_pool ORDER BY rank, name").fetchall()
    columns = [item[0] for item in connection.description]
    players = []
    for row in rows:
        item = dict(zip(columns, row))
        players.append({
            "id": item["game_player_id"], "rank": item["rank"], "allTimeRank": None,
            "currentRank": item["rank"], "name": item["name"], "draftYear": item["draft_year"],
            "position": item["position"], "conference": item["conference"], "team": item["team_name"],
            "teams": [{"team": item["team_name"], "games": item["games"]}],
            "nationality": item["country"], "continent": item["continent"],
            "height": item["height_inches"], "weight": item["weight_pounds"],
            "games": item["games"], "winShares": item["win_shares"],
            "currentWinShares": item["current_win_shares"], "nbaId": item["nba_id"],
            "espnId": item["espn_id"], "twoKRating": int(item["rating_value"]),
            "active": item["active"], "rosterSeason": item["season_label"],
        })
    players_path.parent.mkdir(parents=True, exist_ok=True)
    rendered_players = json.dumps(players, indent=2, ensure_ascii=False) + "\n"
    players_path.write_text(rendered_players, encoding="utf-8")
    version = hashlib.sha256(rendered_players.encode()).hexdigest()[:16]

    puzzle_rows = connection.execute("""
        SELECT CAST(puzzle_date AS VARCHAR), game_player_id, seed, selection_hash
        FROM analytics_analytics.fact_daily_puzzle ORDER BY puzzle_date
    """).fetchall()
    puzzles = [{"date": row[0], "playerId": row[1], "seed": row[2], "selectionHash": row[3]} for row in puzzle_rows]
    puzzles_path.parent.mkdir(parents=True, exist_ok=True)
    puzzles_path.write_text(json.dumps({"datasetVersion": version, "puzzles": puzzles}, indent=2) + "\n", encoding="utf-8")

    health = connection.execute("""
        SELECT COUNT(*) AS runs,
               SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) AS successful_runs,
               MAX(completed_at) AS latest_run
        FROM ops.pipeline_run
    """).fetchone()
    freshness = connection.execute("SELECT MAX(captured_at), COUNT(*), SUM(record_count) FROM raw.source_snapshot").fetchone()
    confidence = connection.execute("SELECT ROUND(AVG(confidence), 4), SUM(CASE WHEN resolution_status = 'quarantined' THEN 1 ELSE 0 END) FROM core.identity_resolution_event").fetchone()
    by_position = connection.execute("SELECT position, COUNT(*) FROM analytics_analytics.mart_current_player_pool GROUP BY 1 ORDER BY 2 DESC, 1").fetchall()
    report = [
        "# Daily Roster pipeline report", "",
        f"Generated: {utc_now().isoformat()}", "",
        "## Pipeline health", "",
        f"- Runs recorded: {health[0]}",
        f"- Successful runs: {health[1] or 0}",
        f"- Latest completed run: {health[2] or 'none'}",
        f"- Source snapshots: {freshness[1]}",
        f"- Source records: {freshness[2] or 0}",
        f"- Latest source capture: {freshness[0]}",
        f"- Mean identity confidence: {confidence[0] or 0}",
        f"- Quarantined identity events: {confidence[1] or 0}",
        f"- Current player pool: {len(players)}", f"- Scheduled puzzles: {len(puzzles)}",
        f"- Dataset version: `{version}`", "", "## Players by position", "",
        "| Position | Players |", "|---|---:|",
        *[f"| {position} | {count} |" for position, count in by_position], "",
        "The report is generated from DuckDB after dbt tests pass. Team, country, seasonal roster, rating-change, and puzzle-coverage detail remains queryable in the documented marts.",
    ]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(report) + "\n", encoding="utf-8")
    return version


def complete_run(connection: duckdb.DuckDBPyConnection, run_id: str, status: str, metrics: Metrics, started: float, error: str | None = None) -> None:
    connection.execute("""
        UPDATE ops.pipeline_run SET completed_at = ?, status = ?, metrics = ?,
            dataset_version = ?, error_message = ?, runtime_seconds = ? WHERE run_id = ?
    """, [utc_now(), status, canonical_json(metrics.as_dict()), metrics.dataset_version or None, error, round(time.monotonic() - started, 4), run_id])


def run_pipeline(snapshot_paths: Iterable[Path], db_path: Path, puzzle_start: date, puzzle_days: int, seed: str, run_game_tests: bool) -> Metrics:
    started = time.monotonic()
    run_id = str(uuid.uuid4())
    metrics = Metrics()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect(str(db_path))
    initialize_database(connection)
    connection.execute("INSERT INTO ops.pipeline_run VALUES (?, ?, NULL, 'running', ?, NULL, ?, NULL, NULL, NULL, ?)", [run_id, utc_now(), "stored_fixture", canonical_json(metrics.as_dict()), SCHEMA_VERSION])
    try:
        snapshots = []
        for snapshot_path in snapshot_paths:
            payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
            snapshots.append((date.fromisoformat(payload["effective_date"]), snapshot_path))
        last_snapshot_id = None
        for _, snapshot_path in sorted(snapshots):
            last_snapshot_id, _, _ = load_snapshot(connection, snapshot_path, metrics)
        connection.execute("UPDATE ops.pipeline_run SET snapshot_id = ? WHERE run_id = ?", [last_snapshot_id, run_id])
        connection.close()

        dbt_result = run_dbt(db_path)
        metrics.tests_passed += dbt_result["passed"]
        metrics.tests_failed += dbt_result["failed"]
        connection = duckdb.connect(str(db_path))
        provisional = content_hash(connection.execute("SELECT player_id, content_hash FROM core.player_history WHERE is_current ORDER BY player_id").fetchall())[:16]
        deterministic_puzzles(connection, puzzle_start, puzzle_days, seed, run_id, provisional)
        connection.close()

        puzzle_result = run_dbt(db_path, "fact_daily_puzzle")
        metrics.tests_passed += puzzle_result["passed"]
        metrics.tests_failed += puzzle_result["failed"]
        connection = duckdb.connect(str(db_path))
        metrics.dataset_version = export_products(connection, DEFAULT_PLAYERS, DEFAULT_PUZZLES, DEFAULT_REPORT)
        connection.execute("UPDATE ops.daily_puzzle SET dataset_version = ? WHERE source_run_id = ?", [metrics.dataset_version, run_id])
        if run_game_tests:
            node_bin = Path.home() / ".nvm" / "versions" / "node" / "v24.14.1" / "bin"
            npm = node_bin / "npm"
            environment = os.environ.copy()
            environment["PATH"] = f"{node_bin}:{environment.get('PATH', '')}"
            run_command([str(npm), "test"], "game_tests", environment)
            metrics.extra["game_tests"] = "passed"
        complete_run(connection, run_id, "success", metrics, started)
        LOG.info(canonical_json({"event": "pipeline_completed", "run_id": run_id, **metrics.as_dict()}))
        return metrics
    except Exception as error:
        try:
            complete_run(connection, run_id, "failed", metrics, started, str(error))
        except duckdb.ConnectionException:
            connection = duckdb.connect(str(db_path))
            complete_run(connection, run_id, "failed", metrics, started, str(error))
        LOG.exception(canonical_json({"event": "pipeline_failed", "run_id": run_id, "error": str(error)}))
        raise
    finally:
        try:
            connection.close()
        except Exception:
            pass


def snapshots_in_range(directory: Path, start: date | None, end: date | None) -> list[Path]:
    selected = []
    for path in sorted(directory.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        effective = date.fromisoformat(payload["effective_date"])
        if (start is None or effective >= start) and (end is None or effective <= end):
            selected.append(path)
    if not selected:
        raise ValueError("no snapshots matched the requested date range")
    return selected


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    snapshot = subparsers.add_parser("snapshot", help="wrap an approved local fixture in the versioned snapshot envelope")
    snapshot.add_argument("--input", required=True, type=Path)
    snapshot.add_argument("--output", required=True, type=Path)
    snapshot.add_argument("--captured-at", required=True)
    snapshot.add_argument("--effective-date", required=True)
    run = subparsers.add_parser("run", help="load snapshots, build/test dbt, schedule puzzles, and export the game dataset")
    run.add_argument("--snapshots", default=ROOT / "data" / "source_snapshots", type=Path)
    run.add_argument("--from-date", type=date.fromisoformat)
    run.add_argument("--to-date", type=date.fromisoformat)
    run.add_argument("--db", default=DEFAULT_DB, type=Path)
    run.add_argument("--puzzle-start", default=date.today(), type=date.fromisoformat)
    run.add_argument("--puzzle-days", default=90, type=int)
    run.add_argument("--seed", default="daily-roster-v1")
    run.add_argument("--skip-game-tests", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.command == "snapshot":
        create_snapshot(args.input, args.output, args.captured_at, args.effective_date)
        return 0
    paths = snapshots_in_range(args.snapshots, args.from_date, args.to_date)
    run_pipeline(paths, args.db, args.puzzle_start, args.puzzle_days, args.seed, not args.skip_game_tests)
    return 0


if __name__ == "__main__":
    sys.exit(main())
