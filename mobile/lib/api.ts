import { parseEvents, OddsApiEvent, ParsedGame } from './oddsParser';

export const BASE_URL = 'https://bet-mate-ten.vercel.app';

export async function fetchNRL(): Promise<ParsedGame[]> {
  const res = await fetch(`${BASE_URL}/api/odds/nrl`);
  if (!res.ok) throw new Error(`NRL fetch failed: ${res.status}`);
  const events: OddsApiEvent[] = await res.json();
  return parseEvents(events, 'NRL');
}

export async function fetchAFL(): Promise<ParsedGame[]> {
  const res = await fetch(`${BASE_URL}/api/odds/afl`);
  if (!res.ok) throw new Error(`AFL fetch failed: ${res.status}`);
  const events: OddsApiEvent[] = await res.json();
  return parseEvents(events, 'AFL');
}

export async function fetchMovements(): Promise<Record<string, { direction: 'up' | 'down'; changePct: number }>> {
  try {
    const res = await fetch(`${BASE_URL}/api/odds/movements`);
    if (!res.ok) return {};
    return await res.json();
  } catch {
    return {};
  }
}

export async function sendBazMessage(
  messages: { role: 'user' | 'assistant'; content: string }[],
  onChunk: (text: string) => void,
): Promise<void> {
  const res = await fetch(`${BASE_URL}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ messages }),
  });

  if (!res.ok) throw new Error(`Chat failed: ${res.status}`);
  if (!res.body) throw new Error('No response body');

  const reader = res.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    const chunk = decoder.decode(value, { stream: true });
    // Parse Vercel AI SDK data stream: lines like 0:"text content"
    const lines = chunk.split('\n');
    for (const line of lines) {
      const match = line.match(/^0:"(.*)"$/);
      if (match) {
        // Unescape JSON string content
        try {
          const text = JSON.parse(`"${match[1]}"`);
          onChunk(text);
        } catch {
          onChunk(match[1]);
        }
      }
    }
  }
}
