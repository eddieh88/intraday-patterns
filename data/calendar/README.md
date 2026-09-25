# Calendar files for prereg/selection.md

| file | contents | source |
|---|---|---|
| `fomc_decisions.csv` | 48 scheduled FOMC decision days, 2021–2026 (the second day of each meeting). `sep` marks meetings with projections. | [federalreserve.gov/monetarypolicy/fomccalendars.htm](https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm), fetched 2026-09-25 and parsed from the page's own markup. |

The 2025-08-22 notation vote is excluded: it is not a meeting and has no 14:00
decision. All 46 decisions inside the data fall on trading sessions.

FOMC decisions come at 14:00, after the 09:30–11:00 window, so the decision-day
feature measures anticipation. The session *after* a decision is a second feature.

**Not here yet: CPI and the jobs report (NFP).** Both are released at 08:30,
before the open. BLS blocks automated retrieval, and FRED timed out, so these
dates must come from a manual download or a FRED API key. The 2025 shutdown
delayed or cancelled several releases, so they cannot be generated from a rule.

Computed in code rather than stored: **options expiration** (third Friday of the
month, or the preceding session if the market is closed) and **month-end** (last
session of the month).
