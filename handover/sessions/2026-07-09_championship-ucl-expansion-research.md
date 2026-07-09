# 2026-07-09 — Championship + Champions League expansion research

User confirmed EPL engine build will start soon, and wants Championship + Champions
League engines too. Asked for web research on how both differ and how the engine must
"skew" for each. Full research doc (with sources):
`BettingEngine/WorldCupEngine/ml/epl/LEAGUE_EXPANSION_RESEARCH.md`

## Headlines
- **Championship:** draw-heavy (~1 in 3), low-scoring (O2.5 sub-50%), stronger home
  advantage, and structurally distorted by parachute payments (relegated clubs 3× more
  likely to be promoted; £90m vs £27m average revenue). Understat does NOT cover it →
  goals-fed Dixon-Coles v1 (no xG, no PPDA/T2), football-data.co.uk E1 gives everything
  else incl. referee. The genuinely new component: a season-reset prior for the 6 new
  teams each year (ClubElo seed + parachute flag) — likely where the market edge lives.
- **UCL:** cross-league strength is the core problem — solve with ClubElo (free API) as
  the T1 backbone, domestic Understat xG as the form layer, blend weights flipped
  (Elo-primary). Only 8 league-phase games/team → price from imported domestic state.
  Swiss format thresholds (top-8 / top-24) need motivation flags; knockouts score below
  average and reuse the WorldCupEngine two-leg/ET/pens machinery.
- **Build order:** Championship (Aug) → UCL league phase (Sep) → UCL knockouts (Dec–Jan).
- **Engineering rule before starting:** refactor the EPL engine league-parameterised
  (one engine, N league configs) — don't fork three copies of price_match.py.

## Also this session (earlier)
- EPL engine smoke-tested on work machine ✅ (prices Arsenal–Chelsea, 4,180 matches,
  full tier stack). GW1-ready after the scripted August data refresh.
- EPL build diary confirmed missing from repo (home machine only) — noted in CLAUDE.md.
- BetMate + Odds API recorded as intentionally paused until ~2026-07-14 (payday).
