import {
  Bookmark,
  BookmarkPatch,
  CronListResponse,
  DashboardConfig,
  HealthResponse,
  SearchResponse,
  ServiceEntry,
  ServiceHealth,
  ServicesResponse,
  ThemeDefinition,
  TileLoginResponse,
  WidgetDefinition,
} from "./types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

async function jsonOrThrow<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText} ${text}`.trim());
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  async getConfig(): Promise<DashboardConfig> {
    try {
      const res = await fetch(`${API_BASE}/api/config`, {
        headers: { Accept: "application/json" },
      });
      const cfg = await jsonOrThrow<DashboardConfig>(res);
      // Normalize — server may legitimately return an empty object on first run.
      // The `...cfg.X` spread goes FIRST so the explicit fallbacks below it only
      // fill gaps when the server omitted those keys (TS2783 safe).
      return {
        services: cfg.services ?? [],
        background: {
          ...cfg.background,
          effects_enabled: cfg.background?.effects_enabled ?? true,
          mode: cfg.background?.mode ?? "gradient",
          wallpaper_blend: cfg.background?.wallpaper_blend ?? 0.6,
          gradient_colors:
            cfg.background?.gradient_colors ?? ["#0ea5e9", "#7c3aed", "#ec4899"],
          particle_density: cfg.background?.particle_density ?? 40,
          particle_speed: cfg.background?.particle_speed ?? 30,
        },
        theme: {
          ...cfg.theme,
          active_theme: cfg.theme?.active_theme ?? "midnight-neon",
          accent_color: cfg.theme?.accent_color ?? "#22d3ee",
          density: cfg.theme?.density ?? "comfortable",
        },
        bookmarks: cfg.bookmarks ?? [],
        custom_themes: cfg.custom_themes ?? [],
        updated_at: cfg.updated_at,
      };
    } catch (err) {
      console.warn("[api] getConfig failed, returning empty default", err);
      throw err;
    }
  },

  // Full replacement write (PUT). Used by every settings mutation after the
  // store optimistically updates the in-memory config.
  async saveConfig(config: DashboardConfig): Promise<DashboardConfig> {
    const res = await fetch(`${API_BASE}/api/config`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(config),
    });
    return jsonOrThrow<DashboardConfig>(res);
  },

  // Granular service CRUD (POST/PUT/DELETE). The backend persistence layer is
  // the same JSON file / SQLite row — these are sugar over PUT /api/config.
  async addService(entry: Omit<ServiceEntry, "id" | "display_order">): Promise<ServiceEntry> {
    const res = await fetch(`${API_BASE}/api/config/services`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(entry),
    });
    return jsonOrThrow<ServiceEntry>(res);
  },

  async updateService(id: string, patch: Partial<ServiceEntry>): Promise<ServiceEntry> {
    const res = await fetch(`${API_BASE}/api/config/services/${encodeURIComponent(id)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    });
    return jsonOrThrow<ServiceEntry>(res);
  },

  async deleteService(id: string): Promise<void> {
    const res = await fetch(`${API_BASE}/api/config/services/${encodeURIComponent(id)}`, {
      method: "DELETE",
    });
    await jsonOrThrow<void>(res);
  },

  async reorderServices(orderedIds: string[]): Promise<void> {
    const res = await fetch(`${API_BASE}/api/config/services/reorder`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ordered_ids: orderedIds }),
    });
    await jsonOrThrow<void>(res);
  },

  async uploadWallpaper(file: File): Promise<{ id: string; url: string }> {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${API_BASE}/api/config/wallpaper`, {
      method: "POST",
      body: form,
    });
    return jsonOrThrow<{ id: string; url: string }>(res);
  },

  async listWallpapers(): Promise<{ id: string; url: string; name: string }[]> {
    const res = await fetch(`${API_BASE}/api/config/wallpapers`);
    return jsonOrThrow(res);
  },

  // ─────────────────────────────────────────────────────────────────────
  // Discovery + health (consumed by the HomePage, task t_dc212077).
  // ─────────────────────────────────────────────────────────────────────
  async getServices(): Promise<ServicesResponse> {
    const res = await fetch(`${API_BASE}/api/services`, {
      headers: { Accept: "application/json" },
    });
    return jsonOrThrow<ServicesResponse>(res);
  },

  async getServiceHealth(serviceId: string): Promise<ServiceHealth | null> {
    try {
      const res = await fetch(
        `${API_BASE}/api/services/${encodeURIComponent(serviceId)}/health`,
        { headers: { Accept: "application/json" } }
      );
      if (res.status === 404) return null;
      const data = await jsonOrThrow<HealthResponse>(res);
      return data.health;
    } catch {
      return null;
    }
  },

  // ─────────────────────────────────────────────────────────────────────
  // Root-task (t_c8aa6b03) endpoints: bookmarks, custom themes, cron, search.
  // ─────────────────────────────────────────────────────────────────────
  async listBookmarks(): Promise<Bookmark[]> {
    const res = await fetch(`${API_BASE}/api/config/bookmarks`);
    return jsonOrThrow<Bookmark[]>(res);
  },

  async addBookmark(entry: Omit<Bookmark, "id" | "display_order">): Promise<Bookmark> {
    const res = await fetch(`${API_BASE}/api/config/bookmarks`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(entry),
    });
    return jsonOrThrow<Bookmark>(res);
  },

  async updateBookmark(id: string, patch: BookmarkPatch): Promise<Bookmark> {
    const res = await fetch(`${API_BASE}/api/config/bookmarks/${encodeURIComponent(id)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    });
    return jsonOrThrow<Bookmark>(res);
  },

  async deleteBookmark(id: string): Promise<void> {
    const res = await fetch(`${API_BASE}/api/config/bookmarks/${encodeURIComponent(id)}`, {
      method: "DELETE",
    });
    await jsonOrThrow<void>(res);
  },

  async listCustomThemes(): Promise<ThemeDefinition[]> {
    const res = await fetch(`${API_BASE}/api/config/themes`);
    return jsonOrThrow<ThemeDefinition[]>(res);
  },

  async addCustomTheme(theme: Omit<ThemeDefinition, "id">): Promise<ThemeDefinition> {
    const res = await fetch(`${API_BASE}/api/config/themes`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(theme),
    });
    return jsonOrThrow<ThemeDefinition>(res);
  },

  async deleteCustomTheme(id: string): Promise<void> {
    const res = await fetch(`${API_BASE}/api/config/themes/${encodeURIComponent(id)}`, {
      method: "DELETE",
    });
    await jsonOrThrow<void>(res);
  },

  async search(query: string): Promise<SearchResponse> {
    const res = await fetch(
      `${API_BASE}/api/search?query=${encodeURIComponent(query)}`,
      { headers: { Accept: "application/json" } }
    );
    return jsonOrThrow<SearchResponse>(res);
  },

  async listCron(): Promise<CronListResponse> {
    const res = await fetch(`${API_BASE}/api/cron`, {
      headers: { Accept: "application/json" },
    });
    return jsonOrThrow(res);
  },

  // ─────────────────────────────────────────────────────────────────────
  // Widget registry + per-tile auto-login (t_d7921f0b).
  // ─────────────────────────────────────────────────────────────────────
  async listWidgets(): Promise<WidgetDefinition[]> {
    const res = await fetch(`${API_BASE}/api/widgets`, {
      headers: { Accept: "application/json" },
    });
    return jsonOrThrow(res);
  },

  async getWidget(widgetId: string): Promise<WidgetDefinition> {
    const res = await fetch(`${API_BASE}/api/widgets/${encodeURIComponent(widgetId)}`, {
      headers: { Accept: "application/json" },
    });
    return jsonOrThrow(res);
  },

  async tileLogin(tileId: string): Promise<TileLoginResponse> {
    const res = await fetch(`${API_BASE}/api/tiles/${encodeURIComponent(tileId)}/auth`, {
      method: "POST",
      headers: { Accept: "application/json" },
    });
    return jsonOrThrow(res);
  },
};