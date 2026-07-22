# `frontend/src/pages/SettingsPage.tsx`

Dashboard settings — tile CRUD with drag-and-drop reorder, background
effects/mode/wallpaper controls, theme selection + custom theme CRUD.

## Exported component

### `SettingsPage`

No props. Reads `useSettings()` store directly (config + every mutating
action). Auto-loads config on mount if status is idle.

## Layout

```
<div className="space-y-6">
  <header /* title + StatusPill */ />
  <TilesSection /* tile CRUD + DnD */ />
  <BackgroundSection />
  <ThemeSection />
  <footer /* last saved timestamp */ />
</div>
```

`StatusPill` reflects `status` (idle/loading/saving/error) with an icon and
color; error message is in the `title` tooltip.

## Component: `StatusPill`

Idle = green "Synced". Saving/loading = amber with spinner. Error = rose.
The pill is the source of truth for save state across the page.

## Section: `TilesSection`

`@dnd-kit`-powered sortable list of tiles.

### Props

```ts
{
  services: ServiceEntry[];
  onAdd, onUpdate, onDelete, onReorder;
}
```

### Behavior

- Renders each tile as a `<SortableTileRow>` (uses
  `useSortable` from `@dnd-kit/sortable`).
- `DndContext` with `PointerSensor` + `KeyboardSensor` (keyboard coordinates
  from `sortableKeyboardCoordinates`).
- `collisionDetection={closestCenter}`.
- `DragOverlay` renders a snapshot of the dragged tile while in flight.
- `onDragEnd` uses `arrayMove` to compute the new order and calls
  `onReorder(orderedIds)` — the store persists via
  `api.reorderServices`.
- "Add tile" button at the top opens an `<TileEditor>` (modal-style form)
  for creating a new tile.
- Each row exposes "Edit" (pencil) and "Delete" (trash). Delete is
  immediate — there is no confirmation dialog (intentional: KISS; the user
  can re-add via Add tile).

### Subcomponents

- `SortableTileRow` — a single row with the gripper handle, tile icon,
  name/url/icon fields, the container_id linker dropdown, and Edit/Delete
  buttons. `useSortable` returns transform/transition CSS that the row
  applies for the drag animation.
- `TileEditor` — form with `name`, `url`, `icon`, `container_id`, `category`. Used for
  both Add and Edit (in Edit mode, fields are pre-populated and the save
  button label changes). On submit, calls either `onAdd` or `onUpdate`.

## Section: `BackgroundSection`

Controls `config.background` via `setBackground` from the store.

### Controls

- **Effects toggle** — master `effects_enabled` switch (uses the `Toggle`
  subcomponent). When off, the entire `BackgroundLayer` on the Home page
  hides.
- **Mode dropdown** — `none` / `gradient` / `particles` / `wallpaper`.
  Switching updates `background.mode` and reveals mode-specific controls.
- **Gradient colors** — three `<input type="color">` widgets for the three
  gradient stops. Updates `gradient_colors` as a tuple (TS casts the array
  to `[string, string, string]`).
- **Particles** — two `<RangeField>` sliders for `particle_density` and
  `particle_speed` (only visible in `mode === "particles"`).
- **Wallpaper blend** — a single `<RangeField>` (only visible in
  `mode === "wallpaper"`).
- **Wallpaper picker + upload** — a list of previously uploaded wallpapers
  (fetched via `api.listWallpapers()`) with thumbnails; selecting one sets
  `wallpaper_url`. The upload control uses `api.uploadWallpaper(file)`
  which uploads then immediately switches background to the new wallpaper
  via `uploadWallpaper` in the store.

## Section: `ThemeSection`

Controls `config.theme` and `config.custom_themes`.

### Controls

- **Active theme dropdown** — built from `[...BUILTIN_THEMES, ...customThemes]`.
- **Accent color** — `<input type="color">`, overrides the active theme's
  accent.
- **Density dropdown** — `compact` / `comfortable` / `spacious`.
- **"New theme" button** — opens `<ThemeEditor>` to define a custom theme.
- **Custom themes list** — each has an Edit and Delete button. Delete
  uses `api.deleteCustomTheme`. If the active theme is deleted, the
  dropdown falls back to `BUILTIN_THEMES[0]` on next render.

### Subcomponents

- `ThemeEditor` — modal form for name + dark flag + 6 `<input type="color">`
  pickers (accent, bg, surface, text, muted, border). On submit, calls
  `api.addCustomTheme`.
- `Toggle` — `{ checked, onChange }`. Animated switch.
- `RangeField` — `{ label, min, max, value, onChange, suffix?, className? }`.

## Persisted actions

Every mutation goes through the `useSettings` store:

| Action | Store method | Backend route |
|---|---|---|
| Add tile | `addService(entry)` | `POST /api/config/services` |
| Edit tile | `updateService(id, patch)` | `PUT /api/config/services/{id}` |
| Delete tile | `deleteService(id)` | `DELETE /api/config/services/{id}` |
| Reorder | `reorderServices(ids)` | `PUT /api/config/services/reorder` |
| Background patch | `setBackground(patch)` | `PUT /api/config` (full replace) |
| Theme patch | `setTheme(patch)` | `PUT /api/config` |
| Add custom theme | (direct `api.addCustomTheme`) | `POST /api/config/themes` |
| Delete custom theme | (direct `api.deleteCustomTheme`) | `DELETE /api/config/themes/{id}` |
| Upload wallpaper | `uploadWallpaper(file)` | `POST /api/config/wallpaper` |

## Conventions

- **Optimistic updates**: every store mutator updates `config` locally before
  the network call. The optimistic state is visible immediately; if the
  PUT fails, `status === "error"` lights up the pill but the local state
  stays as the optimistic value (no rollback). Acceptable for a single-user
  dashboard — re-open the page to resync.
- **No confirmation dialogs**: deletes are immediate. Power-user UX;
  re-add via Add Tile if you fat-finger.
- **Drag-and-drop**: `@dnd-kit/sortable` with `verticalListSortingStrategy`
  for the tile list. Keyboard accessible via the `KeyboardSensor` — tab
  to a row, hit Space to start dragging, arrow keys to move, Space again
  to drop.

---

*created by [@dhir0hit](https://github.com/dhir0hit) using [Hermes Agent](https://hermes-agent.nousresearch.com)*
