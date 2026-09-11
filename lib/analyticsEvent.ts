const EVENT_NAMES = new Set([
  'page_view', 'page_exit', 'page_visibility_change', 'click', 'search_submitted',
  'filter_changed', 'market_selected', 'odds_card_expanded', 'baz_opened',
  'baz_question_submitted', 'baz_response_rendered', 'sign_in_started',
  'sign_in_completed', 'registration_started', 'registration_completed',
  'subscription_viewed', 'subscription_action',
]);
const DEVICE_CLASSES = new Set(['mobile', 'tablet', 'desktop']);
const CONSENT_STATES = new Set(['granted', 'denied', 'not_required']);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

export function validAnalyticsEvent(event: unknown): event is Record<string, unknown> {
  if (!isRecord(event)) return false;
  if (typeof event.event_name !== 'string' || !EVENT_NAMES.has(event.event_name)) return false;
  if (typeof event.occurred_at_utc !== 'string' || typeof event.session_id !== 'string') return false;
  if (typeof event.route !== 'string' || event.route.length < 1 || event.route.length > 200) return false;
  if (typeof event.app_version !== 'string' || event.app_version.length < 1 || event.app_version.length > 80) return false;
  if (typeof event.consent_state !== 'string' || !CONSENT_STATES.has(event.consent_state)) return false;
  if (event.device_class !== undefined && event.device_class !== null &&
      (typeof event.device_class !== 'string' || !DEVICE_CLASSES.has(event.device_class))) return false;
  if (event.duration_seconds !== undefined && event.duration_seconds !== null &&
      (typeof event.duration_seconds !== 'number' || !Number.isInteger(event.duration_seconds) ||
       event.duration_seconds < 0 || event.duration_seconds > 86400)) return false;
  if (event.metadata !== undefined && !isRecord(event.metadata)) return false;
  return true;
}
