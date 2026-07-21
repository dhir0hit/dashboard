# `frontend/src/pages/SearchPage.tsx`

DuckDuckGo web search page — front-end shell that talks to the backend
`/api/search` proxy (CORS-free, no tracking, no ads).

## Exported component

### `SearchPage`

No props. Local state only.

## Local state

| Hook | Type | Purpose |
|---|---|---|
| `useState("")` | `q` | Search-box value. |
| `useState<SearchResponse \| null>` | `data` | Last response. |
| `useState(false)` | `loading` | While the request is in flight. |
| `useState<string \| null>` | `err` | Error text, or null. |

## Behavior

`onSubmit(e)` (form submit handler):

1. `e.preventDefault()`; bail if `q.trim()` is empty.
2. `setLoading(true)`, `setErr(null)`, `setData(null)`.
3. `const out = await api.search(q)` — single attempt, no retries.
4. On success: `setData(out)`.
5. On error: `setErr((e as Error).message)` and `setData(null)`.
6. Always `setLoading(false)`.

## Render

```
<div className="mx-auto max-w-3xl">
  <header /* title "Web search" + intro */ />
  <form onSubmit={onSubmit}>
    <SearchIcon />
    <input type="search" value={q} ... />
    <button /* Submit */>Search</button>
  </form>
  {loading && <Loader2 spinner />}
  {err && <AlertTriangle error banner />}
  {data && (
    <ul>
      {data.results.map(r => <SearchResult row={r} />)}
    </ul>
  )}
</div>
```

### `SearchResult` (inline subcomponent)

Renders one result:
- Favicon (if present) via `<img src={r.favicon}>`.
- Title as a clickable `<a href={r.url}>` opening in a new tab with
  `rel="noreferrer"`.
- URL host as small muted text below the title.
- `r.snippet` (currently empty from DuckDuckGo HTML parser — the backend
  regex only extracts title + uddg-redirect URL).

## Conventions

- **No result caching** — every search hits the backend. The backend hits
  DuckDuckGo fresh every time, so caching at the client wouldn't help.
- **No search history** — the form is uncontrolled across visits; reopening
  the page clears the query. If you want search history, add a
  `localStorage`-backed recent-queries list.
- **Up to 30 results** — the backend caps at 30 and the frontend renders
  every one returned. No pagination / "load more" today.

---

*created by [@dhir0hit](https://github.com/dhir0hit) using [Hermes Agent](https://hermes-agent.nousresearch.com)*
