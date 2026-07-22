# Docker Dashboard — Code Documentation

Per-module documentation for the Docker Dashboard codebase. Every markdown
file in this tree documents one source module — backend or frontend — with
its exported symbols, types, side effects, and notable implementation
details.

For end-user configuration (env vars, the Settings page, deployment), see
[`../CONFIGURATION.md`](../CONFIGURATION.md). For the project overview /
setup instructions, see [`../README.md`](../README.md).

## Layout

```
docs/
├── README.md           # this file
├── ARCHITECTURE.md     # how the pieces connect
├── backend/            # one MD per module in backend/app/
│   ├── __init__.md
│   ├── config.md
│   ├── config_store.md
│   ├── docker_discover.md
│   ├── main.md
│   ├── mock_data.md
│   ├── schemas.md
│   ├── wallpapers.md
│   └── widgets.md
└── frontend/           # one MD per module in frontend/src/
    ├── App.md
    ├── api.md
    ├── index-css.md
    ├── main.md
    ├── store.md
    ├── types.md
    ├── vite-env-dts.md
    └── pages/
        ├── BookmarksPage.md
        ├── CalendarPage.md
        ├── HomePage.md
        ├── SearchPage.md
        └── SettingsPage.md
```

## Reading order

If you're new to the codebase, this order builds understanding roughly
end-to-end:

1. [`ARCHITECTURE.md`](ARCHITECTURE.md) — the 30k-foot view.
2. **Backend foundation** (in this order):
   - [`backend/config.md`](backend/config.md) — every env var and its
     default.
   - [`backend/schemas.md`](backend/schemas.md) — the public API contract.
   - [`backend/config_store.md`](backend/config_store.md) — how config
     persists.
   - [`backend/docker_discover.md`](backend/docker_discover.md) — finding
     containers on the host.
   - [`backend/wallpapers.md`](backend/wallpapers.md) — wallpaper upload/
     serve.
   - [`backend/mock_data.md`](backend/mock_data.md) — what you see in mock
     mode.
   - [`backend/main.md`](backend/main.md) — FastAPI routes binding it all
     together.
3. **Frontend foundation**:
   - [`frontend/types.md`](frontend/types.md) — mirrors the backend
     schemas; the contract every frontend module consumes.
   - [`frontend/api.md`](frontend/api.md) — typed `fetch` wrapper.
   - [`frontend/store.md`](frontend/store.md) — zustand store + actions.
   - [`frontend/App.md`](frontend/App.md) — router + layout chrome.
   - [`frontend/main.md`](frontend/main.md) — entry point.
   - [`frontend/index-css.md`](frontend/index-css.md) — design-system
     primitives + animations.
   - [`frontend/vite-env-dts.md`](frontend/vite-env-dts.md) — one env var.
4. **Frontend pages** — read in any order, but the order below matches
   complexity:
   - [`frontend/pages/HomePage.md`](frontend/pages/HomePage.md) — the
     largest and most central; tiles + discovery + background.
   - [`frontend/pages/SettingsPage.md`](frontend/pages/SettingsPage.md) —
     tile CRUD + theme + background.
   - [`frontend/pages/BookmarksPage.md`](frontend/pages/BookmarksPage.md) —
     bookmarks CRUD.
   - [`frontend/pages/CalendarPage.md`](frontend/pages/CalendarPage.md) —
     Hermes cron view.
   - [`frontend/pages/SearchPage.md`](frontend/pages/SearchPage.md) —
     DuckDuckGo proxy.

## Conventions used by these docs

- **Each module is self-contained**: you can read any one MD without having
  read the others. Cross-references point to other docs by relative path.
- **Field tables** mirror the source — when the backend pydantic model
  changes, update the matching doc. Same for the frontend `types.ts`.
- **Notable details** sections flag actual gotchas (no retries, no auth
  layer, single-row convention, etc.) — not "could theoretically"-style
  speculation.
- **No prose summaries in survey dumps**: the surveys that built these docs
  produced raw facts; the docs are written for humans to skim.

---

*created by [@dhir0hit](https://github.com/dhir0hit) using [Hermes Agent](https://hermes-agent.nousresearch.com)*
