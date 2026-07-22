# `frontend/src/pages/HomePage.tsx`

The dashboard home — renders user-configured tiles from the settings store,
overlays live status/health from discovery/health APIs, shows an animated
background layer, and renders a "Discovered (unlinked)" section for
discovery results the user hasn't yet turned into managed tiles.

## Exported component

### `HomePage`

```tsx
function HomePage({ intervalMs = HEALTH_POLL_MS }: { intervalMs?: number })
```

- `intervalMs` defaults to `10_000` (10s). Override in tests / stories to
  speed up or disable health polling.

## Constants

- `HEALTH_POLL_MS = 10_000` — health polling interval in milliseconds.
- `ICON_HINT_TO_EMOJI` — map of `docker_image_hint` → emoji (e.g.
  `"grafana" → "📊"`). Used as a fallback when a tile has no explicit
  `icon` set.
- `WEEKDAYS`, `MONTHS` — used by the (small) header helper logic.

## Local state (inside `HomePage`)

| Hook | Type | Purpose |
|---|---|---|
| `useSettings()` (destructured) | store | Reads `config` slice. |
| `useState<ServicesResponse \| null>` | `discovery` | Result of `/api/services`. |
| `useState<string \| null>` | `discoveryError` | Error string, or null. |
| `useState(true)` | `loading` | True on first load only. |
| `useState(false)` | `refreshing` | True during refresh; doesn't blank the grid. |
| `useState<number \| null>` | `lastRefresh` | `Date.now()` of the last successful refresh — rendered as "updated Xs ago". |
| `useState<Record<id, ServiceHealth>>` | `healthById` | Latest health per discovered service id. |
| `useState("")` | `query` | Filter textbox value. |
| `useState<"all" \| ServiceStatus>` | `filter` | Active status filter chip. |

## Types

### `Tile` (local)

```ts
type Tile = {
  entry: ServiceEntry;
  discovered?: DiscoveredService;
  health?: ServiceHealth;
  effectiveStatus: ServiceStatus;
};
```

The composite view used for rendering and stats — a user tile paired with
its discovered-service overlay (if any), latest health (if any), and the
effective status (health → discovered → "unknown").

`Tile` is declared inside `HomePage` so subsequent memos (`tiles`,
`unlinkedTiles`, etc.) can use it without prop-drilling.

## Memos

### `loadDiscovery(silent = false)`

`useCallback`-wrapped async. Calls `api.getServices()`. The non-silent path
sets `loading=true` first (which switches the grid to `<LoadingGrid />`);
both paths set `refreshing=true`. On success: stores
`ServicesResponse`, clears the error, sets `lastRefresh`. On error: stores
the message in `discoveryError`. Always clears `loading`/`refreshing`.

Fires on mount via `useEffect(() => void loadDiscovery(), [loadDiscovery])`.

### `byContainerId: Map<string, DiscoveredService>`

Built from `discovery?.services`. Used to overlay `discovered` onto user
tiles via `entry.container_id`.

### `tiles: Tile[]`

The user's configured tiles (`config.services`), sorted by
`display_order`, with their `discovered` + `health` overlays looked up from
the maps above. `effectiveStatus = health?.status ?? discovered?.status ??
"unknown"`.

### `unlinkedTiles: Tile[]`

**The recent addition**. Discovered services that NO user tile has claimed
via `container_id`. Each is synthesized into a minimal `Tile` with:

```ts
entry: {
  id: `disc-${s.id}`,
  name: s.name,
  container_id: s.id,
  display_order: 0,
},
discovered: s,
effectiveStatus: s.status,
```

The synthetic `entry` lets the existing `TileCard`/`TileGrid` render them
unchanged. `display_order` is irrelevant — they render in a separate
section, not in the user-tile groups.

### `unlinkedFiltered: Tile[]`

Same filter logic as `groups` (filter + query), applied to `unlinkedTiles`.

### `groups: [string, Tile[]][]`

User tiles only, filtered, then bucketed by user-defined category
(`${entry.category}` for tiles with a category, `"Uncategorized"` for tiles
without one).

### `stats: Stats`

Counts across `[...tiles, ...unlinkedTiles]`:

| Stat | 来源 |
|---|---|
| `total` | `tiles.length + unlinkedTiles.length` |
| `running` | count where `effectiveStatus === "running"` |
| `stopped` | ... `=== "stopped"` |
| `paused` | ... `=== "paused"` |
| `unknown` | ... all else (termed "Unlinked" in the UI) |

Stats iterate over the **concatenated** list so the stat cards and filter
chips agree with what's visually on screen.

### `pollHealth`

`useCallback`. For every linked user tile (one with a non-empty
`container_id`), calls `api.getServiceHealth(id)` in parallel via
`Promise.all`. Failures don't propagate — the existing `healthById` entry
stays. Only updates state if the component is still mounted (uses
`mountedRef`).

Fires on every `tiles` change and every `intervalMs` via `setInterval`.

## Render tree

```
<div className="relative space-y-6">
  <BackgroundLayer />
  {discoveryError && <ErrorBanner />}
  <Hero />
  <Stats stats={stats} />
  <Filters />
  {loading ? <LoadingGrid />
   : tiles.length === 0 && unlinkedTiles.length === 0 ? <EmptyState />
   : groups.length === 0 && unlinkedFiltered.length === 0 ? <NoMatch/>
   : (
     <div className="space-y-8">
       {groups.map((...)) /* user-tile sections */}
       {unlinkedFiltered.length > 0 && <Discovered (unlinked) section>}
     </div>
   )}
  <footer /* last settings save timestamp */ />
</div>
```

The empty-state branch requires both `tiles.length === 0` AND
`unlinkedTiles.length === 0` — so a fresh install with discovery running
shows the "Discovered (unlinked)" section instead of the empty CTA.

## Subcomponents

### `BackgroundLayer`

Renders the appropriate background based on `config.background`:

- `mode === "gradient"` → animated gradient div (uses CSS vars
  `--g1`/`--g2`/`--g3` set inline from `gradient_colors`).
- `mode === "particles"` → `<ParticlesCanvas>`.
- `mode === "wallpaper"` → `<img src={wallpaper_url}>` with `wallpaper_blend`
  opacity.
- Master switch: `effects_enabled && mode !== "none"` — otherwise renders
  an empty transparent layer.

Always wraps the background with a `bg-slate-950/40` dark scrim so text
remains readable over bright images.

Aria-hidden, pointer-events-none, `fixed inset-0 -z-10`.

### `ParticlesCanvas({ density, speed })`

Canvas-based particle animation. On mount: sizes the canvas via
`window.devicePixelRatio`, constructs the particle vector array with
sizes scaled by `density`, attaches a `requestAnimationFrame` loop, listens
to `resize`. Cleanup: removes listener, cancels RAF.

Particle count: `Math.max(20, round((area / 16000) * (density / 40)))` —
scales with viewport area and the user's density setting.

Particles `ctx.fillStyle = "rgba(125, 211, 252, 0.55)"` (light cyan). Each
particle drifts on `(vx, vy)`, wrapping at the canvas borders.

### `Hero({ source, count, loading, refreshing, lastRefresh, onRefresh })`

Top header card. Title "Dashboard". Subtitle shows count + source label
(`"Mock mode"` for `source === "mock"`, `"Proxmox · <host>"` otherwise).
Refresh button (icon spins while `refreshing`). Link to `/settings`
labeled "Manage tiles".

### `Stats({ stats })`

5-card grid: `Tiles` / `Running` / `Stopped` / `Paused` / `Unlinked` —
each with a colored icon and the corresponding stat.

### `StatCard({ label, value, icon, tone })`

One stat card. `tone ∈ {slate, emerald, rose, amber, violet}` controls icon
color.

### `Filters({ query, onQuery, filter, onFilter, stats })`

Search box + 5 status chips. Chip count comes from the `stats` object so
`All N` / `Running N` / etc. always reflect the current view.

### `TileGrid({ items: Tile[] })`

Responsive 1/2/3/4-column grid rendering `<TileCard>` for each item.

### `TileCard({ entry, discovered, health, status })`

A single tile. Shows icon (from `entry.icon` or `iconForHint(discovered?.icon_hint)`),
status dot + label, tile name, image (discovered) or url (config), port
chip, guest chip, "unlinked" badge if `container_id` is set but no
discovery match. Hover reveals health details (uptime, last seen) when
`health` is available.

The whole card is wrapped in an absolute-positioned `<a>` if `link` is
non-empty, so clicking opens it in a new tab. The `link` is
`entry.url?.trim() || makeBestGuessUrl(discovered)`.

### `LoadingGrid`

6 pulsing placeholder cards rendered while `loading` is true.

### `EmptyState`

The "no dashboard tiles configured yet" CTA with a link to `/settings`.

## Helpers

### `timeAgo(ts: number): string`

`"just now"` / `"Ns ago"` / `"Nm ago"` / `"Nh ago"`.

### `labelForStatus(s): string` / `formatUptime(s): string`

UI label and human-readable uptime string. Uptime collapses to `"—" when 0`.

### `iconForHint(hint?: string): string`

`ICON_HINT_TO_EMOJI[hint.toLowerCase()] ?? "🧩"`.

### `makeBestGuessUrl(s: DiscoveredService): string`

Builds `http://<node>.local:<first_port>` so mock-mode cards are clickable.
Only meaningful in mock mode; production tiles should set their own URL.

---

*created by [@dhir0hit](https://github.com/dhir0hit) using [Hermes Agent](https://hermes-agent.nousresearch.com)*
