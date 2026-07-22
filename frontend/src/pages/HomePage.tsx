import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  Activity,
  AlertTriangle,
  ArrowUpRight,
  Boxes,
  CheckCircle2,
  ExternalLink,
  Loader2,
  LogIn,
  PauseCircle,
  RefreshCw,
  Search,
  Settings as SettingsIcon,
  XCircle,
} from "lucide-react";
import clsx from "clsx";

import { api } from "../api";
import { useSettings } from "../store";
import type {
  DiscoveredService,
  ServiceEntry,
  ServiceHealth,
  ServiceStatus,
  ServicesResponse,
  WidgetDefinition,
} from "../types";

// Full Dashboard home page (frontend-visuals task t_dc212077).
//
// Renders the user's configured tiles from /api/config, overlays live
// status/health from /api/services + /api/services/{id}/health, and layers an
// animated background (gradient / particles / wallpaper) behind the content.
// Referenced by board.md task t_dc212077. Replaces the minimal placeholder
// HomePage shipped before this task landed.

const HEALTH_POLL_MS = 10_000;

export function HomePage({ intervalMs = HEALTH_POLL_MS }: { intervalMs?: number }) {
  const { config } = useSettings();

  // --- discovery state ----------------------------------------------------
  const [discovery, setDiscovery] = useState<ServicesResponse | null>(null);
  const [discoveryError, setDiscoveryError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [lastRefresh, setLastRefresh] = useState<number | null>(null);

  // --- health map (service_id -> health) --------------------------------
  const [healthById, setHealthById] = useState<Record<string, ServiceHealth>>({});

  // --- filters ----------------------------------------------------------
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<"all" | ServiceStatus>("all");

  // --- widget registry (for auth_schema lookup on the Login button) ------
  const [widgets, setWidgets] = useState<WidgetDefinition[]>([]);
  useEffect(() => {
    api.listWidgets()
      .then(setWidgets)
      .catch(() => setWidgets([]));
  }, []);

  const loadDiscovery = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    setRefreshing(true);
    try {
      const resp = await api.getServices();
      setDiscovery(resp);
      setDiscoveryError(null);
      setLastRefresh(Date.now());
    } catch (err) {
      setDiscoveryError((err as Error).message || "Failed to load services");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    void loadDiscovery();
  }, [loadDiscovery]);

  // --- overlay discovered status onto user tiles ------------------------
  const byContainerId = useMemo(() => {
    const m = new Map<string, DiscoveredService>();
    for (const s of discovery?.services ?? []) m.set(s.id, s);
    return m;
  }, [discovery]);

  // Composite view used for rendering + stats. Each user tile gets:
  //   - its own config (name/url/icon/container_id)
  //   - the discovered Service if container_id matches a real id
  //   - the latest health we polled (if any)
  type Tile = {
    entry: ServiceEntry;
    discovered?: DiscoveredService;
    health?: ServiceHealth;
    effectiveStatus: ServiceStatus;
  };

  const tiles: Tile[] = useMemo(() => {
    const sorted = [...config.services].sort(
      (a, b) => a.display_order - b.display_order
    );
    return sorted.map((entry) => {
      const discovered = entry.container_id
        ? byContainerId.get(entry.container_id)
        : undefined;
      const health = entry.container_id ? healthById[entry.container_id] : undefined;
      const effectiveStatus: ServiceStatus =
        health?.status ?? discovered?.status ?? "unknown";
      return { entry, discovered, health, effectiveStatus };
    });
  }, [config.services, byContainerId, healthById]);

  // --- group tiles by guest (vmid:node:kind) or "Unlinked" --------------
  const groups = useMemo(() => {
    const filtered = tiles.filter((t) => {
      if (filter !== "all" && t.effectiveStatus !== filter) return false;
      if (query.trim()) {
        const q = query.toLowerCase();
        const hay = [t.entry.name, t.entry.url ?? "", t.entry.container_id ?? "", t.discovered?.image ?? ""]
          .join(" ")
          .toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
    const buckets = new Map<string, Tile[]>();
    for (const t of filtered) {
      const key = t.discovered
        ? `${t.discovered.node} · ${t.discovered.kind.toUpperCase()} ${t.discovered.vmid}`
        : "Unlinked";
      buckets.set(key, [...(buckets.get(key) ?? []), t]);
    }
    return [...buckets.entries()];
  }, [tiles, filter, query]);

  // --- unlinked discovered services ---------------------------------------
  // Discovered services that no user tile has claimed via `container_id`.
  // Rendered in their own section below user tiles so the dashboard isn't
  // empty in mock mode (and real-mode users see what's available to link).
  const unlinkedTiles: Tile[] = useMemo(() => {
    const linkedIds = new Set(
      config.services
        .map((s) => s.container_id)
        .filter((id): id is string => !!id)
    );
    return (discovery?.services ?? [])
      .filter((s) => !linkedIds.has(s.id))
      .map((s) => ({
        entry: {
          id: `disc-${s.id}`,
          name: s.name,
          container_id: s.id,
          display_order: 0,
        },
        discovered: s,
        effectiveStatus: s.status,
      }));
  }, [config.services, discovery]);

  const unlinkedFiltered = useMemo(() => {
    return unlinkedTiles.filter((t) => {
      if (filter !== "all" && t.effectiveStatus !== filter) return false;
      if (query.trim()) {
        const q = query.toLowerCase();
        const hay = [t.entry.name, t.discovered?.image ?? "", t.discovered?.id ?? ""]
          .join(" ")
          .toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
  }, [unlinkedTiles, filter, query]);

  // --- stats ------------------------------------------------------------
  // Includes unlinked discovered services so the cards and counts agree.
  const stats = useMemo(() => {
    let running = 0,
      stopped = 0,
      paused = 0,
      unknown = 0;
    for (const t of [...tiles, ...unlinkedTiles]) {
      const s = t.effectiveStatus;
      if (s === "running") running++;
      else if (s === "stopped") stopped++;
      else if (s === "paused") paused++;
      else unknown++;
    }
    return { total: tiles.length + unlinkedTiles.length, running, stopped, paused, unknown };
  }, [tiles, unlinkedTiles]);

  // --- health polling ---------------------------------------------------
  // Poll /api/services/{id}/health for every linked tile. We do staggered,
  // per-tile fetches so a missing/404'd container id does not cancel the
  // whole batch; failures just leave the existing value in place.
  const mountedRef = useRef(true);
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const pollHealth = useCallback(async () => {
    const linked = tiles
      .map((t) => t.entry.container_id)
      .filter((id): id is string => !!id);
    if (linked.length === 0) return;
    const updates: Record<string, ServiceHealth> = {};
    await Promise.all(
      linked.map(async (id) => {
        const h = await api.getServiceHealth(id);
        if (h) updates[id] = h;
      })
    );
    if (mountedRef.current && Object.keys(updates).length) {
      setHealthById((prev) => ({ ...prev, ...updates }));
    }
  }, [tiles]);

  useEffect(() => {
    void pollHealth();
    const handle = window.setInterval(() => void pollHealth(), intervalMs);
    return () => window.clearInterval(handle);
  }, [pollHealth, intervalMs]);

  // ----------------------------------------------------------------------
  return (
    <div className="relative space-y-6">
      <BackgroundLayer />

      {discoveryError && (
        <div className="glass flex items-start gap-3 border-rose-500/30 bg-rose-950/40 p-4 text-rose-100">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-rose-300" />
          <div className="flex-1 text-sm">
            <div className="font-medium">Couldn't reach /api/services</div>
            <code className="mt-1 block break-all text-xs text-rose-200/80">
              {discoveryError}
            </code>
            <div className="mt-1 text-xs text-rose-200/60">
              Showing tiles from saved config only. Live status unavailable.
            </div>
          </div>
          <button
            type="button"
            onClick={() => void loadDiscovery()}
            className="btn-ghost px-3 py-1.5 text-xs"
          >
            <RefreshCw className={clsx("h-3.5 w-3.5", refreshing && "animate-spin")} />
            Retry
          </button>
        </div>
      )}

      <Hero
        source={discovery?.source ?? null}
        count={discovery?.count ?? null}
        loading={loading}
        refreshing={refreshing}
        lastRefresh={lastRefresh}
        onRefresh={() => void loadDiscovery(true)}
      />

      <Stats stats={stats} />

      <Filters
        query={query}
        onQuery={setQuery}
        filter={filter}
        onFilter={setFilter}
        stats={stats}
      />

      {loading ? (
        <LoadingGrid />
      ) : tiles.length === 0 && unlinkedTiles.length === 0 ? (
        <EmptyState />
      ) : groups.length === 0 && unlinkedFiltered.length === 0 ? (
        <div className="glass p-10 text-center text-sm text-slate-400">
          No tiles match your filters.
        </div>
      ) : (
        <div className="space-y-8">
          {groups.map(([label, items]) => (
            <section key={label} className="animate-fade-in">
              <header className="mb-3 flex items-center gap-2">
                <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                  {label}
                </h2>
                <span className="chip border border-white/10 bg-white/5 text-slate-300">
                  {items.length}
                </span>
                <div className="ml-2 h-px flex-1 bg-gradient-to-r from-white/10 to-transparent" />
              </header>
              <TileGrid items={items} widgets={widgets} />
            </section>
          ))}

          {unlinkedFiltered.length > 0 && (
            <section className="animate-fade-in">
              <header className="mb-3 flex items-center gap-2">
                <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                  Discovered (unlinked)
                </h2>
                <span className="chip border border-white/10 bg-white/5 text-slate-300">
                  {unlinkedFiltered.length}
                </span>
                <div className="ml-2 h-px flex-1 bg-gradient-to-r from-white/10 to-transparent" />
              </header>
              <TileGrid items={unlinkedFiltered} widgets={widgets} />
            </section>
          )}
        </div>
      )}

      <footer className="pt-2 text-xs text-slate-500">
        {config.updated_at
          ? `Last settings save: ${new Date(config.updated_at).toLocaleString()}`
          : ""}
      </footer>
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────
// Animated background layer — gradient / particles / wallpaper modes.
// ────────────────────────────────────────────────────────────────────────

function BackgroundLayer() {
  const { config } = useSettings();
  const bg = config.background;
  const enabled = bg.effects_enabled && bg.mode !== "none";

  return (
    <div
      aria-hidden
      className={clsx(
        "pointer-events-none fixed inset-0 -z-10 overflow-hidden",
        !enabled && "bg-transparent"
      )}
    >
      {enabled && bg.mode === "gradient" && (
        <div
          className="bg-gradient-animated absolute inset-0"
          style={{
            ["--g1" as string]: (bg.gradient_colors ?? ["#0ea5e9"])[0],
            ["--g2" as string]: (bg.gradient_colors ?? ["#0ea5e9", "#7c3aed"])[1] ?? "#7c3aed",
            ["--g3" as string]:
              (bg.gradient_colors ?? ["#0ea5e9", "#7c3aed", "#ec4899"])[2] ?? "#ec4899",
          }}
        />
      )}
      {enabled && bg.mode === "particles" && (
        <ParticlesCanvas density={bg.particle_density ?? 40} speed={bg.particle_speed ?? 30} />
      )}
      {enabled && bg.mode === "wallpaper" && bg.wallpaper_url && (
        <img
          src={bg.wallpaper_url}
          alt=""
          className="bg-wallpaper-img absolute inset-0"
          style={{ opacity: bg.wallpaper_blend ?? 0.6 }}
        />
      )}
      {/* Subtle dark scrim so foreground text always reads regardless of bg. */}
      <div className="absolute inset-0 bg-slate-950/40" />
    </div>
  );
}

function ParticlesCanvas({ density, speed }: { density: number; speed: number }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let raf = 0;
    type P = { x: number; y: number; vx: number; vy: number; r: number };
    let particles: P[] = [];

    function resize() {
      if (!canvas) return;
      const dpr = window.devicePixelRatio || 1;
      canvas.width = canvas.offsetWidth * dpr;
      canvas.height = canvas.offsetHeight * dpr;
      ctx?.scale(dpr, dpr);
      // particle count scales roughly with width * height vs density
      const area = canvas.offsetWidth * canvas.offsetHeight;
      const count = Math.max(20, Math.round((area / 16000) * (density / 40)));
      particles = Array.from({ length: count }, () => ({
        x: Math.random() * canvas.offsetWidth,
        y: Math.random() * canvas.offsetHeight,
        vx: (Math.random() - 0.5) * (speed / 100) * 0.8,
        vy: (Math.random() - 0.5) * (speed / 100) * 0.8,
        r: 1 + Math.random() * 1.5,
      }));
    }
    resize();
    const onResize = () => resize();
    window.addEventListener("resize", onResize);

    function tick() {
      if (!ctx || !canvas) return;
      ctx.clearRect(0, 0, canvas.offsetWidth, canvas.offsetHeight);
      ctx.fillStyle = "rgba(125, 211, 252, 0.55)";
      for (const p of particles) {
        p.x += p.vx;
        p.y += p.vy;
        // wrap edges
        if (p.x < -10) p.x = canvas.offsetWidth + 10;
        if (p.x > canvas.offsetWidth + 10) p.x = -10;
        if (p.y < -10) p.y = canvas.offsetHeight + 10;
        if (p.y > canvas.offsetHeight + 10) p.y = -10;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fill();
      }
      raf = requestAnimationFrame(tick);
    }
    raf = requestAnimationFrame(tick);
    return () => {
      window.removeEventListener("resize", onResize);
      cancelAnimationFrame(raf);
    };
  }, [density, speed]);

  return <canvas ref={canvasRef} className="bg-particles-canvas absolute inset-0" />;
}

// ────────────────────────────────────────────────────────────────────────
// Hero — title, source, refresh, last-update timestamp.
// ────────────────────────────────────────────────────────────────────────

function Hero({
  source,
  count,
  loading,
  refreshing,
  lastRefresh,
  onRefresh,
}: {
  source: string | null;
  count: number | null;
  loading: boolean;
  refreshing: boolean;
  lastRefresh: number | null;
  onRefresh: () => void;
}) {
  const sourceLabel = source === "mock" ? "Mock mode" : source ? `Docker · ${source}` : "—";
  return (
    <header className="glass flex flex-wrap items-end justify-between gap-3 p-5">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-white">Dashboard</h1>
        <p className="mt-1 text-sm text-slate-400">
          {loading
            ? "Loading services…"
            : count != null
            ? `${count} service${count === 1 ? "" : "s"} discovered · ${sourceLabel}`
            : sourceLabel}
        </p>
      </div>
      <div className="flex items-center gap-2">
        {lastRefresh && (
          <span className="hidden text-xs text-slate-500 sm:inline">
            updated {timeAgo(lastRefresh)}
          </span>
        )}
        <button
          type="button"
          onClick={onRefresh}
          className="btn-ghost"
          disabled={refreshing}
          aria-label="Refresh services"
        >
          <RefreshCw className={clsx("h-4 w-4", refreshing && "animate-spin")} />
          Refresh
        </button>
        <Link to="/settings" className="btn-ghost">
          <SettingsIcon className="h-4 w-4" /> Manage tiles
        </Link>
      </div>
    </header>
  );
}

function timeAgo(ts: number): string {
  const s = Math.max(0, Math.round((Date.now() - ts) / 1000));
  if (s < 5) return "just now";
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  return `${h}h ago`;
}

// ────────────────────────────────────────────────────────────────────────
// Stats — compact cards summarizing the fleet state.
// ────────────────────────────────────────────────────────────────────────

type Stats = {
  total: number;
  running: number;
  stopped: number;
  paused: number;
  unknown: number;
};

function Stats({ stats }: { stats: Stats }) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
      <StatCard label="Tiles" value={stats.total} icon={<Boxes className="h-4 w-4" />} tone="slate" />
      <StatCard label="Running" value={stats.running} icon={<CheckCircle2 className="h-4 w-4" />} tone="emerald" />
      <StatCard label="Stopped" value={stats.stopped} icon={<XCircle className="h-4 w-4" />} tone="rose" />
      <StatCard label="Paused" value={stats.paused} icon={<PauseCircle className="h-4 w-4" />} tone="amber" />
      <StatCard label="Unlinked" value={stats.unknown} icon={<Activity className="h-4 w-4" />} tone="violet" />
    </div>
  );
}

function StatCard({
  label,
  value,
  icon,
  tone,
}: {
  label: string;
  value: number;
  icon: React.ReactNode;
  tone: "slate" | "emerald" | "rose" | "amber" | "violet";
}) {
  const toneClass = {
    slate: "text-slate-300",
    emerald: "text-emerald-300",
    rose: "text-rose-300",
    amber: "text-amber-300",
    violet: "text-violet-300",
  }[tone];
  return (
    <div className="glass flex items-center gap-3 p-4">
      <div className={clsx("rounded-lg bg-white/5 p-2", toneClass)}>{icon}</div>
      <div>
        <div className="text-2xl font-semibold tabular-nums text-white">{value}</div>
        <div className="text-xs uppercase tracking-wider text-slate-400">{label}</div>
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────
// Filters — search box + status filter chips.
// ────────────────────────────────────────────────────────────────────────

function Filters({
  query,
  onQuery,
  filter,
  onFilter,
  stats,
}: {
  query: string;
  onQuery: (q: string) => void;
  filter: "all" | ServiceStatus;
  onFilter: (f: "all" | ServiceStatus) => void;
  stats: Stats;
}) {
  const chips: { id: "all" | ServiceStatus; label: string; count: number }[] = [
    { id: "all", label: "All", count: stats.total },
    { id: "running", label: "Running", count: stats.running },
    { id: "stopped", label: "Stopped", count: stats.stopped },
    { id: "paused", label: "Paused", count: stats.paused },
    { id: "unknown", label: "Unlinked", count: stats.unknown },
  ];
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="relative w-full sm:max-w-xs">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
        <input
          type="search"
          value={query}
          onChange={(e) => onQuery(e.target.value)}
          placeholder="Filter tiles by name, image, id…"
          className="input pl-9"
        />
      </div>
      <div className="flex flex-wrap gap-1">
        {chips.map((c) => (
          <button
            key={c.id}
            type="button"
            onClick={() => onFilter(c.id)}
            className={clsx(
              "chip border transition",
              filter === c.id
                ? "border-cyan-400/40 bg-cyan-400/10 text-cyan-200"
                : "border-white/10 bg-white/5 text-slate-400 hover:text-white"
            )}
          >
            {c.label}
            <span className="ml-1 tabular-nums text-slate-500">{c.count}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────
// Grid + tile cards.
// ────────────────────────────────────────────────────────────────────────

function TileGrid({
  items,
  widgets = [],
}: {
  items: {
    entry: ServiceEntry;
    discovered?: DiscoveredService;
    health?: ServiceHealth;
    effectiveStatus: ServiceStatus;
  }[];
  widgets?: WidgetDefinition[];
}) {
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
      {items.map((t) => (
        <TileCard
          key={t.entry.id}
          entry={t.entry}
          discovered={t.discovered}
          health={t.health}
          status={t.effectiveStatus}
          widgets={widgets}
        />
      ))}
    </div>
  );
}

// Login button for widget-backed tiles. Calls /api/tiles/{id}/auth to
// perform server-side login, plants any returned cookies on the browser,
// then opens the redirect URL in a new tab. Lives INSIDE the TileCard so
// its click handler can stopPropagation before the tile's full-card link
// catches the event.
function TileLoginButton({ entry }: { entry: ServiceEntry }) {
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function handleLogin(e: React.MouseEvent) {
    // Critical: the parent TileCard is wrapped in an <a> that would otherwise
    // catch the click. Without stopPropagation the click just opens the link.
    e.preventDefault();
    e.stopPropagation();
    setLoading(true);
    setErr(null);
    try {
      const out = await api.tileLogin(entry.id);
      if (out.cookies?.length) {
        // Set-Cookie comes back as `name=val; Path=/; HttpOnly; SameSite=Lax`.
        // browsers ignore Set-Cookie attributes set via document.cookie for
        // the HttpOnly flag - they take the cookie as plain strings.
        for (const c of out.cookies) {
          // Strip attributes after the first `;` so document.cookie accepts it.
          const crumb = c.split(";", 1)[0];
          document.cookie = `${crumb}; path=/`;
        }
      }
      window.open(out.redirect_url, "_blank", "noopener,noreferrer");
    } catch (e) {
      setErr((e as Error).message || "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <button
      type="button"
      onClick={handleLogin}
      disabled={loading}
      className="btn-ghost relative z-10 px-2 py-1 text-[11px]"
      aria-label={`Log in to ${entry.name}`}
      title={err ?? `Auto-login to ${entry.name}`}
    >
      {loading ? (
        <Loader2 className="h-3 w-3 animate-spin" />
      ) : (
        <LogIn className="h-3 w-3" />
      )}
      <span>Login</span>
      {err && (
        <span className="ml-1 text-rose-300" title={err}>!</span>
      )}
    </button>
  );
}

function TileCard({
  entry,
  discovered,
  health,
  status,
  widgets = [],
}: {
  entry: ServiceEntry;
  discovered?: DiscoveredService;
  health?: ServiceHealth;
  status: ServiceStatus;
  widgets?: WidgetDefinition[];
}) {
  const icon = entry.icon?.trim() || iconForHint(discovered?.icon_hint);
  const iconUrl = entry.icon_url?.trim();
  const [open, setOpen] = useState(false);
  const [tileInfo, setTileInfo] = useState<any>(null);
  const [infoError, setInfoError] = useState<string | null>(null);
  const statusLabel = labelForStatus(status);
  const primaryPort = discovered?.ports?.[0];
  const link = entry.url?.trim() || (discovered && primaryPort ? makeBestGuessUrl(discovered) : "");
  const widgetDef = entry.widget_type ? widgets.find((w) => w.id === entry.widget_type) : undefined;
  const hasWidget = !!entry.widget_type;
  // Only show the Login button when the widget actually needs credentials.
  // auth_schema "none" means the tile is just a link — no auto-login.
  const needsLogin = hasWidget && widgetDef && widgetDef.auth_schema !== "none";

  // Fetch live service info (ping / Jellyfin / Radarr / qBittorrent) when hovered.
  useEffect(() => {
    if (!open || !link) return;
    let cancelled = false;
    setTileInfo(null);
    setInfoError(null);
    api
      .getTileInfo(entry.id)
      .then((info) => {
        if (!cancelled) setTileInfo(info);
      })
      .catch((err) => {
        if (!cancelled) setInfoError(err?.message || "failed");
      });
    return () => {
      cancelled = true;
    };
  }, [open, link, entry.id]);
  const content = (
    <>
      <div className="flex items-start justify-between gap-2">
        <span className="grid h-10 w-10 place-items-center rounded-xl bg-white/5 text-xl">
          {iconUrl ? (
            <img
              src={iconUrl}
              alt={entry.name}
              className="h-7 w-7 object-contain"
              onError={(e) => {
                // If the custom icon fails to load, fall back to emoji/hint.
                (e.currentTarget as HTMLImageElement).style.display = "none";
                const fallback = (e.currentTarget.parentElement as HTMLElement);
                if (fallback) fallback.textContent = icon;
              }}
            />
          ) : (
            icon
          )}
        </span>
        <div className="flex items-center gap-1.5 text-xs">
          <span className={clsx("status-dot", `status-dot-${status}`)} aria-label={statusLabel} />
          <span className="text-slate-400">{statusLabel}</span>
        </div>
      </div>
      <div className="mt-3 min-w-0">
        <div className="truncate text-sm font-semibold text-white">{entry.name}</div>
        <div className="mt-0.5 truncate text-xs text-slate-400">
          {discovered?.image || entry.url || "—"}
        </div>
      </div>
      <div className="mt-3 flex items-center justify-between gap-2">
        <div className="flex flex-wrap gap-1">
          {primaryPort && (
            <span className="chip border border-white/10 bg-black/30 text-slate-300">
              :{primaryPort.host}
            </span>
          )}
          {discovered && (
            <span className="chip border border-white/10 bg-black/30 text-slate-300">
              {discovered.kind.toUpperCase()} {discovered.vmid}
            </span>
          )}
          {!discovered && entry.container_id && (
            <span className="chip border border-amber-400/20 bg-amber-400/10 text-amber-200">
              unlinked
            </span>
          )}
          {hasWidget && (
            <span className="chip border border-cyan-400/30 bg-cyan-400/10 text-cyan-200">
              {entry.widget_type}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {needsLogin && <TileLoginButton entry={entry} />}
          {link && <ArrowUpRight className="h-3.5 w-3.5 text-slate-400 opacity-0 transition group-hover:opacity-100" />}
        </div>
      </div>
      {health && open && (
        <div className="mt-3 animate-fade-in rounded-lg border border-white/10 bg-black/30 p-2 text-[11px] text-slate-300">
          <div className="flex items-center justify-between">
            <span className="text-slate-500">uptime</span>
            <span>{formatUptime(health.uptime_seconds)}</span>
          </div>
          <div className="mt-1 flex items-center justify-between">
            <span className="text-slate-500">last seen</span>
            <span>{health.last_seen ? new Date(health.last_seen).toLocaleString() : "—"}</span>
          </div>
          {health.message && (
            <div className="mt-1 truncate text-slate-400" title={health.message}>
              {health.message}
            </div>
          )}
        </div>
      )}
      {open && tileInfo && (
        <div className="mt-2 animate-fade-in rounded-lg border border-white/10 bg-black/30 p-2 text-[11px] text-slate-300">
          {tileInfo.type === "jellyfin" && (
            <>
              <div className="flex items-center justify-between">
                <span className="text-slate-500">Server</span>
                <span>{tileInfo.server_name || "Jellyfin"}</span>
              </div>
              {tileInfo.version && (
                <div className="mt-1 flex items-center justify-between">
                  <span className="text-slate-500">Version</span>
                  <span>{tileInfo.version}</span>
                </div>
              )}
              {tileInfo.active_connections != null && (
                <div className="mt-1 flex items-center justify-between">
                  <span className="text-slate-500">Active</span>
                  <span>{tileInfo.active_connections} connections</span>
                </div>
              )}
            </>
          )}
          {tileInfo.type === "radarr" && (
            <>
              <div className="flex items-center justify-between">
                <span className="text-slate-500">Version</span>
                <span>{tileInfo.version || "—"}</span>
              </div>
              <div className="mt-1 flex items-center justify-between">
                <span className="text-slate-500">Movies</span>
                <span>{tileInfo.movie_count ?? 0}</span>
              </div>
              {tileInfo.wanted_count != null && (
                <div className="mt-1 flex items-center justify-between">
                  <span className="text-slate-500">Wanted</span>
                  <span>{tileInfo.wanted_count}</span>
                </div>
              )}
            </>
          )}
          {tileInfo.type === "qbittorrent" && (
            <>
              <div className="flex items-center justify-between">
                <span className="text-slate-500">Version</span>
                <span>{tileInfo.qbittorrent_version || "—"}</span>
              </div>
              <div className="mt-1 flex items-center justify-between">
                <span className="text-slate-500">Downloading</span>
                <span>{tileInfo.downloading ?? 0}</span>
              </div>
              <div className="mt-1 flex items-center justify-between">
                <span className="text-slate-500">Uploading</span>
                <span>{tileInfo.uploading ?? 0}</span>
              </div>
              {tileInfo.total_downloaded && (
                <div className="mt-1 flex items-center justify-between">
                  <span className="text-slate-500">Downloaded</span>
                  <span>{formatBytes(tileInfo.total_downloaded)}</span>
                </div>
              )}
            </>
          )}
          {tileInfo.type === "ping" && (
            <>
              <div className="flex items-center justify-between">
                <span className="text-slate-500">Status</span>
                <span className={tileInfo.online ? "text-emerald-400" : "text-rose-400"}>
                  {tileInfo.online ? "Online" : "Offline"}
                </span>
              </div>
              {tileInfo.status_code && (
                <div className="mt-1 flex items-center justify-between">
                  <span className="text-slate-500">HTTP</span>
                  <span>{tileInfo.status_code}</span>
                </div>
              )}
              {tileInfo.response_time_ms != null && (
                <div className="mt-1 flex items-center justify-between">
                  <span className="text-slate-500">Response</span>
                  <span>{tileInfo.response_time_ms}ms</span>
                </div>
              )}
            </>
          )}
        </div>
      )}
      {open && infoError && (
        <div className="mt-2 text-[11px] text-slate-500">{infoError}</div>
      )}
    </>
  );

  return (
    <div
      className="tile-card glass group relative overflow-hidden p-4 hover:border-cyan-400/40 hover:shadow-cyan-500/10"
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
    >
      {link ? (
        <a
          href={link}
          target="_blank"
          rel="noreferrer"
          className="absolute inset-0"
          aria-label={`Open ${entry.name}`}
        />
      ) : null}
      {content}
      {entry.container_id && !discovered && (
        <div className="pointer-events-none mt-3 flex items-center gap-1 text-[11px] text-amber-300/80">
          <ExternalLink className="h-3 w-3" /> container not discovered
        </div>
      )}
    </div>
  );
}

function LoadingGrid() {
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="glass animate-pulse p-4">
          <div className="flex items-start justify-between">
            <div className="h-10 w-10 rounded-xl bg-white/5" />
            <div className="h-2.5 w-2.5 rounded-full bg-white/10" />
          </div>
          <div className="mt-3 h-3.5 w-3/4 rounded bg-white/10" />
          <div className="mt-2 h-3 w-1/2 rounded bg-white/5" />
          <div className="mt-4 h-3.5 w-1/3 rounded bg-white/5" />
        </div>
      ))}
    </div>
  );
}

function EmptyState() {
  return (
    <div className="glass p-10 text-center">
      <div className="mx-auto mb-4 grid h-12 w-12 place-items-center rounded-2xl bg-white/5 text-2xl">
        ◈
      </div>
      <p className="text-sm text-slate-400">No dashboard tiles configured yet.</p>
      <p className="mt-1 text-xs text-slate-500">
        Add tiles on the settings page to see them here.
      </p>
      <Link to="/settings" className="btn-primary mt-4 inline-flex">
        <SettingsIcon className="h-4 w-4" /> Add your first tile
      </Link>
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────
// Small helpers.
// ────────────────────────────────────────────────────────────────────────

function labelForStatus(s: ServiceStatus): string {
  switch (s) {
    case "running":
      return "Running";
    case "stopped":
      return "Stopped";
    case "paused":
      return "Paused";
    default:
      return "Unknown";
  }
}

function formatUptime(seconds: number): string {
  if (!seconds || seconds < 1) return "—";
  const s = seconds % 60;
  const m = Math.floor(seconds / 60) % 60;
  const h = Math.floor(seconds / 3600) % 24;
  const d = Math.floor(seconds / 86400);
  if (d) return `${d}d ${h}h`;
  if (h) return `${h}h ${m}m`;
  if (m) return `${m}m ${s}s`;
  return `${s}s`;
}

function formatBytes(bytes: number): string {
  if (!bytes || bytes < 0) return "—";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let val = bytes;
  let unit = 0;
  while (val >= 1024 && unit < units.length - 1) {
    val /= 1024;
    unit++;
  }
  return `${val.toFixed(unit === 0 ? 0 : 1)} ${units[unit]}`;
}

const ICON_HINT_TO_EMOJI: Record<string, string> = {
  sonarr: "📺",
  radarr: "🎬",
  lidarr: "🎵",
  bazarr: "💬",
  readarr: "📚",
  prowlarr: "🏴‍☠️",
  postgres: "🐘",
  postgresql: "🐘",
  mysql: "🐬",
  mariadb: " MaraDB",
  redis: "♻️",
  mongodb: "🍃",
  elasticsearch: "🔍",
  kibana: "📈",
  vault: "🔐",
  traefik: "TLS",
  caddy: "🌐",
  nodejs: "🟢",
  python: "🐍",
  "home-assistant": "🏠",
  "home assistant": "🏠",
  pihole: "🕳️",
  adguard: "🛡️",
  "uptime-kuma": "⏱️",
  docker: "🐳",
};

function iconForHint(hint?: string): string {
  if (!hint) return "🧩";
  return ICON_HINT_TO_EMOJI[hint.toLowerCase()] ?? "🧩";
}

// Try to build a clickable URL when a tile hasn't set one but has a discovered
// container with a port. We assume localhost in dev — only really meaningful in
// mock mode; production tiles should set their own URL.
function makeBestGuessUrl(s: DiscoveredService): string {
  const p = s.ports?.[0];
  if (!p) return "";
  return `http://${s.node}.local:${p.host}`;
}