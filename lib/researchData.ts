export type BetResult = 'win' | 'loss' | 'push';
export type Sport = 'NRL' | 'AFL' | 'FOOTBALL' | 'OTHER';

export interface LegacyBet {
  id: number;
  date?: string;         // ISO YYYY-MM-DD, only for section-2 bets (283+)
  match: string;
  market: string;
  odds: number | null;
  closingOdds: number | null;
  clv?: number | null;
  clvLabel?: string;
  result: BetResult;
  cumPL: number;
  sport: Sport;
  notes: string;
}

// NRL Betting Model tab — one row per bet with predicted line + CLV data
export interface ModelBet {
  id: number;
  date: string;
  match: string;
  market: string;
  predictedLine: number | null;  // model's predicted line or fair-odds estimate
  takenPrice: number | null;
  closingPrice: number | null;
  clv?: number | null;
  clvLabel?: string;
  result: BetResult;
  plUnits: number;               // individual bet P&L per unit staked
  runningTotal: number;          // cumulative P&L
}

function sport(raw: string | undefined): Sport {
  const s = (raw ?? '').toUpperCase().trim();
  if (s === 'NRL') return 'NRL';
  if (s === 'AFL') return 'AFL';
  if (s === 'FOOTBALL' || s === 'FOOTBAL') return 'FOOTBALL';
  return 'OTHER';
}

function result(raw: string): BetResult {
  const r = raw.toLowerCase().trim();
  if (r === 'win' || r === 'won' || r === 'win ') return 'win';
  if (r === 'loss' || r === 'lost' || r === 'lloss') return 'loss';
  return 'push';
}

// ─── Section 1: Legacy bets (rows 7-282) ────────────────────────────────────
// Inferred sport from team names / comments where not tagged.
// NRL teams: Cowboys, Tigers, Sea Eagles, Storm, Raiders, Roosters, Panthers,
//   Dragons, Knights, Bulldogs, Broncos/Broncoes, Sharks, Titans, Rabbitohs/Rabbitos,
//   Warriors, Dolphins, Eels, Manly, Souths, Canberra, Saints (NRL context)
// AFL teams: Dockers, Pies/Collingwood, Eagles, Saints (AFL), Crows/Adelaide,
//   Hawks/Hawthorn, Power/Port, Giants/GWS, Cats/Geelong, Lions/Brisbane,
//   Demons/Melbourne, Swans/Sydney, Richmond/Tigers (AFL), Bulldogs (AFL),
//   North Melbourne/Kangaroos, St Kilda, West Coast, Fremantle, Gold Coast Suns

export const LEGACY_BETS: LegacyBet[] = [
  { id:1, date:'2025-05-30',  match:'Cowboys vs Tigers',              market:'Total',             odds:1.9, closingOdds:null, result:'loss', cumPL:-1,    sport:'NRL',      notes:'Weather report changed — line drifted 2-3 points. Missed trading opportunity.' },
  { id:2, date:'2025-07-18',  match:'Sea Eagles vs Storm',            market:'Game',              odds:1.9,  closingOdds:null, result:'loss', cumPL:-2,    sport:'NRL',      notes:'Got the best of it at 1.9. Price came in heavily. Right bet.' },
  { id:3, date:'2025-07-19',  match:'Dockers vs Collingwood',         market:'Trade',             odds:1.9, closingOdds:null, result:'loss', cumPL:-3,    sport:'AFL',      notes:'Game ended in a draw. Should hedge with $2 on draw.' },
  { id:4, date:'2025-05-31',  match:'Raiders vs Roosters',            market:'Line',              odds:1.9, closingOdds:null, result:'loss', cumPL:-4,    sport:'NRL',      notes:'Blown out of the water.' },
  { id:5, date:'2025-03-20',  match:'Collingwood vs Bulldogs',        market:'Game (2.5 Dogs)',   odds:2.5,  closingOdds:null, result:'win',  cumPL:-3.85, sport:'AFL',      notes:'Traded off.' },
  { id:6, date:'2025-05-16',  match:'Warriors vs Dolphins',           market:'Game (Dolphins 1.7)', odds:1.7, closingOdds:null, result:'loss', cumPL:-4.85, sport:'NRL',     notes:'Had opportunity to hedge. Didnt.' },
  { id:7, date:'2025-05-16',  match:'Warriors vs Dolphins',           market:'Total Under',       odds:2.0, closingOdds:null, result:'win',  cumPL:-3.85, sport:'NRL',      notes:'Waited till 55th minute with 4-point buffer. Double-or-nothing in 2nd half.' },
  { id:8, date:'2025-06-25',  match:'Port vs Carlton',               market:'Total Under 170.5', odds:1.9, closingOdds:null, result:'loss', cumPL:-4.85, sport:'AFL',      notes:'Wind died. Monitor weather changes.' },
  { id:9, date:'2025-07-31',  match:'Hawthorn vs Adelaide',          market:'Game 2.3',          odds:2.3,  closingOdds:null, result:'win',  cumPL:-3.85, sport:'AFL',      notes:'Traded off.' },
  { id:10, date:'2025-06-22', match:'Roosters vs Cowboys',           market:'Handicap +19.5',    odds:2.0, closingOdds:null, result:'win',  cumPL:-2.85, sport:'NRL',      notes:'Good pick. May trade off.' },
  { id:11, date:'2025-06-22', match:'Roosters vs Cowboys',           market:'Game 7.20',         odds:7.2,  closingOdds:null, result:'win',  cumPL: 0.35, sport:'NRL',      notes:'Free bet.' },
  { id:12, date:'2025-06-22', match:'Roosters vs Cowboys',           market:'Total Under 53.5',  odds:2.0, closingOdds:null, result:'win',  cumPL: 1.35, sport:'NRL',      notes:'Easy money. Bog ground.' },
  { id:13, date:'2026-03-27', match:'Knights vs Bulldogs',           market:'Total Over 41.5',   odds:1.9, closingOdds:null, result:'loss', cumPL: 0.35, sport:'NRL',      notes:'Got the weather wrong. Rain didnt come.' },
  { id:14, date:'2026-04-25', match:'Eagles vs Saints',              market:'Total Over 153.5',  odds:1.9, closingOdds:null, result:'loss', cumPL:-0.65, sport:'AFL',      notes:'First quarter did it. Opportunity to trade out at 3/4 time.' },
  { id:15, date:'2026-04-25', match:'Eagles vs Saints',              market:'Game 1.8',          odds:1.8,  closingOdds:null, result:'win',  cumPL: 0.35, sport:'AFL',      notes:'Saints losing first half, came back well.' },
  { id:16, date:'2025-09-05', match:'Panthers vs Saints',            market:'Total Under 43.5',  odds:2.0, closingOdds:null, result:'win',  cumPL: 1.35, sport:'NRL',      notes:'Easy money. Raining.' },
  { id:17, date:'2025-05-02', match:'Dragons vs Tigers',             market:'Total Under 47.5',  odds:1.9, closingOdds:null, result:'loss', cumPL: 0.35, sport:'NRL',      notes:'Should have got off. Good playing surface.' },
  { id:18, date:'2025-06-07', match:'Eagles vs North Melbourne',     market:'Total Over 150.5 1.7', odds:1.7, closingOdds:null, result:'loss', cumPL:-0.65, sport:'AFL',   notes:'Right bet. West Coast could not kick straight.' },
  { id:19, date:'2025-06-21', match:'Broncos vs Sharks',             market:'Game +6.5',         odds:2.0, closingOdds:null, result:'win',  cumPL: 0.35, sport:'NRL',      notes:'Right bet. State of Origin hangover.' },
  { id:20, date:'2025-08-09', match:'Titans vs Rabbitohs',           market:'Total Under 55.5 1.83', odds:1.83, closingOdds:null, result:'push', cumPL: 0.35, sport:'NRL', notes:'Nearly got it.' },
  { id:21, date:'2025-05-03', match:'Cowboys vs Warriors',           market:'Game 2.3',          odds:2.3,  closingOdds:null, result:'win',  cumPL: 1.35, sport:'NRL',      notes:'Excellent bet. State of Origin hangover.' },
  { id:22, date:'2025-07-03', match:'Collingwood vs Carlton',        market:'Game 2.2',          odds:2.2,  closingOdds:null, result:'win',  cumPL: 2.35, sport:'AFL',      notes:'Traded off.' },
  { id:23, date:'2025-08-20', match:'Essendon vs Carlton',           market:'Game 2.6',          odds:2.6,  closingOdds:null, result:'loss', cumPL: 1.35, sport:'AFL',      notes:'Right bet. Too many bets overall — be more selective.' },
  { id:24, date:'2026-03-20', match:'Sharks vs Dolphins',            market:'Handicap +9.5',     odds:2.0, closingOdds:null, result:'win',  cumPL: 2.35, sport:'NRL',      notes:'Good bet.' },
  { id:25, date:'2025-09-06', match:'Tigers vs Titans',              market:'Total Under 51.5',  odds:1.9, closingOdds:null, result:'push', cumPL: 2.35, sport:'NRL',      notes:'Wait until at least half time. Must be a rule.' },
  { id:26, date:'2026-04-10', match:'Warriors vs Storm',             market:'Game 1.94',         odds:1.94, closingOdds:null, result:'win',  cumPL: 3.35, sport:'NRL',      notes:'Against the crowd. Only 50% of late money gets up.' },
  { id:28, date:'2025-05-23', match:'Kangaroos vs Collingwood',      market:'Handicap +38.5',    odds:1.9, closingOdds:null, result:'win',  cumPL: 3.35, sport:'AFL',      notes:'Should have waited. Dogs usually come in late.' },
  { id:29, date:'2025-06-06', match:'GWS vs Port Adelaide',          market:'Game 2.5',          odds:2.5,  closingOdds:null, result:'loss', cumPL: 2.35, sport:'AFL',      notes:'Fair bet. Could have laid off.' },
  { id:30, date:'2025-06-06', match:'GWS vs Port Adelaide',          market:'Total 1.85',        odds:1.85, closingOdds:null, result:'win',  cumPL: 3.35, sport:'AFL',      notes:'Good in-play bet. Both teams kicking behinds.' },
  { id:31, date:'2025-07-24', match:'GWS vs Sydney',                 market:'Half 2.25',         odds:2.25, closingOdds:null, result:'loss', cumPL: 2.35, sport:'AFL',      notes:'Injuries. Must factor in injury list going forward.' },
  { id:32, date:'2026-04-30', match:'Dolphins vs Storm',             market:'Game 2.83',         odds:2.83, closingOdds:null, result:'loss', cumPL: 1.35, sport:'NRL',      notes:'Right bet. Could have traded at half time if watching live.' },
  { id:33, date:'2025-08-15', match:'Roosters vs Bulldogs',          market:'Total Under 50.5',  odds:2.0, closingOdds:null, result:'win',  cumPL: 2.35, sport:'NRL',      notes:'Easy money.' },
  { id:34, date:'2026-04-16', match:'GWS vs Sydney',                 market:'Total Under 170.5', odds:1.9, closingOdds:null, result:'loss', cumPL: 1.35, sport:'AFL',      notes:'Right bet. Both teams kick extremely straight.' },
  { id:35, date:'2025-05-28', match:'Blues vs Maroons',              market:'Game 1.92',         odds:1.92, closingOdds:null, result:'win',  cumPL: 2.35, sport:'NRL',      notes:'Good bet.' },
  { id:36, date:'2026-04-18', match:'Brisbane vs Melbourne',         market:'Total Over 168.5',  odds:1.9, closingOdds:null, result:'loss', cumPL: 1.35, sport:'AFL',      notes:'Right bet. Need to figure out lay-off at quarter time.' },
  { id:37, date:'2025-06-28', match:'Warriors vs Broncos',           market:'Game 2.27',         odds:2.27, closingOdds:null, result:'win',  cumPL: 2.35, sport:'NRL',      notes:'Origin time.' },
  { id:38, date:'2025-07-02', match:'Kangaroos vs Bulldogs',         market:'Game 6.75',         odds:6.75, closingOdds:null, result:'loss', cumPL: 1.35, sport:'AFL',      notes:'Right bet. Could not get it over the line.' },
  { id:39, date:'2026-04-11', match:'Saints vs Port Adelaide',       market:'Game 2.24',         odds:2.24, closingOdds:null, result:'win',  cumPL: 2.35, sport:'AFL',      notes:'Must win for Power.' },
  { id:40, date:'2026-04-16', match:'Storm vs Canberra',             market:'Game 5',            odds:5,    closingOdds:null, result:'loss', cumPL: 1.35, sport:'NRL',      notes:'Right bet.' },
  { id:42, date:'2025-07-12', match:'Saints vs Sydney',              market:'Total Over 168.5',  odds:1.9, closingOdds:null, result:'loss', cumPL: 1.35, sport:'AFL',      notes:'Right bet. 4 points off.' },
  { id:43, date:'2026-04-15', match:'Collingwood vs Carlton',        market:'Game 2.12',         odds:2.12, closingOdds:null, result:'loss', cumPL: 0.35, sport:'AFL',      notes:'Pies in poor form.' },
  { id:44, date:'2026-04-15', match:'Collingwood vs Carlton',        market:'Game 2.6',          odds:2.6,  closingOdds:null, result:'win',  cumPL: 1.35, sport:'AFL',      notes:'Must win for Pies.' },
  { id:45, date:'2025-07-23', match:'Carlton vs Hawthorn',           market:'Game 2',            odds:2,    closingOdds:null, result:'loss', cumPL: 0.35, sport:'AFL',      notes:'Must win for Carlton. Hunch bet.' },
  { id:46, date:'2025-07-30', match:'GWS vs Bulldogs',               market:'Game 2.8',          odds:2.8,  closingOdds:null, result:'loss', cumPL:-0.65, sport:'AFL',      notes:'Did not look at the game well enough.' },
  { id:47, date:'2025-05-25', match:'Arsenal vs Southampton',        market:'Draw 5',            odds:5,    closingOdds:null, result:'loss', cumPL:-1.65, sport:'FOOTBALL', notes:'' },
  { id:48, date:'2025-08-23', match:'Man City vs Tottenham',         market:'Draw 5',            odds:5,    closingOdds:null, result:'loss', cumPL:-2.65, sport:'FOOTBALL', notes:'' },
  { id:49, date:'2026-04-17', match:'Port Adelaide vs Hawthorn',     market:'Game 3',            odds:3,    closingOdds:null, result:'win',  cumPL:-1.65, sport:'AFL',      notes:'' },
  { id:51, date:'2025-06-28', match:'Warriors vs Broncos',           market:'Game 3.1',          odds:3.1,  closingOdds:null, result:'win',  cumPL: 0.35, sport:'NRL',      notes:'' },
  { id:52, date:'2026-04-02', match:'Bulldogs vs Rabbitohs',         market:'Game 3.5',          odds:3.5,  closingOdds:null, result:'loss', cumPL:-0.65, sport:'NRL',      notes:'' },
  { id:53, date:'2026-04-24', match:'Roosters vs Dragons',           market:'Under 45.5',        odds:2,    closingOdds:1.95, result:'loss', cumPL:-1.65, sport:'NRL',      notes:'' },
  { id:54, date:'2026-05-02', match:'Panthers vs Manly',             market:'Under 46.5',        odds:2,    closingOdds:2,    result:'win',  cumPL:-0.65, sport:'NRL',      notes:'' },
  { id:55, date:'2025-04-26', match:'Carlton vs Geelong',            market:'Carlton +11.5',     odds:1.9,  closingOdds:null, result:'win',  cumPL: 0.35, sport:'AFL',      notes:'' },
  { id:56, date:'2025-04-26', match:'Canberra vs Dolphins',          market:'Dolphins +6.5',     odds:1.95, closingOdds:null, result:'loss', cumPL:-0.65, sport:'NRL',      notes:'' },
  { id:57, date:'2025-05-02', match:'Western Bulldogs vs Port Adelaide', market:'Port Adelaide 3.2', odds:3.2, closingOdds:null, result:'loss', cumPL:-1.65, sport:'AFL',  notes:'' },
  { id:58, date:'2025-05-02', match:'Geelong vs Collingwood',        market:'Geelong +11.5',     odds:1.9, closingOdds:null, result:'loss', cumPL:-2.65, sport:'AFL',      notes:'' },
  { id:59, date:'2025-05-03', match:'Sydney vs GWS',                 market:'Sydney 2.4',        odds:2.4,  closingOdds:null, result:'win',  cumPL:-1.65, sport:'AFL',      notes:'' },
  { id:60, date:'2025-05-03', match:'Brisbane vs Gold Coast',        market:'Gold Coast (trade)', odds:1.9, closingOdds:null, result:'loss', cumPL:-2.65, sport:'AFL',     notes:'' },
  { id:61, date:'2025-05-07', match:'Collingwood vs Fremantle',      market:'Collingwood',       odds:1.7,  closingOdds:1.8,  result:'win',  cumPL:-1.65, sport:'AFL',      notes:'Data proves 5-day turnaround not bad. 7.5% edge.' },
  { id:62, date:'2025-05-09', match:'Cowboys vs Panthers',           market:'Cowboys',           odds:2.3,  closingOdds:2.55, result:'push', cumPL:-1.65, sport:'NRL',      notes:'People overestimated Panthers. 7-10% edge.' },
  { id:63, date:'2025-05-10', match:'Richmond vs West Coast',        market:'Richmond',          odds:2.0, closingOdds:1.5,  result:'win',  cumPL:-0.65, sport:'AFL',      notes:'Full moon. 7.5% edge.' },
  { id:64, date:'2025-05-10', match:'North Melbourne vs Brisbane',   market:'Total Over 175',    odds:1.9, closingOdds:1.9,  result:'loss', cumPL:-1.65, sport:'AFL',      notes:'Full moon. 7.5% edge.' },
  { id:65, date:'2025-05-15', match:'Sydney vs Carlton',             market:'Total Under 163.5', odds:2.0, closingOdds:null, result:'win',  cumPL:-0.65, sport:'AFL',      notes:'' },
  { id:66, date:'2025-05-16', match:'Collingwood vs Adelaide',       market:'Adelaide +11.5',    odds:2.0, closingOdds:1.8,  result:'win',  cumPL: 0.35, sport:'AFL',      notes:'' },
  { id:67, date:'2025-05-16', match:'GWS vs Fremantle',              market:'Live Fremantle Win', odds:2.0, closingOdds:null, result:'win', cumPL: 1.35, sport:'AFL',       notes:'' },
  { id:68, date:'2025-05-17', match:'Tigers vs Rabbitohs',           market:'Total Under 45.5',  odds:2.0, closingOdds:null, result:'win',  cumPL: 2.35, sport:'NRL',      notes:'' },
  { id:69, date:'2025-05-17', match:'Broncos vs Dragons',            market:'Broncos +11.5',     odds:1.9, closingOdds:null, result:'loss', cumPL: 1.35, sport:'NRL',      notes:'Hunch bet. No more hunches — purely data driven.' },
  { id:70, date:'2025-05-21', match:'Geelong vs Bulldogs',           market:'BT -15 (2.5)',      odds:2.5,  closingOdds:null, result:'win',  cumPL: 2.35, sport:'AFL',      notes:'' },
  { id:71, date:'2025-05-21', match:'Bulldogs vs Dolphins',          market:'Total Under 44.5',  odds:1.9, closingOdds:null, result:'loss', cumPL: 1.35, sport:'NRL',      notes:'Drifted all week — get on right at the end when edge is in your favour.' },
  { id:72, date:'2025-05-23', match:'Penrith vs Newcastle',          market:'Total Under 44.5',  odds:2.0, closingOdds:null, result:'win',  cumPL: 2.35, sport:'NRL',      notes:'Comeback wins even from bad half-time position.' },
  { id:73, date:'2025-05-24', match:'Melbourne vs Sydney',           market:'Total Under 168.5', odds:1.9, closingOdds:null, result:'loss', cumPL: 1.35, sport:'AFL',      notes:'Game opened up after half time.' },
  { id:74, date:'2025-05-28', match:'QLD vs NSW',                    market:'QLD 2.23',          odds:2.23, closingOdds:null, result:'loss', cumPL: 0.35, sport:'NRL',      notes:'' },
  { id:75, date:'2025-05-30', match:'Titans vs Storm',               market:'Total Under 51.5',  odds:1.9,  closingOdds:null, result:'win',  cumPL: 1.35, sport:'NRL',      notes:'' },
  { id:76, date:'2025-05-30', match:'Cowboys vs Tigers',             market:'Total Over 49.5',   odds:1.9,  closingOdds:null, result:'win',  cumPL: 2.35, sport:'NRL',      notes:'' },
  { id:77, date:'2025-05-30', match:'Sydney vs Adelaide',            market:'Adelaide +5.5',     odds:1.9,  closingOdds:null, result:'win',  cumPL: 3.35, sport:'AFL',      notes:'' },
  { id:78, date:'2025-05-30', match:'Manly vs Brisbane',             market:'Manly',             odds:2.5,  closingOdds:null, result:'win',  cumPL: 5.35, sport:'NRL',      notes:'' },
  { id:79, date:'2025-05-31', match:'Titans vs Melbourne',           market:'Titans +13.5',      odds:1.9,  closingOdds:null, result:'win',  cumPL: 6.35, sport:'NRL',      notes:'Killing it!' },
  { id:80, date:'2025-05-31', match:'West Coast vs Geelong',         market:'Total Over 171.5',  odds:1.9,  closingOdds:null, result:'win',  cumPL: 7.35, sport:'AFL',      notes:'' },
  { id:81, date:'2025-05-31', match:'PSG vs Inter',                  market:'Inter',             odds:3.6,  closingOdds:null, result:'loss', cumPL: 6.35, sport:'FOOTBALL', notes:'' },
  { id:82, date:'2025-06-05', match:'Adelaide vs Brisbane',          market:'Total Under 158.5', odds:2.0, closingOdds:null, result:'win',  cumPL: 7.35, sport:'AFL',      notes:'' },
  { id:83, date:'2025-06-05', match:'Storm vs Cowboys',              market:'Cowboys +14.5',     odds:1.95, closingOdds:null, result:'loss', cumPL: 7.85, sport:'NRL',      notes:'' },
  { id:84, date:'2025-06-05', match:'Storm vs Cowboys',              market:'Total Over 51.5',   odds:2,    closingOdds:null, result:'win',  cumPL: 6.85, sport:'NRL',      notes:'' },
  { id:85, date:'2025-06-06', match:'Broncos vs Titans',             market:'Total Over 51.5',   odds:2.0, closingOdds:null, result:'win',  cumPL: 7.85, sport:'NRL',      notes:'' },
  { id:86, date:'2025-06-07', match:'Tigers vs Panthers',            market:'Total Under 47.5',  odds:2.0, closingOdds:null, result:'win',  cumPL: 8.85, sport:'NRL',      notes:'' },
  { id:87, date:'2025-06-08', match:'Eels vs Bulldogs',              market:'Total Under 46.5',  odds:1.9, closingOdds:null, result:'loss', cumPL: 7.85, sport:'NRL',      notes:'' },
  { id:88, date:'2025-06-08', match:'Melbourne vs Collingwood',      market:'Total Under 156.5', odds:1.5, closingOdds:null, result:'win',  cumPL: 8.35, sport:'AFL',      notes:'' },
  { id:89, date:'2025-06-08', match:'Melbourne vs Collingwood',      market:'Melbourne +23.5',   odds:2.0, closingOdds:null, result:'win',  cumPL: 9.35, sport:'AFL',      notes:'' },
  { id:90, date:'2025-06-11', match:'Western Bulldogs vs St Kilda',  market:'Bulldogs +24.5',    odds:1.9, closingOdds:null, result:'loss', cumPL: 8.35, sport:'AFL',      notes:'' },
  { id:91, date:'2025-06-12', match:'Hawthorn vs Adelaide',          market:'Hawthorn 1.83',     odds:1.83, closingOdds:null, result:'win',  cumPL: 9.35, sport:'AFL',      notes:'' },
  { id:92, date:'2025-06-13', match:'Brisbane vs GWS',               market:'Total Under 168.5', odds:1.9,  closingOdds:null, result:'loss', cumPL: 8.35, sport:'AFL',      notes:'' },
  { id:93, date:'2025-06-14', match:'Port Adelaide vs Melbourne',    market:'Either Team',       odds:2.45, closingOdds:null, result:'loss', cumPL: 7.35, sport:'AFL',      notes:'' },
  { id:94, date:'2025-06-14', match:'Rabbitohs vs Bulldogs',         market:'Rabbitohs +8.5',    odds:1.8,  closingOdds:null, result:'win',  cumPL: 8.35, sport:'NRL',      notes:'' },
  { id:95, date:'2025-06-18', match:'QLD vs NSW',                    market:'QLD 3.06',          odds:3.06, closingOdds:null, result:'win',  cumPL:10.35, sport:'NRL',      notes:'' },
  { id:96, date:'2025-06-18', match:'QLD vs NSW',                    market:'Total Under 41.5',  odds:1.9, closingOdds:null, result:'loss', cumPL: 9.35, sport:'NRL',      notes:'' },
  { id:97, date:'2025-06-19', match:'Geelong vs Brisbane',           market:'Brisbane 3',        odds:3,    closingOdds:null, result:'win',  cumPL:10.35, sport:'AFL',      notes:'' },
  { id:98, date:'2025-06-21', match:'Broncos vs Sharks',             market:'Under 48.5',        odds:1.9, closingOdds:null, result:'loss', cumPL: 9.35, sport:'NRL',      notes:'' },
  { id:99, date:'2025-06-20', match:'Port Adelaide vs Sydney',       market:'Under 168.5',       odds:1.9, closingOdds:null, result:'win',  cumPL:10.35, sport:'AFL',      notes:'' },
  { id:100, date:'2025-06-21',match:'Roosters vs Cowboys',           market:'Cowboys 3',         odds:3,    closingOdds:null, result:'loss', cumPL: 9.35, sport:'NRL',      notes:'' },
  { id:101, date:'2025-06-25',match:'Panthers vs Bulldogs',          market:'Total Under 42.5',  odds:1.9, closingOdds:null, result:'win',  cumPL:10.35, sport:'NRL',      notes:'' },
  { id:102, date:'2025-06-25',match:'Port Adelaide vs Carlton',      market:'Port Adelaide -4.5', odds:2.0, closingOdds:null, result:'win', cumPL:11.35, sport:'AFL',      notes:'' },
  { id:103, date:'2025-06-26',match:'Sydney vs Western Bulldogs',    market:'Bulldogs -9.5',     odds:1.9, closingOdds:null, result:'loss', cumPL:10.35, sport:'AFL',      notes:'' },
  { id:104, date:'2025-06-27',match:'Collingwood vs West Coast',     market:'Total Under 172.5', odds:2.0, closingOdds:null, result:'win',  cumPL:11.35, sport:'AFL',      notes:'' },
  { id:105, date:'2025-06-27',match:'Broncos vs Warriors',           market:'Warriors',          odds:2.5,  closingOdds:null, result:'loss', cumPL:10.35, sport:'NRL',      notes:'' },
  { id:106, date:'2025-06-28',match:'Titans vs Cowboys',             market:'Total Under 50.5',  odds:1.9, closingOdds:null, result:'loss', cumPL: 9.35, sport:'NRL',      notes:'' },
  { id:108, date:'2025-07-03',match:'Bulldogs vs Broncos',           market:'Bulldogs 1.4',      odds:1.4,  closingOdds:null, result:'loss', cumPL: 7.85, sport:'NRL',      notes:'' },
  { id:109, date:'2025-07-03',match:'Carlton vs Collingwood',        market:'Carlton +30.5',     odds:1.9,  closingOdds:null, result:'loss', cumPL: 6.85, sport:'AFL',      notes:'' },
  { id:110, date:'2025-07-04',match:'Geelong vs Richmond',           market:'Under 176.5',       odds:1.9,  closingOdds:null, result:'win',  cumPL: 7.85, sport:'AFL',      notes:'' },
  { id:111, date:'2025-07-05',match:'Sydney vs Fremantle',           market:'Fremantle +7.5',    odds:1.9,  closingOdds:null, result:'loss', cumPL: 6.85, sport:'AFL',      notes:'' },
  { id:112, date:'2025-07-05',match:'Cowboys vs Storm',              market:'Over 47.5',         odds:1.9,  closingOdds:null, result:'loss', cumPL: 5.85, sport:'NRL',      notes:'' },
  { id:113, date:'2025-07-06', match:'Manly vs South Sydney',         market:'Souths 3.75',       odds:3.75, closingOdds:null, result:'loss', cumPL: 4.85, sport:'NRL',      notes:'' },
  { id:114, date:'2025-07-09', match:'PSG vs Real Madrid',            market:'PSG 2.4',           odds:2.4,  closingOdds:null, result:'win',  cumPL: 6.25, sport:'FOOTBALL', notes:'' },
  { id:115, date:'2025-07-11',match:'Fremantle vs Hawthorn',         market:'Over 154.5',        odds:1.9,  closingOdds:null, result:'loss', cumPL: 5.25, sport:'AFL',      notes:'' },
  { id:116, date:'2025-07-11',match:'GWS vs Geelong',                market:'Under 171.5',       odds:1.9,  closingOdds:null, result:'loss', cumPL: 4.25, sport:'AFL',      notes:'' },
  { id:117, date:'2025-07-11',match:'GWS vs Geelong',                market:'Under 178.5',       odds:1.9,  closingOdds:null, result:'loss', cumPL: 3.25, sport:'AFL',      notes:'' },
  { id:118, date:'2025-07-12',match:'St Kilda vs Sydney',            market:'Under 167.5',       odds:1.9,  closingOdds:null, result:'loss', cumPL: 2.25, sport:'AFL',      notes:'' },
  { id:119, date:'2025-07-13', match:'PSG vs Chelsea',                market:'Plus 1',            odds:2,    closingOdds:null, result:'loss', cumPL: 1.25, sport:'FOOTBALL', notes:'' },
  { id:120, date:'2025-07-12',match:'Eels vs Panthers',              market:'Under 46.5',        odds:1.9,  closingOdds:null, result:'win',  cumPL: 2.25, sport:'NRL',      notes:'' },
  { id:121, date:'2025-07-12',match:'Titans vs Broncos',             market:'Over 51.5',         odds:1.9,  closingOdds:null, result:'loss', cumPL: 1.25, sport:'NRL',      notes:'' },
  { id:122, date:'2025-07-18',match:'Hawthorn vs Port Adelaide',     market:'Over 156.5',        odds:1.9,  closingOdds:null, result:'loss', cumPL: 0.25, sport:'AFL',      notes:'' },
  { id:123, date:'2025-07-18',match:'Carlton vs Melbourne',          market:'Under 165.5',       odds:1.9,  closingOdds:null, result:'win',  cumPL: 1.25, sport:'AFL',      notes:'' },
  { id:124, date:'2025-07-19',match:'Adelaide vs Gold Coast',        market:'Under 165.5',       odds:1.9,  closingOdds:null, result:'win',  cumPL: 2.25, sport:'AFL',      notes:'' },
  { id:125, date:'2025-07-23',match:'Hawthorn vs Carlton',           market:'Under 160.5',       odds:1.9,  closingOdds:null, result:'win',  cumPL: 3.25, sport:'AFL',      notes:'' },
  { id:126, date:'2025-07-24',match:'Broncos vs Parramatta',         market:'Over 47.5',         odds:1.9,  closingOdds:null, result:'loss', cumPL: 2.25, sport:'NRL',      notes:'Missed by 5 points.' },
  { id:127, date:'2026-03-27',match:'Panthers vs Eels',              market:'Under 47.5',        odds:1.9,  closingOdds:null, result:'win',  cumPL: 3.25, sport:'NRL',      notes:'' },
  { id:128, date:'2025-09-12',match:'Gold Coast vs Brisbane',        market:'Under 154.5',       odds:1.9,  closingOdds:null, result:'loss', cumPL: 2.25, sport:'AFL',      notes:'Rain came at half time, game mostly over by then.' },
  { id:129, date:'2026-04-30',match:'Adelaide vs Port Adelaide',     market:'Under 149.5',       odds:1.9,  closingOdds:null, result:'loss', cumPL: 1.25, sport:'AFL',      notes:'Windy and rainy yet game still wasnt a factor.' },
  { id:130, date:'2025-09-11',match:'Hawthorn vs Adelaide',          market:'Under 165.5',       odds:1.9,  closingOdds:null, result:'loss', cumPL: 0.25, sport:'AFL',      notes:'' },
  { id:131, date:'2025-09-19',match:'Collingwood vs Brisbane',       market:'Under 164.5',       odds:1.9,  closingOdds:null, result:'win',  cumPL: 1.25, sport:'AFL',      notes:'' },
  { id:132, date:'2026-04-24',match:'Fremantle vs Carlton',          market:'Under 159.5',       odds:1.9,  closingOdds:null, result:'loss', cumPL: 0.25, sport:'AFL',      notes:'' },
  { id:133, date:'2025-08-02',match:'Tigers vs Bulldogs',            market:'Under 42.5',        odds:1.9,  closingOdds:null, result:'win',  cumPL: 1.25, sport:'NRL',      notes:'' },
  { id:134, date:'2025-08-08',match:'Port Adelaide vs Fremantle',    market:'Under 166.5',       odds:1.9,  closingOdds:null, result:'loss', cumPL: 0.25, sport:'AFL',      notes:'' },
  { id:135, date:'2025-08-08',match:'Knights vs Panthers',           market:'Under 46.5',        odds:1.9,  closingOdds:null, result:'loss', cumPL:-0.75, sport:'NRL',      notes:'' },
  { id:136, date:'2025-08-14',match:'Fremantle vs Brisbane',         market:'Under 168.5',       odds:1.9,  closingOdds:null, result:'win',  cumPL: 0.25, sport:'AFL',      notes:'' },
  { id:137, date:'2025-08-17', match:'Chelsea vs Crystal Palace',     market:'Draw 4.2',          odds:4.2,  closingOdds:null, result:'loss', cumPL:-0.75, sport:'FOOTBALL', notes:'' },
  { id:138, date:'2025-08-17', match:'Man United vs Arsenal',         market:'Draw 3.4',          odds:3.4,  closingOdds:1.4,  result:'win',  cumPL: 1.75, sport:'FOOTBALL', notes:'' },
  { id:139, date:'2025-08-21',match:'Collingwood vs Melbourne',      market:'Under 165.5',       odds:1.9,  closingOdds:null, result:'win',  cumPL: 2.75, sport:'AFL',      notes:'' },
  { id:140, date:'2025-08-21',match:'Rabbitohs vs Dragons',          market:'Under 46.5',        odds:1.9,  closingOdds:null, result:'win',  cumPL: 3.75, sport:'NRL',      notes:'' },
  { id:141, date:'2025-08-21',match:'Penrith vs Raiders',            market:'Under 42.5',        odds:1.9,  closingOdds:null, result:'win',  cumPL: 4.75, sport:'NRL',      notes:'' },
  { id:142, date:'2025-08-24', match:'Crystal Palace vs Nottingham',  market:'Draw/Notts 1.7',    odds:1.7,  closingOdds:null, result:'win',  cumPL: 5.45, sport:'FOOTBALL', notes:'90 units in, 7.4% return. Goal is 15%.' },
  { id:143, date:'2025-08-30', match:'Man United vs Burnley',         market:'Man U 1.4',         odds:1.4,  closingOdds:null, result:'win',  cumPL: 5.85, sport:'FOOTBALL', notes:'' },
  { id:144, date:'2025-08-31', match:'Liverpool vs Arsenal',          market:'Liverpool 2.3',     odds:2.3,  closingOdds:1.3,  result:'win',  cumPL: 7.05, sport:'FOOTBALL', notes:'' },
  { id:145, date:'2025-08-30', match:'Leeds vs Newcastle',            market:'Draw/Leeds 1.8',    odds:1.8,  closingOdds:null, result:'win',  cumPL: 7.85, sport:'FOOTBALL', notes:'' },
  { id:146, date:'2025-09-03',match:'Adelaide vs Collingwood',       market:'Collingwood 2.4',   odds:2.4,  closingOdds:null, result:'win',  cumPL: 9.25, sport:'AFL',      notes:'' },
  { id:147, date:'2025-09-04',match:'Geelong vs Brisbane',           market:'Brisbane 2.3',      odds:2.3,  closingOdds:null, result:'loss', cumPL: 8.25, sport:'AFL',      notes:'' },
  { id:148, date:'2025-09-11',match:'Adelaide vs Hawthorn',          market:'Adelaide 1.9',      odds:1.9,  closingOdds:null, result:'loss', cumPL: 7.25, sport:'AFL',      notes:'' },
  { id:149, date:'2025-09-13',match:'Canberra vs Broncos',           market:'Line 2.5',          odds:1.9,  closingOdds:null, result:'loss', cumPL: 6.25, sport:'NRL',      notes:'' },
  { id:150, date:'2025-09-12',match:'Brisbane vs Gold Coast',        market:'Line 8.5',          odds:1.9,  closingOdds:null, result:'win',  cumPL: 7.25, sport:'AFL',      notes:'' },
  { id:151, date:'2025-09-12',match:'Warriors vs Panthers',          market:'Line 9.5',          odds:1.9,  closingOdds:null, result:'loss', cumPL: 6.25, sport:'NRL',      notes:'' },
  { id:152, date:'2025-09-17', match:'Liverpool vs Atletico Madrid',  market:'Liverpool 1.5',     odds:1.5,  closingOdds:null, result:'win',  cumPL: 6.75, sport:'FOOTBALL', notes:'' },
  { id:153, date:'2025-09-19',match:'Brisbane vs Collingwood',       market:'Under 163.5',       odds:1.9,  closingOdds:null, result:'loss', cumPL: 5.75, sport:'AFL',      notes:'Wet, new moon, final footie.' },
  { id:154, date:'2025-09-19',match:'Canberra vs Cronulla',          market:'Canberra 1.8',      odds:1.8,  closingOdds:null, result:'loss', cumPL: 4.75, sport:'NRL',      notes:'' },
  { id:155, date:'2025-09-20', match:'Liverpool vs Everton',          market:'Liverpool 1.5',     odds:1.5,  closingOdds:null, result:'win',  cumPL: 5.25, sport:'FOOTBALL', notes:'' },
  { id:156, date:'2025-09-21', match:'Bournemouth vs Newcastle',      market:'Bournemouth 2.45',  odds:2.45, closingOdds:1.45, result:'push', cumPL: 5.25, sport:'FOOTBALL', notes:'' },
  { id:157, date:'2025-09-21', match:'Arsenal vs Man City',           market:'Arsenal 1.95',      odds:1.95, closingOdds:null, result:'loss', cumPL: 4.25, sport:'FOOTBALL', notes:'' },
  { id:158, date:'2025-09-19',match:'Bulldogs vs Panthers',          market:'Bulldogs +8.5',     odds:1.95, closingOdds:null, result:'loss', cumPL: 3.25, sport:'NRL',      notes:'' },
  { id:159, date:'2025-09-27', match:'Liverpool vs Crystal Palace',   market:'Liverpool 1.9',     odds:1.9,  closingOdds:null, result:'loss', cumPL: 2.25, sport:'FOOTBALL', notes:'' },
  { id:161, date:'2025-09-27',match:'Broncos vs Panthers',           market:'Broncos 1.9',       odds:1.9,  closingOdds:null, result:'win',  cumPL:3.25, sport:'NRL',      notes:'' },
  { id:162, date:'2025-09-27',match:'Broncos vs Panthers',           market:'Under 49.5',        odds:1.9,  closingOdds:null, result:'win',  cumPL:4.15, sport:'NRL',      notes:'' },
  { id:164, date:'2025-10-04', match:'Leeds vs Tottenham',            market:'Win/Draw Leeds 3.4', odds:3.4, closingOdds:1.4,  result:'loss', cumPL:3.15, sport:'FOOTBALL', notes:'' },
  { id:165, date:'2025-10-04', match:'Liverpool vs Chelsea',          market:'Draw 3.8',          odds:3.8,  closingOdds:1.8,  result:'win',  cumPL:4.15, sport:'FOOTBALL', notes:'' },
  { id:166, date:'2026-04-18',match:'Brisbane vs Melbourne',         market:'Win 4.2',           odds:4.2,  closingOdds:null, result:'win',  cumPL:7.35, sport:'AFL',      notes:'Live bet.' },
  { id:167, date:'2025-10-05', match:'Brentford vs Man City',         market:'Draw 4.3',          odds:4.3,  closingOdds:1.3,  result:'loss', cumPL:6.35, sport:'FOOTBALL', notes:'' },
  { id:168, date:'2025-10-19', match:'Liverpool vs Man United',       market:'Liverpool 1.64',    odds:1.64, closingOdds:null, result:'loss', cumPL:5.35, sport:'FOOTBALL', notes:'' },
  { id:169, date:'2025-10-26', match:'Arsenal vs Crystal Palace',     market:'Draw 4.5',          odds:4.5,  closingOdds:null, result:'loss', cumPL:4.35, sport:'FOOTBALL', notes:'' },
  { id:171, date:'2025-10-26', match:'Everton vs Tottenham',          market:'Draw 3.5',          odds:3.5,  closingOdds:null, result:'loss', cumPL:2.35, sport:'FOOTBALL', notes:'' },
  { id:172, date:'2025-11-01', match:'Crystal Palace vs Brentford',   market:'Brentford 4',       odds:4,    closingOdds:1.6,  result:'loss', cumPL:1.35, sport:'FOOTBALL', notes:'' },
  { id:173, date:'2025-11-02', match:'West Ham vs Newcastle',         market:'Newcastle 1.7',     odds:1.7,  closingOdds:null, result:'loss', cumPL:0.35, sport:'FOOTBALL', notes:'' },
  { id:174, date:'2025-12-07', match:'West Ham vs Brighton',          market:'Draw 4.7',          odds:4.7,  closingOdds:3.7,  result:'win',  cumPL:4.05, sport:'FOOTBALL', notes:'' },
  { id:175, date:'2025-12-06', match:'Arsenal vs Aston Villa',        market:'Aston Villa 1.3',   odds:1.3,  closingOdds:2,    result:'win',  cumPL:6.05, sport:'FOOTBALL', notes:'' },
  { id:176, date:'2025-12-06', match:'Everton vs Nottm Forest',       market:'Everton 2',         odds:2,    closingOdds:1,    result:'win',  cumPL:7.05, sport:'FOOTBALL', notes:'' },
  { id:177, date:'2025-12-07', match:'Fulham vs Crystal Palace',      market:'Draw 2',            odds:2,    closingOdds:-1,   result:'loss', cumPL:6.05, sport:'FOOTBALL', notes:'' },
  { id:178, date:'2025-12-08', match:'Man United vs Wolves',          market:'Man U 1.8',         odds:1.8,  closingOdds:null, result:'win',  cumPL:6.85, sport:'FOOTBALL', notes:'' },
  { id:179, date:'2025-12-13', match:'Liverpool vs Brighton',         market:'Brighton/Draw 2',   odds:2,    closingOdds:null, result:'loss', cumPL:5.85, sport:'FOOTBALL', notes:'' },
  { id:181, date:'2025-12-14', match:'Sunderland vs Newcastle',       market:'Sunderland 3.3',    odds:3.3,  closingOdds:null, result:'win',  cumPL:7.15, sport:'FOOTBALL', notes:'' },
  { id:182, date:'2025-12-14', match:'Leeds vs Brentford',            market:'Over 2.5',          odds:1.9,  closingOdds:null, result:'loss', cumPL:6.15, sport:'FOOTBALL', notes:'' },
  { id:183, date:'2025-12-20', match:'Tottenham vs Liverpool',        market:'Liverpool 2.1',     odds:2.1,  closingOdds:null, result:'win',  cumPL:7.25, sport:'FOOTBALL', notes:'' },
  { id:184, date:'2025-12-20', match:'Wolves vs Brentford',           market:'Wolves 3.7',        odds:3.7,  closingOdds:null, result:'loss', cumPL:6.25, sport:'FOOTBALL', notes:'Wrong bet. Wolves playing terrible.' },
  { id:185, date:'2025-12-20', match:'Newcastle vs Chelsea',          market:'Newcastle 2.7',     odds:2.7,  closingOdds:null, result:'push', cumPL:6.25, sport:'FOOTBALL', notes:'' },
  { id:186, date:'2025-12-22', match:'Fulham vs Nottm Forest',        market:'Over 2.5',          odds:2.1,  closingOdds:null, result:'loss', cumPL:5.25, sport:'FOOTBALL', notes:'Wrong bet. Too many strikers out.' },
  { id:187, date:'2025-12-20', match:'Leeds vs Crystal Palace',       market:'Crystal Palace 2.94', odds:2.94, closingOdds:null, result:'loss', cumPL:4.25, sport:'FOOTBALL', notes:'' },
  { id:188, date:'2025-12-21', match:'Aston Villa vs Man United',     market:'Over 2.5',          odds:1.7,  closingOdds:null, result:'win',  cumPL:4.95, sport:'FOOTBALL', notes:'' },
  { id:189, date:'2025-12-27', match:'Man City vs Nottm Forest',      market:'Under 2.5',         odds:2.2,  closingOdds:null, result:'loss', cumPL:3.95, sport:'FOOTBALL', notes:'' },
  { id:190, date:'2025-12-26', match:'Man United vs Newcastle',       market:'Draw No Bet 2.25',  odds:2.25, closingOdds:null, result:'win',  cumPL:4.95, sport:'FOOTBALL', notes:'' },
  { id:191, date:'2025-12-27', match:'Liverpool vs Wolves',           market:'Over 3.5',          odds:1.8,  closingOdds:null, result:'loss', cumPL:3.95, sport:'FOOTBALL', notes:'' },
  { id:192, date:'2025-12-28', match:'Sunderland vs Leeds',           market:'Sunderland +0',     odds:1.9,  closingOdds:null, result:'push', cumPL:3.95, sport:'FOOTBALL', notes:'' },
  { id:193, date:'2026-03-03', match:'Burnley vs Everton',            market:'Under 2.5',         odds:1.75, closingOdds:null, result:'win',  cumPL:4.7,  sport:'FOOTBALL', notes:'' },
  { id:194, date:'2025-12-27', match:'Chelsea vs Aston Villa',        market:'Aston Villa/Draw 2.25', odds:2.25, closingOdds:null, result:'win', cumPL:5.7, sport:'FOOTBALL', notes:'' },
  { id:195, date:'2025-12-27', match:'Chelsea vs Aston Villa',        market:'Over 2.5',          odds:1.8,  closingOdds:null, result:'win',  cumPL:6.5,  sport:'FOOTBALL', notes:'' },
  { id:196, date:'2025-12-28', match:'Crystal Palace vs Tottenham',   market:'Crystal Palace +0', odds:1.7,  closingOdds:null, result:'loss', cumPL:5.5,  sport:'FOOTBALL', notes:'' },
  { id:197, date:'2025-12-28', match:'Crystal Palace vs Tottenham',   market:'Crystal Palace/Draw 2', odds:2, closingOdds:null, result:'loss', cumPL:4.5, sport:'FOOTBALL', notes:'' },
  { id:198, date:'2025-12-30', match:'Chelsea vs Bournemouth',        market:'Draw/Chelsea 4.6',  odds:4.6,  closingOdds:null, result:'win',  cumPL:5.5,  sport:'FOOTBALL', notes:'' },
  { id:199, date:'2025-12-30', match:'Nottm Forest vs Everton',       market:'Draw/Everton 3.45', odds:3.45, closingOdds:null, result:'win',  cumPL:6.5,  sport:'FOOTBALL', notes:'' },
  { id:200, date:'2025-12-30', match:'Nottm Forest vs Everton',       market:'Under 2.5',         odds:1.75, closingOdds:null, result:'win',  cumPL:7.25, sport:'FOOTBALL', notes:'' },
  { id:201, date:'2025-12-06', match:'Arsenal vs Aston Villa',        market:'Draw/Aston Villa',  odds:5,    closingOdds:null, result:'win',  cumPL:6.25, sport:'FOOTBALL', notes:'' },
  { id:202, date:'2025-12-06', match:'Arsenal vs Aston Villa',        market:'BTTS 2.2',          odds:2.2,  closingOdds:null, result:'win',  cumPL:8.45, sport:'FOOTBALL', notes:'' },
  { id:203, date:'2025-12-06', match:'Liverpool vs Leeds',            market:'Liverpool 1.5',     odds:1.5,  closingOdds:null, result:'loss', cumPL:7.45, sport:'FOOTBALL', notes:'Should not have bet this game.' },
  { id:204, date:'2026-01-01', match:'Crystal Palace vs Fulham',      market:'Crystal Palace 2.2', odds:2.2, closingOdds:null, result:'loss', cumPL:6.45, sport:'FOOTBALL', notes:'Should not have bet this game.' },
  { id:205, date:'2026-01-03', match:'Aston Villa vs Nottm Forest',   market:'Draw 2',            odds:2,    closingOdds:null, result:'loss', cumPL:5.45, sport:'FOOTBALL', notes:'' },
  { id:206, date:'2026-01-03', match:'Aston Villa vs Nottm Forest',   market:'Under 2.5',         odds:2.1,  closingOdds:null, result:'loss', cumPL:4.45, sport:'FOOTBALL', notes:'' },
  { id:207, date:'2026-01-03', match:'Brighton vs Burnley',           market:'Draw 3',            odds:3,    closingOdds:null, result:'loss', cumPL:3.45, sport:'FOOTBALL', notes:'' },
  { id:208, date:'2026-01-03', match:'Brighton vs Burnley',           market:'Under 2.5',         odds:2.25, closingOdds:null, result:'win',  cumPL:4.7,  sport:'FOOTBALL', notes:'' },
  { id:209, date:'2026-01-03', match:'Bournemouth vs Arsenal',        market:'Draw/Arsenal 2',    odds:2,    closingOdds:null, result:'push', cumPL:4,  sport:'FOOTBALL', notes:'' },
  { id:210, date:'2026-01-03', match:'Bournemouth vs Arsenal',        market:'Over 3.5 Cards 1.5', odds:1.5, closingOdds:null, result:'win',  cumPL:4.5,  sport:'FOOTBALL', notes:'' },
  { id:211, date:'2026-01-04', match:'Man United vs Leeds',           market:'Draw 2',            odds:2,    closingOdds:null, result:'win',  cumPL:6.5,  sport:'FOOTBALL', notes:'' },
  { id:212, date:'2026-01-04', match:'Man United vs Leeds',           market:'Over 3.5 Cards 1.5', odds:1.5, closingOdds:null, result:'loss', cumPL:5.5, sport:'FOOTBALL',  notes:'' },
  { id:213, date:'2026-01-04', match:'Man City vs Chelsea',           market:'Draw 3',            odds:3,    closingOdds:null, result:'win',  cumPL:7.5,  sport:'FOOTBALL', notes:'' },
  { id:214, date:'2026-01-04', match:'Man City vs Chelsea',           market:'Over 3.5 Cards 1.5', odds:1.5, closingOdds:null, result:'win', cumPL:8,  sport:'FOOTBALL', notes:'' },
  { id:215, date:'2026-01-04', match:'Tottenham vs Sunderland',       market:'BTTS No 2',         odds:2,    closingOdds:null, result:'loss', cumPL:7,  sport:'FOOTBALL', notes:'' },
  { id:216, date:'2026-01-04', match:'Crystal Palace vs Newcastle',   market:'Draw 2',            odds:2,    closingOdds:null, result:'push', cumPL:6.5,  sport:'FOOTBALL', notes:'' },
  { id:217, date:'2026-01-07', match:'Everton vs Wolves',             market:'Draw 1.8',          odds:1.8,  closingOdds:null, result:'win',  cumPL:8.3,  sport:'FOOTBALL', notes:'' },
  { id:218, date:'2026-01-07', match:'Everton vs Wolves',             market:'Under 2.5 Goals 1.8', odds:1.8, closingOdds:null, result:'win', cumPL:10.1, sport:'FOOTBALL', notes:'' },
  { id:219, date:'2026-01-07', match:'Crystal Palace vs Aston Villa', market:'Draw/Crystal Palace 1.8', odds:1.8, closingOdds:null, result:'win', cumPL:11.9, sport:'FOOTBALL', notes:'' },
  { id:220, date:'2026-01-07', match:'Crystal Palace vs Aston Villa', market:'Under 2.5',         odds:1.95, closingOdds:null, result:'win',  cumPL:13.85, sport:'FOOTBALL', notes:'' },
  { id:221, date:'2026-01-08', match:'Arsenal vs Liverpool',          market:'Draw 2.5',          odds:2.5,  closingOdds:null, result:'win',  cumPL:16.35, sport:'FOOTBALL', notes:'' },
  { id:222, date:'2026-01-17', match:'Man United vs Man City',        market:'Under 3.5',         odds:1.7,  closingOdds:null, result:'win',  cumPL:18,  sport:'FOOTBALL', notes:'' },
  { id:223, date:'2026-01-17', match:'Man United vs Man City',        market:'Under 3.5 Cards 2.2', odds:2.2, closingOdds:null, result:'loss', cumPL:17, sport:'FOOTBALL', notes:'' },
  { id:224, date:'2026-01-17', match:'Sunderland vs Crystal Palace',  market:'Penalty Awarded 4.5', odds:4.5, closingOdds:null, result:'loss', cumPL:16, sport:'FOOTBALL', notes:'' },
  { id:225, date:'2026-01-17', match:'Leeds vs Fulham',               market:'Fulham 0/0.5',      odds:2,    closingOdds:null, result:'loss', cumPL:15,  sport:'FOOTBALL', notes:'' },
  { id:226, date:'2026-01-17', match:'Leeds vs Fulham',               market:'Under 3.5 Cards 2.3', odds:2.3, closingOdds:null, result:'loss', cumPL:14, sport:'FOOTBALL', notes:'' },
  { id:227, date:'2026-01-17', match:'Liverpool vs Burnley',          market:'Under 3.5 Cards 1.7', odds:1.7, closingOdds:null, result:'win',  cumPL:14.7,  sport:'FOOTBALL', notes:'' },
  { id:228, date:'2026-01-17', match:'Nottm Forest vs Arsenal',       market:'Draw 4.5',          odds:4.5,  closingOdds:1.8,  result:'win',  cumPL:17.5,  sport:'FOOTBALL', notes:'' },
  { id:229, date:'2026-01-18', match:'Aston Villa vs Everton',        market:'Over 2.5',          odds:2,    closingOdds:null, result:'win',  cumPL:16.5,  sport:'FOOTBALL', notes:'' },
  { id:230, date:'2026-01-17', match:'Chelsea vs Brentford',          market:'Away/Draw 2.2',     odds:2.2,  closingOdds:null, result:'loss', cumPL:15.5,  sport:'FOOTBALL', notes:'' },
  { id:233, date:'2026-01-24', match:'West Ham vs Sunderland',        market:'Under 2.5/BTTS 1.85', odds:1.85, closingOdds:null, result:'push', cumPL:15.4, sport:'FOOTBALL', notes:'' },
  { id:234, date:'2026-01-24', match:'Bournemouth vs Liverpool',      market:'Liverpool 2',       odds:2,    closingOdds:null, result:'loss', cumPL:14.3,  sport:'FOOTBALL', notes:'' },
  { id:235, date:'2026-01-24', match:'Bournemouth vs Liverpool',      market:'Over 2.5',          odds:1.6,  closingOdds:null, result:'win',  cumPL:15.3,  sport:'FOOTBALL', notes:'' },
  { id:236, date:'2026-01-25', match:'Crystal Palace vs Chelsea',     market:'Draw 3.8',          odds:3.8,  closingOdds:1.8,  result:'loss', cumPL:14.3,  sport:'FOOTBALL', notes:'' },
  { id:237, date:'2026-01-25', match:'Newcastle vs Aston Villa',      market:'Draw 4',            odds:4,    closingOdds:1.8,  result:'loss', cumPL:13.3,  sport:'FOOTBALL', notes:'' },
  { id:238, date:'2026-01-25', match:'Brentford vs Nottm Forest',     market:'Under 2.5',         odds:2,    closingOdds:null, result:'win',  cumPL:14.3,  sport:'FOOTBALL', notes:'' },
  { id:239, date:'2026-01-25', match:'Arsenal vs Man United',         market:'Draw 4.4',          odds:4.4,  closingOdds:1.8,  result:'push', cumPL:14.3,  sport:'FOOTBALL', notes:'' },
  { id:240, date:'2026-01-25', match:'Arsenal vs Man United',         market:'Under 3.5',         odds:1.5,  closingOdds:null, result:'loss', cumPL:13.3,  sport:'FOOTBALL', notes:'' },
  { id:241, date:'2026-01-31', match:'Chelsea vs West Ham',           market:'Cards Over 3.5',    odds:1.6,  closingOdds:null, result:'win',  cumPL:13.9,  sport:'FOOTBALL', notes:'' },
  { id:242, date:'2026-02-01', match:'Tottenham vs Man City',         market:'Cards Over 4.5',    odds:2.1,  closingOdds:null, result:'win',  cumPL:16,  sport:'FOOTBALL', notes:'' },
  { id:243, date:'2026-02-01', match:'Tottenham vs Man City',         market:'Draw 4.3',          odds:4.3,  closingOdds:1.8,  result:'win',  cumPL:18.5,  sport:'FOOTBALL', notes:'' },
  { id:244, date:'2026-01-31', match:'Liverpool vs Newcastle',        market:'Cards Over 3.5',    odds:1.6,  closingOdds:null, result:'win',  cumPL:19.1,  sport:'FOOTBALL', notes:'' },
  { id:245, date:'2026-01-31', match:'Liverpool vs Newcastle',        market:'Liverpool 1.85',    odds:1.85, closingOdds:null, result:'win',  cumPL:21,  sport:'FOOTBALL', notes:'' },
  { id:246, date:'2026-02-01', match:'Man United vs Fulham',          market:'Fulham 5.8',        odds:5.8,  closingOdds:1.8,  result:'loss', cumPL:20,  sport:'FOOTBALL', notes:'' },
  { id:247, date:'2026-02-01', match:'Man United vs Fulham',          market:'Over 2.5',          odds:1.75, closingOdds:null, result:'win',  cumPL:20.75, sport:'FOOTBALL', notes:'' },
  { id:248, date:'2026-02-01', match:'Nottm Forest vs Crystal Palace', market:'Crystal Palace 4.3', odds:4.3, closingOdds:1.8, result:'loss', cumPL:19.75, sport:'FOOTBALL', notes:'' },
  { id:249, date:'2026-01-31', match:'Bournemouth vs Wolves',         market:'Over 2.5',          odds:1.85, closingOdds:null, result:'loss', cumPL:18.75, sport:'FOOTBALL', notes:'' },
  { id:250, date:'2026-02-01', match:'Aston Villa vs Brentford',      market:'Over 2.5',          odds:1.8,  closingOdds:null, result:'loss', cumPL:17.75, sport:'FOOTBALL', notes:'' },
  { id:251, date:'2026-02-07', match:'Man United vs Tottenham',       market:'Draw 4.8',          odds:4.8,  closingOdds:1.8,  result:'loss', cumPL:16.75, sport:'FOOTBALL', notes:'' },
  { id:252, date:'2026-02-07', match:'Newcastle vs Brentford',        market:'Newcastle 2.1',     odds:2.1,  closingOdds:null, result:'loss', cumPL:15.75, sport:'FOOTBALL', notes:'' },
  { id:253, date:'2026-02-07', match:'Bournemouth vs Aston Villa',    market:'BTTS 1.7',          odds:1.7,  closingOdds:null, result:'win',  cumPL:16.45, sport:'FOOTBALL', notes:'' },
  { id:254, date:'2026-02-07', match:'Wolves vs Chelsea',             market:'BTTS 1.85',         odds:1.85, closingOdds:null, result:'win',  cumPL:17.25, sport:'FOOTBALL', notes:'' },
  { id:255, date:'2026-02-08', match:'Liverpool vs Man City',         market:'Draw/Liverpool 3.9', odds:3.9,  closingOdds:1.8,  result:'loss', cumPL:16.25, sport:'FOOTBALL', notes:'' },
  { id:256, date:'2026-02-10', match:'Man United vs West Ham',        market:'Draw 4.7',          odds:4.7,  closingOdds:1.7,  result:'win',  cumPL:19.25, sport:'FOOTBALL', notes:'' },
  { id:257, date:'2026-02-10', match:'Tottenham vs Newcastle',        market:'Draw 3.6',          odds:3.6,  closingOdds:null, result:'loss', cumPL:18.25, sport:'FOOTBALL', notes:'' },
  { id:258, date:'2026-02-11', match:'Wolves vs Nottm Forest',        market:'BTTS 2',            odds:2,    closingOdds:null, result:'loss', cumPL:17.25, sport:'FOOTBALL', notes:'' },
  { id:259, date:'2026-02-11', match:'Aston Villa vs Brighton',       market:'BTTS 1.8',          odds:1.8,  closingOdds:null, result:'loss', cumPL:16.25, sport:'FOOTBALL', notes:'' },
  { id:260, date:'2026-02-21', match:'Brentford vs Brighton',         market:'Brentford 2',       odds:2,    closingOdds:null, result:'loss', cumPL:15.25, sport:'FOOTBALL', notes:'' },
  { id:261, date:'2026-02-21', match:'West Ham vs Bournemouth',       market:'BTTS 1.5',          odds:1.5,  closingOdds:null, result:'loss', cumPL:14.25, sport:'FOOTBALL', notes:'' },
  { id:262, date:'2026-02-22', match:'Tottenham vs Arsenal',          market:'Draw 4.4',          odds:4.4,  closingOdds:1.7,  result:'loss', cumPL:13.25, sport:'FOOTBALL', notes:'' },
  { id:263, date:'2026-02-23', match:'Everton vs Man United',         market:'Draw 4',            odds:4,    closingOdds:1.7,  result:'loss', cumPL:12.25, sport:'FOOTBALL', notes:'' },
  { id:264, date:'2026-02-28', match:'Leeds vs Man City',             market:'Over 2.5',          odds:1.9, closingOdds:null, result:'loss', cumPL:11.25, sport:'FOOTBALL', notes:'' },
  { id:265, date:'2026-03-01', match:'Arsenal vs Chelsea',            market:'Draw',              odds:1.9, closingOdds:null, result:'loss', cumPL:10.25, sport:'FOOTBALL', notes:'' },
  { id:266, date:'2026-03-01', match:'Arsenal vs Chelsea',            market:'Over 3.5 Cards',    odds:1.5, closingOdds:null, result:'win',  cumPL:10.75, sport:'FOOTBALL', notes:'' },
  { id:267, date:'2026-03-05', match:'Tottenham vs Crystal Palace',   market:'Draw',              odds:1.9, closingOdds:null, result:'loss', cumPL:9.75, sport:'FOOTBALL', notes:'' },
];

// ─── Section 2: Sports Betting diary — structured bets Mar-Apr 2026 ──────────
// Appended to LEGACY_BETS. Dates stored as Australian DD/MM in Excel (swapped
// by Excel's US-locale serial parser — all corrected here to true AU dates).
LEGACY_BETS.push(
  { id:283, date:'2026-03-06', match:'Dolphins vs Souths',                  market:'Over 48.5',        odds:1.9,  closingOdds:1.9,  result:'win',  cumPL:16.4,  sport:'NRL',      notes:'' },
  { id:284, date:'2026-03-12', match:'Carlton vs Richmond',                  market:'Under 178.5',      odds:1.9,  closingOdds:1.9,  result:'win',  cumPL:17.3,  sport:'AFL',      notes:'' },
  { id:285, date:'2026-03-13', match:'Essendon vs Hawthorn',                market:'Over 183.5',        odds:1.9,  closingOdds:1.9,  result:'win',  cumPL:18.2,  sport:'AFL',      notes:'' },
  { id:286, date:'2026-03-14', match:'Penrith vs Cronulla',                  market:'Under 44.5',       odds:1.9,  closingOdds:1.9,  result:'win',  cumPL:19.1,  sport:'NRL',      notes:'' },
  { id:287, date:'2026-03-14', match:'Man United vs Aston Villa',            market:'Man U 1.74',       odds:1.7,  closingOdds:null, result:'win',  cumPL:19.8,  sport:'FOOTBALL', notes:'' },
  { id:288, date:'2026-03-14', match:'Sydney vs Brisbane',                   market:'Win',              odds:3.2,  closingOdds:3.2,  result:'loss', cumPL:18.8,  sport:'AFL',      notes:'' },
  { id:289, date:'2026-03-14', match:'Sydney vs Brisbane',                   market:'Under 190.5',      odds:1.95, closingOdds:1.95, result:'win',  cumPL:19.75, sport:'AFL',      notes:'' },
  { id:290, date:'2026-03-15', match:'Melbourne vs St Kilda',                market:'Under 180.5',      odds:1.9,  closingOdds:1.9,  result:'loss', cumPL:18.75, sport:'AFL',      notes:'Overpriced for both teams. Bottom 8, cagey. MCG is a big factor.' },
  { id:291, date:'2026-03-19', match:'Hawthorn vs Sydney',                   market:'Line 10.5 Sydney', odds:1.9,  closingOdds:1.9,  result:'loss', cumPL:17.75, sport:'AFL',      notes:'Sydney in rare form. If going to win at MCG it was now.' },
  { id:292, date:'2026-03-22', match:'Brighton vs Liverpool',                market:'Under 2.5',        odds:2.3,  closingOdds:null, result:'loss', cumPL:16.75, sport:'FOOTBALL', notes:'Early kickoff, low morale, Liverpool not converting.' },
  { id:293, date:'2026-03-22', match:'Brighton vs Liverpool',                market:'Draw',             odds:3.85, closingOdds:null, result:'loss', cumPL:15.75, sport:'FOOTBALL', notes:'Liverpool afraid to lose, conceding late goals.' },
  { id:294, date:'2026-03-22', match:'Newcastle vs Sunderland',              market:'Draw',             odds:4.2,  closingOdds:null, result:'loss', cumPL:14.85, sport:'FOOTBALL', notes:'Sunderland must get points. Derby. Both afraid to lose.' },
  { id:295, date:'2026-03-19', match:'Tottenham vs Atletico Madrid',         market:'Under 3.5 Cards',  odds:2.0,  closingOdds:2.0,  result:'loss', cumPL:13.75, sport:'FOOTBALL', notes:'' },
  { id:296, date:'2026-03-19', match:'Canberra vs Canterbury',               market:'Under 49.5',       odds:1.9,  closingOdds:null, result:'win',  cumPL:14.65, sport:'NRL',      notes:'' },
  { id:297, date:'2026-03-22', match:'West Coast Eagles vs North Melbourne', market:'Under 179.5',      odds:1.9,  closingOdds:null, result:'loss', cumPL:13.75, sport:'AFL',      notes:'' },
  { id:298, date:'2026-03-22', match:'North QLD vs Gold Coast',              market:'Under 57.5',       odds:1.9,  closingOdds:null, result:'win',  cumPL:14.75, sport:'NRL',      notes:'' },
  { id:299, date:'2026-03-26', match:'Geelong vs Adelaide',                  market:'Under 179.5',      odds:1.9,  closingOdds:null, result:'win',  cumPL:15.65, sport:'AFL',      notes:'' },
  { id:300, date:'2026-03-27', match:'Collingwood vs GWS',                   market:'Under 179.6',      odds:1.9,  closingOdds:null, result:'win',  cumPL:16.55, sport:'AFL',      notes:'' },
  { id:301, date:'2026-03-28', match:'Carlton vs North Melbourne',           market:'Under 180.5',      odds:1.9,  closingOdds:null, result:'win',  cumPL:17.45, sport:'AFL',      notes:'' },
  { id:302, date:'2026-03-27', match:'Australia vs Cameroon',                market:'Under 2.5',        odds:1.75, closingOdds:null, result:'win',  cumPL:18.2,  sport:'FOOTBALL', notes:'' },
  { id:303, date:'2026-03-29', match:'Penrith vs Parramatta',                market:'Under 47.5',       odds:1.95, closingOdds:null, result:'loss', cumPL:17.2,  sport:'NRL',      notes:'' },
  { id:304, date:'2026-04-03', match:'Brisbane vs Collingwood',              market:'Over 176.5',       odds:1.9,  closingOdds:null, result:'win',  cumPL:18.1,  sport:'AFL',      notes:'' },
  { id:305, date:'2026-04-04', match:'St George vs North Queensland',        market:'Under 49.5',       odds:1.8,  closingOdds:null, result:'win',  cumPL:18.9,  sport:'NRL',      notes:'' },
  { id:306, date:'2026-04-05', match:'Parramatta vs Wests Tigers',           market:'Tigers Win',       odds:2.0,  closingOdds:null, result:'win',  cumPL:19.9,  sport:'NRL',      notes:'' },
  { id:307, date:'2026-04-10', match:'Collingwood vs Fremantle',             market:'Under 174.5',      odds:1.9,  closingOdds:null, result:'win',  cumPL:20.8,  sport:'AFL',      notes:'' },
  { id:308, date:'2026-04-09', match:'PSG vs Liverpool',                     market:'PSG Win',          odds:1.75, closingOdds:null, result:'win',  cumPL:21.55, sport:'FOOTBALL', notes:'' },
  { id:309, date:'2026-04-11', match:'Sunderland vs Tottenham',              market:'Tottenham Win',    odds:2.7,  closingOdds:null, result:'loss', cumPL:20.55, sport:'FOOTBALL', notes:'' },
  { id:310, date:'2026-04-09', match:'Canterbury vs Penrith',                market:'Bulldogs +18.5',   odds:1.9,  closingOdds:null, result:'win',  cumPL:21.45, sport:'NRL',      notes:'' },
  { id:311, date:'2026-04-11', match:'North Melbourne vs Brisbane',          market:'Under 192.5',      odds:1.9,  closingOdds:null, result:'win',  cumPL:22.45, sport:'AFL',      notes:'' },
  { id:312, date:'2026-04-11', match:'Hawthorn vs Western Bulldogs',         market:'Under 182.5',      odds:1.9,  closingOdds:null, result:'win',  cumPL:23.45, sport:'AFL',      notes:'' },
  { id:313, date:'2026-04-12', match:'Parramatta vs Gold Coast',             market:'Under 49.5',       odds:1.9,  closingOdds:null, result:'loss', cumPL:22.45, sport:'NRL',      notes:'' },
  { id:314, date:'2026-04-12', match:'Wests Tigers vs Newcastle',            market:'Under 49.5',       odds:1.9,  closingOdds:null, result:'loss', cumPL:21.45, sport:'NRL',      notes:'' },
  { id:315, date:'2026-04-12', match:'GWS vs Richmond',                      market:'Under 178.5',      odds:1.9,  closingOdds:null, result:'loss', cumPL:20.45, sport:'AFL',      notes:'' },
  { id:316, date:'2026-04-12', match:'Chelsea vs Man City',                  market:'Man City Win',     odds:2.0,  closingOdds:null, result:'win',  cumPL:21.55, sport:'FOOTBALL', notes:'' },
  { id:317, date:'2026-04-17', match:'Geelong vs Western Bulldogs',          market:'Geelong -10.5',    odds:1.9,  closingOdds:null, result:'win',  cumPL:22.65, sport:'AFL',      notes:'' },
  { id:318, date:'2026-04-17', match:'Tottenham vs Brighton',                market:'Over 2.5',         odds:1.7,  closingOdds:null, result:'win',  cumPL:23.35, sport:'FOOTBALL', notes:'' },
  { id:319, date:'2026-04-17', match:'Chelsea vs Man United',                market:'Under 2.5',        odds:2.3,  closingOdds:null, result:'win',  cumPL:24.65, sport:'FOOTBALL', notes:'' },
  { id:320, date:'2026-04-17', match:'Everton vs Liverpool',                 market:'Under 2.5',        odds:2.0,  closingOdds:null, result:'loss', cumPL:23.65, sport:'FOOTBALL', notes:'' },
  { id:321, date:'2026-04-17', match:'Man City vs Arsenal',                  market:'Man City Win',     odds:2.0,  closingOdds:null, result:'win',  cumPL:24.55, sport:'FOOTBALL', notes:'' },
  { id:322, date:'2026-04-25', match:'Wolves vs Tottenham',                  market:'Tottenham Win',    odds:1.75, closingOdds:null, result:'win',  cumPL:25.3,  sport:'FOOTBALL', notes:'' },
  { id:323, date:'2026-04-25', match:'Fulham vs Aston Villa',                market:'Over 2.5',         odds:2.0,  closingOdds:null, result:'loss', cumPL:24.3,  sport:'FOOTBALL', notes:'' },
  { id:324, date:'2026-04-25', match:'Liverpool vs Crystal Palace',          market:'Under 2.5',        odds:2.0,  closingOdds:null, result:'loss', cumPL:23.3,  sport:'FOOTBALL', notes:'' },
  { id:325, date:'2026-04-25', match:'Brisbane vs Adelaide Crows',           market:'Under 189.5',      odds:2.0,  closingOdds:null, result:'loss', cumPL:22.3,  sport:'AFL',      notes:'' },
  { id:326, date:'2026-05-01', match:'Western Bulldogs vs Fremantle',         market:'Western Bulldogs', odds:3.21, closingOdds:null, result:'loss', cumPL:21.64, sport:'AFL',      notes:'Actual bet log. Stake $33. Fremantle won 114-102.' },
  { id:327, date:'2026-05-01', match:'Adelaide vs Port Adelaide',             market:'Adelaide -9.5',    odds:1.89, closingOdds:null, result:'loss', cumPL:20.64, sport:'AFL',      notes:'Actual bet log. Stake $50. Adelaide won by 1 but did not cover.' },
  { id:328, date:'2026-05-01', match:'Dolphins vs Melbourne Storm',           market:'Under 54.5',       odds:1.84, closingOdds:null, result:'win',  cumPL:21.48, sport:'NRL',      notes:'Actual bet log. Stake $50. Dolphins won 28-10, total 38.' },
  { id:329, date:'2026-05-01', match:'Dolphins vs Melbourne Storm',           market:'Dolphins -3.5',    odds:1.89, closingOdds:null, result:'win',  cumPL:22.37, sport:'NRL',      notes:'Actual bet log. Stake $50. Dolphins covered by 18.' },
  { id:330, date:'2026-05-02', match:'Carlton vs St Kilda',                   market:'Carlton',          odds:2.55, closingOdds:null, result:'loss', cumPL:21.57, sport:'AFL',      notes:'Actual bet log. Stake $40. St Kilda won.' },
  { id:331, date:'2026-05-02', match:'Carlton vs St Kilda',                   market:'Under 183.5',      odds:1.89, closingOdds:null, result:'win',  cumPL:22.46, sport:'AFL',      notes:'Actual bet log. Stake $50. Under landed.' },
  { id:332, date:'2026-05-03', match:'Cronulla Sharks vs Wests Tigers',       market:'Cronulla -7.5',    odds:1.90, closingOdds:null, result:'win',  cumPL:23.36, sport:'NRL',      notes:'Actual bet log. Stake $50. Cronulla won 52-10, covered by 44.5.' },
);

// ─── Section 3: Week ending 2026-05-12 (NRL R10 + AFL R9) ───────────────────
LEGACY_BETS.push(
  { id:333, date:'2026-05-07', match:'Dolphins vs Canterbury',               market:'Dolphins -5.5',    odds:1.84, closingOdds:null, result:'win',  cumPL:24.20, sport:'NRL',      notes:'Actual bet log. Stake $50.' },
  { id:334, date:'2026-05-08', match:'Port Adelaide vs W Bulldogs',          market:'Port Adelaide Win', odds:1.96, closingOdds:null, result:'loss', cumPL:23.20, sport:'AFL',      notes:'Actual bet log. Stake $50.' },
  { id:335, date:'2026-05-09', match:'Gold Coast vs St Kilda',               market:'Gold Coast -17.5', odds:1.89, closingOdds:null, result:'win',  cumPL:24.09, sport:'AFL',      notes:'Actual bet log. Stake $50.' },
  { id:336, date:'2026-05-09', match:'Geelong vs Collingwood',               market:'Geelong -11.5',    odds:1.89, closingOdds:null, result:'win',  cumPL:24.98, sport:'AFL',      notes:'Actual bet log. Stake $50.' },
  { id:337, date:'2026-05-09', match:'GWS vs Essendon',                      market:'Under 193.5',      odds:1.87, closingOdds:null, result:'win',  cumPL:25.85, sport:'AFL',      notes:'Actual bet log. Stake $50.' },
  { id:338, date:'2026-05-09', match:'St George vs Newcastle',               market:'Dragons +8.5',     odds:1.89, closingOdds:null, result:'loss', cumPL:24.85, sport:'NRL',      notes:'Actual bet log. Stake $50.' },
  { id:339, date:'2026-05-10', match:'Canberra vs Penrith',                  market:'Canberra Win',     odds:3.62, closingOdds:null, result:'loss', cumPL:23.85, sport:'NRL',      notes:'Actual bet log. Stake $50.' },
  { id:340, date:'2026-05-10', match:'Melbourne Storm vs Wests Tigers',      market:'Storm -5.5',       odds:1.90, closingOdds:null, result:'win',  cumPL:24.75, sport:'NRL',      notes:'Actual bet log. Stake $50.' },
);

// ─── Section 4: Week ending 2026-05-19 (NRL R11 Magic Round + AFL R10) ──────
LEGACY_BETS.push(
  { id:341, date:'2026-05-15', match:'Sydney Swans vs Collingwood',        market:'Under 181.5',      odds:1.86, closingOdds:null, result:'win',  cumPL:25.61, sport:'AFL', notes:'Actual bet log. Stake $50. Under landed.' },
  { id:342, date:'2026-05-15', match:'Sydney Swans vs Collingwood',        market:'Collingwood +35.5', odds:1.91, closingOdds:null, result:'win',  cumPL:26.07, sport:'AFL', notes:'Actual bet log. Stake $25. Collingwood covered.' },
  { id:343, date:'2026-05-15', match:'Gold Coast vs Port Adelaide',        market:'Gold Coast -26.5', odds:1.90, closingOdds:null, result:'loss', cumPL:25.07, sport:'AFL', notes:'Actual bet log. Stake $50.' },
  { id:344, date:'2026-05-15', match:'Rabbitohs vs Dolphins',              market:'Dolphins Win',     odds:1.85, closingOdds:null, result:'win',  cumPL:25.92, sport:'NRL', notes:'Actual bet log. Stake $50. Dolphins won.' },
  { id:345, date:'2026-05-15', match:'Cronulla vs Canterbury',             market:'Under 50.5',       odds:1.90, closingOdds:null, result:'loss', cumPL:24.94, sport:'NRL', notes:'Actual bet log. Stake $48.80.' },
  { id:346, date:'2026-05-16', match:'Carlton vs Western Bulldogs',        market:'Carlton Win',      odds:2.56, closingOdds:null, result:'win',  cumPL:25.72, sport:'AFL', notes:'Actual bet log. Stake $25. Carlton won.' },
  { id:347, date:'2026-05-16', match:'Melbourne vs Hawthorn',              market:'Hawthorn -18.5',   odds:1.91, closingOdds:null, result:'loss', cumPL:24.72, sport:'AFL', notes:'Actual bet log. Stake $50.' },
  { id:348, date:'2026-05-16', match:'Adelaide vs North Melbourne',        market:'Adelaide -18.5',   odds:1.90, closingOdds:null, result:'win',  cumPL:25.62, sport:'AFL', notes:'Actual bet log. Stake $50. Adelaide covered.' },
  { id:349, date:'2026-05-16', match:'Roosters vs Cowboys',                market:'Cowboys +16.5',    odds:1.74, closingOdds:null, result:'win',  cumPL:26.03, sport:'NRL', notes:'Actual bet log. Stake $27.50. Cowboys covered.' },
  { id:350, date:'2026-05-17', match:'Warriors vs Broncos',                market:'Warriors -2.5',    odds:1.91, closingOdds:null, result:'win',  cumPL:26.94, sport:'NRL', notes:'Actual bet log. Stake $50. Warriors covered.' },
  { id:351, date:'2026-05-17', match:'Panthers vs Dragons',                market:'Under 56.5',       odds:1.82, closingOdds:null, result:'win',  cumPL:27.35, sport:'NRL', notes:'Actual bet log. Stake $25. Under landed.' },
);

// ─── Section 5: Week ending 2026-05-25 (NRL R12 + AFL R11) ──────────────────
LEGACY_BETS.push(
  { id:352, date:'2026-05-21', match:'Hawthorn vs Adelaide Crows',        market:'Hawthorn Win',       odds:1.41, closingOdds:null, result:'win',  cumPL:27.80, sport:'AFL', notes:'Actual bet log. Stake $55. Hawthorn won.' },
  { id:353, date:'2026-05-21', match:'Hawthorn vs Adelaide Crows',        market:'Adelaide Crows Win', odds:2.88, closingOdds:null, result:'loss', cumPL:27.30, sport:'AFL', notes:'Actual bet log. Stake $25.' },
  { id:354, date:'2026-05-21', match:'Hawthorn vs Adelaide Crows',        market:'Hawthorn -15.5',     odds:1.90, closingOdds:null, result:'loss', cumPL:26.80, sport:'AFL', notes:'Actual bet log. Stake $25. Hawthorn won by 9.' },
  { id:355, date:'2026-05-21', match:'Hawthorn vs Adelaide Crows',        market:'Adelaide +19.5',     odds:1.89, closingOdds:null, result:'win',  cumPL:27.25, sport:'AFL', notes:'Actual bet log. Stake $25. Crows covered +19.5.' },
  { id:356, date:'2026-05-22', match:'Richmond vs Essendon',              market:'Under 176.5',        odds:1.88, closingOdds:null, result:'win',  cumPL:27.69, sport:'AFL', notes:'Actual bet log. Stake $25. Under landed.' },
  { id:357, date:'2026-05-22', match:'Canterbury Bulldogs vs Melbourne Storm', market:'Bulldogs -3.5', odds:1.90, closingOdds:null, result:'win',  cumPL:28.14, sport:'NRL', notes:'Actual bet log. Stake $25. Bulldogs won 26-18, covered.' },
  { id:358, date:'2026-05-22', match:'Canterbury Bulldogs vs Melbourne Storm', market:'Under 48.5',    odds:1.84, closingOdds:null, result:'loss', cumPL:27.64, sport:'NRL', notes:'Actual bet log. Stake $25. Total was 44 — wait, did it land? Check.' },
  { id:359, date:'2026-05-22', match:'Canterbury Bulldogs vs Melbourne Storm', market:'Under 49.5',    odds:1.90, closingOdds:null, result:'loss', cumPL:27.14, sport:'NRL', notes:'Actual bet log. Stake $25.' },
  { id:360, date:'2026-05-23', match:'Geelong Cats vs Sydney Swans',      market:'Swans +10.5',        odds:1.90, closingOdds:null, result:'loss', cumPL:26.64, sport:'AFL', notes:'Actual bet log. Stake $25.' },
  { id:361, date:'2026-05-23', match:'Collingwood vs West Coast Eagles',  market:'Under 180.5',        odds:1.87, closingOdds:null, result:'win',  cumPL:27.08, sport:'AFL', notes:'Actual bet log. Stake $25. Under landed.' },
  { id:362, date:'2026-05-23', match:'St George Illawarra vs NZ Warriors',market:'Under 50.5',         odds:1.90, closingOdds:null, result:'win',  cumPL:27.34, sport:'NRL', notes:'Actual bet log. Stake $14.30.' },
  { id:363, date:'2026-05-23', match:'Manly Sea Eagles vs Gold Coast Titans', market:'Manly -11.5',    odds:1.83, closingOdds:null, result:'loss', cumPL:26.84, sport:'NRL', notes:'Actual bet log. Stake $25.' },
  { id:364, date:'2026-05-23', match:'Manly Sea Eagles vs Gold Coast Titans', market:'Gold Coast +12.5', odds:1.89, closingOdds:null, result:'win', cumPL:27.06, sport:'NRL', notes:'Actual bet log. Stake $12.50.' },
  { id:365, date:'2026-05-23', match:'Manly Sea Eagles vs Gold Coast Titans', market:'Gold Coast Win', odds:4.35, closingOdds:null, result:'loss', cumPL:26.81, sport:'NRL', notes:'Actual bet log. Stake $12.50.' },
  { id:366, date:'2026-05-24', match:'Cowboys vs South Sydney Rabbitohs', market:'Cowboys Win',         odds:1.67, closingOdds:null, result:'win',  cumPL:27.73, sport:'NRL', notes:'Actual bet log. Stake $68.68. Triple matrix confluence. Cowboys won.' },
  { id:367, date:'2026-05-24', match:'Cowboys vs South Sydney Rabbitohs', market:'Cowboys Win',         odds:1.69, closingOdds:null, result:'win',  cumPL:28.08, sport:'NRL', notes:'Actual bet log. Stake $25. Cowboys won.' },
  { id:368, date:'2026-05-24', match:'Cowboys vs South Sydney Rabbitohs', market:'Cowboys -2.5',        odds:1.90, closingOdds:null, result:'win',  cumPL:28.53, sport:'NRL', notes:'Actual bet log. Stake $25. Cowboys covered.' },
);

// ─── Section 6: Week ending 2026-06-01 (NRL R13 + AFL R12) ──────────────────
LEGACY_BETS.push(
  // AFL R12 — Thu 28 May
  { id:369, date:'2026-05-28', match:'St Kilda vs Hawthorn',                   market:'Hawthorn -19.5',      odds:1.90, closingOdds:null, result:'win',  cumPL:28.98, sport:'AFL', notes:'Actual bet log. Stake $25. Hawthorn won.' },
  // NRL R13 — Fri 29 May (Cronulla vs Manly)
  { id:370, date:'2026-05-29', match:'Cronulla Sharks vs Manly',               market:'Cronulla Win',         odds:1.87, closingOdds:null, result:'win',  cumPL:29.85, sport:'NRL', notes:'Actual bet log. Stake $50. Cronulla won. 7-way H2H matrix confluence.' },
  { id:371, date:'2026-05-29', match:'Cronulla Sharks vs Manly',               market:'Over 44.5 alt total',  odds:1.77, closingOdds:null, result:'win',  cumPL:30.12, sport:'NRL', notes:'Actual bet log. Stake $17.50. Alternative total line won.' },
  { id:372, date:'2026-05-29', match:'Cronulla Sharks vs Manly',               market:'Under 46.5',           odds:1.89, closingOdds:null, result:'loss', cumPL:29.62, sport:'NRL', notes:'Actual bet log. Stake $25.' },
  { id:373, date:'2026-05-29', match:'Cronulla Sharks vs Manly',               market:'Under 50.5',           odds:1.81, closingOdds:null, result:'win',  cumPL:30.03, sport:'NRL', notes:'Actual bet log. Stake $25. Under landed.' },
  { id:374, date:'2026-05-29', match:'Cronulla Sharks vs Manly',               market:'Manly Win',            odds:1.98, closingOdds:null, result:'loss', cumPL:29.63, sport:'NRL', notes:'Actual bet log. Stake $20.' },
  // AFL R12 — Fri 29 May (Carlton vs Geelong)
  { id:375, date:'2026-05-29', match:'Carlton vs Geelong Cats',                market:'Over 178.5',           odds:1.89, closingOdds:null, result:'loss', cumPL:29.13, sport:'AFL', notes:'Actual bet log. Stake $25. 4-way OVERS matrix confluence — did not land.' },
  // NRL R13 — Sat 30 May (Tigers vs Bulldogs)
  { id:376, date:'2026-05-30', match:'Wests Tigers vs Canterbury Bulldogs',    market:'Over 48.5',            odds:1.90, closingOdds:null, result:'loss', cumPL:28.63, sport:'NRL', notes:'Actual bet log. Stake $25.' },
  // AFL R12 — Sat 30 May (Bulldogs vs Collingwood)
  { id:378, date:'2026-05-30', match:'Western Bulldogs vs Collingwood',        market:'Collingwood Win',       odds:2.26, closingOdds:null, result:'loss', cumPL:28.13, sport:'AFL', notes:'Actual bet log. Stake $25.' },
  // NRL R13 — Sun 31 May (Panthers vs Warriors)
  { id:379, date:'2026-05-31', match:'Penrith Panthers vs NZ Warriors',        market:'Under 47.5',           odds:1.90, closingOdds:null, result:'win',  cumPL:28.58, sport:'NRL', notes:'Actual bet log. Stake $25. Under landed. Model predicted 44.1.' },
  { id:380, date:'2026-05-31', match:'Penrith Panthers vs NZ Warriors',        market:'Under 46.5',           odds:1.84, closingOdds:null, result:'win',  cumPL:29.00, sport:'NRL', notes:'Actual bet log. Stake $25. Under landed.' },
  { id:381, date:'2026-05-31', match:'Penrith Panthers vs NZ Warriors',        market:'Panthers -3.5',        odds:1.83, closingOdds:null, result:'loss', cumPL:28.50, sport:'NRL', notes:'Actual bet log. Stake $25. Model had Panthers by 12.7 — missed.' },
  { id:382, date:'2026-05-31', match:'Penrith Panthers vs NZ Warriors',        market:'Panthers -5.5',        odds:1.72, closingOdds:null, result:'loss', cumPL:28.00, sport:'NRL', notes:'Actual bet log. Stake $25.' },
  // NRL R13 — Sun 31 May (Raiders vs Cowboys)
  { id:383, date:'2026-05-31', match:'Canberra Raiders vs Cowboys',            market:'Cowboys +4.5',         odds:1.73, closingOdds:null, result:'loss', cumPL:27.50, sport:'NRL', notes:'Actual bet log. Stake $25.' },
  // AFL R12 — Sun 31 May (West Coast vs Essendon)
  { id:385, date:'2026-05-31', match:'West Coast Eagles vs Essendon',          market:'Essendon Win',         odds:2.39, closingOdds:null, result:'loss', cumPL:27.00, sport:'AFL', notes:'Actual bet log. Stake $25. Eagles won.' },
);

// ─── Section 7: Week ending 2026-06-08 (NRL R14 + AFL R13) ──────────────────
LEGACY_BETS.push(
  // NRL R14 — Fri 5 Jun (Melbourne Storm vs Newcastle Knights)
  { id:386, date:'2026-06-05', match:'Melbourne Storm vs Newcastle Knights',     market:'Newcastle +4.5',   odds:1.85, closingOdds:null, result:'win',  cumPL:27.43, sport:'NRL', notes:'Actual bet log. Stake $25.' },
  // AFL R13 — Fri 5 Jun (Hawthorn vs Western Bulldogs) — three bets, two lines
  { id:387, date:'2026-06-05', match:'Hawthorn vs Western Bulldogs',             market:'Hawthorn -11.5',   odds:1.90, closingOdds:null, result:'loss', cumPL:26.93, sport:'AFL', notes:'Actual bet log. Stake $25.' },
  { id:388, date:'2026-06-05', match:'Hawthorn vs Western Bulldogs',             market:'Hawthorn -20.5',   odds:1.91, closingOdds:null, result:'loss', cumPL:26.53, sport:'AFL', notes:'Actual bet log. Stake $20.' },
  { id:389, date:'2026-06-05', match:'Hawthorn vs Western Bulldogs',             market:'Hawthorn -20.5',   odds:1.91, closingOdds:null, result:'loss', cumPL:26.03, sport:'AFL', notes:'Actual bet log. Stake $25.' },
  // AFL R13 — Sat 6 Jun (Gold Coast Suns vs Brisbane Lions)
  { id:390, date:'2026-06-06', match:'Gold Coast Suns vs Brisbane Lions',        market:'Under 188.5',      odds:1.88, closingOdds:null, result:'win',  cumPL:26.47, sport:'AFL', notes:'Actual bet log. Stake $25. Under landed.' },
  // NRL R14 — Sat 6 Jun (North Queensland Cowboys vs Dolphins)
  { id:391, date:'2026-06-06', match:'North Queensland Cowboys vs Dolphins',     market:'Cowboys Win',      odds:2.38, closingOdds:null, result:'loss', cumPL:26.07, sport:'NRL', notes:'Actual bet log. Stake $20.' },
  // AFL R13 — Sat 6 Jun (West Coast Eagles vs Port Adelaide) — two lines
  { id:392, date:'2026-06-06', match:'West Coast Eagles vs Port Adelaide',       market:'Port Adelaide -6.5', odds:1.88, closingOdds:null, result:'loss', cumPL:25.47, sport:'AFL', notes:'Actual bet log. Stake $30.' },
  { id:393, date:'2026-06-06', match:'West Coast Eagles vs Port Adelaide',       market:'Port Adelaide -7.5', odds:1.90, closingOdds:null, result:'loss', cumPL:24.97, sport:'AFL', notes:'Actual bet log. Stake $25.' },
  // NRL R14 — Sat 6 Jun (Brisbane Broncos vs Gold Coast Titans)
  { id:394, date:'2026-06-06', match:'Brisbane Broncos vs Gold Coast Titans',    market:'Under 50.5',       odds:1.90, closingOdds:null, result:'loss', cumPL:24.47, sport:'NRL', notes:'Actual bet log. Stake $25.' },
  // NRL R14 — Sun 7 Jun (Wests Tigers vs Penrith Panthers)
  { id:395, date:'2026-06-07', match:'Wests Tigers vs Penrith Panthers',         market:'Under 49.5',       odds:1.91, closingOdds:null, result:'loss', cumPL:23.97, sport:'NRL', notes:'Actual bet log. Stake $25.' },
  // AFL R13 — Sun 7 Jun (Sydney Swans vs St Kilda)
  { id:396, date:'2026-06-07', match:'Sydney Swans vs St Kilda',                 market:'Sydney -29.5',     odds:1.89, closingOdds:null, result:'loss', cumPL:23.47, sport:'AFL', notes:'Actual bet log. Stake $25.' },
  // NRL R14 — Sun 7 Jun (Cronulla Sharks vs St George Illawarra)
  { id:397, date:'2026-06-07', match:'Cronulla Sharks vs St George Illawarra',   market:'Cronulla -10.5',   odds:1.91, closingOdds:null, result:'win',  cumPL:23.83, sport:'NRL', notes:'Actual bet log. Stake $20.' },
  // AFL R13 — Sun 7 Jun (Essendon vs Carlton) — two under lines
  { id:398, date:'2026-06-07', match:'Essendon vs Carlton',                      market:'Under 168.5',      odds:1.89, closingOdds:null, result:'win',  cumPL:24.28, sport:'AFL', notes:'Actual bet log. Stake $25. Under landed.' },
  { id:399, date:'2026-06-07', match:'Essendon vs Carlton',                      market:'Under 173.5',      odds:1.88, closingOdds:null, result:'win',  cumPL:24.72, sport:'AFL', notes:'Actual bet log. Stake $25. Under landed.' },
  // AFL R13 — Mon 8 Jun (Collingwood vs Melbourne) — two bets
  { id:400, date:'2026-06-08', match:'Collingwood vs Melbourne',                 market:'Collingwood Win',  odds:1.90, closingOdds:null, result:'loss', cumPL:24.32, sport:'AFL', notes:'Actual bet log. Stake $20.' },
  { id:401, date:'2026-06-08', match:'Collingwood vs Melbourne',                 market:'Collingwood Win',  odds:1.90, closingOdds:null, result:'loss', cumPL:23.82, sport:'AFL', notes:'Actual bet log. Stake $25.' },
  // NRL R14 — Mon 8 Jun (Canterbury Bulldogs vs Parramatta Eels) — two lines
  { id:402, date:'2026-06-08', match:'Canterbury Bulldogs vs Parramatta Eels',   market:'Bulldogs -5.5',    odds:1.88, closingOdds:null, result:'loss', cumPL:23.32, sport:'NRL', notes:'Actual bet log. Stake $25.' },
  { id:403, date:'2026-06-08', match:'Canterbury Bulldogs vs Parramatta Eels',   market:'Bulldogs -6.5',    odds:1.97, closingOdds:null, result:'loss', cumPL:22.92, sport:'NRL', notes:'Actual bet log. Stake $20.' },
);

// ─── Section 8: Week ending 2026-06-15 (NRL R15 + AFL R14 + Soccer) ──────────
LEGACY_BETS.push(
  // AFL R14 — Thu 11 Jun (Western Bulldogs vs Adelaide Crows)
  { id:404, date:'2026-06-11', match:'Western Bulldogs vs Adelaide Crows',         market:'Adelaide Crows Win',  odds:2.10, closingOdds:null, result:'win',  cumPL:23.47, sport:'AFL',      notes:'Actual bet log. Stake $25. Crows won — model had Crows favoured.' },
  { id:405, date:'2026-06-11', match:'Western Bulldogs vs Adelaide Crows',         market:'Adelaide Crows Win',  odds:2.07, closingOdds:null, result:'win',  cumPL:24.01, sport:'AFL',      notes:'Actual bet log. Stake $25 alt book.' },
  // NRL R15 — Thu 11 Jun (South Sydney Rabbitohs vs Brisbane Broncos)
  { id:406, date:'2026-06-11', match:'South Sydney Rabbitohs vs Brisbane Broncos', market:'Souths Win',           odds:1.48, closingOdds:null, result:'win',  cumPL:24.49, sport:'NRL',      notes:'Actual bet log. Stake $50. T10 Origin: Broncos lost Haas/Walsh/Staggs.' },
  // NRL R15 — Fri 12 Jun (Dolphins vs Sydney Roosters)
  { id:407, date:'2026-06-12', match:'Dolphins vs Sydney Roosters',                market:'Dolphins -3.5',        odds:1.85, closingOdds:null, result:'win',  cumPL:25.34, sport:'NRL',      notes:'Actual bet log. Stake $50. T10 Origin: Roosters lost Tedesco + Walker.' },
  // AFL R14 — Sat 13 Jun (Melbourne Demons vs Essendon Bombers)
  { id:408, date:'2026-06-13', match:'Melbourne Demons vs Essendon Bombers',       market:'Under 162.5',          odds:1.89, closingOdds:null, result:'win',  cumPL:26.23, sport:'AFL',      notes:'Actual bet log. Stake $50. Matrix unders call: Melbourne short rest + June pattern.' },
  { id:409, date:'2026-06-13', match:'Melbourne Demons vs Essendon Bombers',       market:'Over 79.5 2nd Half',   odds:1.89, closingOdds:null, result:'loss', cumPL:25.78, sport:'AFL',      notes:'Actual bet log. Stake $22.50.' },
  // NRL R15 — Sat 13 Jun (New Zealand Warriors vs Cronulla Sharks)
  { id:410, date:'2026-06-13', match:'New Zealand Warriors vs Cronulla Sharks',    market:'Sharks +4.5',          odds:1.87, closingOdds:null, result:'win',  cumPL:26.22, sport:'NRL',      notes:'Actual bet log. Stake $25.' },
  // Soccer — Sun 14 Jun (World Cup)
  { id:411, date:'2026-06-14', match:'Brazil vs Morocco',                          market:'Draw',                 odds:3.60, closingOdds:null, result:'win',  cumPL:27.52, sport:'FOOTBALL', notes:'Actual bet log. Stake $25. World Cup.' },
  { id:412, date:'2026-06-14', match:'Australia vs Turkey',                        market:'Draw',                 odds:3.75, closingOdds:null, result:'loss', cumPL:27.02, sport:'FOOTBALL', notes:'Actual bet log. Stake $25. World Cup.' },
  // AFL R14 — Sun 14 Jun (St Kilda Saints vs GWS Giants)
  { id:413, date:'2026-06-14', match:'St Kilda Saints vs GWS Giants',              market:'GWS Win',              odds:2.10, closingOdds:null, result:'loss', cumPL:26.81, sport:'AFL',      notes:'Actual bet log. Stake $10.38. Saints upset — model had GWS -12.2.' },
  { id:414, date:'2026-06-14', match:'St Kilda Saints vs GWS Giants',              market:'GWS Win',              odds:2.08, closingOdds:null, result:'loss', cumPL:26.31, sport:'AFL',      notes:'Actual bet log. Stake $25.' },
  { id:415, date:'2026-06-14', match:'St Kilda Saints vs GWS Giants',              market:'Under 185.5',          odds:1.89, closingOdds:null, result:'win',  cumPL:26.83, sport:'AFL',      notes:'Actual bet log. Stake $28.95. Matrix unders call paid off.' },
);

// ─── Section 9: Week ending 2026-06-22 (NRL R16 + AFL R15 + Soccer) ──────────
LEGACY_BETS.push(
  // AFL R15 — Thu 18 Jun (Fremantle vs Geelong)
  { id:416, date:'2026-06-18', match:'Fremantle Dockers vs Geelong Cats',          market:'Geelong +33.5 PYL',    odds:1.50, closingOdds:null, result:'win',  cumPL:27.08, sport:'AFL',      notes:'Actual bet log. Stake $25. Pick Your Line safety bet — Freo model -14.9, Geelong got +33.5 cushion. Freo won by 9.' },
  // AFL R15 — Fri 19 Jun (Gold Coast Suns vs Hawthorn)
  { id:417, date:'2026-06-19', match:'Gold Coast Suns vs Hawthorn Hawks',          market:'Under 180.5',          odds:1.90, closingOdds:1.90, result:'loss', cumPL:26.08, sport:'AFL',      notes:'Actual bet log. Stake $50. Model total 175.1 (rules) / 132.1 (ML). Market closed 178.5. Total went over.' },
  { id:418, date:'2026-06-19', match:'Gold Coast Suns vs Hawthorn Hawks',          market:'Hawthorn Win',         odds:1.77, closingOdds:1.70, result:'win',  cumPL:26.47, sport:'AFL',      notes:'Actual bet log. Stake $25. Model fair odds 1.69. Got 1.77 — +4.1% CLV.' },
  // Soccer — Fri 19 Jun (World Cup)
  { id:419, date:'2026-06-19', match:'Mexico vs South Korea',                      market:'Draw',                 odds:3.30, closingOdds:null, result:'loss', cumPL:26.10, sport:'FOOTBALL', notes:'Actual bet log. Stake $18.50. World Cup. CLV exempt.' },
  // AFL R15 — Sat 20 Jun (Adelaide vs Melbourne, Collingwood vs Port Adelaide)
  { id:420, date:'2026-06-20', match:'Adelaide Crows vs Melbourne Demons',         market:'Adelaide -4.5 PYL',    odds:1.82, closingOdds:null, result:'win',  cumPL:26.46, sport:'AFL',      notes:'Actual bet log. Stake $22. Pick Your Line — model Adelaide by 31.8. Market close was -19.5. Custom safe line.' },
  { id:421, date:'2026-06-20', match:'Collingwood Magpies vs Port Adelaide Power', market:'Collingwood -13.5',    odds:1.90, closingOdds:1.90, result:'win',  cumPL:26.91, sport:'AFL',      notes:'Actual bet log. Stake $25. Model Collingwood by 26.8. Won by 26.' },
  // NRL R16 — Sat 20 Jun (Bulldogs vs Sea Eagles, Tigers vs Dolphins)
  { id:422, date:'2026-06-20', match:'Canterbury Bulldogs vs Manly Sea Eagles',    market:'Under 48.5',           odds:1.83, closingOdds:1.88, result:'win',  cumPL:27.74, sport:'NRL',      notes:'Actual bet log. Stake $50. Model fair total 38.6. Bulldogs won 1pt — low scoring game as expected.' },
  { id:423, date:'2026-06-20', match:'Wests Tigers vs Dolphins',                   market:'Tigers Win',           odds:1.83, closingOdds:2.88, result:'loss', cumPL:27.30, sport:'NRL',      notes:'Actual bet log. Stake $22. LIVE BET — pre-game market had Tigers at 2.88. Bet at 1.83 in-play. Tigers lost by 14.' },
  // Soccer — Sat 20 Jun (World Cup)
  { id:424, date:'2026-06-20', match:'USA vs Australia',                           market:'Draw',                 odds:4.10, closingOdds:null, result:'loss', cumPL:26.92, sport:'FOOTBALL', notes:'Actual bet log. Stake $19. World Cup. CLV exempt.' },
  // AFL R15 — Sun 21 Jun (Richmond vs North Melbourne)
  { id:425, date:'2026-06-21', match:'Richmond Tigers vs North Melbourne Kangaroos', market:'NM -17.5',           odds:1.89, closingOdds:1.90, result:'win',  cumPL:27.37, sport:'AFL',      notes:'Actual bet log. Stake $25. Model NM by 18.7 (rules) / 37.3 (ML). Close was -21.5. NM won by 25.' },
  { id:426, date:'2026-06-21', match:'Richmond Tigers vs North Melbourne Kangaroos', market:'Under 176.5',        odds:1.91, closingOdds:1.90, result:'win',  cumPL:28.28, sport:'AFL',      notes:'Actual bet log. Stake $50. Model total 152.6 (rules). Close was 174.5. Under landed easily.' },
  // NRL R16 — Sun 21 Jun (Storm vs Raiders, Roosters vs Sharks)
  { id:427, date:'2026-06-21', match:'Melbourne Storm vs Canberra Raiders',        market:'Raiders +8.5',         odds:1.90, closingOdds:1.89, result:'loss', cumPL:27.28, sport:'NRL',      notes:'Actual bet log. Stake $50. Model Storm -1.9 (Raiders should cover). Storm won by 22 — T10 over-penalised Origin absences.' },
  { id:428, date:'2026-06-21', match:'Melbourne Storm vs Canberra Raiders',        market:'Under 67.5',           odds:2.05, closingOdds:null, result:'win',  cumPL:27.81, sport:'NRL',      notes:'Actual bet log. Stake $25. LIVE BET — standard market line 50.5. Model total 44.3. Under landed.' },
  { id:429, date:'2026-06-21', match:'Sydney Roosters vs Cronulla Sharks',         market:'Sharks Win',           odds:2.53, closingOdds:2.48, result:'loss', cumPL:26.81, sport:'NRL',      notes:'Actual bet log. Stake $50. Model near-50/50 (Roosters +0.3). Roosters won by 19 — T10 again: massive Origin absences underestimated Roosters depth.' },
  // Soccer — Sun 21 Jun (World Cup)
  { id:430, date:'2026-06-21', match:'Tunisia vs Japan',                           market:'Under 2.5 Goals',      odds:1.77, closingOdds:null, result:'loss', cumPL:26.42, sport:'FOOTBALL', notes:'Actual bet log. Stake $19.29. World Cup. CLV exempt.' },
  // Soccer — Mon 22 Jun (World Cup)
  { id:431, date:'2026-06-22', match:'Belgium vs Iran',                            market:'Iran And Draw DC',     odds:2.85, closingOdds:null, result:'win',  cumPL:27.16, sport:'FOOTBALL', notes:'Actual bet log. Stake $20. Double Chance. World Cup. CLV exempt.' },
);

// ─── Section 10: Week ending 2026-06-29 (NRL R17 + AFL R16 + Soccer) ─────────
LEGACY_BETS.push(
  // Soccer — Wed 24 Jun (World Cup)
  { id:432, date:'2026-06-24', match:'Panama vs Croatia',                           market:'Panama And Draw DC',   odds:2.90, closingOdds:null, result:'loss', cumPL:26.88, sport:'FOOTBALL', notes:'Actual bet log. Stake $14. Double Chance. No return.' },
  // NRL R17 — Thu 25 Jun (Parramatta vs South Sydney)
  { id:433, date:'2026-06-25', match:'Parramatta Eels vs South Sydney Rabbitohs',   market:'Souths -5.5',          odds:1.85, closingOdds:1.85, clv:0.0,  clvLabel:'0.0 pts',   result:'win',  cumPL:27.25, sport:'NRL',      notes:'Actual bet log. Stake $21.82. Return $40.37. Model Souths by 10.3. Closed Souths -5.5.' },
  // NRL R17 — Fri 26 Jun (Gold Coast vs Canterbury)
  { id:434, date:'2026-06-26', match:'Gold Coast Titans vs Canterbury Bulldogs',    market:'Under 46.5',           odds:1.90, closingOdds:1.87, clv:2.0,  clvLabel:'+2.0 pts',  result:'win',  cumPL:28.15, sport:'NRL',      notes:'Actual bet log. Stake $50. Return $95.00. Model total 35.7. Closed total 44.5.' },
  { id:435, date:'2026-06-26', match:'Gold Coast Titans vs Canterbury Bulldogs',    market:'Bulldogs 1 to 12',     odds:3.05, closingOdds:null, result:'loss', cumPL:28.15, sport:'NRL',      notes:'Actual bet log. Bonus bet stake $12.32. No cash P&L impact.' },
  // AFL R16 — Fri 26 Jun (Hawthorn vs GWS)
  { id:436, date:'2026-06-26', match:'Hawthorn Hawks vs GWS Giants',                market:'Hawthorn -19.5',       odds:1.90, closingOdds:1.90, clv:2.0,  clvLabel:'+2.0 pts',  result:'loss', cumPL:27.65, sport:'AFL',      notes:'Actual bet log. Stake $25. Model Hawthorn by 28.0. No return. Closed Hawthorn -21.5.' },
  // AFL R16 — Sat 27 Jun (Collingwood vs Richmond)
  { id:437, date:'2026-06-27', match:'Collingwood Magpies vs Richmond Tigers',      market:'Under 170.5',          odds:1.87, closingOdds:1.90, clv:6.0,  clvLabel:'+6.0 pts',  result:'loss', cumPL:26.65, sport:'AFL',      notes:'Actual bet log. Stake $50. No return. Model total 155.1, but game cleared the number. Closed total 164.5.' },
  // NRL R17 — Sat 27 Jun (Manly vs Melbourne)
  { id:438, date:'2026-06-27', match:'Manly Sea Eagles vs Melbourne Storm',         market:'Manly -3.5 PYL',       odds:1.73, closingOdds:null, clv:2.0,  clvLabel:'+2.0 pts',  result:'win',  cumPL:27.02, sport:'NRL',      notes:'Actual bet log. Stake $25. Return $43.25. Model Manly by 13.1. Standard line closed Manly -5.5; PYL price not apples-to-apples.' },
  // AFL R16 — Sat 27 Jun (Carlton vs West Coast)
  { id:439, date:'2026-06-27', match:'Carlton Blues vs West Coast Eagles',          market:'Carlton -32.5',        odds:1.90, closingOdds:1.89, clv:4.0,  clvLabel:'+4.0 pts',  result:'win',  cumPL:27.38, sport:'AFL',      notes:'Actual bet log. Stake $20.23. Return $38.44. Model Carlton by 30.9. Closed Carlton -36.5.' },
  // AFL R16 — Sun 28 Jun (North Melbourne vs Essendon)
  { id:440, date:'2026-06-28', match:'North Melbourne Kangaroos vs Essendon Bombers', market:'North Melbourne -15.5', odds:1.90, closingOdds:1.91, clv:-2.0, clvLabel:'-2.0 pts',  result:'loss', cumPL:27.06, sport:'AFL',      notes:'Actual bet log. Stake $15.82. Model North Melbourne by 29.1. No return. Closed North Melbourne -13.5.' },
  // Soccer — Sun 28 Jun (World Cup)
  { id:441, date:'2026-06-28', match:'Croatia vs Ghana',                            market:'Draw',                 odds:3.20, closingOdds:null, result:'loss', cumPL:26.60, sport:'FOOTBALL', notes:'Actual bet log. Stake $23. Win-Draw-Win. No return.' },
);

// ─── AFL Betting Model (mid-April 2026 onwards) ──────────────────────────────
// All AFL bets from LEGACY_BETS with date >= 2026-04-15.
// plUnits = (stake/$50) × (odds-1) for win, -(stake/$50) for loss.
// Bets pre-id:326 have no explicit stake recorded — assumed 1.0u.
export const AFL_MODEL_BETS: ModelBet[] = [
  // R5-R6 (Apr 15-18)
  // id:1 Collingwood close=1.60 (Carlton won, Coll drifted from 2.12 to 1.60 favourite)
  // id:2 Carlton close=2.35 (live bet on Carlton at 2.6, Carlton closed 2.35)
  // id:5 Port close=7.00 (Hawthorn hosted Port; Hawthorn closed 1.10, Port drifted to 7.00)
  { id:1,  date:'2026-04-15', match:'Collingwood vs Carlton',                  market:'Game 2.12',            predictedLine:null, takenPrice:2.12, closingPrice:1.60, result:'loss', plUnits:-1.00,  runningTotal:-1.00  },
  { id:2,  date:'2026-04-15', match:'Collingwood vs Carlton',                  market:'Game 2.6',             predictedLine:null, takenPrice:2.60, closingPrice:2.35, result:'win',  plUnits:1.60,   runningTotal:0.60   },
  { id:3,  date:'2026-04-16', match:'GWS vs Sydney',                           market:'Under 170.5',          predictedLine:null, takenPrice:1.90, closingPrice:1.90, result:'loss', plUnits:-1.00,  runningTotal:-0.40  },
  { id:4,  date:'2026-04-17', match:'Geelong vs Western Bulldogs',             market:'Geelong -10.5',        predictedLine:null, takenPrice:1.90, closingPrice:1.90, result:'win',  plUnits:0.90,   runningTotal:0.50   },
  { id:5,  date:'2026-04-17', match:'Port Adelaide vs Hawthorn',               market:'Port Adelaide Win',    predictedLine:null, takenPrice:3.00, closingPrice:7.00, result:'win',  plUnits:2.00,   runningTotal:2.50   },
  { id:6,  date:'2026-04-18', match:'Brisbane vs Melbourne',                   market:'Over 168.5',           predictedLine:189.5, takenPrice:1.90, closingPrice:1.80, result:'loss', plUnits:-1.00,  runningTotal:1.50   },
  { id:7,  date:'2026-04-18', match:'Brisbane vs Melbourne',                   market:'Brisbane Win (Live)',  predictedLine:1.37, takenPrice:4.20, closingPrice:1.25, result:'win',  plUnits:3.20,   runningTotal:4.70   },
  // R7 (Apr 24-25)
  { id:8,  date:'2026-04-24', match:'Fremantle vs Carlton',                    market:'Under 159.5',          predictedLine:145.6, takenPrice:1.90, closingPrice:1.90, result:'loss', plUnits:-1.00,  runningTotal:3.70   },
  { id:9,  date:'2026-04-25', match:'Eagles vs Saints',                        market:'Over 153.5',           predictedLine:168.1, takenPrice:1.90, closingPrice:1.95, result:'loss', plUnits:-1.00,  runningTotal:2.70   },
  { id:10, date:'2026-04-25', match:'Eagles vs Saints',                        market:'Game 1.8',             predictedLine:1.11, takenPrice:1.80, closingPrice:1.1, result:'win',  plUnits:0.80,   runningTotal:3.50   },
  { id:11, date:'2026-04-25', match:'Brisbane vs Adelaide Crows',              market:'Under 189.5',          predictedLine:154, takenPrice:2.00, closingPrice:1.90, result:'loss', plUnits:-1.00,  runningTotal:2.50   },
  // R8 (Apr 30 - May 2)
  { id:12, date:'2026-04-30', match:'Adelaide vs Port Adelaide',               market:'Under 149.5',          predictedLine:168, takenPrice:1.90, closingPrice:1.90, result:'loss', plUnits:-1.00,  runningTotal:1.50   },
  { id:13, date:'2026-05-01', match:'Western Bulldogs vs Fremantle',           market:'Bulldogs Win',         predictedLine:1.67, takenPrice:3.21, closingPrice:3.15, result:'loss', plUnits:-0.66,  runningTotal:0.84   },
  { id:14, date:'2026-05-01', match:'Adelaide vs Port Adelaide',               market:'Adelaide -9.5',        predictedLine:55.7, takenPrice:1.89, closingPrice:1.95, result:'loss', plUnits:-1.00,  runningTotal:-0.16  },
  { id:15, date:'2026-05-02', match:'Carlton vs St Kilda',                     market:'Carlton Win',          predictedLine:1.75, takenPrice:2.55, closingPrice:2.45, result:'loss', plUnits:-0.80,  runningTotal:-0.96  },
  { id:16, date:'2026-05-02', match:'Carlton vs St Kilda',                     market:'Under 183.5',          predictedLine:170.9, takenPrice:1.89, closingPrice:1.85, result:'win',  plUnits:0.89,   runningTotal:-0.07  },
  // R9 (May 8-9)
  { id:17, date:'2026-05-08', match:'Port Adelaide vs Western Bulldogs',       market:'Port Adelaide Win',    predictedLine:2.94, takenPrice:1.96, closingPrice:2.00, result:'loss', plUnits:-1.00,  runningTotal:-1.07  },
  { id:18, date:'2026-05-09', match:'Gold Coast vs St Kilda',                  market:'Gold Coast -17.5',     predictedLine:48.9, takenPrice:1.89, closingPrice:1.85, result:'win',  plUnits:0.89,   runningTotal:-0.18  },
  { id:19, date:'2026-05-09', match:'Geelong vs Collingwood',                  market:'Geelong -11.5',        predictedLine:23.2, takenPrice:1.89, closingPrice:1.90, result:'win',  plUnits:0.89,   runningTotal:0.71   },
  { id:20, date:'2026-05-09', match:'GWS vs Essendon',                         market:'Under 193.5',          predictedLine:174.3, takenPrice:1.87, closingPrice:1.85, result:'win',  plUnits:0.87,   runningTotal:1.58   },
  // R10 (May 15-16)
  { id:21, date:'2026-05-15', match:'Sydney Swans vs Collingwood',             market:'Under 181.5',          predictedLine:null, takenPrice:1.86, closingPrice:2.00, result:'win',  plUnits:0.86,   runningTotal:2.44   },
  { id:22, date:'2026-05-15', match:'Sydney Swans vs Collingwood',             market:'Collingwood +35.5',    predictedLine:null, takenPrice:1.91, closingPrice:1.90, result:'win',  plUnits:0.46,   runningTotal:2.90   },
  { id:23, date:'2026-05-15', match:'Gold Coast vs Port Adelaide',             market:'Gold Coast -26.5',     predictedLine:null, takenPrice:1.90, closingPrice:1.90, result:'loss', plUnits:-1.00,  runningTotal:1.90   },
  { id:24, date:'2026-05-16', match:'Carlton vs Western Bulldogs',             market:'Carlton Win',          predictedLine:null, takenPrice:2.56, closingPrice:2.35, result:'win',  plUnits:0.78,   runningTotal:2.68   },
  { id:25, date:'2026-05-16', match:'Melbourne vs Hawthorn',                   market:'Hawthorn -18.5',       predictedLine:null, takenPrice:1.91, closingPrice:1.95, result:'loss', plUnits:-1.00,  runningTotal:1.68   },
  { id:26, date:'2026-05-16', match:'Adelaide vs North Melbourne',             market:'Adelaide -18.5',       predictedLine:null, takenPrice:1.90, closingPrice:1.85, result:'win',  plUnits:0.90,   runningTotal:2.58   },
  // R11 (May 21-23)
  { id:27, date:'2026-05-21', match:'Hawthorn vs Adelaide Crows',             market:'Hawthorn Win',          predictedLine:1.29, takenPrice:1.41, closingPrice:1.55, result:'win',  plUnits:0.45,   runningTotal:3.03   },
  { id:28, date:'2026-05-21', match:'Hawthorn vs Adelaide Crows',             market:'Adelaide Crows Win',    predictedLine:4.48, takenPrice:2.88, closingPrice:2.45, result:'loss', plUnits:-0.50,  runningTotal:2.53   },
  { id:29, date:'2026-05-21', match:'Hawthorn vs Adelaide Crows',             market:'Hawthorn -15.5',        predictedLine:27.4, takenPrice:1.90, closingPrice:1.95, result:'loss', plUnits:-0.50,  runningTotal:2.03   },
  { id:30, date:'2026-05-21', match:'Hawthorn vs Adelaide Crows',             market:'Adelaide +19.5',        predictedLine:27.4, takenPrice:1.89, closingPrice:1.85, result:'win',  plUnits:0.45,   runningTotal:2.48   },
  { id:31, date:'2026-05-22', match:'Richmond vs Essendon',                   market:'Under 176.5',           predictedLine:150.8, takenPrice:1.88, closingPrice:2, result:'win',  plUnits:0.44,   runningTotal:2.92   },
  { id:32, date:'2026-05-23', match:'Geelong Cats vs Sydney Swans',           market:'Swans +10.5',           predictedLine:5.8, takenPrice:1.90, closingPrice:1.85, result:'loss', plUnits:-0.50,  runningTotal:2.42   },
  { id:33, date:'2026-05-23', match:'Collingwood vs West Coast Eagles',       market:'Under 180.5',           predictedLine:184.4, takenPrice:1.87, closingPrice:1.99, result:'win',  plUnits:0.44,   runningTotal:2.86   },
  // R12 (May 28 - Jun 1)
  { id:34, date:'2026-05-28', match:'St Kilda vs Hawthorn',                   market:'Hawthorn -19.5',        predictedLine:30.4, takenPrice:1.90, closingPrice:1.90, result:'win',  plUnits:0.45,   runningTotal:3.31   },
  { id:35, date:'2026-05-29', match:'Carlton vs Geelong Cats',                market:'Over 178.5',            predictedLine:186.9, takenPrice:1.89, closingPrice:1.80, result:'loss', plUnits:-0.50,  runningTotal:2.81   },
  { id:36, date:'2026-05-30', match:'Western Bulldogs vs Collingwood',        market:'Collingwood Win',        predictedLine:2.09, takenPrice:2.26, closingPrice:2.35, result:'loss', plUnits:-0.50,  runningTotal:2.31   },
  { id:37, date:'2026-05-31', match:'West Coast Eagles vs Essendon',          market:'Essendon Win (cash out)', predictedLine:1.98, takenPrice:2.31, closingPrice:2.80, result:'win',  plUnits:0.40,   runningTotal:2.71   },
  { id:38, date:'2026-05-31', match:'West Coast Eagles vs Essendon',          market:'Essendon Win',           predictedLine:1.98, takenPrice:2.39, closingPrice:2.80, result:'loss', plUnits:-0.50,  runningTotal:2.21   },
  // R13 (Jun 5-8)
  { id:39, date:'2026-06-05', match:'Hawthorn vs Western Bulldogs',           market:'Hawthorn -11.5',         predictedLine:38.7, takenPrice:1.90, closingPrice:1.95, result:'loss', plUnits:-0.50,  runningTotal:1.71   },
  { id:40, date:'2026-06-05', match:'Hawthorn vs Western Bulldogs',           market:'Hawthorn -20.5',         predictedLine:38.7, takenPrice:1.91, closingPrice:1.95, result:'loss', plUnits:-0.40,  runningTotal:1.31   },
  { id:41, date:'2026-06-05', match:'Hawthorn vs Western Bulldogs',           market:'Hawthorn -20.5',         predictedLine:38.7, takenPrice:1.91, closingPrice:1.95, result:'loss', plUnits:-0.50,  runningTotal:0.81   },
  { id:42, date:'2026-06-06', match:'Gold Coast Suns vs Brisbane Lions',      market:'Under 188.5',            predictedLine:176.4, takenPrice:1.88, closingPrice:2.04, result:'win',  plUnits:0.44,   runningTotal:1.25   },
  { id:43, date:'2026-06-06', match:'West Coast Eagles vs Port Adelaide',     market:'Port Adelaide -6.5',     predictedLine:25.5, takenPrice:1.88, closingPrice:1.90, result:'loss', plUnits:-0.60,  runningTotal:0.65   },
  { id:44, date:'2026-06-06', match:'West Coast Eagles vs Port Adelaide',     market:'Port Adelaide -7.5',     predictedLine:25.5, takenPrice:1.90, closingPrice:1.90, result:'loss', plUnits:-0.50,  runningTotal:0.15   },
  { id:45, date:'2026-06-07', match:'Sydney Swans vs St Kilda',               market:'Sydney -29.5',           predictedLine:54.4, takenPrice:1.89, closingPrice:1.95, result:'loss', plUnits:-0.50,  runningTotal:-0.35  },
  { id:46, date:'2026-06-07', match:'Essendon vs Carlton',                    market:'Under 168.5',            predictedLine:160.5, takenPrice:1.89, closingPrice:2.00, result:'win',  plUnits:0.45,   runningTotal:0.10   },
  { id:47, date:'2026-06-07', match:'Essendon vs Carlton',                    market:'Under 173.5',            predictedLine:160.5, takenPrice:1.88, closingPrice:2, result:'win',  plUnits:0.44,   runningTotal:0.54   },
  { id:48, date:'2026-06-08', match:'Collingwood vs Melbourne',               market:'Collingwood Win',         predictedLine:1.38, takenPrice:1.90, closingPrice:1.90, result:'loss', plUnits:-0.40,  runningTotal:0.14   },
  { id:49, date:'2026-06-08', match:'Collingwood vs Melbourne',               market:'Collingwood Win',         predictedLine:1.38, takenPrice:1.90, closingPrice:1.90, result:'loss', plUnits:-0.50,  runningTotal:-0.36  },
  // R14 (Jun 11-14) — closes from web research (Bet365). Adelaide 2.07, GWS 2.08.
  // Melb/Ess total closed ~175.5; Under 162.5 close=1.91 (standard-line approx, 13pt alt gap). SK/GWS total Bet365 184.5 under=1.91.
  { id:50, date:'2026-06-11', match:'Western Bulldogs vs Adelaide Crows',     market:'Adelaide Crows Win',      predictedLine:1.72, takenPrice:2.10, closingPrice:2.07, result:'win',  plUnits:0.55,   runningTotal:0.19   },
  { id:51, date:'2026-06-11', match:'Western Bulldogs vs Adelaide Crows',     market:'Adelaide Crows Win',      predictedLine:1.72, takenPrice:2.07, closingPrice:2.07, result:'win',  plUnits:0.54,   runningTotal:0.73   },
  { id:52, date:'2026-06-13', match:'Melbourne Demons vs Essendon Bombers',   market:'Under 162.5',             predictedLine:169.9, takenPrice:1.89, closingPrice:1.91, result:'win',  plUnits:0.89,   runningTotal:1.62   },
  { id:53, date:'2026-06-13', match:'Melbourne Demons vs Essendon Bombers',   market:'Over 79.5 2nd Half',      predictedLine:null, takenPrice:1.89, closingPrice:null, result:'loss', plUnits:-0.45,  runningTotal:1.17   },
  { id:54, date:'2026-06-14', match:'St Kilda Saints vs GWS Giants',          market:'GWS Win',                 predictedLine:1.58, takenPrice:2.10, closingPrice:2.08, result:'loss', plUnits:-0.21,  runningTotal:0.96   },
  { id:55, date:'2026-06-14', match:'St Kilda Saints vs GWS Giants',          market:'GWS Win',                 predictedLine:1.58, takenPrice:2.08, closingPrice:2.08, result:'loss', plUnits:-0.50,  runningTotal:0.46   },
  { id:56, date:'2026-06-14', match:'St Kilda Saints vs GWS Giants',          market:'Under 185.5',             predictedLine:187.8, takenPrice:1.89, closingPrice:1.91, result:'win',  plUnits:0.52,   runningTotal:0.98   },
  // R15 (Jun 18-21) — 6W 1L. PYL bets both won with large cushions. NM total model-accurate.
  { id:57, date:'2026-06-18', match:'Fremantle Dockers vs Geelong Cats',          market:'Geelong +33.5 PYL',       predictedLine:14.9,  takenPrice:1.50, closingPrice:null, result:'win',  plUnits:0.25,   runningTotal:1.23   },
  { id:58, date:'2026-06-19', match:'Gold Coast Suns vs Hawthorn Hawks',          market:'Under 180.5',             predictedLine:175.1, takenPrice:1.90, closingPrice:1.90, result:'loss', plUnits:-1.00,  runningTotal:0.23   },
  { id:59, date:'2026-06-19', match:'Gold Coast Suns vs Hawthorn Hawks',          market:'Hawthorn Win',            predictedLine:1.69,  takenPrice:1.77, closingPrice:1.70, result:'win',  plUnits:0.39,   runningTotal:0.62   },
  { id:60, date:'2026-06-20', match:'Adelaide Crows vs Melbourne Demons',         market:'Adelaide -4.5 PYL',       predictedLine:31.8,  takenPrice:1.82, closingPrice:null, result:'win',  plUnits:0.36,   runningTotal:0.98   },
  { id:61, date:'2026-06-20', match:'Collingwood Magpies vs Port Adelaide Power', market:'Collingwood -13.5',       predictedLine:26.8,  takenPrice:1.90, closingPrice:1.90, result:'win',  plUnits:0.45,   runningTotal:1.43   },
  { id:62, date:'2026-06-21', match:'Richmond Tigers vs North Melbourne Kangaroos', market:'NM -17.5',              predictedLine:-18.7, takenPrice:1.89, closingPrice:1.90, result:'win',  plUnits:0.45,   runningTotal:1.88   },
  { id:63, date:'2026-06-21', match:'Richmond Tigers vs North Melbourne Kangaroos', market:'Under 176.5',           predictedLine:152.6, takenPrice:1.91, closingPrice:1.90, result:'win',  plUnits:0.91,   runningTotal:2.79   },
  // R16 (Jun 26-28)
  { id:64, date:'2026-06-26', match:'Hawthorn Hawks vs GWS Giants',                market:'Hawthorn -19.5',         predictedLine:28.0,  takenPrice:1.90, closingPrice:1.90, clv:2.0,  clvLabel:'+2.0 pts', result:'loss', plUnits:-0.50,  runningTotal:2.29   },
  { id:65, date:'2026-06-27', match:'Carlton Blues vs West Coast Eagles',          market:'Carlton -32.5',          predictedLine:30.9,  takenPrice:1.90, closingPrice:1.89, clv:4.0,  clvLabel:'+4.0 pts', result:'win',  plUnits:0.36,   runningTotal:2.65   },
  { id:66, date:'2026-06-27', match:'Collingwood Magpies vs Richmond Tigers',      market:'Under 170.5',            predictedLine:155.1, takenPrice:1.87, closingPrice:1.90, clv:6.0,  clvLabel:'+6.0 pts', result:'loss', plUnits:-1.00,  runningTotal:1.65   },
  { id:67, date:'2026-06-28', match:'North Melbourne Kangaroos vs Essendon Bombers', market:'North Melbourne -15.5', predictedLine:29.1,  takenPrice:1.90, closingPrice:1.91, clv:-2.0, clvLabel:'-2.0 pts', result:'loss', plUnits:-0.32,  runningTotal:1.33   },
];

// ─── NRL Betting Model (separate tab) ────────────────────────────────────────
// 26 NRL-only bets. predictedLine = model's fair-odds or predicted total score.
// plUnits = individual bet P&L per 1 unit staked. runningTotal = cumulative.
export const MODEL_BETS: ModelBet[] = [
  { id:1,  date:'2026-03-19', match:'Canberra Raiders vs Canterbury Bulldogs', market:'Canberra -1.5',     predictedLine:1.74, takenPrice:1.9,  closingPrice:1.86, result:'loss', plUnits:-1,    runningTotal:-1    },
  { id:2,  date:'2026-03-21', match:'Parramatta vs St George',                 market:'Parramatta Win',    predictedLine:1.35, takenPrice:1.5,  closingPrice:1.5,  result:'win',  plUnits:0.5,   runningTotal:-0.5  },
  { id:3,  date:'2026-03-20', match:'Sydney Roosters vs Penrith Panthers',      market:'Under 45.5',        predictedLine:42,   takenPrice:1.95, closingPrice:1.95, result:'win',  plUnits:0.95,  runningTotal:0.45  },
  { id:4,  date:'2026-03-22', match:'Parramatta vs St George',                 market:'Under 52.5',        predictedLine:46,   takenPrice:1.95, closingPrice:1.95, result:'win',  plUnits:0.95,  runningTotal:1.4   },
  { id:5,  date:'2026-03-22', match:'Cowboys vs Titans',                       market:'Cowboys +3.5',      predictedLine:9,    takenPrice:1.9,  closingPrice:1.95, result:'win',  plUnits:0.9,   runningTotal:2.35  },
  { id:6,  date:'2026-03-21', match:'Newcastle vs Warriors',                   market:'Warriors Win',      predictedLine:1.34, takenPrice:1.5,  closingPrice:1.5,  result:'win',  plUnits:0.5,   runningTotal:2.85  },
  { id:7,  date:'2026-03-21', match:'Souths vs Tigers',                        market:'Under 52.5',        predictedLine:null, takenPrice:1.9,  closingPrice:1.9,  result:'win',  plUnits:0.9,   runningTotal:3.75  },
  { id:8,  date:'2026-03-26', match:'Manly vs Roosters',                       market:'Manly Win',         predictedLine:2.25, takenPrice:2.85, closingPrice:2.5,  result:'loss', plUnits:-1,    runningTotal:2.75  },
  { id:9,  date:'2026-03-27', match:'Broncos vs Dolphins',                     market:'Dolphins +6.5',     predictedLine:1.7,  takenPrice:2.0,  closingPrice:2.0,  result:'loss', plUnits:-1,    runningTotal:1.75  },
  { id:10, date:'2026-03-28', match:'Raiders vs Cronulla',                     market:'Raiders -1.5',      predictedLine:1.7,  takenPrice:2.0,  closingPrice:2.0,  result:'loss', plUnits:-1,    runningTotal:0.75  },
  { id:11, date:'2026-04-04', match:'St George vs Cowboys',                    market:'St George Win',     predictedLine:2.2,  takenPrice:2.05, closingPrice:2.05, result:'loss', plUnits:-1,    runningTotal:-0.25 },
  { id:12, date:'2026-04-04', match:'Newcastle vs Canberra',                   market:'Newcastle Win',     predictedLine:2.0,  takenPrice:2.4,  closingPrice:2.4,  result:'win',  plUnits:1.4,   runningTotal:1.15  },
  { id:13, date:'2026-04-05', match:'Sharks vs Warriors',                      market:'Warriors Win',      predictedLine:2.0,  takenPrice:2.36, closingPrice:2.3,  result:'loss', plUnits:-1,    runningTotal:0.15  },
  { id:14, date:'2026-04-04', match:'Broncos vs Cowboys',                      market:'Broncos Win',       predictedLine:1.3,  takenPrice:1.9,  closingPrice:1.9,  result:'loss', plUnits:-1,    runningTotal:-0.85 },
  { id:15, date:'2026-04-05', match:'Melbourne vs Warriors',                   market:'Melbourne Win',     predictedLine:1.3,  takenPrice:1.5,  closingPrice:1.35, result:'loss', plUnits:-1,    runningTotal:-1.85 },
  { id:16, date:'2026-04-06', match:'Sharks vs Roosters',                      market:'Sharks Win',        predictedLine:1.7,  takenPrice:2.05, closingPrice:2.1,  result:'loss', plUnits:-1,    runningTotal:-2.85 },
  { id:17, date:'2026-04-10', match:'Broncos vs Cowboys',                      market:'Under 49.5',        predictedLine:2.0,  takenPrice:2.0,  closingPrice:2.0,  result:'loss', plUnits:-1,    runningTotal:-3.85 },
  { id:18, date:'2026-04-10', match:'Parramatta vs Gold Coast',                market:'Parramatta Win',    predictedLine:1.7,  takenPrice:1.8,  closingPrice:1.65, result:'loss', plUnits:-1,    runningTotal:-4.85 },
  { id:19, date:'2026-04-16', match:'North Queensland vs Manly',               market:'Under 53.5',        predictedLine:50.5, takenPrice:1.9,  closingPrice:1.85, result:'win',  plUnits:0.9,   runningTotal:-3.95 },
  { id:20, date:'2026-04-16', match:'Dolphins vs Penrith',                     market:'Under 51.5',        predictedLine:48.5, takenPrice:1.9,  closingPrice:1.85, result:'win',  plUnits:0.9,   runningTotal:-3.05 },
  { id:21, date:'2026-04-16', match:'Parramatta vs Canterbury (+13.5)',        market:'Parramatta +13.5',  predictedLine:6.5,  takenPrice:1.9,  closingPrice:1.85, result:'win',  plUnits:0.9,   runningTotal:-2.15 },
  { id:22, date:'2026-04-16', match:'Rabbitohs vs St George',                  market:'Under 51.5',        predictedLine:null, takenPrice:1.9,  closingPrice:1.95, result:'win',  plUnits:0.9,   runningTotal:-1.25 },
  { id:23, date:'2026-04-16', match:'Wests Tigers vs Brisbane',                market:'Brisbane Win',      predictedLine:2.0,  takenPrice:2.5,  closingPrice:2.45, result:'win',  plUnits:1.5,   runningTotal:0.25  },
  { id:24, date:'2026-04-24', match:'Wests Tigers vs Canberra',                market:'Canberra Win',      predictedLine:2.0,  takenPrice:2.0,  closingPrice:2.65, result:'loss', plUnits:-1,    runningTotal:-0.75 },
  { id:25, date:'2026-04-24', match:'Wests Tigers vs Canberra',                market:'Under 52.5',        predictedLine:51.5, takenPrice:1.9,  closingPrice:2.05, result:'win',  plUnits:0.90,  runningTotal:0.15  },
  { id:26, date:'2026-04-24', match:'St George vs Penrith',                    market:'St George Win',     predictedLine:2.2,  takenPrice:1.9,  closingPrice:9.50, result:'loss', plUnits:-1,    runningTotal:-0.85 },
  // R11 Magic Round
  { id:27, date:'2026-05-15', match:'Cronulla vs Canterbury',                  market:'Under 49',          predictedLine:49.0, takenPrice:1.90, closingPrice:2.12, result:'loss', plUnits:-1,    runningTotal:-1.85 },
  { id:28, date:'2026-05-15', match:'Rabbitohs vs Dolphins',                   market:'Dolphins Win',      predictedLine:1.86, takenPrice:1.85, closingPrice:1.74, result:'win',  plUnits:0.85,  runningTotal:-1.00 },
  { id:29, date:'2026-05-16', match:'Roosters vs Cowboys',                     market:'Cowboys +16.5',     predictedLine:7.6,  takenPrice:1.74, closingPrice:1.85, result:'win',  plUnits:0.74,  runningTotal:-0.26 },
  { id:30, date:'2026-05-17', match:'Warriors vs Broncos',                     market:'Warriors -2.5',     predictedLine:13.0, takenPrice:1.91, closingPrice:1.90, result:'win',  plUnits:0.91,  runningTotal:0.65  },
  { id:31, date:'2026-05-17', match:'Panthers vs Dragons',                     market:'Under 56.5',        predictedLine:46.5, takenPrice:1.82, closingPrice:2.12, result:'win',  plUnits:0.82,  runningTotal:1.47  },
  // R12
  { id:32, date:'2026-05-22', match:'Canterbury Bulldogs vs Melbourne Storm',  market:'Bulldogs -3.5',     predictedLine:1.4,  takenPrice:1.90, closingPrice:1.90, result:'win',  plUnits:0.90,  runningTotal:2.37  },
  { id:33, date:'2026-05-24', match:'Cowboys vs South Sydney Rabbitohs',       market:'Cowboys Win',       predictedLine:1.56, takenPrice:1.67, closingPrice:1.58, result:'win',  plUnits:0.67,  runningTotal:3.04  },
  { id:34, date:'2026-05-24', match:'Cowboys vs South Sydney Rabbitohs',       market:'Cowboys -2.5',      predictedLine:4.3,  takenPrice:1.90, closingPrice:1.80, result:'win',  plUnits:0.90,  runningTotal:3.94  },
  // R13 — ids 35-41 all 0.5u stakes ($25)
  { id:35, date:'2026-05-29', match:'Cronulla Sharks vs Manly Sea Eagles',     market:'Cronulla Win',      predictedLine:1.72, takenPrice:1.87, closingPrice:1.80, result:'win',  plUnits:0.87,  runningTotal:4.81  },
  { id:36, date:'2026-05-31', match:'Penrith Panthers vs NZ Warriors',         market:'Under 46.5',        predictedLine:44.1, takenPrice:1.84, closingPrice:2.08, result:'win',  plUnits:0.42,  runningTotal:5.23  },
  { id:37, date:'2026-05-31', match:'Penrith Panthers vs NZ Warriors',         market:'Under 47.5',        predictedLine:44.1, takenPrice:1.90, closingPrice:2.08, result:'win',  plUnits:0.45,  runningTotal:5.68  },
  { id:38, date:'2026-05-31', match:'Penrith Panthers vs NZ Warriors',         market:'Panthers -3.5',     predictedLine:12.7, takenPrice:1.83, closingPrice:1.95, result:'loss', plUnits:-0.50, runningTotal:5.18  },
  { id:39, date:'2026-05-31', match:'Penrith Panthers vs NZ Warriors',         market:'Panthers -5.5',     predictedLine:12.7, takenPrice:1.72, closingPrice:1.95, result:'loss', plUnits:-0.50, runningTotal:4.68  },
  { id:40, date:'2026-05-30', match:'Wests Tigers vs Canterbury Bulldogs',     market:'Over 48.5',         predictedLine:48.5, takenPrice:1.90, closingPrice:1.95, result:'loss', plUnits:-0.50, runningTotal:4.18  },
  { id:41, date:'2026-05-31', match:'Canberra Raiders vs Cowboys',             market:'Cowboys +4.5',      predictedLine:1.3,  takenPrice:1.73, closingPrice:1.95, result:'loss', plUnits:-0.50, runningTotal:3.68  },
  // R14 — all 0.5u stakes ($25/$20)
  { id:42, date:'2026-06-05', match:'Melbourne Storm vs Newcastle Knights',     market:'Newcastle +4.5',    predictedLine:0.6,  takenPrice:1.85, closingPrice:1.90, result:'win',  plUnits:0.43,  runningTotal:4.11  },
  { id:43, date:'2026-06-06', match:'North Queensland Cowboys vs Dolphins',     market:'Cowboys Win',       predictedLine:2.64, takenPrice:2.38, closingPrice:2.65, result:'loss', plUnits:-0.50, runningTotal:3.61  },
  { id:44, date:'2026-06-06', match:'Brisbane Broncos vs Gold Coast Titans',    market:'Under 50.5',        predictedLine:39.7, takenPrice:1.90, closingPrice:2.08, result:'loss', plUnits:-0.50, runningTotal:3.11  },
  { id:45, date:'2026-06-07', match:'Wests Tigers vs Penrith Panthers',         market:'Under 49.5',        predictedLine:46.4, takenPrice:1.91, closingPrice:2.20, result:'loss', plUnits:-0.50, runningTotal:2.61  },
  { id:46, date:'2026-06-07', match:'Cronulla Sharks vs St George Illawarra',   market:'Cronulla -10.5',    predictedLine:16.7, takenPrice:1.91, closingPrice:1.90, result:'win',  plUnits:0.46,  runningTotal:3.07  },
  { id:47, date:'2026-06-08', match:'Canterbury Bulldogs vs Parramatta Eels',   market:'Bulldogs -5.5',     predictedLine:9.6,  takenPrice:1.88, closingPrice:1.85, result:'loss', plUnits:-0.50, runningTotal:2.57  },
  { id:48, date:'2026-06-08', match:'Canterbury Bulldogs vs Parramatta Eels',   market:'Bulldogs -6.5',     predictedLine:9.6,  takenPrice:1.97, closingPrice:1.85, result:'loss', plUnits:-0.50, runningTotal:2.07  },
  // R15 — all 3 bets won. T10 Origin overlay fired (Broncos & Roosters depleted).
  { id:49, date:'2026-06-11', match:'South Sydney Rabbitohs vs Brisbane Broncos', market:'Souths Win',         predictedLine:1.19, takenPrice:1.48, closingPrice:1.43, result:'win',  plUnits:0.48,  runningTotal:2.55  },
  { id:50, date:'2026-06-12', match:'Dolphins vs Sydney Roosters',                market:'Dolphins -3.5',      predictedLine:6.7,  takenPrice:1.85, closingPrice:1.548, result:'win',  plUnits:0.85,  runningTotal:3.40  },
  { id:51, date:'2026-06-13', match:'New Zealand Warriors vs Cronulla Sharks',    market:'Sharks +4.5 (Live)', predictedLine:-10.4, takenPrice:1.87, closingPrice:null,  result:'win',  plUnits:0.44,  runningTotal:3.84  },
  // R16 — Origin G2 depleted. T10 over-penalised Storm/Roosters. Live bets included.
  { id:52, date:'2026-06-20', match:'Canterbury Bulldogs vs Manly Sea Eagles',    market:'Under 48.5',         predictedLine:38.6,  takenPrice:1.83, closingPrice:1.88, result:'win',  plUnits:0.83,  runningTotal:4.67  },
  { id:53, date:'2026-06-20', match:'Wests Tigers vs Dolphins',                  market:'Tigers Win (Live)',   predictedLine:2.07,  takenPrice:1.83, closingPrice:null, result:'loss', plUnits:-0.44, runningTotal:4.23  },
  { id:54, date:'2026-06-21', match:'Melbourne Storm vs Canberra Raiders',        market:'Raiders +8.5',       predictedLine:-1.9,  takenPrice:1.90, closingPrice:1.89, result:'loss', plUnits:-1.00, runningTotal:3.23  },
  { id:55, date:'2026-06-21', match:'Melbourne Storm vs Canberra Raiders',        market:'Under 67.5 (Live)',  predictedLine:44.3,  takenPrice:2.05, closingPrice:null, result:'win',  plUnits:0.53,  runningTotal:3.76  },
  { id:56, date:'2026-06-21', match:'Sydney Roosters vs Cronulla Sharks',         market:'Sharks Win',         predictedLine:2.04,  takenPrice:2.53, closingPrice:2.48, result:'loss', plUnits:-1.00, runningTotal:2.76  },
  // R17
  { id:57, date:'2026-06-25', match:'Parramatta Eels vs South Sydney Rabbitohs',   market:'Souths -5.5',        predictedLine:-10.3, takenPrice:1.85, closingPrice:1.85, clv:0.0, clvLabel:'0.0 pts',  result:'win',  plUnits:0.37,  runningTotal:3.13  },
  { id:58, date:'2026-06-26', match:'Gold Coast Titans vs Canterbury Bulldogs',    market:'Under 46.5',         predictedLine:35.7,  takenPrice:1.90, closingPrice:1.87, clv:2.0, clvLabel:'+2.0 pts', result:'win',  plUnits:0.90,  runningTotal:4.03  },
  { id:59, date:'2026-06-27', match:'Manly Sea Eagles vs Melbourne Storm',         market:'Manly -3.5 PYL',     predictedLine:13.1,  takenPrice:1.73, closingPrice:null, clv:2.0, clvLabel:'+2.0 pts', result:'win',  plUnits:0.37,  runningTotal:4.40  },
];
