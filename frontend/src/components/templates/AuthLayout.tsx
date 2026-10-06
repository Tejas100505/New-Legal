/**
 * AuthLayout template — centered layout for login page.
 */

import { Outlet, Navigate } from 'react-router-dom';
import { useAuthStore } from '@/features/auth/store';

export function AuthLayout() {
  const { isAuthenticated } = useAuthStore();

  if (isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center relative overflow-hidden">
      {/* Animated gradient background */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute -top-[40%] -left-[20%] w-[80%] h-[80%] rounded-full bg-indigo-500/5 blur-[120px] animate-pulse" />
        <div className="absolute -bottom-[40%] -right-[20%] w-[80%] h-[80%] rounded-full bg-violet-500/5 blur-[120px] animate-pulse" style={{ animationDelay: '1s' }} />
        <div className="absolute top-[20%] right-[10%] w-[40%] h-[40%] rounded-full bg-cyan-500/3 blur-[100px] animate-pulse" style={{ animationDelay: '2s' }} />
      </div>

      {/* Grid pattern */}
      <div className="absolute inset-0 bg-grid-pattern opacity-20" />

      {/* Content */}
      <div className="relative z-10 w-full max-w-md mx-4">
        <Outlet />
      </div>
    </div>
  );
}
