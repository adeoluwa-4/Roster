"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";

type Tier = "Legend" | "MVP" | "All-Star" | "Starter";
type Player = { id: string; name: string; debut: number; position: string; conference: "East" | "West"; team: string; nationality: string; continent: string; height: number; tier: Tier };
type Match = "exact" | "close" | "miss";

const rawPlayers: Array<[string, number, string, "East" | "West", string, string, string, number, Tier]> = [
  ["LeBron James",2003,"Forward","West","Lakers","USA","North America",81,"Legend"],
  ["Stephen Curry",2009,"Guard","West","Warriors","USA","North America",74,"MVP"],
  ["Kevin Durant",2007,"Forward","West","Rockets","USA","North America",83,"MVP"],
  ["Giannis Antetokounmpo",2013,"Forward","East","Bucks","Greece","Europe",83,"MVP"],
  ["Nikola Jokic",2015,"Center","West","Nuggets","Serbia","Europe",83,"MVP"],
  ["Luka Doncic",2018,"Guard / Forward","West","Lakers","Slovenia","Europe",78,"All-Star"],
  ["Jayson Tatum",2017,"Forward","East","Celtics","USA","North America",80,"All-Star"],
  ["Shai Gilgeous-Alexander",2018,"Guard","West","Thunder","Canada","North America",78,"MVP"],
  ["Anthony Edwards",2020,"Guard","West","Timberwolves","USA","North America",76,"All-Star"],
  ["Victor Wembanyama",2023,"Center / Forward","West","Spurs","France","Europe",88,"All-Star"],
  ["Joel Embiid",2016,"Center","East","76ers","Cameroon","Africa",84,"MVP"],
  ["Devin Booker",2015,"Guard","West","Suns","USA","North America",78,"All-Star"],
  ["Donovan Mitchell",2017,"Guard","East","Cavaliers","USA","North America",75,"All-Star"],
  ["Ja Morant",2019,"Guard","West","Grizzlies","USA","North America",74,"All-Star"],
  ["Jimmy Butler",2011,"Forward","West","Warriors","USA","North America",79,"All-Star"],
  ["Kawhi Leonard",2011,"Forward","West","Clippers","USA","North America",79,"All-Star"],
  ["Damian Lillard",2012,"Guard","East","Bucks","USA","North America",74,"All-Star"],
  ["Jalen Brunson",2018,"Guard","East","Knicks","USA","North America",74,"All-Star"],
  ["Bam Adebayo",2017,"Center","East","Heat","USA","North America",81,"All-Star"],
  ["Pascal Siakam",2016,"Forward","East","Pacers","Cameroon","Africa",80,"All-Star"],
  ["Karl-Anthony Towns",2015,"Center","East","Knicks","Dominican Republic","North America",84,"All-Star"],
  ["Trae Young",2018,"Guard","East","Hawks","USA","North America",73,"All-Star"],
  ["Paolo Banchero",2022,"Forward","East","Magic","USA","North America",82,"Starter"],
  ["Cade Cunningham",2021,"Guard","East","Pistons","USA","North America",78,"All-Star"],
  ["Michael Jordan",1984,"Guard","East","Bulls","USA","North America",78,"Legend"],
  ["Kobe Bryant",1996,"Guard","West","Lakers","USA","North America",78,"Legend"],
  ["Shaquille O'Neal",1992,"Center","West","Lakers","USA","North America",85,"Legend"],
  ["Magic Johnson",1979,"Guard","West","Lakers","USA","North America",81,"Legend"],
  ["Larry Bird",1979,"Forward","East","Celtics","USA","North America",81,"Legend"],
  ["Tim Duncan",1997,"Forward / Center","West","Spurs","US Virgin Islands","North America",83,"Legend"],
  ["Dirk Nowitzki",1998,"Forward","West","Mavericks","Germany","Europe",84,"Legend"],
  ["Hakeem Olajuwon",1984,"Center","West","Rockets","Nigeria","Africa",84,"Legend"],
  ["Steve Nash",1996,"Guard","West","Suns","Canada","North America",75,"Legend"],
  ["Yao Ming",2002,"Center","West","Rockets","China","Asia",90,"Legend"],
  ["Manu Ginobili",2002,"Guard","West","Spurs","Argentina","South America",78,"Legend"],
  ["Dwyane Wade",2003,"Guard","East","Heat","USA","North America",76,"Legend"],
];

const players: Player[] = rawPlayers.map(([name,debut,position,conference,team,nationality,continent,height,tier]) => ({ id: name.toLowerCase().replace(/[^a-z0-9]+/g,"-"), name,debut,position,conference,team,nationality,continent,height,tier }));
const tiers: Tier[] = ["Starter","All-Star","MVP","Legend"];
const initials = (name: string) => name.split(/[ -]/).filter(Boolean).map(word => word[0]).slice(0,3).join("");
const height = (value: number) => `${Math.floor(value / 12)}'${value % 12}\"`;
const todayKey = () => new Date().toISOString().slice(0,10);
const numeric = (guess: number, answer: number, range: number) => ({ state: (guess === answer ? "exact" : Math.abs(guess-answer) <= range ? "close" : "miss") as Match, arrow: guess === answer ? "" : answer > guess ? "↑" : "↓" });
const position = (guess: string, answer: string): Match => guess === answer ? "exact" : answer.split(" / ").some(part => guess.split(" / ").includes(part)) ? "close" : "miss";

function clues(guess: Player, answer: Player) {
  const year = numeric(guess.debut,answer.debut,3), size = numeric(guess.height,answer.height,2);
  const tierGap = Math.abs(tiers.indexOf(guess.tier)-tiers.indexOf(answer.tier));
  return [
    ["Debut",String(guess.debut),year.state,year.arrow,year.arrow === "↑" ? "Later" : "Earlier"],
    ["Position",guess.position,position(guess.position,answer.position),"","Position"],
    ["Conference",guess.conference,guess.conference === answer.conference ? "exact" : "miss","","Conference"],
    ["Team",guess.team,guess.team === answer.team ? "exact" : "miss","","Team"],
    ["Nationality",guess.nationality,guess.nationality === answer.nationality ? "exact" : guess.continent === answer.continent ? "close" : "miss","",guess.continent === answer.continent ? "Same region" : "Different region"],
    ["Height",height(guess.height),size.state,size.arrow,size.arrow === "↑" ? "Taller" : "Shorter"],
    ["Career tier",guess.tier,guess.tier === answer.tier ? "exact" : tierGap === 1 ? "close" : "miss","","Career tier"],
  ] as Array<[string,string,Match,string,string]>;
}

export default function Home() {
  const today = useMemo(todayKey,[]);
  const answer = players[(Math.floor((Date.parse(`${today}T00:00:00Z`)-Date.UTC(2026,0,1))/86400000)+players.length)%players.length];
  const [query,setQuery] = useState("");
  const [guesses,setGuesses] = useState<string[]>([]);
  const [status,setStatus] = useState<"playing"|"won"|"lost">("playing");
  const [open,setOpen] = useState(false);
  const [message,setMessage] = useState("");
  const [ready,setReady] = useState(false);
  const [stats,setStats] = useState({played:0,wins:0,streak:0});
  const input = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const game = localStorage.getItem(`roster-game-${today}`), savedStats = localStorage.getItem("roster-stats");
    if (game) { const saved = JSON.parse(game); setGuesses(saved.guesses); setStatus(saved.status); }
    if (savedStats) setStats(JSON.parse(savedStats));
    setReady(true);
  },[today]);
  useEffect(() => { if (ready) localStorage.setItem(`roster-game-${today}`,JSON.stringify({guesses,status})); },[ready,guesses,status,today]);
  useEffect(() => {
    if (!ready || status === "playing" || localStorage.getItem(`roster-done-${today}`)) return;
    const previous = new Date(`${today}T00:00:00Z`); previous.setUTCDate(previous.getUTCDate()-1);
    const consecutive = localStorage.getItem("roster-last") === previous.toISOString().slice(0,10);
    const next = { played: stats.played+1, wins: stats.wins+(status === "won" ? 1 : 0), streak: status === "won" ? (consecutive ? stats.streak+1 : 1) : 0 };
    setStats(next); localStorage.setItem("roster-stats",JSON.stringify(next)); localStorage.setItem("roster-last",today); localStorage.setItem(`roster-done-${today}`,"1");
  },[ready,status,today,stats]);

  const suggestions = players.filter(player => query.trim() && player.name.toLowerCase().includes(query.toLowerCase()) && !guesses.includes(player.id)).slice(0,6);
  const pick = (player: Player) => {
    if (status !== "playing" || guesses.includes(player.id)) return;
    const next = [...guesses,player.id]; setGuesses(next); setQuery(""); setOpen(false); setMessage("");
    if (player.id === answer.id) setStatus("won"); else if (next.length === 10) setStatus("lost"); else setTimeout(() => input.current?.focus(),0);
  };
  const submit = (event: FormEvent) => { event.preventDefault(); const player = players.find(item => item.name.toLowerCase() === query.trim().toLowerCase()); if (player) pick(player); else { setMessage("Choose an athlete from the list."); setOpen(true); } };
  const share = async () => {
    const rows = guesses.map(id => clues(players.find(player => player.id === id)!,answer).map(clue => clue[2] === "exact" ? "🟩" : clue[2] === "close" ? "🟨" : "⬛").join(""));
    try { await navigator.clipboard.writeText(`ROSTER ${today} ${status === "won" ? guesses.length : "X"}/10\n${rows.join("\n")}\n\nCan you name today's athlete?`); setMessage("Result copied — no spoilers."); } catch { setMessage("Sharing is unavailable in this browser."); }
  };

  return <main className="site-shell">
    <header className="topbar"><a className="brand" href="#game"><span>R</span>ROSTER</a><div className="topbar-meta"><b>NBA EDITION</b><i />{today}</div></header>
    <section className="hero" id="game">
      <aside className="intro">
        <p className="eyebrow"><span />Today&apos;s challenge</p><h1>KNOW THE<br/><em>PLAYER.</em></h1>
        <p className="intro-copy">One mystery NBA athlete. Seven clues per guess. Ten shots to find the name.</p>
        <div className="attempts"><strong>{String(10-guesses.length).padStart(2,"0")}</strong><span>GUESSES<br/>REMAINING</span></div>
        <div className="legend"><span><i className="exact"/>Exact</span><span><i className="close"/>Close</span><span><i className="miss"/>No match</span></div>
      </aside>
      <div className="game-column">
        {status === "playing" ? <div className="search-block">
          <label htmlFor="athlete">Guess an NBA athlete</label><form className="search-form" onSubmit={submit}>
            <input id="athlete" ref={input} value={query} onFocus={() => setOpen(true)} onChange={event => {setQuery(event.target.value);setOpen(true);setMessage("");}} placeholder="Type a player name..." autoComplete="off" aria-expanded={open && suggestions.length > 0}/><button>GUESS <span>↗</span></button>
          </form>
          {open && suggestions.length > 0 && <ul className="suggestions">{suggestions.map(player => <li key={player.id}><button onClick={() => pick(player)}><b>{initials(player.name)}</b><span><strong>{player.name}</strong><small>{player.position} · {player.team}</small></span></button></li>)}</ul>}
          <p className={`message ${message ? "active" : ""}`} aria-live="polite">{message || "Start typing to search the player pool."}</p>
        </div> : <section className={`result ${status}`}>
          <p className="eyebrow"><span />{status === "won" ? "Buzzer beater" : "Final whistle"}</p><h2>{status === "won" ? "YOU GOT IT." : "NOT THIS TIME."}</h2>
          <div className="answer"><b>{initials(answer.name)}</b><span><small>Today&apos;s athlete</small><strong>{answer.name}</strong></span></div>
          <p>{status === "won" ? `Solved in ${guesses.length} ${guesses.length === 1 ? "guess" : "guesses"}. Game-winning knowledge.` : "Ten shots taken. Come back tomorrow for a fresh matchup."}</p><button onClick={share}>COPY RESULT ↗</button>
          <div className="stats"><span><b>{stats.played}</b>Played</span><span><b>{stats.played ? Math.round(stats.wins/stats.played*100) : 0}%</b>Win rate</span><span><b>{stats.streak}</b>Streak</span></div><p className="message active">{message}</p>
        </section>}
        <div className="history">{guesses.length === 0 ? <div className="empty"><b>01</b><span><strong>TAKE YOUR FIRST SHOT</strong><p>Search any current star or NBA legend to reveal your first clues.</p></span></div> : [...guesses].reverse().map((id,index) => {
          const player = players.find(item => item.id === id)!; const number = guesses.length-index;
          return <article className="guess" key={id}><header><div className="player"><b>{initials(player.name)}</b><span><small>Guess {String(number).padStart(2,"0")}</small><h2>{player.name}</h2></span></div>{id === answer.id && <mark>CORRECT</mark>}</header>
            <div className="clues">{clues(player,answer).map(([label,value,state,arrow,hint]) => <div className={`clue ${state}`} key={label} aria-label={`${label}: ${value}, ${state}, ${hint}`}><small>{label}</small><strong>{value} {arrow && <b>{arrow}</b>}</strong><span>{state === "exact" ? "EXACT" : state === "close" ? "CLOSE" : hint.toUpperCase()}</span></div>)}</div>
          </article>;
        })}</div>
      </div>
    </section>
    <footer><p>Green is exact. Amber is close. Arrows point toward the mystery athlete.</p><span>ROSTER · DAILY NBA TRIVIA</span></footer>
  </main>;
}
