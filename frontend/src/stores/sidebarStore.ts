/**
 * Sidebar Zustand store — manages collapse state and mobile overlay.
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface SidebarStore {
  isCollapsed: boolean;
  isMobileOpen: boolean;
  toggle: () => void;
  collapse: () => void;
  expand: () => void;
  setMobileOpen: (open: boolean) => void;
  toggleMobile: () => void;
}

export const useSidebarStore = create<SidebarStore>()(
  persist(
    (set, get) => ({
      isCollapsed: false,
      isMobileOpen: false,

      toggle: () => set({ isCollapsed: !get().isCollapsed }),
      collapse: () => set({ isCollapsed: true }),
      expand: () => set({ isCollapsed: false }),
      setMobileOpen: (open: boolean) => set({ isMobileOpen: open }),
      toggleMobile: () => set({ isMobileOpen: !get().isMobileOpen }),
    }),
    {
      name: 'sidebar-storage',
      partialize: (state) => ({ isCollapsed: state.isCollapsed }),
    }
  )
);
