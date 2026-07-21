# `frontend/src/api.ts`

Thin typed wrapper around `fetch` for every backend endpoint. Exports a single
`api` object — every page and the zustand store call methods on it; no page
makes a raw `fetch` itself.

## Constants

- `API_BASE = import.meta.env.VITE_API_BASE ?? ""` — empty in production
  (nginx reverse-proxies `/api` to the backend on the same origin). Override
  with the `VITE_API_BASE` env var at build time for separate-origin dev.

## Internal helpers

### `jsonOrThrow<T>(res: Response): Promise<T>`

- `res.ok === false` → throws `Error("${status} ${statusText} ${body}")`.
- `res.status === 204` → resolves `undefined as T`.
- Otherwise → `await res.json()`.
Used by every method below.

## Methods

### Config

#### `getConfig(): Promise<DashboardConfig>`

`GET /api/config` (Accept: application/json).

On success, normalizes the response so the frontend never sees missing keys:
fills in `services`, `background`, `theme`, `bookmarks`, `custom_themes`,
`updated_at` with defaults when the server omitted them. The spreads go **first**
so explicit fallbacks below only fill gaps (TS2783-safe).

Catches fetch errors, logs `"[api] getConfig failed, returning empty default"`
to `console.warn`, and re-throws — so the store's `load()` can set the error
state. Does NOT swallow the throw.

#### `saveConfig(config: DashboardConfig): Promise<DashboardConfig>`

`PUT /api/config` (Content-Type: application/json). Full-replacement write —
the backend persists the entire config and returns the updated object (with
`updated_at` backfilled).

### Tile CRUD

#### `addService(entry: Omit<ServiceEntry, "id" | "display_order">): Promise<ServiceEntry>`

`POST /api/config/services`. Backend auto-generates `id` and `display_order`.

#### `updateService(id: string, patch: Partial<ServiceEntry>): Promise<ServiceEntry>`

`PUT /api/config/services/{id}`.

#### `deleteService(id: string): Promise<void>`

`DELETE /api/config/services/{id}`. No body on success.

#### `reorderServices(orderedIds: string[]): Promise<void>`

`PUT /api/config/services/reorder` with `{ ordered_ids: [...] }`. No body on
success.

### Background & wallpaper

#### `uploadWallpaper(file: File): Promise<{ id: string; url: string }>`

`POST /api/config/wallpaper` with multipart form data (`file` field). Returns
the new wallpaper's id and `/wallpapers/<name>` URL.

#### `listWallpapers(): Promise<{ id: string; url: string; name: string }[]>`

`GET /api/config/wallpapers`.

### Discovery + health

#### `getServices(): Promise<ServicesResponse>`

`GET /api/services` (Accept: application/json).

#### `getServiceHealth(serviceId: string): Promise<ServiceHealth | null>`

`GET /api/services/{id}/health`. Returns `null` on 404 (container not
discovered) or on any network error (caught, log omitted). Never throws — safe
to call in `Promise.all` batches.

### Bookmarks

#### `listBookmarks(): Promise<Bookmark[]>`

`GET /api/config/bookmarks`.

#### `addBookmark(entry: Omit<Bookmark, "id" | "display_order">): Promise<Bookmark>`

`POST /api/config/bookmarks`. Backend auto-generates `id` and `display_order`.

#### `updateBookmark(id: string, patch: BookmarkPatch): Promise<Bookmark>`

`PUT /api/config/bookmarks/{id}`.

#### `deleteBookmark(id: string): Promise<void>`

`DELETE /api/config/bookmarks/{id}`.

### Custom themes

#### `listCustomThemes(): Promise<ThemeDefinition[]>`

`GET /api/config/themes`.

#### `addCustomTheme(theme: Omit<ThemeDefinition, "id">): Promise<ThemeDefinition>`

`POST /api/config/themes`. Backend auto-generates `id`.

#### `deleteCustomTheme(id: string): Promise<void>`

`DELETE /api/config/themes/{id}`.

### Search

#### `search(query: string): Promise<SearchResponse>`

`GET /api/search?query=<query>` (Accept: application/json).

### Cron

#### `listCron(): Promise<CronListResponse>`

`GET /api/cron` (Accept: application/json).

### Widget registry + auto-login

#### `listWidgets(): Promise<WidgetDefinition[]>`

`GET /api/widgets` (Accept: application/json). Returns the full widget
registry. The Settings page uses this to populate the widget-type dropdown;
the Home page uses it to decide whether to show the Login button on a tile
(`auth_schema !== "none"`).

#### `getWidget(widgetId: string): Promise<WidgetDefinition>`

`GET /api/widgets/{widgetId}`. Single widget lookup. Currently unused by
the frontend (the full list is fetched once), but available for
widget-specific detail pages.

#### `tileLogin(tileId: string): Promise<TileLoginResponse>`

`POST /api/tiles/{tileId}/auth`. Triggers server-side login for the tile.
The backend loads the tile by id, looks up its `widget_type` in the
registry, and performs the appropriate login call (api_key header, HTTP
basic, or form POST) against `api_url + login_path`. Returns cookies
(Set-Cookie strings) and a `redirect_url`.

The frontend plants the cookies via `document.cookie` then opens
`redirect_url` in a new tab — the service sees the authenticated session
and the user lands on the dashboard without manually logging in.

## Conventions

- Every method goes through `jsonOrThrow`, so HTTP non-2xx becomes a thrown
  `Error` with a string like `"502 Bad Gateway ..."`. Pages and the store
  catch and surface these in their local `err` state.
- Only `getServiceHealth` swallows errors internally (returns `null`); every
  other method propagates.
- Method names mirror backend route verbs (`getConfig` ↔ `GET /api/config`).
- No retries, no auth headers — the backend has no auth and the frontend relies
  on nginx same-origin proxying in production.

---

*created by [@dhir0hit](https://github.com/dhir0hit) using [Hermes Agent](https://hermes-agent.nousresearch.com)*
