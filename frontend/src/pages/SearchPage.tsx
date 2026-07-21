// Root-task (t_c8aa6b03): DuckDuckGo web search page.
// Front-end shell that talks to the backend /api/search proxy (CORS-free).

import { FormEvent, useState } from "react";
import { Search as SearchIcon, ExternalLink, Loader2, AlertTriangle } from "lucide-react";
import clsx from "clsx";
import { api } from "../api";
import type { SearchResponse } from "../types";


export function SearchPage() {
  const [q, setQ] = useState("");
  const [data, setData] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!q.trim()) return;
    setLoading(true);
    setErr(null);
    setData(null);
    try {
      const out = await api.search(q);
      setData(out);
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold text-slate-100 flex items-center gap-2">
          <SearchIcon className="h-6 w-6 text-cyan-400" /> Web search
        </h1>
        <p className="mt-1 text-sm text-slate-400">
          DuckDuckGo private search, proxied through your backend. No tracking, no ads.
        </p>
      </header>

      <form onSubmit={onSubmit} className="relative mb-6">
        <input
          type="search"
          autoFocus
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search the web…"
          className={clsx(
            "w-full rounded-xl border border-white/10 bg-slate-900/70 px-4 py-3 pl-11",
            "text-slate-100 placeholder-slate-500 outline-none",
            "focus:border-cyan-500/50 focus:ring-2 focus:ring-cyan-500/20 transition"
          )}
        />
        <SearchIcon className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
        <button
          type="submit"
          disabled={loading || !q.trim()}
          className={clsx(
            "absolute right-2 top-1/2 -translate-y-1/2 rounded-lg px-3 py-1.5 text-sm font-semibold",
            "bg-cyan-500/90 text-slate-950 hover:bg-cyan-400 disabled:opacity-40 transition"
          )}
        >
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Search"}
        </button>
      </form>

      {err && (
        <div className="mb-4 flex items-start gap-3 rounded-lg border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-300">
          <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0" />
          <div>
            <div className="font-semibold">Search failed</div>
            <div className="opacity-80">{err}</div>
          </div>
        </div>
      )}

      {data && data.results.length === 0 && (
        <div className="rounded-lg border border-white/10 bg-slate-900/50 px-4 py-8 text-center text-slate-400">
          No results for <span className="text-slate-200">{data.query}</span>.
        </div>
      )}

      {data && data.results.length > 0 && (
        <ol className="space-y-3">
          {data.results.map((r, i) => {
            let host = "";
            try { host = new URL(r.url).hostname.replace(/^www\./, ""); } catch { /* ignore */ }
            return (
              <li
                key={i}
                className="group rounded-lg border border-white/5 bg-slate-900/40 p-4 transition hover:border-cyan-500/30 hover:bg-slate-900/60"
              >
                <a
                  href={r.url}
                  target="_blank"
                  rel="noreferrer noopener"
                  className="flex items-start gap-3"
                >
                  {r.favicon && (
                    <img
                      src={r.favicon}
                      alt=""
                      className="mt-0.5 h-4 w-4 flex-shrink-0 rounded-sm"
                      onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
                    />
                  )}
                  <div className="min-w-0 flex-1">
                    <div className="font-medium text-cyan-300 group-hover:text-cyan-200 truncate">
                      {r.title}
                    </div>
                    <div className="mt-0.5 text-xs text-slate-500 truncate">{host}</div>
                  </div>
                  <ExternalLink className="h-4 w-4 flex-shrink-0 text-slate-500 opacity-0 group-hover:opacity-100" />
                </a>
              </li>
            );
          })}
        </ol>
      )}

      {!loading && !data && !err && (
        <div className="rounded-lg border border-white/10 bg-slate-900/40 px-4 py-12 text-center text-slate-500">
          Type a query above and press <kbd className="rounded bg-slate-800 px-1.5 py-0.5 text-xs text-slate-300">Enter</kbd> to search the web.
        </div>
      )}
    </div>
  );
}