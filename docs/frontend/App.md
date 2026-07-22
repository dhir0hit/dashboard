# `frontend/src/App.tsx`

The application shell — routing, layout chrome (header + nav), and the theme
applier. No tile logic, no API calls beyond the one-time `load()`.

## Components

### `App` (default export)

```tsx
export default function App() {
  return (
    <BrowserRouter>
      <AppContent />
    </BrowserRouter>
  );
}
```

`App` does ONLY the router provider. It must not call `useLocation()` or any
react-router hook — those require a router context, which only exists below
`<BrowserRouter>`. (Calling them at the top of `App` was the cause of the
"blank page" bug; the split below is the fix.)

### `AppContent`

Renders inside the router. Owns:

- `useSettings((s) => s.load)` → `useEffect(() => { void load(); }, [load])`.
  Fires once on mount; populates the global config store.
- `useLocation()` for the current pathname.
- `useEffect` that scrolls to top on `location.pathname` change — feels much
  better on mobile when navigating between routes.
- `<ThemeApplier />` — sets `--theme-*` CSS variables on `<html>` based on the
  active theme.
- `<Header />` (desktop top bar, hidden on `< md`).
- `<MobileTopBar />` (mobile top bar, hidden on `>= md`).
- `<main>` containing `<Routes>`:
  - `/` → `<HomePage />`
  - `/search` → `<SearchPage />`
  - `/bookmarks` → `<BookmarksPage />`
  - `/calendar` → `<CalendarPage />`
  - `/settings` → `<SettingsPage />`
- `<MobileBottomNav />` (fixed bottom nav, hidden on `>= md`).

### `ThemeApplier`

```tsx
const theme = useSettings((s) => s.config.theme);
const customThemes = useSettings((s) => s.config.custom_themes);
const active = [...BUILTIN_THEMES, ...customThemes]
  .find((t) => t.id === theme.active_theme) ?? BUILTIN_THEMES[0];
```

On every change to `theme.active_theme` or `customThemes`, sets these CSS
custom properties on `document.documentElement`:

- `--theme-accent` (with `accent_color` override if set)
- `--theme-bg`
- `--theme-surface`
- `--theme-text`
- `--theme-muted`
- `--theme-border`

And toggles `document.body` class `theme-light` based on `active.dark`.

Renders `null` — pure side effect.

### `Header`

Desktop-only (`hidden md:block`) sticky top bar:

- "◈ Dashboard" brand.
- `<nav>` of 5 `<NavLink>`s from the `NAV` array (Home, Search, Bookmarks,
  Calendar, Settings). Active link gets `bg-white/10 text-white`; inactive
  gets `text-slate-400 hover:text-white`.

### `MobileTopBar`

Mobile-only (`md:hidden`) sticky top bar with the brand only.

### `MobileBottomNav`

Mobile-only (`md:hidden`) fixed bottom nav — 5-column grid of `<NavLink>`s
matching the desktop header. Active: `text-cyan-300`; inactive:
`text-slate-500`.

### `useDesktopNav()`

Currently returns `null`. Kept as a hook for future window-size detection.
The component currently renders both layouts and toggles via Tailwind
`hidden`/`md:flex` classes, so JS overhead is minimal and there's no flash
on SSR.

## Constants

### `NAV`

Array of 5 `{ to, end, label, Icon }` objects — `to` is the route path, `end`
is react-router's `end` prop (true for `/` so it doesn't match every route),
`label` is the nav text, `Icon` is a `lucide-react` component.

## Layout philosophy

- The router lives at the OUTERMOST level (`App`). Everything router-aware
  lives at or below `AppContent`. This split is load-bearing — see the file
  header comment in App.tsx for the historical reason.
- Both nav layouts are always in the DOM, toggled by Tailwind responsive
  classes. Cheaper than conditional rendering and SSR-safe.
- `<main>` has `max-w-6xl` and consistent padding across all routes so pages
  share an aligned grid.

---

*created by [@dhir0hit](https://github.com/dhir0hit) using [Hermes Agent](https://hermes-agent.nousresearch.com)*
