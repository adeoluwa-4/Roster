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

test("server-renders the ROSTER daily game", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);
  const html = await response.text();
  assert.match(html, /ROSTER/);
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
  assert.match(page, /localStorage\.setItem\("roster-stats"/);
  await assert.rejects(access(new URL("../app/_sites-preview/SkeletonPreview.tsx", import.meta.url)));
  await access(new URL("../public/og.png", import.meta.url));
});
