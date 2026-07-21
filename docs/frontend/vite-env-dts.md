# `frontend/src/vite-env.d.ts`

TypeScript ambient declarations for Vite's environment variables. 8 lines.

```ts
/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
```

## Purpose

Augments the global `import.meta.env` shape with our project's env vars so
TypeScript knows `import.meta.env.VITE_API_BASE` is a `string | undefined`.
Without this, any access to `import.meta.env.<NAME>` would be `any`.

## Variables

### `VITE_API_BASE`

Optional string. Empty in production (nginx reverse-proxies `/api` on the
same origin). Override at build time when the frontend and backend are on
different origins:

```bash
VITE_API_BASE=https://api.example.com npm run build
```

Consumed only in `frontend/src/api.ts` — every `fetch` path is prefixed with
it (so it's empty by default and `/api/...` resolves on the same origin).

---

*created by [@dhir0hit](https://github.com/dhir0hit) using [Hermes Agent](https://hermes-agent.nousresearch.com)*
