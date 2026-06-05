# Session Diary — 2026-05-26 — Baz Tunnel Live

## What we did

Got Baz online on betmate.au. Two separate workstreams this session:
1. Fixed the mobile layout root cause (documented in `2026-05-26_mobile-layout-root-cause-fix.md`)
2. Wired the Cloudflare Tunnel so Baz brain is reachable from Vercel

## Baz Tunnel — What Was Broken

The tunnel itself was already configured and the DNS was correct (`baz.betmate.au` resolved to Cloudflare IPs 172.67.168.98 / 104.21.70.151). But Vercel was still sending `X-Baz-Brain: offline` in API responses.

Root cause: `BAZ_TUNNEL_URL` was set to an **empty string** `""` in Vercel's production environment. The `vercel env pull` command always shows encrypted vars as empty — so this wasn't visible from the outside. The env var appeared to exist but resolved to falsy in Node.js, causing the route to fall through to `localhost:8765` (which Vercel can't reach).

## Fix

1. Removed the bad env var: `npx vercel env rm BAZ_TUNNEL_URL production`
2. Re-added with correct value: `printf 'https://baz.betmate.au' | npx vercel env add BAZ_TUNNEL_URL production`
3. Triggered production redeploy: `npx vercel --prod --yes`
4. Confirmed: `curl -X POST https://bet-mate-ten.vercel.app/api/chat ...` → `X-Baz-Brain: online` ✅

## Start Script

Created `scripts/start_baz.ps1`:
- Kills any stale `cloudflared` process
- Starts `baz_server.py` (FastAPI on port 8765) if not already running
- Starts `cloudflared tunnel run betmate-baz`
- Health checks `https://baz.betmate.au/health` after 8 seconds

Run this manually when the machine restarts or tunnel drops.

## Architecture Reminder

```
betmate.au (Vercel)
  → /api/chat
    → BAZ_TUNNEL_URL=https://baz.betmate.au (Vercel env)
      → Cloudflare (DNS + proxy)
        → cloudflared tunnel (betmate-baz)
          → localhost:8765 (baz_server.py / FastAPI)
            → BettingEngine context + Claude API
```

The BettingEngine IP stays local. Cloudflare Tunnel bridges it to the public internet without exposing the machine.

## State After Session

- Mobile layout: **fixed** ✅ (documented separately)
- betmate.au mobile: Ask Baz, Details, BVI, H/A Value all visible on 375px viewport
- Baz: **ONLINE on betmate.au** ✅ — `X-Baz-Brain: online` confirmed
- `scripts/start_baz.ps1` created ✅

## Pending (unchanged)

- **MCP layer**: next major work — sports MCP server + crypto MCP server, same Baz brain
- Custom domain `betmate.au`: SSL pending, `www.betmate.au` CNAME needs updating
- Supabase UNIQUE constraint on `key` column
- R12 CLV not yet filed
- Refs on Vercel (static JSON removed, need Supabase route)
- AFL totals model bias fix
- EV signals on Vercel (wire BettingEngine arrows via same Cloudflare Tunnel)
