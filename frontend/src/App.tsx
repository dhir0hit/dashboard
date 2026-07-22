import { useEffect, useMemo } from "react";
import { BrowserRouter, Routes, Route, NavLink, useLocation } from "react-router-dom";
import {
  Home,
  Settings as SettingsIcon,
  Search as SearchIcon,
  Bookmark as BookmarkIcon,
  Calendar as CalendarIcon,
} from "lucide-react";
import clsx from "clsx";

import { useSettings } from "./store";
import { SettingsPage } from "./pages/SettingsPage";
import { HomePage } from "./pages/HomePage";
import { SearchPage } from "./pages/SearchPage";
import { BookmarksPage } from "./pages/BookmarksPage";
import { CalendarPage } from "./pages/CalendarPage";
import { BUILTIN_THEMES } from "./types";

const NAV = [
  { to: "/", end: true, label: "Home", Icon: Home },
  { to: "/search", end: false, label: "Search", Icon: SearchIcon },
  { to: "/bookmarks", end: false, label: "Bookmarks", Icon: BookmarkIcon },
  { to: "/calendar", end: false, label: "Calendar", Icon: CalendarIcon },
  { to: "/settings", end: false, label: "Settings", Icon: SettingsIcon },
] as const;

function useDesktopNav() {
  // SSR-safe check; we render UI for both layouts and toggle via CSS
  // (Tailwind `hidden md:flex` etc.) so JS overhead is minimal.
  return null;
}

function Header() {
  return (
    <header className="sticky top-0 z-30 hidden border-b border-white/5 bg-slate-950/40 backdrop-blur-xl md:block">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
        <div className="text-sm font-semibold tracking-tight text-slate-200">
          <span className="mr-2 text-cyan-400">◈</span> Dashboard
        </div>
        <nav className="flex items-center gap-1">
          {NAV.map(({ to, end, label, Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                clsx(
                  "inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition",
                  isActive ? "bg-white/10 text-white" : "text-slate-400 hover:text-white"
                )
              }
            >
              <Icon className="h-4 w-4" /> {label}
            </NavLink>
          ))}
        </nav>
      </div>
    </header>
  );
}

function MobileTopBar() {
  return (
    <header className="sticky top-0 z-30 border-b border-white/5 bg-slate-950/50 backdrop-blur-xl md:hidden">
      <div className="flex items-center justify-center px-4 py-3">
        <div className="text-sm font-semibold tracking-tight text-slate-200">
          <span className="mr-2 text-cyan-400">◈</span> Dashboard
        </div>
      </div>
    </header>
  );
}

function MobileBottomNav() {
  return (
    <nav className="fixed inset-x-0 bottom-0 z-40 grid grid-cols-5 border-t border-white/10 bg-slate-950/80 backdrop-blur-xl md:hidden">
      {NAV.map(({ to, end, label, Icon }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          className={({ isActive }) =>
            clsx(
              "flex flex-col items-center justify-center gap-0.5 py-2 text-[10px] font-medium transition",
              isActive ? "text-cyan-300" : "text-slate-500 hover:text-slate-300"
            )
          }
        >
          <Icon className="h-5 w-5" />
          <span>{label}</span>
        </NavLink>
      ))}
    </nav>
  );
}

// Global site footer — visible on every page (task t_76f0d993).
// Styled to match the existing per-page footers: small, muted, unobtrusive.
function SiteFooter() {
  return (
    <footer className="mx-auto max-w-6xl px-4 pb-6 pt-2 text-center text-xs text-slate-500 md:px-6">
      Created by{" "}
      <span className="text-slate-400">@dhir0hit</span>{" "}
      using{" "}
      <span className="text-slate-400">Hermes Agent</span>
    </footer>
  );
}

function ThemeApplier() {
  const theme = useSettings((s) => s.config.theme);
  const customThemes = useSettings((s) => s.config.custom_themes);
  const active = useMemo(() => {
    const all = [...BUILTIN_THEMES, ...customThemes];
    return all.find((t) => t.id === theme.active_theme) ?? BUILTIN_THEMES[0];
  }, [theme.active_theme, customThemes]);

  useEffect(() => {
    const root = document.documentElement;
    root.style.setProperty("--theme-accent", theme.accent_color || active.accent);
    root.style.setProperty("--theme-bg", active.bg);
    root.style.setProperty("--theme-surface", active.surface);
    root.style.setProperty("--theme-text", active.text);
    root.style.setProperty("--theme-muted", active.muted);
    root.style.setProperty("--theme-border", active.border);
    document.body.classList.toggle("theme-light", !active.dark);
  }, [theme.accent_color, active]);

  return null;
}

// Inner content lives INSIDE <BrowserRouter>, so it can safely call
// useLocation() (which requires a router context). App itself renders the
// router, so it must not call useLocation() directly — that invariant
// failure was leaving #root empty (blank page).
function AppContent() {
  const load = useSettings((s) => s.load);
  useDesktopNav();
  const location = useLocation();
  useEffect(() => { void load(); }, [load]);
  // Scroll to top on route change — feels much better on mobile.
  useEffect(() => { window.scrollTo({ top: 0, behavior: "smooth" }); }, [location.pathname]);

  return (
    <>
      <ThemeApplier />
      <div className="flex min-h-screen flex-col pb-16 md:pb-0">
        <Header />
        <MobileTopBar />
        <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 md:px-6 md:py-8">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/search" element={<SearchPage />} />
            <Route path="/bookmarks" element={<BookmarksPage />} />
            <Route path="/calendar" element={<CalendarPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </main>
        <SiteFooter />
        <MobileBottomNav />
      </div>
    </>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppContent />
    </BrowserRouter>
  );
}