'use client';

import { useEffect, useRef, useState } from 'react';
import { getValidTipSelections, isGameweekLocked } from '@/lib/tipping';
import type { Fixture, TipSelection, TippingTip } from '@/lib/tipping';

interface RoundData {
  scope: string;
  fixtures: Fixture[];
  tips: Record<string, TipSelection>;
  grades: Record<string, { result: TipSelection | null; points: number | null }>;
  complete: boolean;
}

/** Fixtures and saved selections must belong to the same round and account. */
export function useTippingRound(gameweek: number, userId: string | null, compId: string | null, seasonComplete: boolean) {
  const scope = JSON.stringify([gameweek, userId, compId, seasonComplete]);
  const [data, setData] = useState<RoundData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [retryVersion, setRetryVersion] = useState(0);
  const dirty = useRef(false);
  const editRevision = useRef(0);
  const savingRef = useRef(false);
  const generation = useRef(0);
  const saveController = useRef<AbortController | null>(null);

  useEffect(() => {
    const currentGeneration = ++generation.current;
    const controller = new AbortController();
    let inFlight = false;
    dirty.current = false;
    savingRef.current = false;
    setData(null);
    setError(null);
    setSaved(false);
    setSaving(false);

    async function load() {
      // Refreshing must not erase a draft or race a save already in progress.
      if (!userId || seasonComplete || inFlight || dirty.current || savingRef.current) return;
      inFlight = true;
      const requestedRevision = editRevision.current;
      try {
        const options = { signal: controller.signal, cache: 'no-store' as const };
        const [fixturesResponse, tipsResponse] = await Promise.all([
          fetch(`/api/tipping/fixtures?gameweek=${gameweek}`, options),
          compId ? fetch(`/api/tipping/tips?${new URLSearchParams({ comp_id: compId, user_id: userId, gameweek: String(gameweek) })}`, options) : null,
        ]);
        if (!fixturesResponse.ok || (tipsResponse && !tipsResponse.ok)) throw new Error('load');
        const [fixturePayload, tipPayload] = await Promise.all([
          fixturesResponse.json(), tipsResponse ? tipsResponse.json() : { tips: [] },
        ]);
        if (fixturePayload.gameweek !== gameweek || !Array.isArray(fixturePayload.fixtures) || !Array.isArray(tipPayload.tips)) throw new Error('invalid round');
        if (controller.signal.aborted || generation.current !== currentGeneration || requestedRevision !== editRevision.current || dirty.current || savingRef.current) return;

        const fixtures: Fixture[] = fixturePayload.fixtures.filter((fixture: Fixture) => fixture.gameweek === gameweek);
        const fixtureIds = new Set(fixtures.map(fixture => fixture.id));
        const tips: RoundData['tips'] = {};
        const grades: RoundData['grades'] = {};
        const rows: TippingTip[] = tipPayload.tips.filter((tip: TippingTip) => tip.gameweek === gameweek);
        const validSelections = getValidTipSelections(gameweek, rows);
        for (const { fixture, selection } of validSelections) {
          if (!fixtureIds.has(fixture.id)) continue;
          const row = rows.find(tip => tip.game_id === fixture.id)!;
          tips[fixture.id] = selection;
          grades[fixture.id] = { result: row.result ?? null, points: row.result == null ? null : Number(row.points ?? 0) };
        }
        setData({ scope, fixtures, tips, grades, complete: fixturePayload.round_complete === true });
        setError(null);
      } catch {
        if (!controller.signal.aborted && generation.current === currentGeneration) {
          setError('Could not load this round’s fixtures and saved tips. Please retry.');
        }
      } finally {
        inFlight = false;
      }
    }

    void load();
    const timer = window.setInterval(load, 5 * 60 * 1000);
    return () => {
      controller.abort();
      saveController.current?.abort();
      window.clearInterval(timer);
    };
  }, [scope, gameweek, userId, compId, seasonComplete, retryVersion]);

  const round = data?.scope === scope ? data : null;
  const fixtures = round?.fixtures ?? [];
  const tips = round?.tips ?? {};
  const loading = !!userId && !seasonComplete && !round && !error;

  function selectTip(gameId: string, selection: TipSelection) {
    if (!round || !compId || savingRef.current || isGameweekLocked(round.fixtures) || !round.fixtures.some(fixture => fixture.id === gameId)) return;
    dirty.current = true;
    editRevision.current += 1;
    setSaved(false);
    setData(previous => previous?.scope === scope ? { ...previous, tips: { ...previous.tips, [gameId]: selection } } : previous);
  }

  async function saveTips() {
    if (!round || !userId || !compId || savingRef.current || isGameweekLocked(round.fixtures)) return;
    const currentGeneration = generation.current;
    const controller = new AbortController();
    saveController.current = controller;
    savingRef.current = true;
    setSaving(true);
    setSaved(false);
    setError(null);
    const submittedTips = round.fixtures.filter(fixture => tips[fixture.id]).map(fixture => ({ game_id: fixture.id, selection: tips[fixture.id] }));
    try {
      const response = await fetch('/api/tipping/tips', {
        method: 'POST', signal: controller.signal,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ comp_id: compId, gameweek, tips: submittedTips }),
      });
      const payload = await response.json();
      if (controller.signal.aborted || generation.current !== currentGeneration) return;
      // The existing API reports individual write failures even with HTTP 200.
      if (!response.ok || !Array.isArray(payload.results) || payload.results.length !== submittedTips.length || payload.results.some((result: { success?: boolean; error?: string }) => result.error || result.success !== true)) {
        throw new Error(payload.error || 'Some tips could not be saved. Your choices are still here; please try again.');
      }
      dirty.current = false;
      setSaved(true);
    } catch (failure) {
      if (!controller.signal.aborted && generation.current === currentGeneration) {
        setError(failure instanceof Error ? failure.message : 'Could not save tips. Please try again.');
      }
    } finally {
      if (!controller.signal.aborted && generation.current === currentGeneration) {
        savingRef.current = false;
        setSaving(false);
      }
    }
  }

  return {
    fixtures, tips, tipGrades: round?.grades ?? {}, roundComplete: round?.complete ?? false,
    tippedCount: fixtures.filter(fixture => tips[fixture.id]).length,
    ready: !!round, loading, error, saving, saved, selectTip, saveTips,
    // Retrying a failed background refresh must not discard an unsaved draft.
    retry: () => { if (!dirty.current && !savingRef.current) setRetryVersion(version => version + 1); },
  };
}
