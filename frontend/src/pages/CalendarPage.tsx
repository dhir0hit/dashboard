// Calendar page — unified view of local day-planning events, Google Calendar
// sync, and Hermes cron jobs. Supports adding/editing/deleting local events,
// marking events as done (day planning), and connecting Google Calendar via
// backend OAuth proxy.

import { useEffect, useMemo, useState, useCallback } from "react";
import {
  CalIcon,
  ChevronLeft,
  ChevronRight,
  RefreshCw,
  Clock,
  Loader2,
  Plus,
  X,
  Check,
  Trash2,
  GoogleLogo,
  Edit2,
} from "./CalendarIcons";
import clsx from "clsx";
import { api } from "../api";
import type {
  CalendarEvent,
  CalendarEventCreate,
  CalendarEventUpdate,
  GoogleAuthStatus,
} from "../types";

const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

// --- date helpers ---
function startOfMonth(d: Date) { return new Date(d.getFullYear(), d.getMonth(), 1); }
function addMonths(d: Date, n: number) { return new Date(d.getFullYear(), d.getMonth() + n, 1); }
function sameDay(a: Date, b: Date) {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
}
function toISODate(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}
function dayKey(d: Date) { return `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`; }

// --- source styling ---
const SOURCE_STYLES: Record<string, { bg: string; text: string; border: string; label: string }> = {
  local:   { bg: "bg-cyan-500/10",   text: "text-cyan-200",   border: "border-cyan-500/20",   label: "📋" },
  google:  { bg: "bg-blue-500/10",   text: "text-blue-200",   border: "border-blue-500/20",   label: "📅" },
  hermes:  { bg: "bg-amber-500/10",  text: "text-amber-200",  border: "border-amber-500/20",  label: "⏰" },
};

export function CalendarPage() {
  const today = useMemo(() => new Date(), []);
  const [cursor, setCursor] = useState<Date>(startOfMonth(today));
  const [selectedDate, setSelectedDate] = useState<Date>(today);
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [googleStatus, setGoogleStatus] = useState<GoogleAuthStatus | null>(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingEvent, setEditingEvent] = useState<CalendarEvent | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [syncMsg, setSyncMsg] = useState<string | null>(null);

  const loadAll = useCallback(async () => {
    setLoading(true);
    setErr(null);
    try {
      // Calculate month range for the grid (includes overlap days)
      const first = startOfMonth(cursor);
      const gridStart = new Date(first);
      gridStart.setDate(first.getDate() - first.getDay());
      const gridEnd = new Date(gridStart);
      gridEnd.setDate(gridStart.getDate() + 41);
      const [localRes, hermesRes, gStatus] = await Promise.all([
        api.listCalendarEvents(toISODate(gridStart), toISODate(gridEnd)),
        api.listHermesCalendarEvents().catch(() => ({ events: [], count: 0 })),
        api.getGoogleAuthStatus().catch(() => null),
      ]);
      const all = [...localRes.events, ...hermesRes.events];
      setEvents(all);
      setGoogleStatus(gStatus);
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [cursor]);

  useEffect(() => { void loadAll(); }, [loadAll]);

  // Index events by day
  const byDay = useMemo(() => {
    const map = new Map<string, CalendarEvent[]>();
    for (const ev of events) {
      const d = new Date(ev.date + "T00:00:00");
      if (isNaN(d.getTime())) continue;
      const k = dayKey(d);
      const arr = map.get(k) ?? [];
      arr.push(ev);
      map.set(k, arr);
    }
    // Sort each day's events: by time (nulls last), then source
    for (const arr of map.values()) {
      arr.sort((a, b) => {
        if (a.time && b.time) return a.time.localeCompare(b.time);
        if (a.time) return -1;
        if (b.time) return 1;
        return 0;
      });
    }
    return map;
  }, [events]);

  // Build 6-week grid
  const grid = useMemo(() => {
    const first = startOfMonth(cursor);
    const start = new Date(first);
    start.setDate(first.getDate() - first.getDay());
    const out: Date[] = [];
    for (let i = 0; i < 42; i++) {
      const d = new Date(start);
      d.setDate(start.getDate() + i);
      out.push(d);
    }
    return out;
  }, [cursor]);

  // Events for the selected day
  const selectedDayEvents = useMemo(() => {
    return byDay.get(dayKey(selectedDate)) ?? [];
  }, [byDay, selectedDate]);

  // --- event actions ---
  async function handleCreate(data: CalendarEventCreate) {
    try {
      await api.createCalendarEvent(data);
      setShowAddForm(false);
      await loadAll();
    } catch (e) {
      setErr((e as Error).message);
    }
  }

  async function handleToggleDone(ev: CalendarEvent) {
    if (ev.source !== "local") return;
    try {
      await api.updateCalendarEvent(ev.id, { done: !ev.done });
      setEvents((prev) =>
        prev.map((e) => e.id === ev.id ? { ...e, done: !e.done } : e)
      );
    } catch (e) {
      setErr((e as Error).message);
    }
  }

  async function handleDelete(id: string) {
    try {
      await api.deleteCalendarEvent(id);
      setEvents((prev) => prev.filter((e) => e.id !== id));
    } catch (e) {
      setErr((e as Error).message);
    }
  }

  async function handleEdit(ev: CalendarEvent, patch: CalendarEventUpdate) {
    try {
      await api.updateCalendarEvent(ev.id, patch);
      setEditingEvent(null);
      await loadAll();
    } catch (e) {
      setErr((e as Error).message);
    }
  }

  async function handleGoogleLogin() {
    try {
      const url = await api.getGoogleLoginUrl();
      window.open(url, "_blank");
    } catch (e) {
      setErr((e as Error).message);
    }
  }

  async function handleGoogleSync() {
    setSyncing(true);
    setSyncMsg(null);
    try {
      const result = await api.syncGoogleCalendar();
      setSyncMsg(`Synced ${result.synced} of ${result.total} events from Google Calendar`);
      await loadAll();
    } catch (e) {
      setSyncMsg(`Sync failed: ${(e as Error).message}`);
    } finally {
      setSyncing(false);
    }
  }

  async function handleGoogleDisconnect() {
    try {
      await api.disconnectGoogle();
      await loadAll();
    } catch (e) {
      setErr((e as Error).message);
    }
  }

  return (
    <div className="mx-auto max-w-5xl">
      <header className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-slate-100 flex items-center gap-2">
            <CalIcon className="h-6 w-6 text-cyan-400" /> Calendar
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            Day planning, Google Calendar sync, and Hermes cron jobs — all in one view.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setCursor(startOfMonth(today))}
            className="rounded-lg border border-white/10 bg-slate-800/60 px-3 py-1.5 text-sm text-slate-300 hover:text-slate-100"
          >
            Today
          </button>
          <button
            onClick={loadAll}
            disabled={loading}
            className="rounded-lg border border-white/10 bg-slate-800/60 p-2 text-slate-300 hover:text-slate-100 disabled:opacity-40"
            title="Refresh"
          >
            <RefreshCw className={clsx("h-4 w-4", loading && "animate-spin")} />
          </button>
        </div>
      </header>

      {/* Google Calendar section */}
      <section className="mb-6 rounded-lg border border-white/10 bg-slate-900/40 p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <GoogleLogo className="h-5 w-5" />
            <span className="text-sm font-medium text-slate-200">Google Calendar</span>
            {googleStatus?.authenticated && googleStatus?.email && (
              <span className="text-xs text-slate-400">({googleStatus.email})</span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {!googleStatus?.configured ? (
              <span className="text-xs text-slate-500">
                Set GOOGLE_CLIENT_ID + GOOGLE_CLIENT_SECRET in backend .env to enable
              </span>
            ) : !googleStatus?.authenticated ? (
              <button
                onClick={handleGoogleLogin}
                className="flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-500"
              >
                <GoogleLogo className="h-3.5 w-3.5" /> Connect Google
              </button>
            ) : (
              <>
                <button
                  onClick={handleGoogleSync}
                  disabled={syncing}
                  className="flex items-center gap-1.5 rounded-lg border border-blue-500/30 bg-blue-500/10 px-3 py-1.5 text-xs font-medium text-blue-200 hover:bg-blue-500/20 disabled:opacity-40"
                >
                  {syncing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
                  Sync now
                </button>
                <button
                  onClick={handleGoogleDisconnect}
                  className="rounded-lg border border-white/10 bg-slate-800/60 px-3 py-1.5 text-xs text-slate-400 hover:text-rose-300"
                >
                  Disconnect
                </button>
              </>
            )}
          </div>
        </div>
        {syncMsg && (
          <p className="mt-2 text-xs text-slate-400">{syncMsg}</p>
        )}
      </section>

      {err && (
        <div className="mb-4 rounded-lg border border-rose-500/30 bg-rose-500/10 px-4 py-2 text-sm text-rose-300">
          {err}
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        {/* Calendar grid */}
        <div>
          {/* Month controls */}
          <div className="mb-3 flex items-center justify-between">
            <button
              onClick={() => setCursor((c) => addMonths(c, -1))}
              className="rounded-lg border border-white/10 bg-slate-800/60 p-2 text-slate-300 hover:text-slate-100"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <div className="text-lg font-semibold text-slate-100">
              {MONTHS[cursor.getMonth()]} {cursor.getFullYear()}
            </div>
            <button
              onClick={() => setCursor((c) => addMonths(c, 1))}
              className="rounded-lg border border-white/10 bg-slate-800/60 p-2 text-slate-300 hover:text-slate-100"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>

          {/* Weekday header */}
          <div className="grid grid-cols-7 gap-1 text-center text-[11px] uppercase tracking-wider text-slate-500 sm:text-xs">
            {WEEKDAYS.map((d) => (
              <div key={d} className="py-1">{d}</div>
            ))}
          </div>

          {/* Day grid */}
          <div className="mt-1 grid grid-cols-7 gap-1">
            {grid.map((d) => {
              const inMonth = d.getMonth() === cursor.getMonth();
              const isToday = sameDay(d, today);
              const isSelected = sameDay(d, selectedDate);
              const dayEvents = byDay.get(dayKey(d)) ?? [];
              return (
                <button
                  key={d.toISOString()}
                  onClick={() => setSelectedDate(d)}
                  className={clsx(
                    "min-h-[60px] rounded-md border p-1 text-left transition sm:min-h-[88px]",
                    inMonth ? "border-white/5 bg-slate-900/40" : "border-transparent bg-slate-900/20",
                    isToday && "ring-1 ring-cyan-500/50",
                    isSelected && "ring-2 ring-cyan-400",
                    "hover:border-white/20"
                  )}
                >
                  <div className={clsx(
                    "mb-1 text-xs font-medium",
                    inMonth ? "text-slate-300" : "text-slate-600",
                    isToday && "text-cyan-300"
                  )}>
                    {d.getDate()}
                  </div>
                  <div className="space-y-0.5">
                    {dayEvents.slice(0, 3).map((ev) => {
                      const s = SOURCE_STYLES[ev.source] ?? SOURCE_STYLES.local;
                      return (
                        <div
                          key={ev.id}
                          className={clsx(
                            "truncate rounded px-1 py-0.5 text-[9px] sm:text-[10px]",
                            s.bg, s.text, s.border,
                            "border",
                            ev.done && "opacity-50 line-through"
                          )}
                        >
                          {s.label} {ev.title}
                        </div>
                      );
                    })}
                    {dayEvents.length > 3 && (
                      <div className="text-[9px] text-slate-500">+{dayEvents.length - 3} more</div>
                    )}
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Day plan sidebar */}
        <div>
          <div className="rounded-lg border border-white/10 bg-slate-900/40 p-4">
            <div className="mb-3 flex items-center justify-between">
              <div>
                <h2 className="text-sm font-semibold text-slate-200">
                  {selectedDate.toLocaleDateString(undefined, { weekday: "long", month: "short", day: "numeric" })}
                </h2>
                <p className="text-xs text-slate-500">{selectedDayEvents.length} event(s)</p>
              </div>
              <button
                onClick={() => { setEditingEvent(null); setShowAddForm(true); }}
                className="flex items-center gap-1 rounded-lg bg-cyan-600 px-2.5 py-1 text-xs font-medium text-white hover:bg-cyan-500"
              >
                <Plus className="h-3 w-3" /> Add
              </button>
            </div>

            {showAddForm && (
              <EventForm
                date={toISODate(selectedDate)}
                onSubmit={handleCreate}
                onCancel={() => setShowAddForm(false)}
              />
            )}

            {editingEvent && (
              <EventForm
                event={editingEvent}
                date={editingEvent.date}
                onSubmit={(data) => handleEdit(editingEvent, data as CalendarEventUpdate)}
                onCancel={() => setEditingEvent(null)}
              />
            )}

            {selectedDayEvents.length === 0 && !showAddForm && !editingEvent ? (
              <div className="py-6 text-center text-sm text-slate-500">
                No events. Click "Add" to plan your day.
              </div>
            ) : (
              <ul className="space-y-2">
                {selectedDayEvents.map((ev) => {
                  const s = SOURCE_STYLES[ev.source] ?? SOURCE_STYLES.local;
                  return (
                    <li
                      key={ev.id}
                      className={clsx(
                        "rounded-lg border p-2.5",
                        s.border, s.bg
                      )}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-1.5">
                            <span className="text-xs">{s.label}</span>
                            <span className={clsx(
                              "text-sm font-medium truncate",
                              s.text,
                              ev.done && "line-through opacity-60"
                            )}>
                              {ev.title}
                            </span>
                          </div>
                          <div className="mt-0.5 flex items-center gap-2 text-[11px] text-slate-400">
                            {ev.time && (
                              <span className="flex items-center gap-0.5">
                                <Clock className="h-3 w-3" /> {ev.time}
                                {ev.duration_minutes ? ` (${ev.duration_minutes}m)` : ""}
                              </span>
                            )}
                            <span className="uppercase tracking-wide">{ev.source}</span>
                          </div>
                          {ev.description && (
                            <p className="mt-1 text-xs text-slate-400 line-clamp-2">{ev.description}</p>
                          )}
                        </div>
                        <div className="flex flex-shrink-0 items-center gap-1">
                          {ev.source === "local" && (
                            <>
                              <button
                                onClick={() => handleToggleDone(ev)}
                                className={clsx(
                                  "rounded p-1 hover:bg-white/10",
                                  ev.done ? "text-green-400" : "text-slate-500"
                                )}
                                title={ev.done ? "Mark as not done" : "Mark as done"}
                              >
                                <Check className="h-3.5 w-3.5" />
                              </button>
                              <button
                                onClick={() => { setShowAddForm(false); setEditingEvent(ev); }}
                                className="rounded p-1 text-slate-500 hover:bg-white/10 hover:text-slate-300"
                                title="Edit"
                              >
                                <Edit2 className="h-3.5 w-3.5" />
                              </button>
                              <button
                                onClick={() => handleDelete(ev.id)}
                                className="rounded p-1 text-slate-500 hover:bg-white/10 hover:text-rose-300"
                                title="Delete"
                              >
                                <Trash2 className="h-3.5 w-3.5" />
                              </button>
                            </>
                          )}
                        </div>
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>

          {/* Legend */}
          <div className="mt-3 flex flex-wrap items-center gap-3 rounded-lg border border-white/5 bg-slate-900/20 p-3 text-[11px] text-slate-400">
            <span className="flex items-center gap-1">📋 Local</span>
            <span className="flex items-center gap-1">📅 Google</span>
            <span className="flex items-center gap-1">⏰ Hermes cron</span>
          </div>
        </div>
      </div>
    </div>
  );
}

// --- Event form (add / edit) ---
function EventForm({
  event,
  date,
  onSubmit,
  onCancel,
}: {
  event?: CalendarEvent;
  date: string;
  onSubmit: (data: CalendarEventCreate) => Promise<void>;
  onCancel: () => void;
}) {
  const [title, setTitle] = useState(event?.title ?? "");
  const [description, setDescription] = useState(event?.description ?? "");
  const [eventDate, setEventDate] = useState(event?.date ?? date);
  const [time, setTime] = useState(event?.time ?? "");
  const [duration, setDuration] = useState(event?.duration_minutes?.toString() ?? "");
  const [saving, setSaving] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    setSaving(true);
    await onSubmit({
      title: title.trim(),
      description: description.trim() || undefined,
      date: eventDate,
      time: time || undefined,
      duration_minutes: duration ? parseInt(duration, 10) : undefined,
      done: event?.done ?? false,
    });
    setSaving(false);
  }

  return (
    <form onSubmit={submit} className="mb-3 rounded-lg border border-cyan-500/20 bg-cyan-500/5 p-3">
      <input
        className="input mb-2"
        placeholder="Event title"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        autoFocus
        required
      />
      <div className="mb-2 grid grid-cols-2 gap-2">
        <input
          type="date"
          className="input"
          value={eventDate}
          onChange={(e) => setEventDate(e.target.value)}
          required
        />
        <input
          type="time"
          className="input"
          value={time}
          onChange={(e) => setTime(e.target.value)}
        />
      </div>
      <input
        className="input mb-2"
        placeholder="Duration (minutes) — optional"
        type="number"
        value={duration}
        onChange={(e) => setDuration(e.target.value)}
      />
      <textarea
        className="input mb-2 min-h-[60px] resize-y"
        placeholder="Description — optional"
        value={description}
        onChange={(e) => setDescription(e.target.value)}
      />
      <div className="flex justify-end gap-2">
        <button
          type="button"
          onClick={onCancel}
          className="rounded-lg border border-white/10 bg-slate-800/60 px-3 py-1 text-xs text-slate-300"
        >
          <X className="inline h-3 w-3" /> Cancel
        </button>
        <button
          type="submit"
          disabled={saving || !title.trim()}
          className="rounded-lg bg-cyan-600 px-3 py-1 text-xs font-medium text-white hover:bg-cyan-500 disabled:opacity-40"
        >
          {saving ? <Loader2 className="inline h-3 w-3 animate-spin" /> : <Plus className="inline h-3 w-3" />}
          {event ? "Save" : "Add event"}
        </button>
      </div>
    </form>
  );
}
