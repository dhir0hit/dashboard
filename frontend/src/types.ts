// Shared types — match backend pydantic models (backend/app/schemas.py).

export type ServiceStatus = "running" | "stopped" | "paused" | "unknown";

// ────────────────────────────────────────────────────────────────────────────
// Backend /api/services + /api/services/{id}/health — mirrored from backend
// pydantic models in app/schemas.py. The HomePage (frontend-visuals task
// t_dc212077) overlays discovered-container status/health on top of user tiles.
// ────────────────────────────────────────────────────────────────────────────

export interface PortMapping {
  host: number;
  container: number;
  protocol: string;
}

export interface DiscoveredService {
  id: string;            // e.g. "pve-lxc-100-docker-sonarr"
  name: string;
  node: string;
  vmid: number;
  kind: "lxc" | "qemu";
  status: ServiceStatus;
  image: string;
  ports: PortMapping[];
  icon_hint: string;
  labels: Record<string, string>;
}

export interface ServicesResponse {
  services: DiscoveredService[];
  source: string;       // "mock" | "proxmox:<host>"
  count: number;
}

export interface ServiceHealth {
  id: string;
  status: ServiceStatus;
  healthy: boolean;
  uptime_seconds: number;
  last_seen: string | null;
  message: string;
}

export interface HealthResponse {
  health: ServiceHealth;
}

export interface ServiceEntry {
  id: string;
  name: string;
  url?: string;          // click-through URL (also used as api_url fallback)
  icon?: string;         // emoji or short hint like "sonarr"
  icon_url?: string;     // custom icon URL (.svg/.png/.jpg) — overrides emoji
  container_id?: string; // e.g. "pve-lxc-100-docker-sonarr"
  display_order: number;
  // Optional read-only fields surfaced from Proxmox discovery (not editable
  // from the settings page — they come from /api/services).
  status?: ServiceStatus;
  ports?: { host: number; container: number; protocol: string }[];
  image?: string;
  // --- Widget integration (auto-login per `widget_type`) ------------------
  widget_type?: string;  // one of WIDGET_REGISTRY ids (e.g. service-specific)
  api_url?: string;      // base URL of the service API/web UI
  api_key?: string;     // bearer / token auth
  username?: string;    // form-login / basic-auth username
  password?: string;    // paired with username
  category?: string;    // user-assigned category for grouping tiles
}

export type WidgetAuthSchema = "none" | "api_key" | "basic" | "form";

export interface WidgetDefinition {
  id: string;            // stable identifier used in ServiceEntry.widget_type
  name: string;          // display name for the dropdown
  icon_hint: string;     // maps to IconHintToEmoji on the frontend
  auth_schema: WidgetAuthSchema;
  login_path?: string | null;
  auth_header_format?: string;     // api_key widgets
  login_form_template?: string;    // form widgets
  description: string;
}

export interface TileLoginResponse {
  method: string;       // "none" | "api_key" | "basic" | "form"
  cookies?: string[];   // Set-Cookie strings to inject client-side
  redirect_url: string;  // where the browser should navigate after setting cookies
  message: string;
}

// Service info — live stats fetched from the service's own API via the
// backend's GET /api/tiles/{id}/info endpoint. The returned dict is
// widget-specific (e.g. sonarr returns version + uptime, qBittorrent
// returns download/upload speeds, Pi-hole returns DNS queries, etc.).
export interface ServiceInfo {
  widget_type: string;
  error?: string;
  [key: string]: string | number | boolean | object | undefined;
}

export interface BackgroundSettings {
  mode: "none" | "gradient" | "particles" | "wallpaper";
  effects_enabled: boolean;
  wallpaper_url?: string;
  wallpaper_blend?: number; // 0..1 opacity
  gradient_colors?: [string, string, string];
  particle_density?: number;
  particle_speed?: number;
}

export interface ThemeSettings {
  active_theme: string; // "midnight-neon" | "aurora" | custom id
  accent_color: string; // hex
  density: "compact" | "comfortable" | "spacious";
}

// ────────────────────────────────────────────────────────────────────────────
// Root-task (t_c8aa6b03) additions: bookmarks, custom themes, cron, search.
// ────────────────────────────────────────────────────────────────────────────

export interface Bookmark {
  id: string;
  title: string;
  url: string;
  category: string;
  icon?: string | null;
  display_order: number;
}

export interface BookmarkPatch {
  title?: string;
  url?: string;
  category?: string;
  icon?: string;
  display_order?: number;
}

export interface ThemeDefinition {
  id: string;
  name: string;
  dark: boolean;
  accent: string;
  bg: string;
  surface: string;
  text: string;
  muted: string;
  border: string;
}

export interface CronEntry {
  id: string;
  name?: string | null;
  schedule?: string | null;
  enabled: boolean;
  next_run?: string | null;
  last_run?: string | null;
  description?: string | null;
}

// --- Calendar events (local + Google + Hermes cron, unified) ---

export type CalendarEventSource = "local" | "google" | "hermes";

export interface CalendarEvent {
  id: string;
  title: string;
  description?: string | null;
  date: string;            // "YYYY-MM-DD"
  time?: string | null;    // "HH:MM" or null for all-day
  duration_minutes?: number | null;
  source: CalendarEventSource;
  done: boolean;
  google_event_id?: string | null;
}

export interface CalendarEventCreate {
  title: string;
  description?: string;
  date: string;
  time?: string;
  duration_minutes?: number;
  done?: boolean;
}

export interface CalendarEventUpdate {
  title?: string;
  description?: string;
  date?: string;
  time?: string;
  duration_minutes?: number;
  done?: boolean;
}

export interface CalendarListResponse {
  events: CalendarEvent[];
  count: number;
}

// Google OAuth is now handled entirely in the frontend (see googleAuth.ts):
// the access/refresh tokens live in localStorage, and the backend's
// /api/calendar/google/sync endpoint accepts the access_token as a Bearer
// header. There is no backend GoogleAuthStatus/GoogleConfig model anymore.

export interface CronListResponse {
  jobs: CronEntry[];
  source: string;
  count: number;
}

export interface SearchResult {
  title: string;
  url: string;
  snippet: string;
  favicon?: string | null;
}

export interface SearchResponse {
  query: string;
  engine: string;
  results: SearchResult[];
}

export interface DashboardConfig {
  services: ServiceEntry[];
  background: BackgroundSettings;
  theme: ThemeSettings;
  bookmarks: Bookmark[];
  custom_themes: ThemeDefinition[];
  updated_at?: string;
}

export const DEFAULT_CONFIG: DashboardConfig = {
  services: [],
  background: {
    mode: "gradient",
    effects_enabled: true,
    wallpaper_blend: 0.6,
    gradient_colors: ["#0ea5e9", "#7c3aed", "#ec4899"],
    particle_density: 40,
    particle_speed: 30,
  },
  theme: {
    active_theme: "midnight-neon",
    accent_color: "#22d3ee",
    density: "comfortable",
  },
  bookmarks: [],
  custom_themes: [],
};

// Built-in themes — always present alongside user custom_themes.
export interface BuiltTheme extends ThemeDefinition {
  builtin: true;
}

export const BUILTIN_THEMES: BuiltTheme[] = [
  {
    id: "midnight-neon",
    name: "Midnight Neon",
    dark: true,
    accent: "#22d3ee",
    bg: "#070b18",
    surface: "#0f172a",
    text: "#e5e7eb",
    muted: "#94a3b8",
    border: "#1f2937",
    builtin: true,
  },
  {
    id: "aurora",
    name: "Aurora",
    dark: true,
    accent: "#a78bfa",
    bg: "#0b1020",
    surface: "#15184266",
    text: "#e9d5ff",
    muted: "#a78b8b",
    border: "#312e6b66",
    builtin: true,
  },
  {
    id: "solarized-dark",
    name: "Solarized Dark",
    dark: true,
    accent: "#268bd2",
    bg: "#002b36",
    surface: "#073642",
    text: "#93a1a1",
    muted: "#586e75",
    border: "#073642",
    builtin: true,
  },
  {
    id: "paper",
    name: "Paper",
    dark: false,
    accent: "#1d4ed8",
    bg: "#fafaf7",
    surface: "#ffffff",
    text: "#1f2937",
    muted: "#6b7280",
    border: "#e5e7eb",
    builtin: true,
  },
];