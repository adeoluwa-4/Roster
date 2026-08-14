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

test("uses six athlete clues, draft years, and victory confetti", async () => {
  const page = await readFile(new URL("../app/page.tsx", import.meta.url), "utf8");
  for (const clue of ["Draft", "Position", "Conference", "Team", "Nationality", "Height"]) {
    assert.match(page, new RegExp(`\\[\"${clue}\"`));
  }
  assert.doesNotMatch(page, /\["Division"/);
  assert.doesNotMatch(page, /Career tier|\btier\b/i);
  assert.match(page, /next\.length === 10/);
  assert.match(page, /guess-athlete-v5-stats/);
  assert.match(page, /guess-nba-player-instructions-v1/);
  assert.match(page, /HOW TO PLAY/);
  assert.match(page, /role="dialog"/);
  assert.match(page, /function VictoryConfetti/);
  assert.match(page, /status === "won" && <VictoryConfetti\/>/);
  assert.match(page, /guess\.draftYear === null \? "Undrafted"/);
  assert.match(page, /const puzzleNumber = useMemo\(\(\) => puzzleNumberForDate\(today\),\[today\]\)/);
  assert.match(page, /const text = `\$\{title\} #\$\{puzzleNumber\} \$\{score\}\/10\\n\$\{rows\.join\("\\n"\)\}`/);
  assert.match(page, /typeof navigator\.share === "function"/);
  assert.match(page, /await navigator\.share\(\{ title, text, url \}\)/);
  assert.match(page, /await navigator\.clipboard\.writeText\(`\$\{text\}\\n\\nPlay: \$\{url\}`\)/);
  assert.match(page, /SHARE RESULT ↗/);
  assert.doesNotMatch(page, /PlayerFilter|player-filter|Filter players by career status/);
  assert.doesNotMatch(page, /\bdebut\b/i);
  assert.doesNotMatch(page, /One mystery player from the all-time 500/);
  assert.match(page, /if \(!player\) return null/);
  await assert.rejects(access(new URL("../app/_sites-preview/SkeletonPreview.tsx", import.meta.url)));
  await access(new URL("../public/og.png", import.meta.url));
  await access(new URL("../public/guess-the-athlete-logo.png", import.meta.url));
  await access(new URL("../public/guess-the-athlete-icon.png", import.meta.url));
});

test("uses the NBA 2K top 250 active players", async () => {
  const players = JSON.parse(await readFile(new URL("../data/players.json", import.meta.url), "utf8"));
  assert.equal(players.length, 250);
  assert.equal(new Set(players.map(player => player.id)).size, players.length);
  assert.deepEqual(players.map(player => player.rank), Array.from({ length: players.length }, (_, index) => index + 1));
  const allTime = players.filter(player => player.allTimeRank !== null);
  const current = players.filter(player => player.currentRank !== null);
  assert.equal(allTime.length, 0);
  assert.equal(current.length, 250);
  assert.deepEqual(current.map(player => player.currentRank), Array.from({ length: 250 }, (_, index) => index + 1));
  assert.ok(current.some(player => player.name === "Victor Wembanyama"));
  assert.equal(players.filter(player => player.active).length, 250);
  const expectedTwoKValues = {
    "Nikola Jokic": { rating: 98, height: 83, weight: 284, position: "Center" },
    "Jayson Tatum": { rating: 94, height: 80, weight: 210, position: "Forward" },
    "LeBron James": { rating: 94, height: 81, weight: 250, position: "Forward" },
  };
  for (const [name, expected] of Object.entries(expectedTwoKValues)) {
    const player = players.find(item => item.name === name);
    assert.deepEqual(
      player && { rating: player.twoKRating, height: player.height, weight: player.weight, position: player.position },
      expected,
    );
  }
  for (const player of players) {
    assert.ok(player.name);
    assert.ok(Number.isInteger(player.nbaId) || Number.isInteger(player.espnId));
    assert.equal(typeof player.active, "boolean");
    assert.equal(player.rosterSeason, "2025-26");
    assert.ok(player.draftYear === null || (Number.isInteger(player.draftYear) && player.draftYear >= 1947 && player.draftYear <= 2025));
    assert.equal("debut" in player, false);
    assert.ok(["East", "West"].includes(player.conference));
    assert.ok(player.team);
    assert.ok(player.teams.length >= 1);
    assert.equal(player.team, player.teams[0].team);
    assert.ok(player.height > 60);
    assert.ok(Number.isInteger(player.weight) && player.weight > 100);
    assert.ok(Number.isInteger(player.twoKRating) && player.twoKRating >= 75);
  }
});
