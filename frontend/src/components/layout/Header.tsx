import { useLocation } from 'react-router-dom';
import { Bell, Search, User } from 'lucide-react';

const routeTitles: Record<string, string> = {
  '/': 'Dashboard',
  '/cases': 'Cases',
  '/upload': 'Upload Documents',
  '/review': 'Review Workspace',
  '/search': 'Semantic Search',
  '/privilege': 'Privilege Detection',
  '/analytics': 'Analytics',
  '/settings': 'Settings',
};

export function Header() {
  const location = useLocation();
  const title = routeTitles[location.pathname] || 'E-Discovery AI';

  return (
    <header className="sticky top-0 z-30 flex items-center justify-between h-16 px-6 border-b border-slate-800/50 bg-slate-950/60 backdrop-blur-xl">
      {/* ── Page Title ────────────────────────────────────────────────── */}
      <div>
        <h2 className="text-lg font-semibold text-slate-100">{title}</h2>
        <p className="text-xs text-slate-500">Agentic AI Legal Intelligence Platform</p>
      </div>

      {/* ── Actions ───────────────────────────────────────────────────── */}
      <div className="flex items-center gap-3">
        {/* Search bar */}
        <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900/80 border border-slate-800 text-slate-400 text-sm">
          <Search className="h-4 w-4" />
          <span>Search docs...</span>
          <kbd className="ml-4 px-1.5 py-0.5 rounded bg-slate-800 text-[10px] font-mono text-slate-500 border border-slate-700">
            ⌘K
          </kbd>
        </div>

        {/* Notifications */}
        <button
          className="relative p-2 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 transition-colors"
          id="notifications-button"
        >
          <Bell className="h-5 w-5" />
          <span className="absolute top-1.5 right-1.5 h-2 w-2 rounded-full bg-indigo-500 ring-2 ring-slate-950" />
        </button>

        {/* User avatar */}
        <button
          className="flex items-center gap-2 p-1.5 rounded-lg hover:bg-slate-800/50 transition-colors"
          id="user-menu-button"
        >
          <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-500 flex items-center justify-center">
            <User className="h-4 w-4 text-white" />
          </div>
        </button>
      </div>
    </header>
  );
}
