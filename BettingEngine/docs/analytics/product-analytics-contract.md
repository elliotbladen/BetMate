# BetMate product analytics contract

**Status:** Draft contract for implementation review  
**Version:** 1.0  
**Owner:** BetMate product and engineering  
**Last updated:** 2026-09-09

This document defines the product events BetMate may collect. It is the source
of truth for the future frontend tracker, backend endpoint, database schema and
analytics dashboard.

## Purpose

The analytics system exists to answer product questions:

- Which pages are being used?
- Which pages receive meaningful active attention?
- Which odds, market and research controls are useful?
- How often is Baz used and from which parts of the product?
- Where do visitors stop before signing up or subscribing?

Analytics is for product improvement and operational monitoring. It is not used
to make decisions about a person's eligibility, credit, identity or access to
essential services.

## Collection principles

1. Collect only events needed to answer a documented product question.
2. Use stable semantic names instead of recording arbitrary DOM clicks.
3. Record active page time, not merely time with a tab left open.
4. Do not collect passwords, payment details, bookmaker credentials, keystrokes,
   full chat contents or page text.
5. Use an anonymous session identifier until a user signs in.
6. Link events to an authenticated user only after the normal product session
   exists; do not attempt to identify anonymous visitors.
7. Honour analytics consent and provide a way to withdraw it.
8. Keep analytics separate from betting decisions and model training.
9. Validate and rate-limit events on the server before storing them.
10. Store timestamps in UTC and retain the app version that emitted the event.

## Event envelope

Every stored event has this common envelope:

| Field | Required | Description |
|---|---:|---|
| `event_id` | Yes | Server-generated unique identifier. |
| `event_name` | Yes | One of the approved event names below. |
| `occurred_at_utc` | Yes | Client occurrence time, checked against server time. |
| `received_at_utc` | Yes | Server receipt time. |
| `session_id` | Yes | Random, non-identifying session identifier. |
| `user_id` | No | Authenticated Supabase user ID, when available. |
| `route` | Yes | Normalised BetMate route, such as `/odds` or `/research`. |
| `source_component` | No | Stable component or feature name. |
| `metadata` | No | Allowlisted, event-specific values only. |
| `duration_seconds` | No | Active duration for page-exit events. |
| `device_class` | No | Coarse value: `mobile`, `tablet` or `desktop`. |
| `app_version` | Yes | BetMate release identifier. |
| `consent_state` | Yes | `granted`, `denied` or `not_required`. |

The server is authoritative for `event_id`, `received_at_utc`, user identity and
validation. Client timestamps are retained only for ordering and must be bounded
against the receipt time.

## Approved events

### Navigation and attention

| Event | Purpose | Allowed metadata |
|---|---|---|
| `page_view` | Count route visits. | `entry_method` |
| `page_exit` | Record active attention on a route. | `exit_method` |
| `page_visibility_change` | Diagnose hidden-tab timing. | `visibility_state` |

`page_exit` must include `duration_seconds`. Duration is accumulated only while
the page is visible and active. A missing exit event must not be interpreted as
zero time.

### Product interaction

| Event | Purpose | Allowed metadata |
|---|---|---|
| `click` | Measure approved feature interactions. | `target_id`, `target_group` |
| `search_submitted` | Understand search demand. | `search_area`, `result_count` |
| `filter_changed` | Understand filter usage. | `filter_name`, `filter_value_group` |
| `market_selected` | Measure market interest. | `sport`, `competition`, `market_type` |
| `odds_card_expanded` | Measure odds-card engagement. | `sport`, `competition`, `market_type` |

`target_id`, `filter_name` and `market_type` must come from server- or code-owned
allowlists. Raw labels and arbitrary user-entered values are not accepted.

### Baz

| Event | Purpose | Allowed metadata |
|---|---|---|
| `baz_opened` | Measure Baz discovery and use. | `entry_route` |
| `baz_question_submitted` | Count questions and understand entry context. | `entry_route`, `question_length_bucket` |
| `baz_response_rendered` | Monitor successful response delivery. | `response_status`, `latency_bucket` |

The question text, response text, prompts, tool results and uploaded content are
never stored in product analytics. Conversation storage, if required, follows a
separate policy and separate data model.

### Account and subscription funnel

| Event | Purpose | Allowed metadata |
|---|---|---|
| `sign_in_started` | Measure sign-in attempts. | `method` |
| `sign_in_completed` | Measure successful sign-ins. | `method` |
| `registration_started` | Measure registration intent. | `method` |
| `registration_completed` | Measure registration completion. | `method` |
| `subscription_viewed` | Measure plan-page interest. | `plan_group` |
| `subscription_action` | Measure checkout actions. | `action`, `plan_group` |

Payment provider IDs, payment amounts, card details, email addresses and error
messages containing personal data are excluded.

## Identity and consent

Anonymous visitors receive a random session identifier stored in a first-party
cookie or equivalent browser storage. It must not be derived from an email,
name, IP address, fingerprint or advertising identifier.

For signed-in users, `user_id` may be attached to future events through the
existing Supabase session. Existing authentication data is not copied into event
metadata.

If analytics consent is required and has not been granted, product analytics
events are not sent. Essential security and authentication logs remain governed
by their own operational policy.

## Retention and access

- Product analytics events: retain for 13 months, then delete or aggregate.
- Aggregated, non-identifying product metrics: may be retained longer.
- Raw analytics access: BetMate owner/admin role only.
- Customer-facing users cannot inspect another user's activity.
- Exports must contain only the minimum fields needed for the stated analysis.

The final retention period and consent wording must be reviewed before production
collection is enabled.

## Initial product questions and dashboard metrics

The first dashboard should report:

- Daily and weekly active users
- Page views by route
- Median active seconds by route
- Odds-card expansion rate
- Market and sport selection counts
- Baz open rate and response success rate
- Registration conversion
- Subscription-page conversion
- Returning-session rate

Metrics should be filterable by date range, app version, device class, sport and
route where the event contract allows it.

## Acceptance criteria for Step 1

Step 1 is complete when:

- Every event has a documented product purpose.
- Every event has an explicit metadata allowlist.
- Active time is defined separately from page views.
- Anonymous, authenticated and consent-denied behaviour is specified.
- Sensitive data exclusions are written down.
- Retention and access rules are documented.
- The future API and database implementation can be derived from this document
  without inventing new event names or fields.

No database table, tracking code or dashboard should be implemented until this
contract has been reviewed and any changes are recorded as a new version.
