import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Header } from './Header';

/**
 * Main application layout with sidebar + header + content area.
 * All authenticated pages are rendered inside this layout.
 */
export function AppLayout() {
  return (
    <div className="flex min-h-screen bg-slate-950">
      <Sidebar />

      {/* Main content area — offset by sidebar width */}
      <div className="flex-1 ml-64 flex flex-col min-h-screen">
        <Header />
        <main className="flex-1 p-6 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
