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
