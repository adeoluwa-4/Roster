#!/usr/bin/env python3
"""Build the all-time 500 plus the current NBA top 150 from historical CSV files."""

from __future__ import annotations

import argparse
import ast
import csv
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path


FRANCHISES = {
    "ATL": ("Atlanta Hawks", "East"), "STL": ("Atlanta Hawks", "East"),
    "MLH": ("Atlanta Hawks", "East"), "TRI": ("Atlanta Hawks", "East"),
    "BOS": ("Boston Celtics", "East"),
    "BRK": ("Brooklyn Nets", "East"), "NJN": ("Brooklyn Nets", "East"),
    "NYA": ("Brooklyn Nets", "East"), "NJA": ("Brooklyn Nets", "East"),
    "CHA": ("Charlotte Hornets", "East"), "CHO": ("Charlotte Hornets", "East"),
    "CHH": ("Charlotte Hornets", "East"),
    "CHI": ("Chicago Bulls", "East"), "CLE": ("Cleveland Cavaliers", "East"),
    "DET": ("Detroit Pistons", "East"), "FTW": ("Detroit Pistons", "East"),
    "IND": ("Indiana Pacers", "East"), "MIA": ("Miami Heat", "East"),
    "MIL": ("Milwaukee Bucks", "East"), "NYK": ("New York Knicks", "East"),
    "ORL": ("Orlando Magic", "East"),
    "PHI": ("Philadelphia 76ers", "East"), "SYR": ("Philadelphia 76ers", "East"),
    "TOR": ("Toronto Raptors", "East"),
    "WAS": ("Washington Wizards", "East"), "WSB": ("Washington Wizards", "East"),
    "CAP": ("Washington Wizards", "East"), "BAL": ("Washington Wizards", "East"),
    "CHZ": ("Washington Wizards", "East"), "CHP": ("Washington Wizards", "East"),
    "DAL": ("Dallas Mavericks", "West"),
    "DEN": ("Denver Nuggets", "West"), "DNR": ("Denver Nuggets", "West"),
    "GSW": ("Golden State Warriors", "West"), "SFW": ("Golden State Warriors", "West"),
    "PHW": ("Golden State Warriors", "West"),
    "HOU": ("Houston Rockets", "West"), "SDR": ("Houston Rockets", "West"),
    "LAC": ("LA Clippers", "West"), "SDC": ("LA Clippers", "West"),
    "BUF": ("LA Clippers", "West"),
    "LAL": ("Los Angeles Lakers", "West"), "MNL": ("Los Angeles Lakers", "West"),
    "MEM": ("Memphis Grizzlies", "West"), "VAN": ("Memphis Grizzlies", "West"),
    "MIN": ("Minnesota Timberwolves", "West"),
    "NOP": ("New Orleans Pelicans", "West"), "NOH": ("New Orleans Pelicans", "West"),
    "NOK": ("New Orleans Pelicans", "West"),
    "OKC": ("Oklahoma City Thunder", "West"), "SEA": ("Oklahoma City Thunder", "West"),
    "PHO": ("Phoenix Suns", "West"), "POR": ("Portland Trail Blazers", "West"),
    "SAC": ("Sacramento Kings", "West"), "KCK": ("Sacramento Kings", "West"),
    "KCO": ("Sacramento Kings", "West"), "CIN": ("Sacramento Kings", "West"),
    "ROC": ("Sacramento Kings", "West"),
    "SAS": ("San Antonio Spurs", "West"), "TEX": ("San Antonio Spurs", "West"),
    "DLC": ("San Antonio Spurs", "West"),
    "UTA": ("Utah Jazz", "West"), "NOJ": ("Utah Jazz", "West"),
}

EAST_LEGACY = {"BLB", "CHS", "DTF", "PIT", "PRO", "STB", "WSC", "NYN"}

COUNTRY_ALIASES = {
    "US": "USA", "United States": "USA", "U.S.": "USA",
    "Bosnia and Herzegovina": "Bosnia & Herzegovina",
    "Congo": "DR Congo",
    "Democratic Republic of the Congo": "DR Congo",
}

CONTINENTS = {
    "Africa": {"Cameroon", "DR Congo", "Egypt", "Gabon", "Ghana", "Guinea", "Mali", "Nigeria", "Senegal", "South Africa", "Sudan", "Tanzania"},
    "Asia": {"China", "Georgia", "Israel", "Japan", "Lebanon", "Philippines", "Turkey"},
    "Europe": {"Austria", "Belgium", "Bosnia & Herzegovina", "Bulgaria", "Croatia", "Czech Republic", "Finland", "France", "Germany", "Greece", "Italy", "Latvia", "Lithuania", "Montenegro", "Netherlands", "North Macedonia", "Poland", "Portugal", "Russia", "Serbia", "Slovenia", "Spain", "Sweden", "Switzerland", "Ukraine", "United Kingdom"},
    "North America": {"Bahamas", "Canada", "Cuba", "Dominican Republic", "Haiti", "Jamaica", "Mexico", "Panama", "Puerto Rico", "Trinidad and Tobago", "USA", "US Virgin Islands"},
    "Oceania": {"Australia", "New Zealand"},
    "South America": {"Argentina", "Brazil", "Colombia", "Uruguay", "Venezuela"},
}


def normalized(value: str) -> str:
    folded = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", folded.lower())


def player_id(name: str) -> str:
    folded = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", folded.lower()).strip("-")


def position_label(raw: str) -> str:
    try:
        values = ast.literal_eval(raw)
    except (SyntaxError, ValueError):
        values = [raw]
    labels = []
    for value in values:
        value = str(value).strip()
        if value and value not in labels:
            labels.append(value)
    return " / ".join(labels) or "Unknown"


def current_position_label(raw: str) -> str:
    labels = []
    for value in raw.split("-"):
        label = {"PG": "Guard", "SG": "Guard", "G": "Guard", "SF": "Forward", "PF": "Forward", "F": "Forward", "C": "Center"}.get(value.strip(), value.strip())
        if label and label not in labels:
            labels.append(label)
    return " / ".join(labels) or "Unknown"


def height_inches(raw: str) -> int:
    feet, inches = raw.split("-", 1)
    return int(feet) * 12 + int(inches)


def continent(country: str) -> str:
    for name, members in CONTINENTS.items():
        if country in members:
            return name
    return "North America" if country == "USA" else "Other"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--players", required=True, type=Path)
    parser.add_argument("--info", required=True, type=Path)
    parser.add_argument("--seasons", required=True, type=Path)
    parser.add_argument("--advanced", required=True, type=Path)
    parser.add_argument("--teams", required=True, type=Path)
    parser.add_argument("--output", default=Path("data/players.json"), type=Path)
    args = parser.parse_args()

    with args.players.open(newline="", encoding="utf-8-sig") as handle:
        candidates = list(csv.DictReader(handle))
    info_by_name = {}
    with args.info.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            info_by_name[normalized(row["DISPLAY_FIRST_LAST"])] = row

    latest_team_names = {}
    with args.teams.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            code = row["abbreviation"]
            season = int(row["season"])
            if code not in latest_team_names or season > latest_team_names[code][0]:
                latest_team_names[code] = (season, row["team"])

    games_by_player = defaultdict(lambda: defaultdict(int))
    with args.seasons.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            if row["lg"] not in {"NBA", "BAA"} or row["team"].endswith("TM"):
                continue
            try:
                games_by_player[normalized(row["player"])][row["team"]] += int(row["g"])
            except ValueError:
                continue

    current_rows = []
    with args.advanced.open(newline="", encoding="utf-8-sig") as handle:
        advanced_rows = [row for row in csv.DictReader(handle) if row["lg"] == "NBA" and row["ws"] not in {"", "NA"}]
    current_season = max(int(row["season"]) for row in advanced_rows)
    current_by_name = {}
    for row in advanced_rows:
        if int(row["season"]) != current_season:
            continue
        key = normalized(row["player"])
        score = (row["team"].endswith("TM"), float(row["ws"]), float(row.get("vorp") or 0), int(row["g"]))
        existing = current_by_name.get(key)
        if existing is None or score > existing[0]:
            current_by_name[key] = (score, row)
    current_rows = [value[1] for value in current_by_name.values()]
    current_rows.sort(key=lambda row: (-float(row["ws"]), -float(row.get("vorp") or 0), -int(row["g"]), row["player"]))
    current_top = current_rows[:150]
    current_rank = {normalized(row["player"]): rank for rank, row in enumerate(current_top, start=1)}
    current_stats = {normalized(row["player"]): row for row in current_top}

    eligible = [
        row for row in candidates
        if row["WS"] and row["Debut"] and row["Height"] and normalized(row["Name"]) in games_by_player
    ]
    eligible.sort(key=lambda row: (-float(row["WS"]), -int(row["G"]), row["Name"]))
    top = eligible[:500]
    candidates_by_name = {normalized(row["Name"]): row for row in candidates}

    output = []
    missing_country = []
    missing_teams = []
    for rank, row in enumerate(top, start=1):
        key = normalized(row["Name"])
        info = info_by_name.get(key, {})
        country = COUNTRY_ALIASES.get(info.get("COUNTRY", "").strip(), info.get("COUNTRY", "").strip())
        if not country:
            country = "USA"
            missing_country.append(row["Name"])

        team_games = sorted(games_by_player.get(key, {}).items(), key=lambda item: (-item[1], item[0]))
        if not team_games:
            missing_teams.append(row["Name"])
            team_games = [("UNK", 0)]
        career_teams = []
        seen = set()
        for code, games in team_games:
            label = FRANCHISES.get(code, (latest_team_names.get(code, (0, code))[1], ""))[0]
            if label in seen:
                existing = next(item for item in career_teams if item["team"] == label)
                existing["games"] += games
            else:
                career_teams.append({"team": label, "games": games})
                seen.add(label)
        career_teams.sort(key=lambda item: (-item["games"], item["team"]))
        team = career_teams[0]["team"]
        conference = next(
            (value[1] for value in FRANCHISES.values() if value[0] == team),
            "East" if team_games[0][0] in EAST_LEGACY else "West",
        )

        output.append({
            "id": player_id(row["Name"]),
            "rank": rank,
            "allTimeRank": rank,
            "currentRank": current_rank.get(key),
            "name": row["Name"],
            "debut": int(row["Debut"]),
            "position": position_label(row["Position"]),
            "conference": conference,
            "team": team,
            "teams": career_teams,
            "nationality": country,
            "continent": continent(country),
            "height": int(row["Height"]),
            "games": int(row["G"]),
            "winShares": float(row["WS"]),
            "currentWinShares": float(current_stats[key]["ws"]) if key in current_stats else None,
        })

    existing_ids = {player["id"] for player in output}
    for row in current_top:
        key = normalized(row["player"])
        identity = candidates_by_name.get(key)
        info = info_by_name.get(key, {})
        name = identity["Name"] if identity else row["player"]
        identifier = player_id(name)
        if identifier in existing_ids:
            continue

        country = COUNTRY_ALIASES.get(info.get("COUNTRY", "").strip(), info.get("COUNTRY", "").strip())
        if not country:
            country = "USA"
            missing_country.append(name)
        team_games = sorted(games_by_player.get(key, {}).items(), key=lambda item: (-item[1], item[0]))
        if not team_games:
            raise ValueError(f"Current top-150 player is missing team history: {name}")
        career_teams = []
        seen = set()
        for code, games in team_games:
            label = FRANCHISES.get(code, (latest_team_names.get(code, (0, code))[1], ""))[0]
            if label in seen:
                existing = next(item for item in career_teams if item["team"] == label)
                existing["games"] += games
            else:
                career_teams.append({"team": label, "games": games})
                seen.add(label)
        career_teams.sort(key=lambda item: (-item["games"], item["team"]))
        team = career_teams[0]["team"]
        conference = next(
            (value[1] for value in FRANCHISES.values() if value[0] == team),
            "East" if team_games[0][0] in EAST_LEGACY else "West",
        )
        if identity:
            debut = int(identity["Debut"])
            position = position_label(identity["Position"])
            height = int(identity["Height"])
            games = int(identity["G"])
            career_win_shares = float(identity["WS"])
        else:
            debut = int(float(info["FROM_YEAR"]))
            position = info.get("POSITION", "").strip() or current_position_label(row["pos"])
            height = height_inches(info["HEIGHT"])
            games = sum(games for _, games in team_games)
            career_win_shares = float(row["ws"])

        output.append({
            "id": identifier,
            "rank": len(output) + 1,
            "allTimeRank": None,
            "currentRank": current_rank[key],
            "name": name,
            "debut": debut,
            "position": position,
            "conference": conference,
            "team": team,
            "teams": career_teams,
            "nationality": country,
            "continent": continent(country),
            "height": height,
            "games": games,
            "winShares": career_win_shares,
            "currentWinShares": float(row["ws"]),
        })
        existing_ids.add(identifier)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(output)} players to {args.output}")
    print(f"All-time players: 500")
    print(f"Current-season top players represented: {len(current_rank)} ({current_season})")
    print(f"Country fallback (USA): {len(missing_country)}")
    print(f"Missing team history: {len(missing_teams)}")


if __name__ == "__main__":
    main()
