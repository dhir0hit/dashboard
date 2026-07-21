# `frontend/src/pages/CalendarPage.tsx`

Calendar synced with Hermes cron jobs. Fetches `/api/cron` (server-side
proxy that shells out to `hermes cronjob list --json`), renders a month
grid, and pins jobs on their `last_run` / `next_run` days.

## Exported component

### `CalendarPage`

No props. Local state only.

## Local state

| Hook | Type | Purpose |
|---|---|---|
| `useState(new Date())` | `today` | Anchors for today styling. |
| `useState(startOfMonth(today))` | `cursor` | Which month is in view. |
| `useState<CronListResponse \| null>` | `data` | Cron data. |
| `useState(true)` | `loading` | First-load gate. |
| `useState<string \| null>` | `err` | Error text, or null. |

## Date helpers

| Function | Behavior |
|---|---|
| `startOfMonth(d)` | Returns `new Date(year, month, 1)`. |
| `addMonths(d, n)` | Returns `new Date(year, month+n, 1)`. |
| `sameDay(a, b)` | True iff same year/month/date. |
| `dayKey(d)` | `<year>-<month>-<date>` — used as map key for jobs-by-day. |
| `parseDate(s)` | Returns `Date` or null on unparseable input. |

## Constants

- `WEEKDAYS = ["Sun", "Mon", ...]` — 7 entries.
- `MONTHS = ["January", ...]` — 12 entries.

## Lifecycle

`useEffect` on mount calls `api.listCron()`. On success: `setData`. On
error: `setErr((e as Error).message)`. Always `setLoading(false)`.

## Render

```
<div className="mx-auto max-w-3xl">
  <header /* title + Refresh button */ />
  {loading ? <Spinner/>
   : err ? <ErrorBanner/>
   : (
     <CalendarGrid
       cursor={cursor}
       today={today}
       jobsByDay={jobsByDay} /* useMemo-built map */}
     />
   )}
  <JobsList /* flat list below the grid */}
</div>
```

### `jobsByDay` (useMemo)

A `Record<string, CronEntry[]>` keyed by `dayKey(parseDate(job.last_run))`
and `dayKey(parseDate(job.next_run))`. A job that has both fields lands on
two cells. A job with neither doesn't appear on the grid (but still shows
in the flat list).

### Grid

- Header row: 7 weekday labels.
- Body: 6 weeks × 7 days. Each day-cell shows the day-of-month, a "today"
  highlight if `sameDay(day, today)`, a faded look for days outside the
  current month, and a job pin per entry in `jobsByDay[dayKey(day)]`.
- Month navigation: chevron-left (-1 month) and chevron-right (+1 month)
  at the top mutate `cursor`.

### `JobsList`

Flat list below the grid showing every job from `data.jobs` with:
- Job name (or `data.jobs[].id` when null).
- Schedule string (e.g. `"0 9 * * *"` or human interval).
- Enabled/disabled indicator.
- Next / last run timestamps (formatted via `parseDate` + `.toLocaleString()`).
- `data.source` — shown as a footer note: `"Data source: hermes-cli"` when
  the cron integration is active, `"Data source: stub (hermes CLI not
  available)"` otherwise.

## Conventions

- **No manual event creation UI**: the calendar is a view onto Hermes cron,
  not a standalone calendar app. To create jobs, install/configure Hermes
  cron via the CLI; on next refresh the calendar picks them up.
- **No rerenders on minute tick**: `today` is computed once at mount via
  `useMemo(() => new Date(), [])`. If a job's `next_run` crosses while the
  page is open, the visual doesn't change — refresh the page to re-fetch
  `/api/cron`.
- **Graceful degradation**: if `/api/cron` returns `source: "stub"` (backend
  can't find `hermes` on PATH), `data.jobs` is empty and the grid just
  shows a regular month calendar with no pins. The footer note tells the
  user why.

---

*created by [@dhir0hit](https://github.com/dhir0hit) using [Hermes Agent](https://hermes-agent.nousresearch.com)*


---

## Google Calendar — frontend-only OAuth (PKCE)

Google Calendar integration now runs entirely in the browser; the backend has
no Google credentials, no `/api/calendar/google/login|callback|config|exchange|`
endpoints, and no `google_token` table. Only one backend endpoint remains:

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/calendar/google/sync` | Pull events from the user's primary Google Calendar (next 90 days) and upsert them as `source='google'` events. **Requires an `Authorization: Bearer <access_token>` header** — supplied by the frontend. |

### Setup (one-time)

1. In [Google Cloud Console → Credentials](https://console.cloud.google.com/apis/credentials),
   create an OAuth client of type **"Desktop app"** (NOT "Web application").
   Desktop clients have no client secret — PKCE (`code_verifier` +
   `code_challenge = SHA-256(verifier)`) replaces it.
2. Copy the client_id into `frontend/.env` as `VITE_GOOGLE_CLIENT_ID=...`.
3. Add the Calendar API scope to the same Google project
   (`Google Calendar API` → Enable).

### Runtime flow (same-tab redirect)

1. User opens `/calendar`, clicks **Connect Google**.
2. `src/googleAuth.ts::beginGoogleLogin` generates a `code_verifier` and state,
   stores them in `sessionStorage`, then `window.location.assign`s Google's
   consent screen with `code_challenge_method=S256`.
3. After consent, Google redirects back to `<origin>/calendar?code=...&state=...`.
4. On mount, `CalendarPage` detects `?code=` and calls
   `handleGoogleRedirect`, which:
   - Verifies state matches `sessionStorage`,
   - POSTs `{code, code_verifier, redirect_uri, grant_type=authorization_code}`
     to `https://oauth2.googleapis.com/token` (NO `client_secret`),
   - Stores `access_token` / `refresh_token` / `expires_at` / `email` in
     `localStorage` under `dashboard.google.tokens.v1`,
   - Cleans the URL (`history.replaceState`).
5. **Sync now** → `getValidAccessToken()` refreshes if expired (using the
   stored `refresh_token`), then calls `api.syncGoogleCalendar(token)` which
   sets `Authorization: Bearer <token>` on `POST /api/calendar/google/sync`.
6. **Disconnect** → `clearStoredTokens()` is purely client-side; no backend
   call.

### Files

| File | Role |
|---|---|
| `frontend/src/googleAuth.ts` | PKCE helpers, token storage (`localStorage`), `beginGoogleLogin`, `handleGoogleRedirect`, `getValidAccessToken`, `clearStoredTokens`. |
| `frontend/src/pages/CalendarPage.tsx` | UI; calls `googleAuth.ts` and `api.syncGoogleCalendar(token)`. |
| `frontend/src/api.ts` | `syncGoogleCalendar(accessToken)` — one Bearer-header POST. |
| `backend/app/main.py` | `POST /api/calendar/google/sync` — reads `Authorization: Bearer`, pulls events, upserts as `source='google'`. No Google credentials anywhere on the server. |

### Pitfalls

- The OAuth client MUST be "Desktop app" type. A "Web application" client
  requires `client_secret` at token exchange, which a pure frontend flow
  cannot provide without leaking it to the browser.
- `prompt=consent` + `access_type=offline` are forced so Google always
  returns a `refresh_token`; otherwise reconnects on the same account may
  return only an `access_token` and silent refresh becomes impossible.
- The token is visible to any script on the same origin (XSS risk). This is
  the standard trade-off for a frontend-only flow — only Calendar.readonly
  scope is requested to limit blast radius.
