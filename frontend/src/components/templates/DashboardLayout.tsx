/**
 * DashboardLayout template — main app layout with sidebar + header + content.
 */

import { Outlet } from 'react-router-dom';
import { cn } from '@/lib/utils';
import { useSidebarStore } from '@/stores/sidebarStore';
import { useIsMobile } from '@/hooks/useMediaQuery';
import { Sidebar } from '@/components/organisms/Sidebar';
import { Header } from '@/components/organisms/Header';
import { CommandPalette } from '@/components/organisms/CommandPalette';

export function DashboardLayout() {
  const { isCollapsed } = useSidebarStore();
  const isMobile = useIsMobile();

  return (
    <div className="flex min-h-screen bg-slate-950 dark:bg-slate-950">
      <Sidebar />
      <CommandPalette />

      {/* Main content area — offset by sidebar width */}
      <div
        className={cn(
          'flex-1 flex flex-col min-h-screen transition-all duration-300',
          isMobile ? 'ml-0' : isCollapsed ? 'ml-[68px]' : 'ml-64'
        )}
      >
        <Header />
        <main className="flex-1 p-4 md:p-6 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
