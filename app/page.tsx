"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import type { CSSProperties } from "react";
import playerData from "../data/players.json";

type Player = { id: string; rank: number; allTimeRank: number | null; currentRank: number | null; name: string; draftYear: number | null; position: string; conference: "East" | "West"; team: string; teams: Array<{ team: string; games: number }>; nationality: string; continent: string; height: number; weight: number; games: number; winShares: number; currentWinShares: number | null; nbaId: number | null; espnId: number | null; twoKRating: number; active: boolean; rosterSeason: string | null };
type Match = "exact" | "close" | "miss";

const players = playerData as Player[];
const storageKeys = {
  game: (date: string) => `guess-athlete-v5-game-${date}`,
  done: (date: string) => `guess-athlete-v5-done-${date}`,
  stats: "guess-athlete-v5-stats",
  last: "guess-athlete-v5-last",
  instructions: "guess-nba-player-instructions-v1",
};
const initials = (name: string) => name.split(/[ -]/).filter(Boolean).map(word => word[0]).slice(0,3).join("");
const height = (value: number) => `${Math.floor(value / 12)}'${value % 12}\"`;
const todayKey = () => new Date().toISOString().slice(0,10);
const puzzleNumberForDate = (date: string) => Math.floor((Date.parse(`${date}T00:00:00Z`) - Date.UTC(2026,0,1)) / 86400000) + 1;
const answerForDate = (date: string) => players[(puzzleNumberForDate(date) - 1 + players.length) % players.length];
const numeric = (guess: number, answer: number, range: number) => ({ state: (guess === answer ? "exact" : Math.abs(guess-answer) <= range ? "close" : "miss") as Match, arrow: guess === answer ? "" : answer > guess ? "↑" : "↓" });
const position = (guess: string, answer: string): Match => guess === answer ? "exact" : answer.split(" / ").some(part => guess.split(" / ").includes(part)) ? "close" : "miss";
const confettiPieces = Array.from({length:60},(_,index) => ({
  id: index,
  x: `${(index * 37) % 101}%`,
  drift: `${((index * 29) % 35) - 17}vw`,
  delay: `${(index % 12) * .045}s`,
  duration: `${2.25 + (index % 7) * .16}s`,
  color: ["#f4a72c","#5fa56d","#f3eddf","#d85d4a","#6fa8dc"][index % 5],
}));

function PlayerAvatar({ player, size = "standard" }: { player: Player; size?: "small" | "standard" | "large" }) {
  const src = player.nbaId
    ? `https://cdn.nba.com/headshots/nba/latest/260x190/${player.nbaId}.png`
    : player.espnId ? `https://a.espncdn.com/i/headshots/nba/players/full/${player.espnId}.png` : null;
  return <span className={`player-avatar avatar-${size}`} aria-hidden="true">
    <b>{initials(player.name)}</b>
    {src && <img src={src} alt="" loading="lazy" decoding="async" onError={event => { event.currentTarget.style.display = "none"; }} />}
  </span>;
}

function VictoryConfetti() {
  return <div className="confetti-burst" aria-hidden="true">{confettiPieces.map(piece => <i key={piece.id} style={{"--x":piece.x,"--drift":piece.drift,"--delay":piece.delay,"--duration":piece.duration,"--confetti":piece.color} as CSSProperties}/>)}</div>;
}

function draftClue(guess: number | null, answer: number | null) {
  if (guess === answer) return { state: "exact" as Match, arrow: "", hint: "Exact" };
  if (guess === null) return { state: "miss" as Match, arrow: "", hint: "Drafted" };
  if (answer === null) return { state: "miss" as Match, arrow: "", hint: "Undrafted" };
  const comparison = numeric(guess,answer,3);
  return { ...comparison, hint: comparison.arrow === "↑" ? "Later" : "Earlier" };
}

function clues(guess: Player, answer: Player) {
  const year = draftClue(guess.draftYear,answer.draftYear), size = numeric(guess.height,answer.height,2);
  return [
    ["Draft",guess.draftYear === null ? "Undrafted" : String(guess.draftYear),year.state,year.arrow,year.hint],
    ["Position",guess.position,position(guess.position,answer.position),"","Position"],
    ["Conference",guess.conference,guess.conference === answer.conference ? "exact" : "miss","","Conference"],
    ["Team",guess.team,guess.team === answer.team ? "exact" : "miss","","Team"],
    ["Nationality",guess.nationality,guess.nationality === answer.nationality ? "exact" : guess.continent === answer.continent ? "close" : "miss","",guess.continent === answer.continent ? "Same region" : "Different region"],
    ["Height",height(guess.height),size.state,size.arrow,size.arrow === "↑" ? "Taller" : "Shorter"],
  ] as Array<[string,string,Match,string,string]>;
}

export default function Home() {
  const today = useMemo(todayKey,[]);
  const puzzleNumber = useMemo(() => puzzleNumberForDate(today),[today]);
  const answer = useMemo(() => answerForDate(today),[today]);
  const [query,setQuery] = useState("");
  const [guesses,setGuesses] = useState<string[]>([]);
  const [status,setStatus] = useState<"playing"|"won"|"lost">("playing");
  const [open,setOpen] = useState(false);
  const [message,setMessage] = useState("");
  const [ready,setReady] = useState(false);
  const [stats,setStats] = useState({played:0,wins:0,streak:0});
  const [instructionsOpen,setInstructionsOpen] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  const instructionsClose = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    const game = localStorage.getItem(storageKeys.game(today)), savedStats = localStorage.getItem(storageKeys.stats);
    try {
      if (game) {
        const saved = JSON.parse(game);
        const validGuesses = Array.isArray(saved.guesses) ? saved.guesses.filter((id: unknown) => typeof id === "string" && players.some(player => player.id === id)) : [];
        setGuesses(validGuesses);
        if (["playing", "won", "lost"].includes(saved.status)) setStatus(saved.status);
      }
      if (savedStats) setStats(JSON.parse(savedStats));
    } catch {
      setGuesses([]); setStatus("playing"); setStats({played:0,wins:0,streak:0});
    }
    setReady(true);
  },[today]);
  useEffect(() => {
    if (!localStorage.getItem(storageKeys.instructions)) setInstructionsOpen(true);
  },[]);
  useEffect(() => {
    if (!instructionsOpen) return;
    const previousOverflow = document.body.style.overflow;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") closeInstructions();
    };
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown",onKeyDown);
    instructionsClose.current?.focus();
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown",onKeyDown);
    };
  },[instructionsOpen]);
  useEffect(() => { if (ready) localStorage.setItem(storageKeys.game(today),JSON.stringify({guesses,status})); },[ready,guesses,status,today]);
  useEffect(() => {
    if (!ready || status === "playing" || localStorage.getItem(storageKeys.done(today))) return;
    const previous = new Date(`${today}T00:00:00Z`); previous.setUTCDate(previous.getUTCDate()-1);
    const consecutive = localStorage.getItem(storageKeys.last) === previous.toISOString().slice(0,10);
    const next = { played: stats.played+1, wins: stats.wins+(status === "won" ? 1 : 0), streak: status === "won" ? (consecutive ? stats.streak+1 : 1) : 0 };
    setStats(next); localStorage.setItem(storageKeys.stats,JSON.stringify(next)); localStorage.setItem(storageKeys.last,today); localStorage.setItem(storageKeys.done(today),"1");
  },[ready,status,today,stats]);

  const suggestions = players.filter(player => query.trim() && player.name.toLowerCase().includes(query.toLowerCase()) && !guesses.includes(player.id)).slice(0,6);
  const pick = (player: Player) => {
    if (status !== "playing" || guesses.includes(player.id)) return;
    const next = [...guesses,player.id]; setGuesses(next); setQuery(""); setOpen(false); setMessage("");
    if (player.id === answer.id) setStatus("won"); else if (next.length === 10) setStatus("lost"); else setTimeout(() => input.current?.focus(),0);
  };
  const submit = (event: FormEvent) => { event.preventDefault(); const player = players.find(item => item.name.toLowerCase() === query.trim().toLowerCase()); if (player) pick(player); else { setMessage("Choose an athlete from the list."); setOpen(true); } };
  const closeInstructions = () => {
    localStorage.setItem(storageKeys.instructions,"seen");
    setInstructionsOpen(false);
    setTimeout(() => input.current?.focus(),0);
  };
  const share = async () => {
    const rows = guesses.flatMap(id => { const player = players.find(item => item.id === id); return player ? [clues(player,answer).map(clue => clue[2] === "exact" ? "🟩" : clue[2] === "close" ? "🟨" : "⬛").join("")] : []; });
    const score = status === "won" ? guesses.length : "X";
    const title = "Guess the NBA Player";
    const text = `${title} #${puzzleNumber} ${score}/10\n${rows.join("\n")}`;
    const url = window.location.origin;
    if (typeof navigator.share === "function") {
      try {
        await navigator.share({ title, text, url });
        setMessage("Result shared.");
        return;
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") return;
      }
    }
    try {
      await navigator.clipboard.writeText(`${text}\n\nPlay: ${url}`);
      setMessage("Result copied with the game link.");
    } catch {
      setMessage("Sharing is unavailable in this browser.");
    }
  };

  return <main className="site-shell">
    {status === "won" && <VictoryConfetti/>}
    <header className="topbar"><a className="brand" href="#game" aria-label="Guess the NBA Player home"><img className="brand-logo" src="/guess-the-athlete-logo.png" alt="Guess the NBA Player" /></a><div className="topbar-actions"><button className="how-to-play" onClick={() => setInstructionsOpen(true)}>HOW TO PLAY</button><div className="topbar-meta"><b>NBA EDITION</b><i />{today}</div></div></header>
    <section className="hero" id="game">
      <aside className="intro">
        <p className="eyebrow"><span />Today&apos;s challenge</p><h1>KNOW THE<br/><em>PLAYER.</em></h1>
        <div className="attempts"><strong>{String(10-guesses.length).padStart(2,"0")}</strong><span>GUESSES<br/>REMAINING</span></div>
        <div className="legend"><span><i className="exact"/>Exact</span><span><i className="close"/>Close</span><span><i className="miss"/>No match</span></div>
      </aside>
      <div className="game-column">
        {status === "playing" ? <div className="search-block">
          <label htmlFor="athlete">Guess an NBA athlete</label><form className="search-form" onSubmit={submit}>
            <input id="athlete" ref={input} value={query} onFocus={() => setOpen(true)} onChange={event => {setQuery(event.target.value);setOpen(true);setMessage("");}} placeholder="Type a player name..." autoComplete="off" aria-expanded={open && suggestions.length > 0}/><button>GUESS</button>
          </form>
          {open && suggestions.length > 0 && <ul className="suggestions">{suggestions.map(player => <li key={player.id}><button onClick={() => pick(player)}><PlayerAvatar player={player} size="small"/><span><strong>{player.name}</strong><small>{player.position} · {player.team}</small></span></button></li>)}</ul>}
          <p className={`message ${message ? "active" : ""}`} aria-live="polite">{message || "Start typing to search the player pool."}</p>
        </div> : <section className={`result ${status}`}>
          <p className="eyebrow"><span />{status === "won" ? "Buzzer beater" : "Final whistle"}</p><h2>{status === "won" ? "YOU GOT IT." : "NOT THIS TIME."}</h2>
          <div className="answer"><PlayerAvatar player={answer} size="large"/><span><small>Today&apos;s athlete</small><strong>{answer.name}</strong></span></div>
          <p>{status === "won" ? `Solved in ${guesses.length} ${guesses.length === 1 ? "guess" : "guesses"}. Game-winning knowledge.` : "Ten shots taken. Come back tomorrow for a fresh matchup."}</p><button onClick={share}>SHARE RESULT ↗</button>
          <div className="stats"><span><b>{stats.played}</b>Played</span><span><b>{stats.played ? Math.round(stats.wins/stats.played*100) : 0}%</b>Win rate</span><span><b>{stats.streak}</b>Streak</span></div><p className="message active">{message}</p>
        </section>}
        <div className="history">{guesses.length === 0 ? <div className="empty"><b>01</b><span><strong>TAKE YOUR FIRST SHOT</strong><p>Search the top 200 all time players and the current top 150 to reveal your first clues.</p></span></div> : [...guesses].reverse().map((id,index) => {
          const player = players.find(item => item.id === id); if (!player) return null; const number = guesses.length-index;
          return <article className="guess" key={id}><header><div className="player"><PlayerAvatar player={player}/><span><small>Guess {String(number).padStart(2,"0")}</small><h2>{player.name}</h2></span></div>{id === answer.id && <mark>CORRECT</mark>}</header>
            <div className="clues">{clues(player,answer).map(([label,value,state,arrow,hint]) => <div className={`clue ${state}`} key={label} aria-label={`${label}: ${value}, ${state}, ${hint}`}><small>{label}</small><strong>{value} {arrow && <b>{arrow}</b>}</strong><span>{state === "exact" ? "EXACT" : state === "close" ? "CLOSE" : hint.toUpperCase()}</span></div>)}</div>
          </article>;
        })}</div>
      </div>
    </section>
    <footer><p>Green is exact. Amber is close. Arrows point toward the mystery player.</p><span>GUESS THE NBA PLAYER · DAILY NBA TRIVIA</span></footer>
    {instructionsOpen && <div className="instructions-backdrop" onMouseDown={event => { if (event.target === event.currentTarget) closeInstructions(); }}>
      <section className="instructions" role="dialog" aria-modal="true" aria-labelledby="instructions-title">
        <header><p>HOW TO PLAY</p><button ref={instructionsClose} onClick={closeInstructions} aria-label="Close instructions">×</button></header>
        <h2 id="instructions-title">GUESS THE NBA PLAYER</h2>
        <p className="instructions-lead">Find the mystery NBA player in ten guesses.</p>
        <ol>
          <li>Type a player name and choose a result from the list.</li>
          <li>Each guess reveals draft year, position, conference, team, nationality, and height.</li>
          <li>Use the colors and arrows to guide your next guess.</li>
        </ol>
        <div className="instruction-example" aria-label="Clue color examples">
          <span className="exact"><b>GREEN</b><small>Exact match</small></span>
          <span className="close"><b>AMBER</b><small>Close match</small></span>
          <span className="miss"><b>GRAY</b><small>No match</small></span>
        </div>
        <p className="arrow-help"><strong>↑ ↓</strong> Arrows show whether the mystery player&apos;s draft year or height is higher or lower.</p>
        <div className="daily-note"><strong>A NEW PLAYER EVERY DAY</strong><p>Your stats and streak are saved on this device.</p></div>
        <button className="play-button" onClick={closeInstructions}>PLAY</button>
      </section>
    </div>}
  </main>;
}
