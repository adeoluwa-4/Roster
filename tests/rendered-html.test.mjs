import assert from "node:assert/strict";
import { access, readFile } from "node:fs/promises";
import test from "node:test";

const root = new URL("../", import.meta.url);

async function render() {
  const workerUrl = new URL(`../dist/server/index.js?test=${process.pid}-${Date.now()}`, import.meta.url);
  const { default: worker } = await import(workerUrl.href);
  return worker.fetch(
    new Request("http://localhost/", { headers: { accept: "text/html", host: "localhost" } }),
    { ASSETS: { fetch: async () => new Response("Not found", { status: 404 }) } },
    { waitUntil() {}, passThroughOnException() {} },
  );
}

test("server-renders the Guess the NBA Player daily game", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);
  const html = await response.text();
  assert.match(html, /Guess the NBA Player/);
  assert.match(html, /KNOW THE/);
  assert.match(html, /PLAYER/);
  assert.match(html, /GUESSES/);
  assert.doesNotMatch(html, /codex-preview|react-loading-skeleton/i);
});

test("uses six athlete clues and excludes division and career tier", async () => {
  const page = await readFile(new URL("../app/page.tsx", import.meta.url), "utf8");
  for (const clue of ["Debut", "Position", "Conference", "Team", "Nationality", "Height"]) {
    assert.match(page, new RegExp(`\\[\"${clue}\"`));
  }
  assert.doesNotMatch(page, /\["Division"/);
  assert.doesNotMatch(page, /Career tier|\btier\b/i);
  assert.match(page, /next\.length === 10/);
  assert.match(page, /guess-athlete-v4-stats/);
  assert.match(page, /guess-nba-player-instructions-v1/);
  assert.match(page, /HOW TO PLAY/);
  assert.match(page, /role="dialog"/);
  assert.doesNotMatch(page, /One mystery player from the all-time 500/);
  assert.match(page, /if \(!player\) return null/);
  await assert.rejects(access(new URL("../app/_sites-preview/SkeletonPreview.tsx", import.meta.url)));
  await access(new URL("../public/og.png", import.meta.url));
  await access(new URL("../public/guess-the-athlete-logo.png", import.meta.url));
  await access(new URL("../public/guess-the-athlete-icon.png", import.meta.url));
});

test("uses the all-time 200 plus the complete current top 150", async () => {
  const players = JSON.parse(await readFile(new URL("../data/players.json", import.meta.url), "utf8"));
  assert.ok(players.length >= 200 && players.length <= 350);
  assert.equal(new Set(players.map(player => player.id)).size, players.length);
  assert.deepEqual(players.map(player => player.rank), Array.from({ length: players.length }, (_, index) => index + 1));
  const allTime = players.filter(player => player.allTimeRank !== null);
  const current = players.filter(player => player.currentRank !== null);
  assert.equal(allTime.length, 200);
  assert.equal(current.length, 150);
  assert.deepEqual(allTime.map(player => player.allTimeRank), Array.from({ length: 200 }, (_, index) => index + 1));
  assert.deepEqual([...current].sort((a, b) => a.currentRank - b.currentRank).map(player => player.currentRank), Array.from({ length: 150 }, (_, index) => index + 1));
  assert.ok(current.some(player => player.name === "Victor Wembanyama"));
  assert.ok(players.filter(player => player.active).length >= 150);
  const expectedCurrentTeams = {
    "LeBron James": "Philadelphia 76ers",
    "Kevin Durant": "Houston Rockets",
    "Giannis Antetokounmpo": "Miami Heat",
    "Luka Dončić": "Los Angeles Lakers",
    "Jimmy Butler": "Golden State Warriors",
  };
  for (const [name, team] of Object.entries(expectedCurrentTeams)) {
    const player = players.find(item => item.name === name);
    assert.equal(player?.team, team);
    assert.equal(player?.active, true);
    assert.equal(player?.rosterSeason, "2026-27");
  }
  for (const player of players) {
    assert.ok(player.name);
    assert.ok(Number.isInteger(player.nbaId) && player.nbaId > 0);
    assert.equal(typeof player.active, "boolean");
    assert.equal(player.rosterSeason, player.active ? "2026-27" : null);
    assert.ok(player.debut >= 1947);
    assert.ok(["East", "West"].includes(player.conference));
    assert.ok(player.team);
    assert.ok(player.teams.length >= 1);
    assert.equal(player.team, player.teams[0].team);
    assert.ok(player.height > 60);
    assert.ok(player.winShares > 0);
  }
});
