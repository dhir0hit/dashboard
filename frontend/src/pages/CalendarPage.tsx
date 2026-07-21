// Root-task (t_c8aa6b03): calendar synced with Hermes cron jobs.
// Fetches /api/cron (server-side proxy that shells out to `hermes cronjob
// list --json`), renders a month-grid calendar, and pins jobs on their
// last_run / next_run days.

import { useEffect, useMemo, useState } from "react";
import {
  Calendar as CalIcon,
  ChevronLeft,
  ChevronRight,
  RefreshCw,
  Clock,
  Loader2,
} from "lucide-react";
import clsx from "clsx";
import { api } from "../api";
import type { CronEntry, CronListResponse } from "../types";

const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

function startOfMonth(d: Date) { return new Date(d.getFullYear(), d.getMonth(), 1); }
function addMonths(d: Date, n: number) { return new Date(d.getFullYear(), d.getMonth() + n, 1); }
function sameDay(a: Date, b: Date) {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
}
function dayKey(d: Date) { return `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`; }
function parseDate(s?: string | null): Date | null {
  if (!s) return null;
  const d = new Date(s);
  return isNaN(d.getTime()) ? null : d;
}

export function CalendarPage() {
  const today = useMemo(() => new Date(), []);
  const [cursor, setCursor] = useState<Date>(startOfMonth(today));
  const [data, setData] = useState<CronListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  async function reload() {
    setLoading(true);
    setErr(null);
    try {
      setData(await api.listCron());
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void reload(); }, []);

  // Index cron jobs by day (last_run + next_run).
  const byDay = useMemo(() => {
    const map = new Map<string, CronEntry[]>();
    for (const j of data?.jobs ?? []) {
      for (const field of [j.last_run, j.next_run]) {
        const d = parseDate(field);
        if (!d) continue;
        const k = dayKey(d);
        const arr = map.get(k) ?? [];
        if (!arr.find((x) => x.id === j.id)) arr.push(j);
        map.set(k, arr);
      }
    }
    return map;
  }, [data]);

  // Build 6-week grid starting from the Sunday before the 1st of cursor month.
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

  return (
    <div className="mx-auto max-w-4xl">
      <header className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-slate-100 flex items-center gap-2">
            <CalIcon className="h-6 w-6 text-cyan-400" /> Calendar
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            Hermes cron jobs pinned on their last run / next run days. Source:{" "}
            <span className="text-slate-300">{data?.source ?? "…"}</span>.
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
            onClick={reload}
            disabled={loading}
            className="rounded-lg border border-white/10 bg-slate-800/60 p-2 text-slate-300 hover:text-slate-100 disabled:opacity-40"
            title="Refresh"
          >
            <RefreshCw className={clsx("h-4 w-4", loading && "animate-spin")} />
          </button>
        </div>
      </header>

      {err && (
        <div className="mb-4 rounded-lg border border-rose-500/30 bg-rose-500/10 px-4 py-2 text-sm text-rose-300">
          {err}
        </div>
      )}

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
          const jobs = byDay.get(dayKey(d)) ?? [];
          return (
            <div
              key={d.toISOString()}
              className={clsx(
                "min-h-[64px] rounded-md border p-1.5 sm:min-h-[96px]",
                inMonth ? "border-white/5 bg-slate-900/40" : "border-transparent bg-slate-900/20",
                isToday && "ring-1 ring-cyan-500/50"
              )}
            >
              <div className={clsx(
                "mb-1 text-xs font-medium",
                inMonth ? "text-slate-300" : "text-slate-600",
                isToday && "text-cyan-300"
              )}>
                {d.getDate()}
              </div>
              <div className="space-y-1">
                {jobs.slice(0, 3).map((j) => (
                  <div
                    key={j.id}
                    title={j.name || j.id}
                    className={clsx(
                      "truncate rounded bg-cyan-500/10 px-1.5 py-0.5 text-[10px] text-cyan-200",
                      "border border-cyan-500/20",
                      !j.enabled && "opacity-50 line-through"
                    )}
                  >
                    {j.name || j.id}
                  </div>
                ))}
                {jobs.length > 3 && (
                  <div className="text-[10px] text-slate-500">+{jobs.length - 3} more</div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Jobs list */}
      <section className="mt-8">
        <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-300">
          <Clock className="h-4 w-4 text-cyan-400" /> All Hermes cron jobs
        </h2>
        {loading ? (
          <div className="flex items-center justify-center py-8 text-slate-500">
            <Loader2 className="h-5 w-5 animate-spin" />
          </div>
        ) : (data?.jobs ?? []).length === 0 ? (
          <div className="rounded-lg border border-white/10 bg-slate-900/40 px-4 py-8 text-center text-slate-500">
            No cron jobs registered with Hermes. Run <code className="rounded bg-slate-800 px-1.5 py-0.5 text-xs text-slate-300">hermes cronjob create</code> to add one.
          </div>
        ) : (
          <ul className="divide-y divide-white/5 rounded-lg border border-white/10 bg-slate-900/40">
            {data!.jobs.map((j) => (
              <li key={j.id} className="px-4 py-3">
                <div className="flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-slate-100 truncate">{j.name || j.id}</span>
                      {!j.enabled && (
                        <span className="rounded bg-slate-700 px-1.5 py-0.5 text-[10px] text-slate-300">disabled</span>
                      )}
                    </div>
                    <div className="mt-0.5 truncate text-xs text-slate-500">
                      {j.description || "—"}
                    </div>
                  </div>
                  <div className="flex-shrink-0 text-right text-xs">
                    {j.schedule && (
                      <div className="font-mono text-cyan-300">{j.schedule}</div>
                    )}
                    {j.next_run && (
                      <div className="mt-1 text-slate-400">next: {fmtTime(j.next_run)}</div>
                    )}
                    {j.last_run && (
                      <div className="text-slate-500">last: {fmtTime(j.last_run)}</div>
                    )}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

function fmtTime(s: string): string {
  const d = parseDate(s);
  if (!d) return s;
  return d.toLocaleString(undefined, {
    month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
  });
}