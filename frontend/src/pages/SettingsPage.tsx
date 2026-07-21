import { useEffect, useMemo, useRef, useState } from "react";
import {
  DndContext,
  DragOverlay,
  KeyboardSensor,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import {
  Check,
  ChevronDown,
  GripVertical,
  Loader2,
  Pencil,
  Plus,
  Trash2,
  Upload,
  X,
} from "lucide-react";
import clsx from "clsx";
import { useSettings } from "../store";
import { api } from "../api";
import type { ServiceEntry, WidgetDefinition, WidgetAuthSchema } from "../types";

export function SettingsPage() {
  const { config, status, error, load, addService, updateService, deleteService, reorderServices } =
    useSettings();

  useEffect(() => {
    if (status === "idle" && config.services.length === 0) void load();
  }, [load, status, config.services.length]);

  return (
    <div className="space-y-6">
      <header className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-white">Settings</h1>
          <p className="mt-1 text-sm text-slate-400">
            Add, edit, and reorder dashboard tiles. Changes persist to the backend.
          </p>
        </div>
        <StatusPill status={status} error={error} />
      </header>

      <TilesSection
        services={config.services}
        onAdd={addService}
        onUpdate={updateService}
        onDelete={deleteService}
        onReorder={reorderServices}
      />

      <BackgroundSection />
      <ThemeSection />

      <footer className="pt-2 text-xs text-slate-500">
        {config.updated_at ? `Last saved: ${new Date(config.updated_at).toLocaleString()}` : ""}
      </footer>
    </div>
  );
}

function StatusPill({ status, error }: { status: string; error: string | null }) {
  const label =
    status === "loading"
      ? "Loading"
      : status === "saving"
      ? "Saving"
      : status === "error"
      ? "Error"
      : "Synced";
  return (
    <span
      className={clsx(
        "chip",
        status === "error"
          ? "bg-rose-500/15 text-rose-300"
          : status === "saving" || status === "loading"
          ? "bg-amber-500/15 text-amber-300"
          : "bg-emerald-500/15 text-emerald-300"
      )}
      title={error ?? undefined}
    >
      {(status === "saving" || status === "loading") && (
        <Loader2 className="h-3 w-3 animate-spin" />
      )}
      {label}
    </span>
  );
}

// ────────────────────────────────────────────────────────────────────
// Tiles section — list with add form + inline edit + drag reorder.
// ────────────────────────────────────────────────────────────────────

function TilesSection({
  services,
  onAdd,
  onUpdate,
  onDelete,
  onReorder,
}: {
  services: ServiceEntry[];
  onAdd: (entry: Omit<ServiceEntry, "id" | "display_order">) => Promise<void>;
  onUpdate: (id: string, patch: Partial<ServiceEntry>) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
  onReorder: (orderedIds: string[]) => Promise<void>;
}) {
  const [showAdd, setShowAdd] = useState(false);

  const sorted = useMemo(
    () => [...services].sort((a, b) => a.display_order - b.display_order),
    [services]
  );

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  const [activeId, setActiveId] = useState<string | null>(null);
  const activeService = activeId ? sorted.find((s) => s.id === activeId) : null;

  function onDragStart(e: DragStartEvent) {
    setActiveId(String(e.active.id));
  }
  async function onDragEnd(e: DragEndEvent) {
    setActiveId(null);
    const { active, over } = e;
    if (!over || active.id === over.id) return;
    const oldIndex = sorted.findIndex((s) => s.id === active.id);
    const newIndex = sorted.findIndex((s) => s.id === over.id);
    if (oldIndex < 0 || newIndex < 0) return;
    const next = arrayMove(sorted, oldIndex, newIndex);
    await onReorder(next.map((s) => s.id));
  }

  return (
    <section className="glass p-5">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-white">Dashboard tiles</h2>
        <button
          type="button"
          onClick={() => setShowAdd((v) => !v)}
          className="btn-primary"
        >
          <Plus className="h-4 w-4" /> Add tile
        </button>
      </div>

      {showAdd && (
        <div className="mt-4 animate-slide-up">
          <ServiceForm
            onCancel={() => setShowAdd(false)}
            onSubmit={async (entry) => {
              await onAdd(entry);
              setShowAdd(false);
            }}
          />
        </div>
      )}

      {sorted.length === 0 ? (
        <p className="mt-6 rounded-xl border border-dashed border-white/10 px-4 py-8 text-center text-sm text-slate-500">
          No tiles yet. Click <span className="text-cyan-300">Add tile</span> to create one.
        </p>
      ) : (
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragStart={onDragStart}
          onDragEnd={onDragEnd}
        >
          <ul className="mt-4 space-y-2">
            <SortableContext
              items={sorted.map((s) => s.id)}
              strategy={verticalListSortingStrategy}
            >
              {sorted.map((s) => (
                <SortableTile
                  key={s.id}
                  service={s}
                  onUpdate={(patch) => onUpdate(s.id, patch)}
                  onDelete={() => onDelete(s.id)}
                />
              ))}
            </SortableContext>
          </ul>
          <DragOverlay>
            {activeService ? <TileRow service={activeService} dragging /> : null}
          </DragOverlay>
        </DndContext>
      )}
    </section>
  );
}

function SortableTile({
  service,
  onUpdate,
  onDelete,
}: {
  service: ServiceEntry;
  onUpdate: (patch: Partial<ServiceEntry>) => Promise<void>;
  onDelete: () => Promise<void>;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: service.id,
  });
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };
  return (
    <li ref={setNodeRef} style={style} className={clsx(isDragging && "opacity-40")}>
      <TileRow
        service={service}
        dragHandleProps={{ ...attributes, ...listeners }}
        onUpdate={onUpdate}
        onDelete={onDelete}
      />
    </li>
  );
}

function TileRow({
  service,
  dragHandleProps,
  onUpdate,
  onDelete,
  dragging,
}: {
  service: ServiceEntry;
  dragHandleProps?: Record<string, unknown>;
  onUpdate?: (patch: Partial<ServiceEntry>) => Promise<void>;
  onDelete?: () => Promise<void>;
  dragging?: boolean;
}) {
  const [editing, setEditing] = useState(false);
  const icon = service.icon?.trim() || "🧩";

  if (editing && onUpdate) {
    return (
      <div className="animate-fade-in">
        <ServiceForm
          initial={service}
          onCancel={() => setEditing(false)}
          onSubmit={async (entry) => {
            await onUpdate(entry);
            setEditing(false);
          }}
        />
      </div>
    );
  }

  return (
    <div
      className={clsx(
        "group flex items-center gap-3 rounded-xl border border-white/10 bg-slate-900/50 px-3 py-2.5 transition",
        dragging ? "shadow-2xl ring-1 ring-cyan-400/40" : "hover:bg-slate-900/80"
      )}
    >
      {dragHandleProps && (
        <button
          type="button"
          className="cursor-grab text-slate-500 hover:text-slate-300 active:cursor-grabbing"
          aria-label="Drag to reorder"
          {...dragHandleProps}
        >
          <GripVertical className="h-5 w-5" />
        </button>
      )}
      <span className="grid h-10 w-10 place-items-center rounded-lg bg-white/5 text-lg">
        {icon}
      </span>
      <div className="min-w-0 flex-1">
        <div className="truncate text-sm font-medium text-white">{service.name}</div>
        <div className="truncate text-xs text-slate-400">
          {service.url || "—"}
        </div>
      </div>
      {service.container_id && (
        <code className="hidden rounded bg-black/40 px-1.5 py-0.5 text-[10px] text-slate-400 sm:block">
          {service.container_id}
        </code>
      )}
      {onUpdate && (
        <button
          type="button"
          onClick={() => setEditing(true)}
          className="btn-ghost px-2 py-1.5 text-slate-300"
          aria-label="Edit tile"
        >
          <Pencil className="h-3.5 w-3.5" />
        </button>
      )}
      {onDelete && (
        <button
          type="button"
          onClick={async () => {
            if (window.confirm(`Remove "${service.name}"? This cannot be undone.`)) {
              await onDelete();
            }
          }}
          className="btn-ghost px-2 py-1.5 text-rose-300 hover:bg-rose-500/10"
          aria-label="Delete tile"
        >
          <Trash2 className="h-3.5 w-3.5" />
        </button>
      )}
    </div>
  );
}

interface FormState {
  name: string;
  url: string;
  icon: string;
  icon_url: string;
  container_id: string;
  widget_type: string;
  api_url: string;
  api_key: string;
  username: string;
  password: string;
}

function ServiceForm({
  initial,
  onSubmit,
  onCancel,
}: {
  initial?: ServiceEntry;
  onSubmit: (entry: Omit<ServiceEntry, "id" | "display_order">) => Promise<void>;
  onCancel: () => void;
}) {
  const [widgets, setWidgets] = useState<WidgetDefinition[]>([]);
  useEffect(() => {
    api.listWidgets()
      .then(setWidgets)
      .catch(() => setWidgets([]));
  }, []);

  const [form, setForm] = useState<FormState>({
    name: initial?.name ?? "",
    url: initial?.url ?? "",
    icon: initial?.icon ?? "",
    icon_url: initial?.icon_url ?? "",
    container_id: initial?.container_id ?? "",
    widget_type: initial?.widget_type ?? "generic",
    api_url: initial?.api_url ?? "",
    api_key: initial?.api_key ?? "",
    username: initial?.username ?? "",
    password: initial?.password ?? "",
  });
  const [submitting, setSubmitting] = useState(false);

  const selectedWidget = widgets.find((w) => w.id === form.widget_type);
  const authSchema: WidgetAuthSchema = selectedWidget?.auth_schema ?? "none";

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.name.trim()) return;
    setSubmitting(true);
    try {
      await onSubmit({
        name: form.name.trim(),
        url: form.url.trim() || undefined,
        icon: form.icon.trim() || undefined,
        icon_url: form.icon_url.trim() || undefined,
        container_id: form.container_id.trim() || undefined,
        widget_type: form.widget_type && form.widget_type !== "generic" ? form.widget_type : undefined,
        api_url: form.api_url.trim() || undefined,
        api_key: authSchema === "api_key" ? (form.api_key || undefined) : undefined,
        username: (authSchema === "basic" || authSchema === "form") ? (form.username.trim() || undefined) : undefined,
        password: (authSchema === "basic" || authSchema === "form") ? (form.password || undefined) : undefined,
      });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="grid grid-cols-1 gap-3 rounded-xl border border-white/10 bg-slate-950/40 p-4 sm:grid-cols-2"
    >
      <div>
        <label className="label">Name *</label>
        <input
          autoFocus
          className="input"
          value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
          placeholder="Grafana"
          required
        />
      </div>
      <div>
        <label className="label">Widget type</label>
        <select
          className="input"
          value={form.widget_type}
          onChange={(e) => setForm({ ...form, widget_type: e.target.value })}
        >
          {widgets.length === 0 ? (
            <option value="generic">Generic link</option>
          ) : (
            widgets.map((w) => (
              <option key={w.id} value={w.id}>
                {w.name}
              </option>
            ))
          )}
        </select>
        {selectedWidget?.description && (
          <p className="mt-1 text-[11px] text-slate-500">{selectedWidget.description}</p>
        )}
      </div>

      <div>
        <label className="label">URL</label>
        <input
          className="input"
          value={form.url}
          onChange={(e) => setForm({ ...form, url: e.target.value })}
          placeholder="https://sonarr.example.com"
        />
      </div>
      <div>
        <label className="label">Icon (emoji or hint)</label>
        <input
          className="input"
          value={form.icon}
          onChange={(e) => setForm({ ...form, icon: e.target.value })}
          placeholder="📺  or  sonarr"
        />
      </div>
      <div>
        <label className="label">Icon URL (overrides emoji)</label>
        <input
          className="input"
          value={form.icon_url}
          onChange={(e) => setForm({ ...form, icon_url: e.target.value })}
          placeholder="https://example.com/sonarr.svg"
        />
        <p className="mt-1 text-[11px] text-slate-500">
          Direct link to a .svg / .png / .jpg icon. Takes priority over the emoji above.
        </p>
      </div>

      {/* Widget auth fields — shown only when the selected widget asks for them. */}
      {authSchema !== "none" && (
        <div className="sm:col-span-2">
          <div className="rounded-lg border border-cyan-400/20 bg-cyan-400/5 p-3">
            <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-cyan-200">
              <Upload className="h-3 w-3" /> Auto-login credentials
            </div>
            <p className="mb-3 text-[11px] text-slate-400">
              Stored on the tile. Click the "Open & login" button on the home page
              and the dashboard will POST these to the service login API on your
              behalf, then redirect you to the dashboard.
            </p>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="sm:col-span-2">
                <label className="label">API URL</label>
                <input
                  className="input"
                  value={form.api_url}
                  onChange={(e) => setForm({ ...form, api_url: e.target.value })}
                  placeholder={form.url || "https://sonarr.example.com"}
                />
              </div>
              {authSchema === "api_key" && (
                <div className="sm:col-span-2">
                  <label className="label">API key</label>
                  <input
                    type="password"
                    className="input font-mono"
                    value={form.api_key}
                    onChange={(e) => setForm({ ...form, api_key: e.target.value })}
                    placeholder="abcd1234…"
                    autoComplete="off"
                  />
                </div>
              )}
              {(authSchema === "basic" || authSchema === "form") && (
                <>
                  <div>
                    <label className="label">Username</label>
                    <input
                      className="input"
                      value={form.username}
                      onChange={(e) => setForm({ ...form, username: e.target.value })}
                      placeholder="admin"
                      autoComplete="off"
                    />
                  </div>
                  <div>
                    <label className="label">Password</label>
                    <input
                      type="password"
                      className="input"
                      value={form.password}
                      onChange={(e) => setForm({ ...form, password: e.target.value })}
                      placeholder="••••••••"
                      autoComplete="new-password"
                    />
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}

      <div>
        <label className="label">Container ID (optional)</label>
        <input
          className="input"
          value={form.container_id}
          onChange={(e) => setForm({ ...form, container_id: e.target.value })}
          placeholder="pve-lxc-100-docker-sonarr"
        />
      </div>
      <div className="flex items-center justify-end gap-2 sm:col-span-2">
        <button type="button" onClick={onCancel} className="btn-ghost">
          <X className="h-4 w-4" /> Cancel
        </button>
        <button type="submit" disabled={submitting} className="btn-primary">
          {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
          {initial ? "Save" : "Add"}
        </button>
      </div>
    </form>
  );
}

// ────────────────────────────────────────────────────────────────────
// Background section — toggle effects, mode, wallpaper upload/select.
// ────────────────────────────────────────────────────────────────────

function BackgroundSection() {
  const { config, setBackground, uploadWallpaper } = useSettings();
  const bg = config.background;
  const [wallpapers, setWallpapers] = useState<{ id: string; url: string; name: string }[]>([]);
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  async function refreshWallpapers() {
    try {
      const list = await fetch("/api/config/wallpapers").then((r) => (r.ok ? r.json() : []));
      setWallpapers(list);
    } catch {
      // ignore — endpoint may not exist yet
    }
  }

  useEffect(() => {
    void refreshWallpapers();
  }, []);

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      await uploadWallpaper(file);
      await refreshWallpapers();
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  return (
    <section className="glass p-5">
      <h2 className="text-lg font-semibold text-white">Background</h2>

      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <div className="flex items-center justify-between rounded-xl border border-white/10 bg-slate-950/40 p-4">
          <div>
            <div className="text-sm font-medium text-white">Background effects</div>
            <p className="text-xs text-slate-400">
              Toggle all animations (particles, gradients, wallpaper fade).
            </p>
          </div>
          <Toggle
            checked={bg.effects_enabled}
            onChange={(v) => void setBackground({ effects_enabled: v })}
          />
        </div>

        <div className="rounded-xl border border-white/10 bg-slate-950/40 p-4">
          <div className="label">Mode</div>
          <select
            className="input"
            value={bg.mode}
            onChange={(e) =>
              void setBackground({ mode: e.target.value as typeof bg.mode })
            }
          >
            <option value="none">None</option>
            <option value="gradient">Animated gradient</option>
            <option value="particles">Particles</option>
            <option value="wallpaper">Wallpaper</option>
          </select>
        </div>
      </div>

      {bg.mode === "gradient" && (
        <div className="mt-4 rounded-xl border border-white/10 bg-slate-950/40 p-4 animate-fade-in">
          <div className="label">Gradient colors</div>
          <div className="flex flex-wrap items-center gap-3">
            {(bg.gradient_colors ?? []).map((c, i) => (
              <input
                key={i}
                type="color"
                value={c}
                onChange={(e) => {
                  const next = [...(bg.gradient_colors ?? [])];
                  next[i] = e.target.value;
                  void setBackground({ gradient_colors: next as [string, string, string] });
                }}
                className="h-9 w-12 cursor-pointer rounded border border-white/10 bg-transparent"
                aria-label={`Gradient color ${i + 1}`}
              />
            ))}
          </div>
        </div>
      )}

      {bg.mode === "particles" && (
        <div className="mt-4 grid gap-4 sm:grid-cols-2 animate-fade-in">
          <RangeField
            label="Particle density"
            min={0}
            max={100}
            value={bg.particle_density ?? 40}
            onChange={(v) => void setBackground({ particle_density: v })}
          />
          <RangeField
            label="Particle speed"
            min={0}
            max={100}
            value={bg.particle_speed ?? 30}
            onChange={(v) => void setBackground({ particle_speed: v })}
          />
        </div>
      )}

      {bg.mode === "wallpaper" && (
        <div className="mt-4 rounded-xl border border-white/10 bg-slate-950/40 p-4 animate-fade-in">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="text-sm font-medium text-white">Wallpaper</div>
              <p className="text-xs text-slate-400">
                Upload a new wallpaper or pick one from the library.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <a
                href="/api/config/wallpapers"
                target="_blank"
                rel="noreferrer"
                className="btn-ghost"
              >
                <ChevronDown className="h-4 w-4" /> Library ({wallpapers.length})
              </a>
              <button
                type="button"
                onClick={() => fileRef.current?.click()}
                className="btn-primary"
                disabled={uploading}
              >
                {uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
                Upload
              </button>
              <input
                ref={fileRef}
                type="file"
                accept="image/*"
                onChange={handleUpload}
                className="hidden"
              />
            </div>
          </div>

          {bg.wallpaper_url && (
            <div className="mt-4 overflow-hidden rounded-xl border border-white/10">
              <img
                src={bg.wallpaper_url}
                alt="Current wallpaper"
                className="h-40 w-full object-cover"
                style={{ opacity: bg.wallpaper_blend ?? 0.6 }}
              />
            </div>
          )}

          {wallpapers.length > 0 && (
            <div className="mt-4 grid grid-cols-3 gap-2 sm:grid-cols-5">
              {wallpapers.map((w) => (
                <button
                  key={w.id}
                  type="button"
                  onClick={() => void setBackground({ wallpaper_url: w.url })}
                  className={clsx(
                    "overflow-hidden rounded-lg border transition",
                    bg.wallpaper_url === w.url
                      ? "border-cyan-400 ring-2 ring-cyan-400/30"
                      : "border-white/10 hover:border-white/30"
                  )}
                >
                  <img src={w.url} alt={w.name} className="h-16 w-full object-cover" />
                </button>
              ))}
            </div>
          )}

          <RangeField
            className="mt-4"
            label="Wallpaper opacity"
            min={0}
            max={100}
            value={Math.round((bg.wallpaper_blend ?? 0.6) * 100)}
            onChange={(v) => void setBackground({ wallpaper_blend: v / 100 })}
            suffix="%"
          />
        </div>
      )}
    </section>
  );
}

function ThemeSection() {
  const { config, setTheme, load } = useSettings();
  const t = config.theme;
  const customThemes = config.custom_themes;
  const builtinOptions = [
    { id: "midnight-neon", name: "Midnight Neon" },
    { id: "aurora", name: "Aurora" },
    { id: "solarized-dark", name: "Solarized Dark" },
    { id: "paper", name: "Paper" },
  ];
  const [showNew, setShowNew] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function deleteTheme(id: string) {
    if (!window.confirm("Remove this custom theme?")) return;
    setErr(null);
    try {
      await api.deleteCustomTheme(id);
      await load();
      if (t.active_theme === id) await setTheme({ active_theme: "midnight-neon" });
    } catch (e) {
      setErr((e as Error).message);
    }
  }

  return (
    <section className="glass p-5">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-white">Theme</h2>
        <button type="button" onClick={() => setShowNew((v) => !v)} className="btn-primary">
          <Plus className="h-4 w-4" /> New theme
        </button>
      </div>

      <div className="mt-4 grid gap-4 sm:grid-cols-3">
        <div>
          <label className="label">Active theme</label>
          <select
            className="input"
            value={t.active_theme}
            onChange={(e) => void setTheme({ active_theme: e.target.value })}
          >
            <optgroup label="Built-in">
              {builtinOptions.map((opt) => (
                <option key={opt.id} value={opt.id}>{opt.name}</option>
              ))}
            </optgroup>
            {customThemes.length > 0 && (
              <optgroup label="Custom">
                {customThemes.map((ct) => (
                  <option key={ct.id} value={ct.id}>{ct.name}</option>
                ))}
              </optgroup>
            )}
          </select>
        </div>
        <div>
          <label className="label">Accent color</label>
          <input
            type="color"
            value={t.accent_color}
            onChange={(e) => void setTheme({ accent_color: e.target.value })}
            className="h-10 w-full cursor-pointer rounded-xl border border-white/10 bg-transparent"
          />
        </div>
        <div>
          <label className="label">Density</label>
          <select
            className="input"
            value={t.density}
            onChange={(e) =>
              void setTheme({ density: e.target.value as "compact" | "comfortable" | "spacious" })
            }
          >
            <option value="compact">Compact</option>
            <option value="comfortable">Comfortable</option>
            <option value="spacious">Spacious</option>
          </select>
        </div>
      </div>

      {customThemes.length > 0 && (
        <div className="mt-4">
          <div className="label mb-2">Custom themes</div>
          <ul className="space-y-1">
            {customThemes.map((ct) => (
              <li
                key={ct.id}
                className="group flex items-center justify-between rounded-lg border border-white/10 bg-slate-950/40 px-3 py-2"
              >
                <div className="flex items-center gap-2 min-w-0">
                  <span
                    className="inline-block h-4 w-4 rounded"
                    style={{ background: ct.accent, borderColor: ct.border }}
                    aria-hidden
                  />
                  <span className="truncate text-sm text-slate-200">{ct.name}</span>
                  <code className="rounded bg-black/40 px-1.5 py-0.5 text-[10px] text-slate-500">{ct.id}</code>
                </div>
                <button
                  type="button"
                  onClick={() => deleteTheme(ct.id)}
                  className="rounded-md px-2 py-1 text-rose-300 opacity-0 transition hover:bg-rose-500/10 group-hover:opacity-100"
                  aria-label="Delete custom theme"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {showNew && (
        <NewThemeForm
          busy={busy}
          err={err}
          onCancel={() => { setShowNew(false); setErr(null); }}
          onSubmit={async (def) => {
            setBusy(true);
            setErr(null);
            try {
              await api.addCustomTheme(def);
              await load();
              setShowNew(false);
            } catch (e) {
              setErr((e as Error).message);
            } finally {
              setBusy(false);
            }
          }}
        />
      )}
    </section>
  );
}

function NewThemeForm({
  onSubmit,
  onCancel,
  busy,
  err,
}: {
  onSubmit: (def: Omit<import("../types").ThemeDefinition, "id">) => Promise<void>;
  onCancel: () => void;
  busy: boolean;
  err: string | null;
}) {
  const [name, setName] = useState("");
  const [dark, setDark] = useState(true);
  const [accent, setAccent] = useState("#22d3ee");
  const [bg, setBg] = useState("#070b18");
  const [surface, setSurface] = useState("#0f172a");
  const [text, setText] = useState("#e5e7eb");
  const [muted, setMuted] = useState("#94a3b8");
  const [border, setBorder] = useState("#1f2937");

  return (
    <form
      onSubmit={async (e) => {
        e.preventDefault();
        if (!name.trim()) return;
        await onSubmit({
          name: name.trim(),
          dark,
          accent,
          bg,
          surface,
          text,
          muted,
          border,
        });
      }}
      className="mt-4 grid gap-3 rounded-xl border border-white/10 bg-slate-950/40 p-4 animate-slide-up sm:grid-cols-2"
    >
      <div>
        <label className="label">Name *</label>
        <input className="input" value={name} onChange={(e) => setName(e.target.value)} required placeholder="My awesome theme" />
      </div>
      <div className="flex items-end">
        <label className="inline-flex items-center gap-2 text-sm text-slate-300">
          <input type="checkbox" checked={dark} onChange={(e) => setDark(e.target.checked)} />
          Dark theme
        </label>
      </div>
      {[
        { label: "Accent", value: accent, set: setAccent },
        { label: "Background", value: bg, set: setBg },
        { label: "Surface", value: surface, set: setSurface },
        { label: "Text", value: text, set: setText },
        { label: "Muted", value: muted, set: setMuted },
        { label: "Border", value: border, set: setBorder },
      ].map(({ label, value, set }) => (
        <div key={label}>
          <label className="label">{label}</label>
          <input
            type="color"
            value={value}
            onChange={(e) => set(e.target.value)}
            className="h-10 w-full cursor-pointer rounded-xl border border-white/10 bg-transparent"
          />
        </div>
      ))}
      {err && <div className="text-sm text-rose-300 sm:col-span-2">{err}</div>}
      <div className="flex items-center justify-end gap-2 sm:col-span-2">
        <button type="button" onClick={onCancel} className="btn-ghost">
          <X className="h-4 w-4" /> Cancel
        </button>
        <button type="submit" disabled={busy} className="btn-primary">
          {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
          Save theme
        </button>
      </div>
    </form>
  );
}

// ────────────────────────────────────────────────────────────────────
// Small reusable primitives.
// ────────────────────────────────────────────────────────────────────

function Toggle({
  checked,
  onChange,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className={clsx(
        "relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition",
        checked ? "bg-cyan-500" : "bg-slate-700"
      )}
    >
      <span
        className={clsx(
          "inline-block h-4 w-4 transform rounded-full bg-white transition-transform",
          checked ? "translate-x-6" : "translate-x-1"
        )}
      />
    </button>
  );
}

function RangeField({
  label,
  min,
  max,
  value,
  onChange,
  suffix,
  className,
}: {
  label: string;
  min: number;
  max: number;
  value: number;
  onChange: (v: number) => void;
  suffix?: string;
  className?: string;
}) {
  return (
    <div className={clsx("rounded-xl border border-white/10 bg-slate-950/40 p-4", className)}>
      <div className="flex items-center justify-between">
        <div className="label mb-0">{label}</div>
        <div className="text-xs text-slate-300">
          {value}
          {suffix}
        </div>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="mt-2 h-1.5 w-full cursor-pointer appearance-none rounded-full bg-slate-700 accent-cyan-400"
      />
    </div>
  );
}