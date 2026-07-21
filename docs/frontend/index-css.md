# `frontend/src/index.css`

Global stylesheet — Tailwind entry + custom component classes + animations
the design depends on. Loaded once at the top of `main.tsx`.

## Tailwind layers

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

Plus the dark color-scheme hint on `:root` and a 100% height chain
(`html, body, #root { height: 100% }`) so absolutely-positioned backgrounds
work.

## Body background

A static layered radial-gradient (cyan + magenta tones on `#050816`) provides
a base color before any `BackgroundLayer` mounts, and remains visible when
`background.mode === "none"`. The animated `BackgroundLayer` from `HomePage`
sits on top of this.

## Component classes (`@layer components`)

Reusable design-system primitives extracted from repeat Tailwind utility
chains. Pages use these class names directly.

| Class | Purpose |
|---|---|
| `.glass` | Frosted card: `rounded-2xl`, white/10 border, `bg-slate-900/60`, `shadow-2xl`, `backdrop-blur-xl`. Used by every panel/card. |
| `.btn` | Base button: inline-flex, gap-2, `px-4 py-2`, `text-sm`, active scale 0.97, disabled opacity. Three modifiers follow. |
| `.btn-primary` | Cyan filled (dark text). CTAs like "Add your first tile". |
| `.btn-ghost` | Outlined translucent. Refresh, Manage tiles, secondary actions. |
| `.btn-danger` | Rose filled. Destructive actions. |
| `.input` | Form input: full-width, slate-950 fill, cyan focus ring. |
| `.label` | Inline-block uppercase text-xs slate-400 — labels above form fields. |
| `.chip` | Pill-shaped badge for stats, port tags, group counts. |
| `.status-dot` | Status indicator dot. Modifier classes below color it. |
| `.status-dot-running` | Emerald-400, with an animated pulsing halo (see `statusPulse`). |
| `.status-dot-stopped` | Rose-400. |
| `.status-dot-paused` | Amber-400. |
| `.status-dot-unknown` | Slate-500. |

The `::after` element on `.status-dot` is the halo — only `.status-dot-running`
animates it (via `animate-status-pulse`); the others paint a static colored
ring.

## Keyframes / animations

### `bgGradientShift` (24s ease-in-out infinite)

Shifts `background-position` 0% → 100% → 0% over 24s. Used by
`.bg-gradient-animated` (the `BackgroundLayer` mode=`gradient` div) to make
the configured gradient orbit slowly. The element's three color stops come
from CSS vars `--g1`, `--g2`, `--g3` set inline by `BackgroundLayer`.

### `.bg-gradient-animated`

A 5-stop `linear-gradient(120deg, …)` over the three themed stops, sized
`300% 300%`, with `filter: saturate(140%) brightness(0.55)` — the brightness
drop keeps the gradient from washing out foreground text.

### `.bg-particles-canvas`

Display: block, full width/height — used by `ParticlesCanvas` in `HomePage`.

### `bgKenBurns` (36s)

Slow scale + drift for `.bg-wallpaper-img` (mode=`wallpaper`). Keeps a static
wallpaper from feeling dead.

### `statusPulse` (2s)

Halo expands and fades from scale 1 to 2.4. Used by
`.status-dot-running::after` via the `.animate-status-pulse` class.

## Tile hover

`.tile-card` gets a 180ms ease-out `translateY(-2px)` lift on hover. Hover
border color/shadow are added in `HomePage`'s JSX via Tailwind utilities.

## Reduced motion

`@media (prefers-reduced-motion: reduce)` disables every animation/transition
on `.bg-gradient-animated`, `.bg-wallpaper-img`, `.animate-status-pulse`, and
`.tile-card`, plus pins the gradient and wallpaper to static positions. The
user gets the same visual design without motion.

---

*created by [@dhir0hit](https://github.com/dhir0hit) using [Hermes Agent](https://hermes-agent.nousresearch.com)*
