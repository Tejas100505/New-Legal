/**
 * SettingsPage — configuration for themes, notifications, and profile details.
 */

import { useState } from 'react';
import { Shield, Bell, Moon, Sun, Laptop } from 'lucide-react';
import { cn } from '@/lib/utils';
import { PageShell } from '@/components/templates/PageShell';
import { Toggle } from '@/components/atoms/Toggle';
import { useThemeStore } from '@/stores/themeStore';
import { useAuthStore } from '@/features/auth/store';
import { Badge } from '@/components/atoms/Badge';

export function SettingsPage() {
  const { theme, setTheme } = useThemeStore();
  const { user } = useAuthStore();

  const [emailAlerts, setEmailAlerts] = useState(true);
  const [insightAlerts, setInsightAlerts] = useState(true);
  const [compactMode, setCompactMode] = useState(false);

  return (
    <PageShell
      title="Settings"
      description="Manage account settings, application theme, and notification preferences."
    >
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Side: Profile overview */}
        <div className="lg:col-span-1 space-y-4">
          <div className="rounded-xl p-5 bg-slate-900/50 border border-slate-800/50 flex flex-col items-center text-center">
            <div className="h-20 w-20 rounded-2xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center font-bold text-white text-2xl shadow-xl shadow-indigo-500/20 mb-4">
              {user?.name ? user.name.split(' ').map(n => n[0]).join('') : 'L'}
            </div>
            <h3 className="text-base font-semibold text-slate-200">{user?.name}</h3>
            <p className="text-xs text-slate-500">{user?.email}</p>
            <Badge variant="purple" size="xs" className="mt-2">Lawyer Role</Badge>
            <div className="w-full border-t border-slate-800/50 mt-5 pt-4 space-y-2.5 text-left text-xs text-slate-400">
              <div className="flex justify-between">
                <span>Firm</span>
                <span className="text-slate-300 font-medium">{user?.firm}</span>
              </div>
              <div className="flex justify-between">
                <span>Bar License</span>
                <span className="text-slate-300 font-medium">{user?.barNumber}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right Side: Configuration panels */}
        <div className="lg:col-span-2 space-y-6">
          {/* Theme selection */}
          <div className="rounded-xl p-5 bg-slate-900/50 border border-slate-800/50">
            <h3 className="text-sm font-semibold text-slate-200 mb-4 flex items-center gap-1.5">
              <Sun className="h-4.5 w-4.5 text-indigo-400" /> Theme Mode
            </h3>
            <div className="grid grid-cols-3 gap-3">
              {(['dark', 'light', 'system'] as const).map((mode) => {
                const Icon = mode === 'dark' ? Moon : mode === 'light' ? Sun : Laptop;
                return (
                  <button
                    key={mode}
                    onClick={() => setTheme(mode)}
                    className={cn(
                      'flex flex-col items-center gap-2 p-4 rounded-xl border transition-all text-xs font-semibold capitalize',
                      theme === mode
                        ? 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30 shadow-lg shadow-indigo-500/5'
                        : 'bg-slate-800/20 text-slate-500 border-slate-800 hover:text-slate-300 hover:bg-slate-800/50'
                    )}
                  >
                    <Icon className="h-5 w-5" />
                    {mode}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Notifications */}
          <div className="rounded-xl p-5 bg-slate-900/50 border border-slate-800/50 space-y-4">
            <h3 className="text-sm font-semibold text-slate-200 mb-1 flex items-center gap-1.5">
              <Bell className="h-4.5 w-4.5 text-orange-400" /> Notification Preferences
            </h3>
            <div className="divide-y divide-slate-800/30 space-y-3">
              <div className="pt-2">
                <Toggle
                  checked={emailAlerts}
                  onChange={setEmailAlerts}
                  label="Email Digests"
                  description="Receive daily review summaries of active case updates."
                />
              </div>
              <div className="pt-3">
                <Toggle
                  checked={insightAlerts}
                  onChange={setInsightAlerts}
                  label="Instant AI Alerts"
                  description="Notify immediately upon detecting critical privilege or risk flags."
                />
              </div>
            </div>
          </div>

          {/* Accessibility & Interface */}
          <div className="rounded-xl p-5 bg-slate-900/50 border border-slate-800/50 space-y-4">
            <h3 className="text-sm font-semibold text-slate-200 mb-1 flex items-center gap-1.5">
              <Shield className="h-4.5 w-4.5 text-emerald-400" /> Interface Customization
            </h3>
            <div>
              <Toggle
                checked={compactMode}
                onChange={setCompactMode}
                label="Compact Workspace"
                description="Maximize screen usage by reducing padding in library tables and file lists."
              />
            </div>
            <div className="pt-3 border-t border-slate-800/50 flex justify-end">
              <button
                onClick={() => {
                  import('react-hot-toast').then(({ default: toast }) => {
                    toast.success('Settings and notification preferences saved successfully.');
                  });
                }}
                className="px-4 py-2 rounded-xl bg-gradient-to-r from-indigo-500 to-violet-500 text-white text-xs font-semibold shadow-lg shadow-indigo-500/20 hover:brightness-110 transition-all cursor-pointer"
              >
                Save Preferences
              </button>
            </div>
          </div>
        </div>
      </div>
    </PageShell>
  );
}
