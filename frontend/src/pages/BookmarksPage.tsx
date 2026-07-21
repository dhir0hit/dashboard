// Root-task (t_c8aa6b03): bookmarks page.
// List/add/edit/remove via UI, persisted to backend /api/config/bookmarks.

import { useEffect, useMemo, useState } from "react";
import {
  Bookmark as BookmarkIcon,
  Plus,
  Pencil,
  Trash2,
  X,
  ExternalLink,
  Loader2,
  Filter,
} from "lucide-react";
import clsx from "clsx";
import { api } from "../api";
import type { Bookmark } from "../types";

type EditingState =
  | { mode: "add" }
  | { mode: "edit"; bookmark: Bookmark }
  | null;

export function BookmarksPage() {
  const [bookmarks, setBookmarks] = useState<Bookmark[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [editing, setEditing] = useState<EditingState>(null);
  const [filter, setFilter] = useState<string>("all");

  async function reload() {
    setLoading(true);
    setErr(null);
    try {
      setBookmarks(await api.listBookmarks());
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void reload(); }, []);

  const categories = useMemo(() => {
    const set = new Set<string>(["general"]);
    bookmarks.forEach((b) => set.add(b.category || "general"));
    return ["all", ...Array.from(set).sort()];
  }, [bookmarks]);

  const filtered = filter === "all" ? bookmarks : bookmarks.filter((b) => (b.category || "general") === filter);

  async function onDelete(id: string) {
    if (!window.confirm("Remove this bookmark?")) return;
    try {
      await api.deleteBookmark(id);
      setBookmarks((prev) => prev.filter((b) => b.id !== id).map((b, i) => ({ ...b, display_order: i })));
    } catch (e) {
      setErr((e as Error).message);
    }
  }

  return (
    <div className="mx-auto max-w-4xl">
      <header className="mb-6 flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-slate-100 flex items-center gap-2">
            <BookmarkIcon className="h-6 w-6 text-cyan-400" /> Bookmarks
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            Save and organize links to any site. Persisted on the backend, available from any device.
          </p>
        </div>
        <button
          onClick={() => setEditing({ mode: "add" })}
          className="inline-flex items-center gap-1.5 rounded-lg bg-cyan-500/90 px-3 py-1.5 text-sm font-semibold text-slate-950 hover:bg-cyan-400 transition"
        >
          <Plus className="h-4 w-4" /> Add
        </button>
      </header>

      {err && (
        <div className="mb-4 rounded-lg border border-rose-500/30 bg-rose-500/10 px-4 py-2 text-sm text-rose-300">
          {err}
        </div>
      )}

      {/* Category filter */}
      {categories.length > 2 && (
        <div className="mb-5 flex items-center gap-2 overflow-x-auto pb-1">
          <Filter className="h-4 w-4 flex-shrink-0 text-slate-500" />
          {categories.map((c) => (
            <button
              key={c}
              onClick={() => setFilter(c)}
              className={clsx(
                "flex-shrink-0 rounded-full px-3 py-1 text-xs font-medium transition",
                filter === c
                  ? "bg-cyan-500/20 text-cyan-200 border border-cyan-500/40"
                  : "bg-slate-800/50 text-slate-400 hover:text-slate-200 border border-white/5"
              )}
            >
              {c}
            </button>
          ))}
        </div>
      )}

      {loading && (
        <div className="flex items-center justify-center py-16 text-slate-500">
          <Loader2 className="h-5 w-5 animate-spin" />
        </div>
      )}

      {!loading && filtered.length === 0 && (
        <div className="rounded-lg border border-white/10 bg-slate-900/40 px-4 py-12 text-center text-slate-500">
          No bookmarks yet. Click <span className="text-slate-300">Add</span> to save your first one.
        </div>
      )}

      {!loading && filtered.length > 0 && (
        <ul className="grid gap-3 sm:grid-cols-2">
          {filtered.map((b) => (
            <li
              key={b.id}
              className="group flex items-start gap-3 rounded-lg border border-white/5 bg-slate-900/50 p-3 transition hover:border-cyan-500/30"
            >
              <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-md bg-cyan-500/10 text-cyan-300 text-lg">
                {b.icon || "🔖"}
              </div>
              <div className="min-w-0 flex-1">
                <a
                  href={b.url}
                  target="_blank"
                  rel="noreferrer noopener"
                  className="font-medium text-slate-100 hover:text-cyan-200 truncate block"
                >
                  {b.title}
                </a>
                <div className="text-xs text-slate-500 truncate">{b.url}</div>
                <div className="mt-1 text-[11px] uppercase tracking-wider text-slate-600">
                  {b.category || "general"}
                </div>
              </div>
              <div className="flex flex-shrink-0 items-center gap-1 opacity-0 transition group-hover:opacity-100">
                <a
                  href={b.url}
                  target="_blank"
                  rel="noreferrer noopener"
                  className="rounded-md p-1.5 text-slate-400 hover:bg-white/5 hover:text-slate-200"
                  title="Open"
                >
                  <ExternalLink className="h-3.5 w-3.5" />
                </a>
                <button
                  onClick={() => setEditing({ mode: "edit", bookmark: b })}
                  className="rounded-md p-1.5 text-slate-400 hover:bg-white/5 hover:text-slate-200"
                  title="Edit"
                >
                  <Pencil className="h-3.5 w-3.5" />
                </button>
                <button
                  onClick={() => onDelete(b.id)}
                  className="rounded-md p-1.5 text-slate-400 hover:bg-rose-500/10 hover:text-rose-300"
                  title="Delete"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}

      {editing && (
        <BookmarkEditor
          state={editing}
          onClose={() => setEditing(null)}
          onSaved={(b, mode) => {
            setBookmarks((prev) => {
              if (mode === "add") return [...prev, b].sort((a, c) => a.display_order - c.display_order);
              return prev.map((x) => (x.id === b.id ? b : x));
            });
            setEditing(null);
          }}
        />
      )}
    </div>
  );
}

interface EditorProps {
  state: { mode: "add" } | { mode: "edit"; bookmark: Bookmark };
  onClose: () => void;
  onSaved: (b: Bookmark, mode: "add" | "edit") => void;
}

function BookmarkEditor({ state, onClose, onSaved }: EditorProps) {
  const editing = state.mode === "edit";
  const initial = state.mode === "edit" ? state.bookmark : null;

  const [title, setTitle] = useState(initial?.title ?? "");
  const [url, setUrl] = useState(initial?.url ?? "");
  const [category, setCategory] = useState(initial?.category ?? "general");
  const [icon, setIcon] = useState(initial?.icon ?? "");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim() || !url.trim()) return;
    setBusy(true);
    setErr(null);
    try {
      if (state.mode === "add") {
        const b = await api.addBookmark({
          title: title.trim(),
          url: url.trim(),
          category: category.trim() || "general",
          icon: icon.trim() || undefined,
        });
        onSaved(b, "add");
      } else if (state.mode === "edit") {
        const b = await api.updateBookmark(state.bookmark.id, {
          title: title.trim(),
          url: url.trim(),
          category: category.trim() || "general",
          icon: icon.trim() || undefined,
        });
        onSaved(b, "edit");
      }
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <form
        onSubmit={onSubmit}
        className="w-full max-w-md rounded-xl border border-white/10 bg-slate-900 p-5 shadow-2xl"
      >
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-100">
            {editing ? "Edit bookmark" : "Add bookmark"}
          </h2>
          <button type="button" onClick={onClose} className="rounded-md p-1 text-slate-400 hover:bg-white/5 hover:text-slate-200">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="space-y-3">
          <Field label="Title*">
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
              className="w-full rounded-lg border border-white/10 bg-slate-800 px-3 py-2 text-sm text-slate-100 outline-none focus:border-cyan-500/50"
            />
          </Field>
          <Field label="URL*">
            <input
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              required
              placeholder="https://example.com"
              className="w-full rounded-lg border border-white/10 bg-slate-800 px-3 py-2 text-sm text-slate-100 outline-none focus:border-cyan-500/50"
            />
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Category">
              <input
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                placeholder="general"
                className="w-full rounded-lg border border-white/10 bg-slate-800 px-3 py-2 text-sm text-slate-100 outline-none focus:border-cyan-500/50"
              />
            </Field>
            <Field label="Icon (emoji)">
              <input
                value={icon}
                onChange={(e) => setIcon(e.target.value)}
                placeholder="🔖"
                className="w-full rounded-lg border border-white/10 bg-slate-800 px-3 py-2 text-sm text-slate-100 outline-none focus:border-cyan-500/50"
              />
            </Field>
          </div>
        </div>

        {err && <div className="mt-3 text-sm text-rose-300">{err}</div>}

        <div className="mt-5 flex justify-end gap-2">
          <button type="button" onClick={onClose} className="rounded-lg px-3 py-1.5 text-sm text-slate-400 hover:text-slate-200">
            Cancel
          </button>
          <button
            type="submit"
            disabled={busy}
            className="rounded-lg bg-cyan-500/90 px-4 py-1.5 text-sm font-semibold text-slate-950 hover:bg-cyan-400 disabled:opacity-40"
          >
            {busy ? "…" : editing ? "Save" : "Add"}
          </button>
        </div>
      </form>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-medium text-slate-400">{label}</span>
      {children}
    </label>
  );
}