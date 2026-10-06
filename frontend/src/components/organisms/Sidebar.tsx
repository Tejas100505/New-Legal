/**
 * Sidebar organism — professional collapsible sidebar with 11 navigation items.
 * Uses Zustand for state management, Framer Motion for animations.
 */

import { useState, useEffect } from 'react';
import { NavLink } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import api from '@/lib/api';
import { useSidebarStore } from '@/stores/sidebarStore';
import { useAuthStore } from '@/features/auth/store';
import { useIsMobile } from '@/hooks/useMediaQuery';
import { Logo } from '@/components/atoms/Logo';
import { Badge } from '@/components/atoms/Badge';
import { Tooltip } from '@/components/atoms/Tooltip';
import { SIDEBAR_NAVIGATION, ROUTES, type SidebarNavItem } from '@/lib/constants';
import {
  LayoutDashboard, FolderOpen, FileText, Search, GitBranch, Clock,
  Brain, Sparkles, FileBarChart, BarChart3, Settings,
  ChevronLeft, ChevronRight, X,
} from 'lucide-react';

const iconMap: Record<string, React.ElementType> = {
  LayoutDashboard, FolderOpen, FileText, Search, GitBranch, Clock,
  Brain, Sparkles, FileBarChart, BarChart3, Settings,
};

const sectionLabels: Record<string, string> = {
  main: 'Navigation',
};

function NavItemLink({ item, collapsed }: { item: SidebarNavItem; collapsed: boolean }) {
  const Icon = iconMap[item.iconName] || FileText;
  const badgeVariantMap: Record<string, 'default' | 'success' | 'warning' | 'danger'> = {
    default: 'default',
    success: 'success',
    warning: 'warning',
    danger: 'danger',
  };

  const link = (
    <NavLink
      to={item.path}
      end={item.path === '/'}
      className={({ isActive }) =>
        cn(
          'group relative flex items-center gap-3 px-3 py-2.5 rounded-xl',
          'text-sm font-medium transition-all duration-200',
          isActive
            ? 'bg-indigo-500/10 text-indigo-400 shadow-sm shadow-indigo-500/5'
            : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
        )
      }
      aria-label={item.label}
    >
      {({ isActive }) => (
        <>
          {isActive && (
            <motion.div
              layoutId="sidebar-active-indicator"
              className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 rounded-r-full bg-indigo-500"
              transition={{ type: 'spring', stiffness: 350, damping: 30 }}
            />
          )}
          <Icon className={cn('h-[18px] w-[18px] shrink-0', isActive ? 'text-indigo-400' : '')} />
          {!collapsed && (
            <motion.span
              initial={{ opacity: 0, width: 0 }}
              animate={{ opacity: 1, width: 'auto' }}
              exit={{ opacity: 0, width: 0 }}
              className="truncate"
            >
              {item.label}
            </motion.span>
          )}
          {!collapsed && item.badge && (
            <Badge
              variant={badgeVariantMap[item.badgeVariant || 'default']}
              size="xs"
              className="ml-auto"
            >
              {item.badge}
            </Badge>
          )}
        </>
      )}
    </NavLink>
  );

  if (collapsed) {
    return (
      <Tooltip content={item.label} side="right">
        {link}
      </Tooltip>
    );
  }

  return link;
}

export function Sidebar() {
  const { isCollapsed, isMobileOpen, toggle, setMobileOpen } = useSidebarStore();
  const isMobile = useIsMobile();
  const { isAuthenticated, token } = useAuthStore();
  const [counts, setCounts] = useState<{ cases?: number }>({});

  useEffect(() => {
    if (!isAuthenticated || !token) return;
    let isMounted = true;
    async function fetchCounts() {
      try {
        const casesRes = await api.get('/cases?page_size=1', {
          suppressErrorToast: true,
        } as any);
        if (!isMounted) return;
        if (casesRes.data?.total !== undefined) {
          setCounts({ cases: casesRes.data.total });
        }
      } catch {
        // Silently catch in background
      }
    }

    fetchCounts();
    const interval = setInterval(fetchCounts, 15000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [isAuthenticated, token]);

  const getDynamicBadge = (item: SidebarNavItem): string | undefined => {
    if (item.label === 'Cases') {
      return counts.cases !== undefined ? String(counts.cases) : undefined;
    }
    return item.badge;
  };

  // Close mobile sidebar on navigation
  const handleNavClick = () => {
    if (isMobile) setMobileOpen(false);
  };

  // Group nav items by section
  const sections = SIDEBAR_NAVIGATION.reduce<Record<string, SidebarNavItem[]>>((acc, item) => {
    if (!acc[item.section]) acc[item.section] = [];
    acc[item.section].push(item);
    return acc;
  }, {});

  const sidebarContent = (
    <aside
      className={cn(
        'flex flex-col h-full',
        'bg-slate-950/90 backdrop-blur-2xl',
        'border-r border-slate-800/50',
        'transition-all duration-300 ease-out'
      )}
      onClick={handleNavClick}
    >
      {/* ── Brand ──────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between px-4 py-5 border-b border-slate-800/50">
        <Logo collapsed={isCollapsed && !isMobile} />
        {isMobile && (
          <button
            onClick={() => setMobileOpen(false)}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 transition-colors"
            aria-label="Close sidebar"
          >
            <X className="h-5 w-5" />
          </button>
        )}
      </div>

      {/* ── Navigation ─────────────────────────────────────────────── */}
      <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-6" aria-label="Main navigation">
        {Object.entries(sections).map(([section, items]) => (
          <div key={section}>
            {!isCollapsed && (
              <p className="px-3 mb-2 text-[10px] font-bold text-slate-600 uppercase tracking-[0.15em]">
                {sectionLabels[section] || section}
              </p>
            )}
            <div className="space-y-0.5">
              {items.map((item) => (
                <NavItemLink
                  key={item.path}
                  item={{ ...item, badge: getDynamicBadge(item) }}
                  collapsed={isCollapsed && !isMobile}
                />
              ))}
            </div>
          </div>
        ))}
      </nav>

      {/* ── Settings & Collapse ────────────────────────────────────── */}
      <div className="border-t border-slate-800/50 px-3 py-3 space-y-0.5">
        <NavItemLink
          item={{ label: 'Settings', path: ROUTES.SETTINGS, iconName: 'Settings', section: 'main' } as SidebarNavItem}
          collapsed={isCollapsed && !isMobile}
        />
        {!isMobile && (
          <button
            onClick={(e) => { e.stopPropagation(); toggle(); }}
            className={cn(
              'w-full flex items-center gap-3 px-3 py-2.5 rounded-xl',
              'text-sm font-medium text-slate-400 hover:text-slate-200 hover:bg-slate-800/50',
              'transition-all duration-200'
            )}
            id="sidebar-toggle"
            aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {isCollapsed ? (
              <ChevronRight className="h-[18px] w-[18px] shrink-0" />
            ) : (
              <>
                <ChevronLeft className="h-[18px] w-[18px] shrink-0" />
                <span className="truncate">Collapse</span>
              </>
            )}
          </button>
        )}
      </div>
    </aside>
  );

  // Mobile: overlay drawer
  if (isMobile) {
    return (
      <AnimatePresence>
        {isMobileOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm"
              onClick={() => setMobileOpen(false)}
            />
            <motion.div
              initial={{ x: -280 }}
              animate={{ x: 0 }}
              exit={{ x: -280 }}
              transition={{ type: 'spring', stiffness: 300, damping: 30 }}
              className="fixed left-0 top-0 z-50 h-screen w-[280px]"
            >
              {sidebarContent}
            </motion.div>
          </>
        )}
      </AnimatePresence>
    );
  }

  // Desktop: fixed sidebar
  return (
    <div
      className={cn(
        'fixed left-0 top-0 z-40 h-screen',
        'transition-all duration-300 ease-out',
        isCollapsed ? 'w-[68px]' : 'w-64'
      )}
    >
      {sidebarContent}
    </div>
  );
}
