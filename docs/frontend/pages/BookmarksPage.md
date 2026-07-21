# `frontend/src/pages/BookmarksPage.tsx`

Bookmarks CRUD UI with category filter. Persists to
`/api/config/bookmarks` via the `api` object — does NOT use the zustand
store (bookmarks aren't part of the `DashboardConfig` the store manages
on the homepage tiles).

## Exported component

### `BookmarksPage`

No props. Manages its own local state and calls `api.listBookmarks` /
`api.addBookmark` / `api.updateBookmark` / `api.deleteBookmark` directly.

## Local state

| Hook | Type | Purpose |
|---|---|---|
| `useState<Bookmark[]>` | `bookmarks` | Current list. |
| `useState(true)` | `loading` | First-load gate. |
| `useState<string \| null>` | `err` | Error banner text, or null. |
| `useState<EditingState>` | `editing` | Modal-mode state. |
| `useState("all")` | `filter` | Active category filter. |

### `EditingState` (local type)

```ts
type EditingState =
  | { mode: "add" }
  | { mode: "edit"; bookmark: Bookmark }
  | null;
```

## Lifecycle

`useEffect` on mount calls `reload()`. `reload` sets `loading=true`, calls
`api.listBookmarks()`, stores the result + clears `err`. Always clears
`loading`.

## Categories filter

`allCategories` is derived via `useMemo` from the union of every bookmark's
`category` — so categories appear organically without the user having to
register them anywhere. The filter dropdown has "All" plus one entry per
category.

`filtered = bookmarks.filter(b => filter === "all" || b.category === filter)`.

## Render

```
<div className="mx-auto max-w-3xl">
  <header /* title "Web bookmarks" */ />
  {err && <ErrorBanner />}
  {loading ? <LoadingSpinner />
   : (
     <>
       {filtered.length === 0 ? <EmptyState/> : <BookmarkList items={filtered} />}
       <CategoryFilter/>
       <AddButton /* opens editor *//>
     </>
   )}
  {editing && <BookmarkEditor ... />}
</div>
```

Sub-nav is the standard mobile/desktop nav from `App.tsx`. Category filter
sits below the list (mobile-friendly ordering).

## Bookmark editor

Modal-style form. Fields:

- `title` — required text input.
- `url` — required URL input (light client-side validation, no enforced
  format — backend accepts any string).
- `category` — freeform text input with a datalist of existing categories
  for autocomplete.
- `icon` — optional emoji / hint input.

On submit: calls `api.addBookmark` (mode `add`) or `api.updateBookmark(id,
patch)` (mode `edit`). On success: clears `editing` and calls `reload()`.
Error: stores the message in `err`, leaves the editor open.

## Delete

Trash button on each bookmark row. No confirmation dialog. Calls
`api.deleteBookmark(id)`, then `reload()`.

## Conventions

- **Local state, not store**: bookmarks are independent of the homepage tile
  state, so they don't pollute the `useSettings` store. This means
  bookmark edits don't trigger a re-render of the homepage — they're
  independent views.
- **Reload after mutation**: every mutation calls `reload()` on success —
  no optimistic local updates. Single-user dashboard, so the round-trip
  cost is acceptable and the code stays simple.
- **Image icons**: when `icon` is empty, the row uses a generic 🔖 emoji.

---

*created by [@dhir0hit](https://github.com/dhir0hit) using [Hermes Agent](https://hermes-agent.nousresearch.com)*
