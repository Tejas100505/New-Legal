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
const CaseWorkspaceLayout = React.lazy(() =>
  import('@/features/case-workspace/CaseWorkspaceLayout').then((m) => ({ default: m.CaseWorkspaceLayout }))
);
const OverviewTab = React.lazy(() =>
  import('@/features/case-workspace/tabs/OverviewTab').then((m) => ({ default: m.OverviewTab }))
);
const EvidenceTab = React.lazy(() =>
  import('@/features/case-workspace/tabs/EvidenceTab').then((m) => ({ default: m.EvidenceTab }))
);
const ReviewTab = React.lazy(() =>
  import('@/features/case-workspace/tabs/ReviewTab').then((m) => ({ default: m.ReviewTab }))
);
const FindingsTab = React.lazy(() =>
  import('@/features/case-workspace/tabs/FindingsTab').then((m) => ({ default: m.FindingsTab }))
);
const RelationshipsTab = React.lazy(() =>
  import('@/features/case-workspace/tabs/RelationshipsTab').then((m) => ({ default: m.RelationshipsTab }))
);
const TimelineTab = React.lazy(() =>
  import('@/features/case-workspace/tabs/TimelineTab').then((m) => ({ default: m.TimelineTab }))
);
const AskTab = React.lazy(() =>
  import('@/features/case-workspace/tabs/AskTab').then((m) => ({ default: m.AskTab }))
);
const ReportTab = React.lazy(() =>
  import('@/features/case-workspace/tabs/ReportTab').then((m) => ({ default: m.ReportTab }))
);
const DocumentViewerPage = React.lazy(() =>
  import('@/features/documents/pages/DocumentViewerPage').then((m) => ({ default: m.DocumentViewerPage }))
);
const SemanticSearchPage = React.lazy(() =>
  import('@/features/semantic-search/pages/SemanticSearchPage').then((m) => ({ default: m.SemanticSearchPage }))
);
const ReportsPage = React.lazy(() =>
  import('@/features/reports/pages/ReportsPage').then((m) => ({ default: m.ReportsPage }))
);
const SettingsPage = React.lazy(() =>
  import('@/features/settings/pages/SettingsPage').then((m) => ({ default: m.SettingsPage }))
);
const SettingsAnalyticsPage = React.lazy(() =>
  import('@/features/settings/pages/SettingsAnalyticsPage').then((m) => ({ default: m.SettingsAnalyticsPage }))
);
const SettingsAgentsPage = React.lazy(() =>
  import('@/features/settings/pages/SettingsAgentsPage').then((m) => ({ default: m.SettingsAgentsPage }))
);
const SettingsSystemPage = React.lazy(() =>
  import('@/features/settings/pages/SettingsSystemPage').then((m) => ({ default: m.SettingsSystemPage }))
);

const NotFound = React.lazy(() =>
  import('@/pages/NotFound').then((m) => ({ default: m.NotFound }))
);

// ── Route Guard: PrivateRoute ────────────────────────────────────────────────

interface PrivateRouteProps {
  children: React.ReactNode;
}

function PrivateRoute({ children }: PrivateRouteProps) {
  const { isAuthenticated, token, logout } = useAuthStore();
  const location = useLocation();

  React.useEffect(() => {
    const handleUnauthorized = () => {
      logout();
    };
    window.addEventListener('auth:unauthorized', handleUnauthorized);
    return () => window.removeEventListener('auth:unauthorized', handleUnauthorized);
  }, [logout]);

  if (!isAuthenticated || !token) {
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

            {/* Nested Case Workspace */}
            <Route path="/cases/:caseId" element={<CaseWorkspaceLayout />}>
              <Route index element={<Navigate to="overview" replace />} />
              <Route path="overview" element={<OverviewTab />} />
              <Route path="evidence" element={<EvidenceTab />} />
              <Route path="review" element={<ReviewTab />} />
              <Route path="findings" element={<FindingsTab />} />
              <Route path="relationships" element={<RelationshipsTab />} />
              <Route path="timeline" element={<TimelineTab />} />
              <Route path="ask" element={<AskTab />} />
              <Route path="report" element={<ReportTab />} />
            </Route>

            {/* Standalone Top-Level Routes */}
            <Route path="/search" element={<SemanticSearchPage />} />
            <Route path="/reports" element={<ReportsPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/settings/analytics" element={<SettingsAnalyticsPage />} />
            <Route path="/settings/agents" element={<SettingsAgentsPage />} />
            <Route path="/settings/system" element={<SettingsSystemPage />} />

            {/* Document Viewer (per-document deep view) */}
            <Route path="/documents/:id" element={<DocumentViewerPage />} />

            {/* Backward Compatibility Redirects */}
            <Route path="/investigation" element={<Navigate to="/cases" replace />} />
            <Route path="/knowledge-graph" element={<Navigate to="/cases" replace />} />
            <Route path="/timeline" element={<Navigate to="/cases" replace />} />
            <Route path="/ai-review" element={<Navigate to="/cases" replace />} />
            <Route path="/analytics" element={<Navigate to="/settings/analytics" replace />} />
            <Route path="/agents" element={<Navigate to="/settings/agents" replace />} />
            <Route path="/documents" element={<Navigate to="/cases" replace />} />

            <Route path="*" element={<NotFound />} />
          </Route>
        </Routes>
      </Suspense>
    </ErrorBoundary>
  );
}
