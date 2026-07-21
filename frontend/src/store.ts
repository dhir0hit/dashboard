import { create } from "zustand";
import { api } from "./api";
import { DashboardConfig, ServiceEntry, DEFAULT_CONFIG } from "./types";

type Status = "idle" | "loading" | "saving" | "error";

interface SettingsState {
  config: DashboardConfig;
  status: Status;
  error: string | null;

  load: () => Promise<void>;
  persist: (next: DashboardConfig) => Promise<void>;

  addService: (entry: Omit<ServiceEntry, "id" | "display_order">) => Promise<void>;
  updateService: (id: string, patch: Partial<ServiceEntry>) => Promise<void>;
  deleteService: (id: string) => Promise<void>;
  reorderServices: (orderedIds: string[]) => Promise<void>;
  setBackground: (patch: Partial<DashboardConfig["background"]>) => Promise<void>;
  setTheme: (patch: Partial<DashboardConfig["theme"]>) => Promise<void>;
  uploadWallpaper: (file: File) => Promise<string>;
}

function genId(name: string): string {
  const slug = name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return `svc-${slug}-${Math.random().toString(36).slice(2, 7)}`;
}

export const useSettings = create<SettingsState>((set, get) => ({
  config: DEFAULT_CONFIG,
  status: "idle",
  error: null,

  load: async () => {
    set({ status: "loading", error: null });
    try {
      const cfg = await api.getConfig();
      set({ config: cfg, status: "idle" });
    } catch (err) {
      // Backend not up yet — keep defaults so the settings page is still usable.
      set({ status: "error", error: (err as Error).message });
    }
  },

  persist: async (next: DashboardConfig) => {
    set({ status: "saving" });
    try {
      const saved = await api.saveConfig(next);
      set({ config: saved, status: "idle", error: null });
    } catch (err) {
      set({ status: "error", error: (err as Error).message });
      throw err;
    }
  },

  addService: async (entry) => {
    const id = genId(entry.name || "service");
    const next: DashboardConfig = {
      ...get().config,
      services: [
        ...get().config.services,
        { ...entry, id, display_order: get().config.services.length },
      ],
    };
    set({ config: next });
    await get().persist(next);
  },

  updateService: async (id, patch) => {
    const next: DashboardConfig = {
      ...get().config,
      services: get().config.services.map((s) => (s.id === id ? { ...s, ...patch } : s)),
    };
    set({ config: next });
    await get().persist(next);
  },

  deleteService: async (id) => {
    const next: DashboardConfig = {
      ...get().config,
      services: get()
        .config.services.filter((s) => s.id !== id)
        .map((s, i) => ({ ...s, display_order: i })),
    };
    set({ config: next });
    await get().persist(next);
  },

  reorderServices: async (orderedIds) => {
    const byId = new Map(get().config.services.map((s) => [s.id, s]));
    const reordered = orderedIds
      .map((id, i) => {
        const s = byId.get(id);
        return s ? { ...s, display_order: i } : null;
      })
      .filter(Boolean) as ServiceEntry[];
    // Append any service we somehow lost (defensive).
    for (const s of get().config.services) {
      if (!orderedIds.includes(s.id)) reordered.push(s);
    }
    const next: DashboardConfig = { ...get().config, services: reordered };
    set({ config: next });
    await get().persist(next);
  },

  setBackground: async (patch) => {
    const next: DashboardConfig = {
      ...get().config,
      background: { ...get().config.background, ...patch },
    };
    set({ config: next });
    await get().persist(next);
  },

  setTheme: async (patch) => {
    const next: DashboardConfig = {
      ...get().config,
      theme: { ...get().config.theme, ...patch },
    };
    set({ config: next });
    await get().persist(next);
  },

  uploadWallpaper: async (file) => {
    const { url } = await api.uploadWallpaper(file);
    await get().setBackground({ mode: "wallpaper", wallpaper_url: url });
    return url;
  },
}));