# `frontend/src/main.tsx`

The Vite entry point — mounted into `<div id="root">` in `index.html`. ~9 lines,
three concerns:

1. Import the global stylesheet (`index.css`) — Tailwind base + components +
   custom classes/animations.
2. Import `App` (the actual application).
3. Mount under React `StrictMode` (double-invokes effects in dev to help catch
   bugs; in production builds it's a no-op).

```tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import App from "./App";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>
);
```

## Notes

- `document.getElementById("root")!` — non-null assertion because `index.html`
  guarantees the `<div id="root">` exists. If you change the root id, also
  update the `index.html` template.
- There is no error boundary here. An uncaught error in any route leaves
  `<div id="root">` empty (white screen). For production deployments,
  consider wrapping `<App />` in a React error boundary that renders a
  fallback message and logs the error to the backend. See the
  `CONFIGURATION.md` troubleshooting section for the historical blank-page
  case this would have caught.
- Vite resolves this file from `index.html`'s `<script type="module">` tag.
  HMR during `npm run dev` is automatic.

---

*created by [@dhir0hit](https://github.com/dhir0hit) using [Hermes Agent](https://hermes-agent.nousresearch.com)*
