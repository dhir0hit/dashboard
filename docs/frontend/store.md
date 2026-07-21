# `frontend/src/store.ts`

The global state container — a single zustand store that owns the
`DashboardConfig` and every mutation that touches `/api/config`. The Settings
page consumes it directly; the Home page reads `config.services` for tiles.

## Setup

```ts
import { create } from "zustand";
import { api } from "./api";
import { DashboardConfig, ServiceEntry, DEFAULT_CONFIG } from "./types";
```

## Types

### `Status`

`"idle" | "loading" | "saving" | "error"` — drives Settings-page UI feedback
(spinner, error banner).

### `SettingsState`

| Field | Type | Notes |
|---|---|---|
| `config` | `DashboardConfig` | Current config; starts at `DEFAULT_CONFIG`. |
| `status` | `Status` | Loading/saving state. |
| `error` | `string \| null` | Last error message, or null. |
| `load` | `() => Promise<void>` | Fetch config from backend. |
| `persist` | `(next: DashboardConfig) => Promise<void>` | PUT-replace config. |
| `addService` | `(entry: Omit<ServiceEntry, "id" \| "display_order">) => Promise<void>` | Add a tile. |
| `updateService` | `(id, patch) => Promise<void>` | Edit a tile. |
| `deleteService` | `(id) => Promise<void>` | Remove a tile. |
| `reorderServices` | `(orderedIds) => Promise<void>` | Reorder tiles. |
| `setBackground` | `(patch: Partial<...["background"]>) => Promise<void>` | Patch background settings. |
| `setTheme` | `(patch: Partial<...["theme"]>) => Promise<void>` | Patch theme settings. |
| `uploadWallpaper` | `(file: File) => Promise<string>` | Upload + select wallpaper. |

## Store shape

```ts
export const useSettings = create<SettingsState>((set, get) => ({
  config: DEFAULT_CONFIG,
  status: "idle",
  error: null,
  // …actions below
}));
```

Pages consume slices via selectors, e.g.
`useSettings((s) => s.config)` — passes a selector to avoid re-rendering on
unrelated state changes (zustand's recommended pattern).

## Actions

### `load`

```ts
set({ status: "loading", error: null });
const cfg = await api.getConfig();
set({ config: cfg, status: "idle" });
```

On error: `set({ status: "error", error: (err as Error).message })`. The config
stays at its prior value so the Settings page remains usable with stale data
— the comment notes "Backend not up yet — keep defaults."

Called once from `AppContent` on mount (see `App.tsx` doc).

### `persist(next)`

```ts
set({ status: "saving" });
const saved = await api.saveConfig(next);
set({ config: saved, status: "idle", error: null });
```

Optimistic-update pattern: callers (`addService`, `updateService`, etc.) mutate
`config` first via `set({ config: next })`, THEN call `persist(next)`. So the
UI reflects the change before the network round-trip completes. If the PUT
fails, `persist` throws after setting `status: "error"` — callers decide
whether to rollback (none currently do).

### `addService(entry)`

- Generates `id = genId(entry.name)` → `svc-<slug>-<5-char-base36>`.
- Appends to `config.services` with `display_order = services.length`.
- `set({ config: next })` (optimistic).
- Awaits `persist(next)`.

### `updateService(id, patch)`

Maps over `config.services`, applying `patch` to the matching id. `id` is
preserved (callers cannot rename it). Persists.

### `deleteService(id)`

Filters out the id, reindexes `display_order` for survivors (0..n-1),
persists. This matches the backend's delete behavior.

### `reorderServices(orderedIds)`

Builds a `byId` map, walks `orderedIds` setting `display_order = i`, dropping
any id not in `byId` (defensive). Then appends any services that weren't in
`orderedIds` (the comment explicitly says "never drop services"). Persists.

### `setBackground(patch)`

`{ ...config, background: { ...config.background, ...patch } }` — true
partial update of the background sub-object. Persists.

### `setTheme(patch)`

Same pattern for the theme sub-object.

### `uploadWallpaper(file)`

```ts
const { url } = await api.uploadWallpaper(file);
await get().setBackground({ mode: "wallpaper", wallpaper_url: url });
return url;
```

Combines upload + immediate background switch. Returns the URL so the caller
(e.g. Settings page) can show it in the wallpaper picker.

## Helpers

### `genId(name: string): string`

```ts
const slug = name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
return `svc-${slug}-${Math.random().toString(36).slice(2, 7)}`;
```

Client-side id generator mirroring the backend's `_gen_service_id`. Used only
by `addService` for the optimistic tile id; the backend will dedupe if a
collision somehow occurs (it appends a hex suffix server-side).

## Conventions

- **Selectors**: always read state via `useSettings((s) => s.field)` to keep
  re-renders narrow. The store is intentionally a single flat object so any
  slice can be a selector target.
- **Optimistic updates**: every mutating action `set`s the next config BEFORE
  awaiting `persist`. Roll-on-error is the caller's responsibility (currently
  not done — Settings page surfaces the error via `status === "error"` and
  lets the user retry).
- **No HTTP-level error handling in the store** beyond setting `error`. Pages
  show banners based on `status === "error"` and `error` text.

---

*created by [@dhir0hit](https://github.com/dhir0hit) using [Hermes Agent](https://hermes-agent.nousresearch.com)*
