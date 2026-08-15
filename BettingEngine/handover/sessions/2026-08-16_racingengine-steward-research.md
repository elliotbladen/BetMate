# RacingEngine — steward reports and rating architecture

Date: 2026-08-16

## Decision made

Steward reports will be a controlled evidence layer in RacingEngine. They will
eventually influence V2 only after a strict chronological ablation study; they
will not become an unbounded language-model adjustment.

## Delivered

- Commit `6931a92` on BetMate `main`: authorised official-report importer,
  auditable source archive, deterministic event categories and review flags.
- Historical backfill: 257 NSW/VIC Saturday metro meetings checked; 1,070
  reports; 6,659 runner events; 551 material/severe review events.
- V1 ratings remain unchanged.

## Weight policy

- Minor: 0.
- Moderate confirmed trip event: max +0.75 rating points.
- Severe: +0.75 to +1.50.
- Global run cap: +2.0.
- Wide/no cover: 0 until corroborated by distance travelled and sectionals.
- Vet report: fitness/uncertainty status only, no automatic forgiveness.

## Critical user instruction

The steward impact study must measure whether an adjusted prior run improves
prediction over the horse's **next three starts**, not just the immediate next
start. Model the effect with decay and test categories separately.

## Source of truth

Use `RacingEngine/docs/project_tracker.md` for completed work, architecture,
guardrails and next build order. Update it after every material RacingEngine
session.
