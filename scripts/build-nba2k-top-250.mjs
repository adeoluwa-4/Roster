#!/usr/bin/env node

import { readFile, writeFile } from "node:fs/promises";

const NBA_2K_ROSTER = "https://www.nba2klab.com/.netlify/functions/player-roster";
const NBA_PLAYERS = "https://raw.githubusercontent.com/swar/nba_api/master/src/nba_api/stats/library/data.py";
const ESPN_TEAMS = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams?limit=100";
const ESPN_ROSTER = (teamId) => `https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/${teamId}/roster`;
const ESPN_PROFILE = (athleteId) => `https://site.web.api.espn.com/apis/common/v3/sports/basketball/nba/athletes/${athleteId}`;
const output = new URL("../data/players.json", import.meta.url);
const existing = new URL("../data/players.json", import.meta.url);

const aliases = new Map([
  ["stephoncurry", "stephencurry"],
  ["tyresehaliburton", "tyresehaliburton"],
  ["domantatassabonis", "domantassabonis"],
  ["alperensengunun", "alperensengun"],
  ["lvicazubacac", "ivicazubac"],
  ["zacchararierisacher", "zaccharierisacher"],
  ["danielgaffford", "danielgafford"],
  ["bobbyportisjr", "bobbyportis"],
  ["alexandresarr", "alexsarr"],
  ["cameronthomas", "camthomas"],
  ["nicolasclaxton", "nicclaxton"],
  ["carltoncarrington", "bubcarrington"],
]);

const canonicalNames = new Map([
  ["ivicazubac", "Ivica Zubac"],
  ["zaccharierisacher", "Zaccharie Risacher"],
]);

const draftYears = new Map([
  ["ivicazubac", 2016], ["alexsarr", 2024], ["bobbyportis", 2015], ["camthomas", 2021],
  ["zaccharierisacher", 2024], ["jadenivey", 2022], ["nicolasclaxton", 2019], ["brandonclarke", 2019],
  ["bubcarrington", 2024], ["jonathankuminga", 2021], ["lonzoball", 2017], ["coleanthony", 2020],
  ["brucebrown", 2018], ["kellyolynyk", 2013], ["nickrichards", 2020], ["spencerdinwiddie", 2014],
  ["danteexum", 2014], ["masonplumlee", 2013], ["nicolasbatum", 2008],
]);

const eastTeams = new Set([
  "Atlanta Hawks", "Boston Celtics", "Brooklyn Nets", "Charlotte Hornets", "Chicago Bulls",
  "Cleveland Cavaliers", "Detroit Pistons", "Indiana Pacers", "Miami Heat", "Milwaukee Bucks",
  "New York Knicks", "Orlando Magic", "Philadelphia 76ers", "Toronto Raptors", "Washington Wizards",
]);

const normalize = (value) => {
  const key = value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[^a-z0-9]/gi, "").toLowerCase();
  return aliases.get(key) ?? key;
};

const slug = (value) => value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");
const position = (value) => [...new Set(value.split("|").map((item) => ({ PG: "Guard", SG: "Guard", SF: "Forward", PF: "Forward", C: "Center" })[item.trim()] ?? item.trim()).filter(Boolean))].join(" / ");
const height = (value) => {
  const match = value.match(/(\d+)'(\d+)/);
  if (!match) throw new Error(`Invalid NBA 2K height: ${value}`);
  return Number(match[1]) * 12 + Number(match[2]);
};
const draftYear = (value) => {
  const match = value?.match(/^(\d{4})/);
  return match ? Number(match[1]) : null;
};
const continent = (country) => {
  if (["Canada", "USA", "Bahamas", "Dominican Republic", "Jamaica", "Puerto Rico"].includes(country)) return "North America";
  if (["Australia", "New Zealand"].includes(country)) return "Oceania";
  if (["Argentina", "Brazil", "Venezuela", "Colombia"].includes(country)) return "South America";
  if (["Nigeria", "Cameroon", "Senegal", "Mali", "South Sudan", "DR Congo"].includes(country)) return "Africa";
  if (["China", "Japan", "Philippines", "Turkey", "Georgia", "Israel"].includes(country)) return "Asia";
  return "Europe";
};

async function fetchJson(url) {
  const response = await fetch(url, { headers: { "user-agent": "DailyRoster data update" } });
  if (!response.ok) throw new Error(`${response.status} from ${url}`);
  return response.json();
}

async function mapPool(items, fn, limit = 12) {
  const results = [];
  for (let index = 0; index < items.length; index += limit) {
    results.push(...await Promise.all(items.slice(index, index + limit).map(fn)));
  }
  return results;
}

const oldPlayers = JSON.parse(await readFile(existing, "utf8"));
const oldByName = new Map(oldPlayers.map((player) => [normalize(player.name), player]));
const nbaPlayersSource = await (await fetch(NBA_PLAYERS)).text();
const nbaIdByName = new Map([...nbaPlayersSource.matchAll(/\[(\d+),\s+"[^"]+",\s+"[^"]+",\s+"([^"]+)",\s+(?:True|False)\]/g)].map(([, id, name]) => [normalize(name), Number(id)]));
const ratings = await fetchJson(NBA_2K_ROSTER);
const top250 = ratings
  .sort((left, right) => right.rating - left.rating || `${left.first_name} ${left.last_name}`.localeCompare(`${right.first_name} ${right.last_name}`))
  .slice(0, 250);

const teams = await fetchJson(ESPN_TEAMS);
const espnRosters = await mapPool(teams.sports[0].leagues[0].teams, async ({ team }) => (await fetchJson(ESPN_ROSTER(team.id))).athletes);
const espnByName = new Map(espnRosters.flat().map((athlete) => [normalize(athlete.displayName), athlete]));
const profiles = await mapPool(top250, async (player) => {
  const athlete = espnByName.get(normalize(`${player.first_name} ${player.last_name}`));
  if (!athlete) return null;
  return [normalize(`${player.first_name} ${player.last_name}`), (await fetchJson(ESPN_PROFILE(athlete.id))).athlete];
});
const profileByName = new Map(profiles.filter(Boolean));

const players = top250.map((twoK, index) => {
  const sourceName = `${twoK.first_name} ${twoK.last_name}`;
  const key = normalize(sourceName);
  const previous = oldByName.get(key);
  const athlete = espnByName.get(key);
  const profile = profileByName.get(key);
  const name = athlete?.displayName ?? canonicalNames.get(normalize(sourceName)) ?? previous?.name ?? sourceName;
  const nationality = previous?.nationality ?? athlete?.birthPlace?.country ?? "USA";
  const team = twoK.team;
  return {
    id: slug(name),
    rank: index + 1,
    allTimeRank: null,
    currentRank: index + 1,
    name,
    draftYear: previous?.draftYear ?? draftYear(profile?.displayDraft) ?? draftYears.get(key) ?? null,
    position: position(twoK.position),
    conference: eastTeams.has(team) ? "East" : "West",
    team,
    teams: [{ team, games: previous?.teams?.[0]?.games ?? 0 }],
    nationality,
    continent: previous?.continent ?? continent(nationality),
    height: height(twoK.height),
    weight: twoK.weight,
    games: previous?.games ?? 0,
    winShares: previous?.winShares ?? 0,
    currentWinShares: previous?.currentWinShares ?? null,
    nbaId: previous?.nbaId ?? nbaIdByName.get(key) ?? null,
    espnId: athlete ? Number(athlete.id) : null,
    twoKRating: twoK.rating,
    active: true,
    rosterSeason: "2025-26",
  };
});

const unmatched = players.filter((player) => player.espnId === null);
if (players.length !== 250 || players.some((player) => !Number.isInteger(player.weight) || player.height < 60 || !player.position)) {
  throw new Error(`Invalid roster: ${players.length} players; ${unmatched.length} players did not have a current ESPN roster match.`);
}

await writeFile(output, `${JSON.stringify(players, null, 2)}\n`);
console.log(`Wrote ${players.length} NBA 2K top-rated active players. Rating floor: ${players.at(-1).twoKRating}. ${unmatched.length} players retain their previous data when available.`);
