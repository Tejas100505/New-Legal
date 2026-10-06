/**
 * CommandPalette organism — Ctrl/Cmd+K searchable command palette.
 */

import { useEffect, useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  LayoutDashboard, FolderOpen, FileText, Search, GitBranch, Clock,
  Brain, Sparkles, FileBarChart, BarChart3, Settings, ArrowRight,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useCommandPaletteStore } from '@/stores/commandPaletteStore';
import { useKeyboardShortcut } from '@/hooks/useKeyboardShortcut';
import { SIDEBAR_NAVIGATION, ROUTES } from '@/lib/constants';

const iconMap: Record<string, React.ElementType> = {
  LayoutDashboard, FolderOpen, FileText, Search, GitBranch, Clock,
  Brain, Sparkles, FileBarChart, BarChart3, Settings,
};

interface PaletteItem {
  id: string;
  label: string;
  description?: string;
  icon: React.ElementType;
  category: string;
  action: () => void;
}

export function CommandPalette() {
  const { isOpen, close, toggle } = useCommandPaletteStore();
  const [query, setQuery] = useState('');
  const [activeIndex, setActiveIndex] = useState(0);
  const navigate = useNavigate();

  // Register keyboard shortcut
  useKeyboardShortcut({ key: 'k', ctrlOrMeta: true }, toggle);

  // Build items list
  const items = useMemo<PaletteItem[]>(() => {
    const navItems: PaletteItem[] = SIDEBAR_NAVIGATION.map((nav) => ({
      id: `nav-${nav.path}`,
      label: nav.label,
      description: `Navigate to ${nav.label}`,
      icon: iconMap[nav.iconName] || FileText,
      category: 'Navigation',
      action: () => { navigate(nav.path); close(); },
    }));

    navItems.push({
      id: 'nav-settings',
      label: 'Settings',
      description: 'Platform settings and preferences',
      icon: Settings,
      category: 'Navigation',
      action: () => { navigate(ROUTES.SETTINGS); close(); },
    });

    const caseItems: PaletteItem[] = ([] as any[]).slice(0, 4).map((c: any) => ({
      id: `case-${c.id}`,
      label: c.name,
      description: c.caseNumber,
      icon: FolderOpen,
      category: 'Cases',
      action: () => { navigate(ROUTES.CASES); close(); },
    }));

    const docItems: PaletteItem[] = ([] as any[]).slice(0, 4).map((d: any) => ({
      id: `doc-${d.id}`,
      label: d.name,
      description: d.caseName,
      icon: FileText,
      category: 'Documents',
      action: () => { navigate(ROUTES.DOCUMENTS); close(); },
    }));

    return [...navItems, ...caseItems, ...docItems];
  }, [navigate, close]);

  // Filter items
  const filtered = useMemo(() => {
    if (!query.trim()) return items;
    const q = query.toLowerCase();
    return items.filter(
      (item) =>
        item.label.toLowerCase().includes(q) ||
        item.description?.toLowerCase().includes(q) ||
        item.category.toLowerCase().includes(q)
    );
  }, [items, query]);

  // Group by category
  const grouped = useMemo(() => {
    const groups: Record<string, PaletteItem[]> = {};
    filtered.forEach((item) => {
      if (!groups[item.category]) groups[item.category] = [];
      groups[item.category].push(item);
    });
    return groups;
  }, [filtered]);

  // Reset state on open/close
  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setActiveIndex(0);
    }
  }, [isOpen]);

  // Keyboard navigation
  useEffect(() => {
    if (!isOpen) return;

    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setActiveIndex((i) => Math.min(i + 1, filtered.length - 1));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setActiveIndex((i) => Math.max(i - 1, 0));
      } else if (e.key === 'Enter' && filtered[activeIndex]) {
        e.preventDefault();
        filtered[activeIndex].action();
      } else if (e.key === 'Escape') {
        close();
      }
    }

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, filtered, activeIndex, close]);

  let flatIndex = -1;

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[60] bg-black/60 backdrop-blur-sm"
            onClick={close}
          />

          {/* Palette */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: -20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -20 }}
            transition={{ duration: 0.2, ease: 'easeOut' }}
            className={cn(
              'fixed z-[70] top-[20%] left-1/2 -translate-x-1/2',
              'w-[90vw] max-w-[600px]',
              'rounded-2xl border border-slate-800/80',
              'bg-slate-900/98 backdrop-blur-2xl',
              'shadow-2xl shadow-black/40 overflow-hidden'
            )}
            role="dialog"
            aria-label="Command palette"
          >
            {/* Search input */}
            <div className="flex items-center gap-3 px-4 py-3 border-b border-slate-800/50">
              <Search className="h-5 w-5 text-slate-500 shrink-0" />
              <input
                autoFocus
                type="text"
                value={query}
                onChange={(e) => { setQuery(e.target.value); setActiveIndex(0); }}
                placeholder="Search pages, cases, documents..."
                className="flex-1 bg-transparent text-sm text-slate-100 placeholder:text-slate-600 outline-none"
              />
              <kbd className="px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700 text-[10px] font-mono text-slate-500">
                ESC
              </kbd>
            </div>

            {/* Results */}
            <div className="max-h-[360px] overflow-y-auto py-2">
              {filtered.length === 0 ? (
                <div className="px-4 py-8 text-center">
                  <p className="text-sm text-slate-500">No results for "{query}"</p>
                </div>
              ) : (
                Object.entries(grouped).map(([category, categoryItems]) => (
                  <div key={category}>
                    <p className="px-4 py-1.5 text-[10px] font-bold text-slate-600 uppercase tracking-[0.15em]">
                      {category}
                    </p>
                    {categoryItems.map((item) => {
                      flatIndex++;
                      const currentIndex = flatIndex;
                      const Icon = item.icon;

                      return (
                        <button
                          key={item.id}
                          onClick={item.action}
                          onMouseEnter={() => setActiveIndex(currentIndex)}
                          className={cn(
                            'w-full flex items-center gap-3 px-4 py-2.5 text-left',
                            'transition-colors duration-100',
                            currentIndex === activeIndex
                              ? 'bg-indigo-500/10 text-indigo-300'
                              : 'text-slate-400 hover:text-slate-200'
                          )}
                        >
                          <Icon className="h-4 w-4 shrink-0" />
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium truncate">{item.label}</p>
                            {item.description && (
                              <p className="text-xs text-slate-600 truncate">{item.description}</p>
                            )}
                          </div>
                          {currentIndex === activeIndex && (
                            <ArrowRight className="h-3.5 w-3.5 text-indigo-400 shrink-0" />
                          )}
                        </button>
                      );
                    })}
                  </div>
                ))
              )}
            </div>

            {/* Footer hints */}
            <div className="flex items-center gap-4 px-4 py-2.5 border-t border-slate-800/50 text-[10px] text-slate-600">
              <span className="flex items-center gap-1">
                <kbd className="px-1 py-0.5 rounded bg-slate-800 border border-slate-700 font-mono">↑↓</kbd>
                Navigate
              </span>
              <span className="flex items-center gap-1">
                <kbd className="px-1 py-0.5 rounded bg-slate-800 border border-slate-700 font-mono">↵</kbd>
                Select
              </span>
              <span className="flex items-center gap-1">
                <kbd className="px-1 py-0.5 rounded bg-slate-800 border border-slate-700 font-mono">ESC</kbd>
                Close
              </span>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
