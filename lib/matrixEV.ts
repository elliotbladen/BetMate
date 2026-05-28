// lib/matrixEV.ts — server-side only (used in API routes)
// Reads NRL matrix data from Supabase (Vercel) or local files (dev).

import fs from 'fs';
import path from 'path';
import * as xlsx from 'xlsx';
import { getDataStore } from '@/lib/supabaseServer';

const ENGINE_OUTPUTS = process.env.BETTING_ENGINE_OUTPUTS_PATH
  ?? path.join(process.cwd(), '..', 'BettingEngine', 'outputs');

// ─── Types ────────────────────────────────────────────────────────────────────

export interface EVSignal {
  market: 'h2h' | 'handicap' | 'totals';
  side: 'home' | 'away' | 'over' | 'under';
  edgePct: number;
  direction: string;
  tier: 'free' | 'pro';
}

type EdgeData = { edgePct: number; direction: string } | null;
type SheetData = Record<string, EdgeData>;
type MatrixData = Record<string, SheetData>;
type HandicapData = Record<string, Record<string, { edgePct: number; direction: string }>>;

// ─── Team name normalisation ──────────────────────────────────────────────────
// Built from shared/teams.json — single source of truth for all team name variants.
// aliases → matrix_key (what BettingEngine writes as XLSX sheet/row names).

import teamsData from '@/shared/teams.json';

type TeamEntry = { matrix_key: string; aliases: string[] };
const _allTeams: TeamEntry[] = [
  ...(teamsData.NRL as TeamEntry[]),
  ...(teamsData.AFL as TeamEntry[]),
];
const CANONICAL: Record<string, string> = {};
for (const t of _allTeams) {
  for (const alias of t.aliases) {
    CANONICAL[alias.toLowerCase()] = t.matrix_key;
  }
}

function canonicalise(name: string): string {
  return CANONICAL[name.toLowerCase().trim()] ?? name;
}

// ─── Edge string parser ───────────────────────────────────────────────────────

function parseEdge(s: string | null | undefined): EdgeData {
  if (!s || s === '—' || s.trim() === '—') return null;
  const m = (s as string).match(/^([\d.]+)%\s+(.+)$/);
  if (!m) return null;
  const pct = parseFloat(m[1]);
  if (isNaN(pct)) return null;
  return { edgePct: pct, direction: m[2].trim() };
}

function tier(edgePct: number): 'free' | 'pro' {
  return edgePct > 15 ? 'pro' : 'free';
}

// ─── Local file loaders (dev only) ───────────────────────────────────────────

function loadXlsxMatrix(filename: string): MatrixData {
  const buf = fs.readFileSync(path.join(ENGINE_OUTPUTS, filename));
  const wb = xlsx.read(buf, { type: 'buffer' });
  const result: MatrixData = {};
  for (const sheetName of wb.SheetNames) {
    const ws = wb.Sheets[sheetName];
    const rows = xlsx.utils.sheet_to_json(ws, { defval: null }) as Record<string, unknown>[];
    if (!rows.length) continue;
    const firstCol = Object.keys(rows[0])[0];
    const sheet: SheetData = {};
    for (const row of rows) {
      const cat = row[firstCol] as string;
      if (!cat || cat === 'Category') continue;
      sheet[cat] = parseEdge(row['__EMPTY_3'] as string);
    }
    result[sheetName] = sheet;
  }
  return result;
}

function loadHandicapCSV(): HandicapData {
  const content = fs.readFileSync(path.join(ENGINE_OUTPUTS, 'nrl_handicap_matrix.csv'), 'utf8');
  const lines = content.trim().split('\n').slice(1);
  const result: HandicapData = {};
  for (const line of lines) {
    const parts = line.split(',');
    const [team, , category, , , , edgePctStr, direction] = parts;
    if (!team || !category) continue;
    const edgePct = parseFloat(edgePctStr);
    if (isNaN(edgePct) || !direction) continue;
    if (!result[team]) result[team] = {};
    result[team][category.trim()] = { edgePct, direction: direction.trim() };
  }
  return result;
}

// ─── Cache ────────────────────────────────────────────────────────────────────

let h2hCache: MatrixData | null = null;
let totalsCache: MatrixData | null = null;
let handicapCache: HandicapData | null = null;

async function getH2H(): Promise<MatrixData> {
  if (h2hCache) return h2hCache;
  const remote = await getDataStore('nrl_h2h_matrix') as MatrixData | null;
  if (remote) { h2hCache = remote; return remote; }
  if (!fs.existsSync(ENGINE_OUTPUTS)) return {};
  h2hCache = loadXlsxMatrix('nrl_h2h_matrix.xlsx');
  return h2hCache;
}

async function getTotals(): Promise<MatrixData> {
  if (totalsCache) return totalsCache;
  const remote = await getDataStore('nrl_totals_matrix') as MatrixData | null;
  if (remote) { totalsCache = remote; return remote; }
  if (!fs.existsSync(ENGINE_OUTPUTS)) return {};
  totalsCache = loadXlsxMatrix('nrl_team_totals_matrix.xlsx');
  return totalsCache;
}

async function getHandicap(): Promise<HandicapData> {
  if (handicapCache) return handicapCache;
  const remote = await getDataStore('nrl_handicap_matrix') as HandicapData | null;
  if (remote) { handicapCache = remote; return remote; }
  if (!fs.existsSync(ENGINE_OUTPUTS)) return {};
  handicapCache = loadHandicapCSV();
  return handicapCache;
}

// ─── Signal helpers ───────────────────────────────────────────────────────────

function qualifies(edgePct: number): boolean { return edgePct >= 10; }

function resolveH2HSide(rawSide: 'home' | 'away', direction: string): EVSignal['side'] {
  const isOpposing = direction.includes('opposing');
  if (rawSide === 'home') return isOpposing ? 'away' : 'home';
  return isOpposing ? 'home' : 'away';
}

function resolveHcapSide(rawSide: 'home' | 'away', direction: string): EVSignal['side'] {
  const isFades = direction === 'fades';
  if (rawSide === 'home') return isFades ? 'away' : 'home';
  return isFades ? 'home' : 'away';
}

// ─── Public API ───────────────────────────────────────────────────────────────

export async function getEVSignals(homeTeam: string, awayTeam: string): Promise<EVSignal[]> {
  const home = canonicalise(homeTeam);
  const away = canonicalise(awayTeam);

  const [h2h, totals, handicap] = await Promise.all([getH2H(), getTotals(), getHandicap()]);

  const signals: EVSignal[] = [];

  // ── H2H ──
  const h2hHomeData = h2h[home]?.['Win % — Home'];
  const h2hAwayData = h2h[away]?.['Win % — Away'];
  if (h2hHomeData && qualifies(h2hHomeData.edgePct)) {
    const side = resolveH2HSide('home', h2hHomeData.direction);
    signals.push({ market: 'h2h', side, edgePct: h2hHomeData.edgePct, direction: h2hHomeData.direction, tier: tier(h2hHomeData.edgePct) });
  }
  if (h2hAwayData && qualifies(h2hAwayData.edgePct)) {
    const side = resolveH2HSide('away', h2hAwayData.direction);
    if (!signals.find(s => s.market === 'h2h' && s.side === side)) {
      signals.push({ market: 'h2h', side, edgePct: h2hAwayData.edgePct, direction: h2hAwayData.direction, tier: tier(h2hAwayData.edgePct) });
    }
  }

  // ── Handicap ──
  const hcapHomeData = handicap[home]?.['Cover Rate — Home'];
  const hcapAwayData = handicap[away]?.['Cover Rate — Away'];
  if (hcapHomeData && qualifies(hcapHomeData.edgePct)) {
    const side = resolveHcapSide('home', hcapHomeData.direction);
    signals.push({ market: 'handicap', side, edgePct: hcapHomeData.edgePct, direction: hcapHomeData.direction, tier: tier(hcapHomeData.edgePct) });
  }
  if (hcapAwayData && qualifies(hcapAwayData.edgePct)) {
    const side = resolveHcapSide('away', hcapAwayData.direction);
    if (!signals.find(s => s.market === 'handicap' && s.side === side)) {
      signals.push({ market: 'handicap', side, edgePct: hcapAwayData.edgePct, direction: hcapAwayData.direction, tier: tier(hcapAwayData.edgePct) });
    }
  }

  // ── Totals ──
  const totHomeData = totals[home]?.['Total Points — Home'];
  const totAwayData = totals[away]?.['Total Points — Away'];
  if (totHomeData && qualifies(totHomeData.edgePct)) {
    const side: EVSignal['side'] = totHomeData.direction.includes('overs') ? 'over' : 'under';
    signals.push({ market: 'totals', side, edgePct: totHomeData.edgePct, direction: totHomeData.direction, tier: tier(totHomeData.edgePct) });
  }
  if (totAwayData && qualifies(totAwayData.edgePct)) {
    const side: EVSignal['side'] = totAwayData.direction.includes('overs') ? 'over' : 'under';
    if (!signals.find(s => s.market === 'totals' && s.side === side)) {
      signals.push({ market: 'totals', side, edgePct: totAwayData.edgePct, direction: totAwayData.direction, tier: tier(totAwayData.edgePct) });
    }
  }

  return signals;
}
