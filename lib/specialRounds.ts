// Special round venue overrides.
// Add an entry here whenever all games are played at a neutral venue
// (Magic Round, State of Origin double-headers, Anzac Day, Las Vegas, etc.)
//
// Format: { season, round, sport } → venue name
// The venue name must exist in VENUE_COORDS in lib/venues.ts.
//
// HOW TO USE:
//   Every Tuesday before pricing, check if the upcoming round is a special event.
//   If so, add an entry below BEFORE running prepare_round.py.
//   Remove old entries after the round completes (keeps the list clean).

export interface SpecialRoundOverride {
  season: number;
  round: number;
  sport: 'NRL' | 'AFL';
  venue: string;       // must match a key in VENUE_COORDS
  label: string;       // human-readable name shown in the UI
  allGames: boolean;   // true = all games at this venue, false = only some (not yet supported)
}

export const SPECIAL_ROUNDS: SpecialRoundOverride[] = [
  // NRL 2026 Magic Round — all 8 games at Suncorp Stadium, Brisbane
  { season: 2026, round: 11, sport: 'NRL', venue: 'Suncorp Stadium', label: 'Magic Round', allGames: true },

  // Add future special rounds here as they're announced:
  // { season: 2026, round: 16, sport: 'NRL', venue: 'Optus Stadium', label: 'Perth Round', allGames: true },
  // { season: 2026, round: 25, sport: 'NRL', venue: 'Allegiant Stadium', label: 'Las Vegas', allGames: true },
];

// Returns the venue override for a given season/round/sport, or null if normal.
export function getSpecialRoundVenue(
  season: number,
  round: number,
  sport: 'NRL' | 'AFL'
): SpecialRoundOverride | null {
  return (
    SPECIAL_ROUNDS.find(
      (s) => s.season === season && s.round === round && s.sport === sport && s.allGames
    ) ?? null
  );
}
