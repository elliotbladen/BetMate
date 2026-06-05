# Session Diary — 2026-05-26 — React Native Mobile App Scaffold

## What we did

Built a full React Native (Expo) mobile app for BetMate in `C:\Users\ElliotBladen\Apps\mobile\`.

### Tech stack
- Expo 56 + Expo Router (file-based navigation, mirrors Next.js routing)
- TypeScript, no additional UI libraries — pure React Native StyleSheet
- Dark theme throughout (BetMate palette: #0D0D0D bg, #00DEB8 accent)

### App structure
```
mobile/
  app/
    _layout.tsx            Root layout (StatusBar)
    (tabs)/
      _layout.tsx          Bottom tab bar (Odds | Baz | Research)
      index.tsx            Odds board screen
      baz.tsx              Baz AI chat screen
      research.tsx         Research / CLV screen
  components/
    GameCard.tsx           Full game card (H2H / Handicap / Totals tabs, horizontal bookmaker tiles)
    TeamBadge.tsx          Team colour badge with abbr
    Countdown.tsx          Live countdown timer
  lib/
    api.ts                 fetch functions → https://bet-mate-ten.vercel.app
    bookmakers.ts          Bookmaker meta + effectivePrice (Betfair 5% commission)
    oddsParser.ts          Parses raw OddsApiEvent[] → ParsedGame[]
    teams.ts               NRL + AFL team colours/abbr (mirrors web lib/teams.ts)
  constants/
    colors.ts              BetMate colour palette
```

### Key decisions
- `package.json` `"main"` changed to `"expo-router/entry"` (Expo Router requirement)
- `app.json`: scheme = `betmate`, dark mode, bundle IDs set to `au.betmate.app`
- All API calls go to `https://bet-mate-ten.vercel.app` (no local API needed)
- Baz chat uses streaming fetch with Vercel AI SDK data stream parser (`0:"text"` chunks)
- TypeScript check: 0 errors

### To run
```powershell
cd C:\Users\ElliotBladen\Apps\mobile
npx expo start
```
Then scan the QR code in Expo Go on iPhone/Android. Or press `i` for iOS simulator, `a` for Android emulator.

### Pending / next session
- Test on real device via Expo Go — verify odds load, bookmaker tiles scroll, Baz chat streams correctly
- Game card "Ask Baz" → Baz screen passes game context via router params (home/away teams)
- Add movement arrows styling (currently rendered but visual polish needed)
- Overround row (not in mobile v1 — can add in footer area)
- Completed games section (not in v1)
- App icon — use BetMate brand colours on the default expo icon
- Consider adding `expo-image` for better favicon caching
- Eventually: EAS Build for TestFlight + App Store submission
