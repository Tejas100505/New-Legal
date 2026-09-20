/**
 * Header organism — top bar with breadcrumbs, search, notifications, user menu.
 */

import { useState, useRef, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Bell, Menu, Moon, Sun, LogOut, User, ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';
import { ROUTE_META } from '@/lib/constants';
import { useAuthStore } from '@/features/auth/store';
import { useThemeStore } from '@/stores/themeStore';
import { useSidebarStore } from '@/stores/sidebarStore';
import { useCommandPaletteStore } from '@/stores/commandPaletteStore';
import { useIsMobile } from '@/hooks/useMediaQuery';
import { Breadcrumbs } from '@/components/molecules/Breadcrumbs';
import { SearchInput } from '@/components/molecules/SearchInput';
import { UserAvatar } from '@/components/molecules/UserAvatar';
import { Badge } from '@/components/atoms/Badge';
import { useCollaborationStore } from '@/stores/collaborationStore';
import { NotificationsDropdown } from '@/components/organisms/NotificationsDropdown';

export function Header() {
  const location = useLocation();
  const { user, logout } = useAuthStore();
  const { resolvedTheme, toggleTheme } = useThemeStore();
  const { toggleMobile } = useSidebarStore();
  const { open: openCommandPalette } = useCommandPaletteStore();
  const isMobile = useIsMobile();

  const [showNotifications, setShowNotifications] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const notifRef = useRef<HTMLDivElement>(null);
  const userRef = useRef<HTMLDivElement>(null);

  const meta = ROUTE_META[location.pathname];
  const { unreadNotificationsCount: unreadCount } = useCollaborationStore();

  // Close dropdowns on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) {
        setShowNotifications(false);
      }
      if (userRef.current && !userRef.current.contains(e.target as Node)) {
        setShowUserMenu(false);
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  return (
    <header
      className={cn(
        'sticky top-0 z-30 flex items-center justify-between h-16 px-6',
        'border-b border-slate-800/50 dark:border-slate-800/50',
        'bg-slate-950/60 dark:bg-slate-950/60 backdrop-blur-xl'
      )}
    >
      {/* ── Left: Mobile hamburger + Breadcrumbs / Title ────────── */}
      <div className="flex items-center gap-4">
        {isMobile && (
          <button
            onClick={toggleMobile}
            className="p-2 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 transition-colors"
            aria-label="Open sidebar"
          >
            <Menu className="h-5 w-5" />
          </button>
        )}
        <div>
          {location.pathname !== '/' ? (
            <Breadcrumbs />
          ) : (
            <>
              <h2 className="text-lg font-semibold text-slate-100 dark:text-slate-100">
                {meta?.title || 'Dashboard'}
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-500">
                {meta?.description || 'Agentic AI Legal Intelligence Platform'}
              </p>
            </>
          )}
        </div>
      </div>

      {/* ── Right: Search, Theme, Notifications, User ──────────── */}
      <div className="flex items-center gap-2">
        {/* Search trigger */}
        {!isMobile && (
          <SearchInput
            placeholder="Search docs..."
            shortcut="⌘K"
            readOnly
            onShortcutClick={openCommandPalette}
            className="w-56 cursor-pointer"
          />
        )}

        {/* Theme toggle */}
        <button
          onClick={toggleTheme}
          className="p-2 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 transition-colors"
          aria-label={`Switch to ${resolvedTheme === 'dark' ? 'light' : 'dark'} mode`}
          id="theme-toggle"
        >
          {resolvedTheme === 'dark' ? <Sun className="h-4.5 w-4.5" /> : <Moon className="h-4.5 w-4.5" />}
        </button>

        {/* Notifications */}
        <div ref={notifRef} className="relative">
          <button
            onClick={() => { setShowNotifications(!showNotifications); setShowUserMenu(false); }}
            className="relative p-2 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 transition-colors"
            id="notifications-button"
            aria-label={`Notifications (${unreadCount} unread)`}
          >
            <Bell className="h-4.5 w-4.5" />
            {unreadCount > 0 && (
              <span className="absolute top-1.5 right-1.5 h-2 w-2 rounded-full bg-indigo-500 ring-2 ring-slate-950" />
            )}
          </button>

          <NotificationsDropdown show={showNotifications} />
        </div>

        {/* User Menu */}
        <div ref={userRef} className="relative">
          <button
            onClick={() => { setShowUserMenu(!showUserMenu); setShowNotifications(false); }}
            className="flex items-center gap-2 p-1.5 rounded-lg hover:bg-slate-800/50 transition-colors"
            id="user-menu-button"
            aria-label="User menu"
          >
            <UserAvatar name={user?.name || 'User'} size="sm" showStatus status="online" />
            {!isMobile && (
              <>
                <div className="text-left hidden lg:block">
                  <p className="text-xs font-medium text-slate-200 truncate max-w-[120px]">
                    {user?.name || 'Lawyer'}
                  </p>
                  <p className="text-[10px] text-slate-500 truncate max-w-[120px]">
                    {user?.firm || 'Law Firm'}
                  </p>
                </div>
                <ChevronDown className="h-3.5 w-3.5 text-slate-500" />
              </>
            )}
          </button>

          <AnimatePresence>
            {showUserMenu && (
              <motion.div
                initial={{ opacity: 0, y: -10, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: -10, scale: 0.95 }}
                transition={{ duration: 0.2 }}
                className={cn(
                  'absolute right-0 top-12 w-64',
                  'rounded-xl border border-slate-800/80',
                  'bg-slate-900/95 dark:bg-slate-900/95 backdrop-blur-2xl',
                  'shadow-2xl shadow-black/30 z-50'
                )}
              >
                <div className="px-4 py-3 border-b border-slate-800/50">
                  <p className="text-sm font-semibold text-slate-200">{user?.name}</p>
                  <p className="text-xs text-slate-500">{user?.email}</p>
                  <Badge variant="purple" size="xs" className="mt-1.5">Lawyer</Badge>
                </div>
                <div className="py-1">
                  <button className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-slate-400 hover:text-slate-200 hover:bg-slate-800/30 transition-colors">
                    <User className="h-4 w-4" />
                    <span>Profile</span>
                  </button>
                  <button
                    onClick={logout}
                    className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-red-400 hover:text-red-300 hover:bg-red-500/5 transition-colors"
                  >
                    <LogOut className="h-4 w-4" />
                    <span>Sign Out</span>
                  </button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </header>
  );
}
