import React, { Suspense } from 'react';
import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '@/features/auth/store';
import { DashboardLayout } from '@/components/templates/DashboardLayout';
import { AuthLayout } from '@/components/templates/AuthLayout';
import { Spinner } from '@/components/atoms/Spinner';

// ── Lazy Loaded Pages ────────────────────────────────────────────────────────

const LoginPage = React.lazy(() =>
  import('@/features/auth/pages/LoginPage').then((m) => ({ default: m.LoginPage }))
);
const DashboardPage = React.lazy(() =>
  import('@/features/dashboard/pages/DashboardPage').then((m) => ({ default: m.DashboardPage }))
);
const CasesPage = React.lazy(() =>
  import('@/features/cases/pages/CasesPage').then((m) => ({ default: m.CasesPage }))
);
const DocumentsPage = React.lazy(() =>
  import('@/features/documents/pages/DocumentsPage').then((m) => ({ default: m.DocumentsPage }))
);
const DocumentViewerPage = React.lazy(() =>
  import('@/features/documents/pages/DocumentViewerPage').then((m) => ({ default: m.DocumentViewerPage }))
);
const InvestigationPage = React.lazy(() =>
  import('@/features/investigation/pages/InvestigationPage').then((m) => ({ default: m.InvestigationPage }))
);
const KnowledgeGraphPage = React.lazy(() =>
  import('@/features/knowledge-graph/pages/KnowledgeGraphPage').then((m) => ({ default: m.KnowledgeGraphPage }))
);
const TimelinePage = React.lazy(() =>
  import('@/features/timeline/pages/TimelinePage').then((m) => ({ default: m.TimelinePage }))
);
const AIReviewPage = React.lazy(() =>
  import('@/features/ai-review/pages/AIReviewPage').then((m) => ({ default: m.AIReviewPage }))
);
const SemanticSearchPage = React.lazy(() =>
  import('@/features/semantic-search/pages/SemanticSearchPage').then((m) => ({ default: m.SemanticSearchPage }))
);
const ReportsPage = React.lazy(() =>
  import('@/features/reports/pages/ReportsPage').then((m) => ({ default: m.ReportsPage }))
);
const AnalyticsPage = React.lazy(() =>
  import('@/features/analytics/pages/AnalyticsPage').then((m) => ({ default: m.AnalyticsPage }))
);
const SettingsPage = React.lazy(() =>
  import('@/features/settings/pages/SettingsPage').then((m) => ({ default: m.SettingsPage }))
);
const AgentsPage = React.lazy(() =>
  import('@/features/agents/pages/AgentsPage').then((m) => ({ default: m.AgentsPage }))
);
const NotFound = React.lazy(() =>
  import('@/pages/NotFound').then((m) => ({ default: m.NotFound }))
);

// ── Route Guard: PrivateRoute ────────────────────────────────────────────────

interface PrivateRouteProps {
  children: React.ReactNode;
}

function PrivateRoute({ children }: PrivateRouteProps) {
  const { isAuthenticated } = useAuthStore();
  const location = useLocation();

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
}

// ── Error Boundary Fallback ──────────────────────────────────────────────────

class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { hasError: boolean; error: Error | null }
> {
  constructor(props: { children: React.ReactNode }) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('ErrorBoundary caught an error', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-6 text-center">
          <div className="h-16 w-16 rounded-2xl bg-red-500/10 flex items-center justify-center mb-4 text-red-400">
            <svg className="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <h2 className="text-xl font-bold text-slate-100 mb-2">Something went wrong</h2>
          <p className="text-sm text-slate-500 max-w-md mb-6">
            An unexpected error occurred in the application layer. Please reload the page or return to safety.
          </p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 rounded-lg bg-indigo-500 hover:bg-indigo-600 text-white text-sm font-semibold transition-colors"
          >
            Reload Application
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

// ── Loading Fallback ─────────────────────────────────────────────────────────

function PageLoading() {
  return (
    <div className="flex h-[50vh] w-full items-center justify-center">
      <Spinner size="lg" />
    </div>
  );
}

// ── Root App Component ───────────────────────────────────────────────────────

export default function App() {
  return (
    <ErrorBoundary>
      <Suspense fallback={<PageLoading />}>
        <Routes>
          {/* Auth Route */}
          <Route element={<AuthLayout />}>
            <Route path="/login" element={<LoginPage />} />
          </Route>

          {/* Authenticated Dashboard Routes */}
          <Route
            element={
              <PrivateRoute>
                <DashboardLayout />
              </PrivateRoute>
            }
          >
            <Route path="/" element={<DashboardPage />} />
            <Route path="/cases" element={<CasesPage />} />
            <Route path="/documents" element={<DocumentsPage />} />
            <Route path="/documents/:id" element={<DocumentViewerPage />} />
            <Route path="/investigation" element={<InvestigationPage />} />
            <Route path="/knowledge-graph" element={<KnowledgeGraphPage />} />
            <Route path="/timeline" element={<TimelinePage />} />
            <Route path="/ai-review" element={<AIReviewPage />} />
            <Route path="/search" element={<SemanticSearchPage />} />
            <Route path="/reports" element={<ReportsPage />} />
            <Route path="/analytics" element={<AnalyticsPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/agents" element={<AgentsPage />} />
            <Route path="*" element={<NotFound />} />
          </Route>
        </Routes>
      </Suspense>
    </ErrorBoundary>
  );
}
