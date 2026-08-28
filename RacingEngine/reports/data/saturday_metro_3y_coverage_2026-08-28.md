# Saturday metro three-year coverage audit

Window: 2023-08-28 through 2026-08-28 (latest completed Saturday: 2026-08-22).

The authorised public meeting calendars were compared directly with canonical
database sources on 28 August 2026.

| Region | Official meetings | Stored meetings | Missing | Extra | Races | Runners |
|---|---:|---:|---:|---:|---:|---:|
| Sydney (Randwick/Rosehill) | 137 | 137 | 0 | 0 | 1,368 | 19,611 |
| Melbourne metro | 137 | 137 | 0 | 0 | 1,311 | 16,575 |
| Total | 274 | 274 | 0 | 0 | 2,679 | 36,186 |

All stored races have distance and carried weight. Victorian structured data
has three missing official race clocks. The NSW structured identity/result
cards do not populate the race-time field; authorised NSW sectional evidence
is stored separately where available. There are 245 NSW rows labelled finished
without a numeric finishing position; downstream clean-rating eligibility
continues to exclude such rows explicitly.

No import was required because the canonical stores already exactly matched
the official metropolitan schedules. Standalone provincial Saturdays are not
missing city meetings and remain outside the requested scope.
