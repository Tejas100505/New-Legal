/**
 * Theme Zustand store — manages dark/light mode.
 * Persisted to localStorage and syncs with document class.
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { ThemeMode } from '@/types';

interface ThemeStore {
  theme: ThemeMode;
  resolvedTheme: 'dark' | 'light';
  setTheme: (theme: ThemeMode) => void;
  toggleTheme: () => void;
}

function getSystemTheme(): 'dark' | 'light' {
  if (typeof window === 'undefined') return 'dark';
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function resolveTheme(theme: ThemeMode): 'dark' | 'light' {
  if (theme === 'system') return getSystemTheme();
  return theme;
}

function getInitialTheme(): ThemeMode {
  if (typeof window === 'undefined') return 'dark';
  try {
    const stored = localStorage.getItem('casegraph-theme') || localStorage.getItem('theme-storage');
    if (stored) {
      try {
        const parsed = JSON.parse(stored);
        if (parsed?.state?.theme) return parsed.state.theme;
        if (typeof parsed === 'string') return parsed as ThemeMode;
      } catch {
        if (stored === 'light' || stored === 'dark' || stored === 'system') return stored as ThemeMode;
      }
    }
  } catch {}
  return 'dark';
}

function applyTheme(resolved: 'dark' | 'light') {
  if (typeof document === 'undefined') return;
  const root = document.documentElement;
  root.classList.remove('dark', 'light');
  root.classList.add(resolved);
  root.setAttribute('data-theme', resolved);
  root.style.colorScheme = resolved;
}

const initialTheme = getInitialTheme();
const initialResolved = resolveTheme(initialTheme);
applyTheme(initialResolved);

export const useThemeStore = create<ThemeStore>()(
  persist(
    (set, get) => ({
      theme: initialTheme,
      resolvedTheme: initialResolved,

      setTheme: (theme: ThemeMode) => {
        const resolved = resolveTheme(theme);
        applyTheme(resolved);
        set({ theme, resolvedTheme: resolved });
      },

      toggleTheme: () => {
        const current = get().resolvedTheme;
        const next = current === 'dark' ? 'light' : 'dark';
        applyTheme(next);
        set({ theme: next, resolvedTheme: next });
      },
    }),
    {
      name: 'casegraph-theme',
      partialize: (state) => ({ theme: state.theme }),
      onRehydrateStorage: () => (state) => {
        if (state) {
          const resolved = resolveTheme(state.theme);
          applyTheme(resolved);
          state.resolvedTheme = resolved;
        }
      },
    }
  )
);
