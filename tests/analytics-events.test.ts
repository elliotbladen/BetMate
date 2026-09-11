import test from 'node:test';
import assert from 'node:assert/strict';
import { validAnalyticsEvent } from '../lib/analyticsEvent';

const valid = {
  event_name: 'page_view', occurred_at_utc: '2026-09-09T00:00:00.000Z',
  session_id: '00000000-0000-4000-8000-000000000001', route: '/odds',
  app_version: 'dev', consent_state: 'granted', metadata: {}, device_class: 'desktop',
};

test('accepts a valid analytics event envelope', () => {
  assert.equal(validAnalyticsEvent(valid), true);
});

test('rejects unknown events and sensitive free-form payloads', () => {
  assert.equal(validAnalyticsEvent({ ...valid, event_name: 'raw_dom_click' }), false);
  assert.equal(validAnalyticsEvent({ ...valid, metadata: 'chat transcript' }), false);
});

test('rejects invalid duration and device values', () => {
  assert.equal(validAnalyticsEvent({ ...valid, duration_seconds: -1 }), false);
  assert.equal(validAnalyticsEvent({ ...valid, device_class: 'phone' }), false);
});
