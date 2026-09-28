import { NavLink } from 'react-router-dom';
import { SlidersHorizontal, BarChart3, Brain, Server } from 'lucide-react';
import { cn } from '@/lib/utils';

const SETTINGS_LINKS = [
  { to: '/settings', label: 'General', icon: SlidersHorizontal, end: true },
  { to: '/settings/analytics', label: 'Analytics', icon: BarChart3, end: false },
  { to: '/settings/agents', label: 'AI Agents', icon: Brain, end: false },
  { to: '/settings/system', label: 'System Health', icon: Server, end: false },
] as const;

export function SettingsSubNav() {
  return (
    <div className="flex items-center gap-1.5 p-1 bg-slate-900/60 border border-slate-800/80 rounded-xl mb-6 backdrop-blur-sm overflow-x-auto">
      {SETTINGS_LINKS.map(({ to, label, icon: Icon, end }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          className={({ isActive }) =>
            cn(
              'flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all whitespace-nowrap',
              isActive
                ? 'bg-indigo-600 text-white shadow-sm shadow-indigo-600/20'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
            )
          }
        >
          <Icon className="h-3.5 w-3.5 shrink-0" />
          <span>{label}</span>
        </NavLink>
      ))}
    </div>
  );
}
