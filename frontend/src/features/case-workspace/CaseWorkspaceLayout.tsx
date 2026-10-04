import { useEffect, useState, useCallback } from 'react';
import { useParams, NavLink, Outlet, Link, useNavigate, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  ArrowLeft, LayoutDashboard, Files, ShieldAlert,
  Sparkles, GitBranch, Clock, MessageSquare, FileBarChart,
  AlertCircle, RefreshCw
} from 'lucide-react';
import api from '@/lib/api';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/atoms/Badge';
import { Spinner } from '@/components/atoms/Spinner';
import type { LegalCase, CaseStatus } from '@/types';
import { CaseWorkspaceContext } from './CaseWorkspaceContext';

const CASE_TABS = [
  { id: 'overview', label: 'Overview', path: 'overview', icon: LayoutDashboard },
  { id: 'evidence', label: 'Evidence', path: 'evidence', icon: Files },
  { id: 'review', label: 'Review', path: 'review', icon: ShieldAlert },
  { id: 'findings', label: 'Findings', path: 'findings', icon: Sparkles },
  { id: 'relationships', label: 'Relationships', path: 'relationships', icon: GitBranch },
  { id: 'timeline', label: 'Timeline', path: 'timeline', icon: Clock },
  { id: 'ask', label: 'Ask', path: 'ask', icon: MessageSquare },
  { id: 'report', label: 'Report', path: 'report', icon: FileBarChart },
] as const;

export function CaseWorkspaceLayout() {
  const { caseId } = useParams<{ caseId: string }>();
  const navigate = useNavigate();
  const location = useLocation();

  const [caseData, setCaseData] = useState<LegalCase | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (caseId && (location.pathname === `/cases/${caseId}` || location.pathname === `/cases/${caseId}/`)) {
      navigate(`/cases/${caseId}/overview`, { replace: true });
    }
  }, [caseId, location.pathname, navigate]);

  const fetchCase = useCallback(async () => {
    if (!caseId) {
      setError('No case identifier provided in route.');
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await api.get(`/cases/${caseId}`);
      const c = response.data;
      const mappedCase: LegalCase = {
        id: c.id,
        name: c.name,
        caseNumber: c.case_number || `CASE-${c.id.slice(0, 8).toUpperCase()}`,
        description: c.description || '',
        status: c.status as CaseStatus,
        priority: c.priority || 'high',
        riskLevel: c.risk_level || 'none',
        client: c.client || '',
        assignedTo: c.assigned_to || '',
        documentCount: c.document_count || 0,
        evidenceCount: c.evidence_count || 0,
        createdAt: c.created_at,
        updatedAt: c.updated_at,
        dueDate: c.due_date || '',
        tags: c.tags || [],
      };
      setCaseData(mappedCase);
    } catch (err: any) {
      const status = err?.response?.status;
      if (status === 404) {
        setError(`Case with ID "${caseId}" was not found.`);
      } else if (status === 403) {
        setError('Access denied: You do not have permission to view this case.');
      } else {
        setError(err?.response?.data?.detail || err?.message || 'Failed to load case metadata.');
      }
    } finally {
      setIsLoading(false);
    }
  }, [caseId]);

  useEffect(() => {
    fetchCase();
  }, [fetchCase]);

  const priorityVariant = caseData?.priority === 'critical' ? 'danger'
    : caseData?.priority === 'high' ? 'warning'
    : caseData?.priority === 'medium' ? 'info'
    : 'default';

  const statusVariant = caseData?.status === 'completed' ? 'success'
    : caseData?.status === 'in_progress' ? 'warning'
    : caseData?.status === 'under_review' ? 'purple'
    : caseData?.status === 'created' ? 'info'
    : 'default';

  const activeTabObj = CASE_TABS.find((t) => location.pathname.includes(`/${t.path}`)) || CASE_TABS[0];
  const currentSectionName = activeTabObj.label;

  return (
    <CaseWorkspaceContext.Provider
      value={{
        caseData,
        isLoading,
        error,
        caseId: caseId || '',
        refetchCase: fetchCase,
      }}
    >
      <div className="space-y-4">
        {/* Top Case Header */}
        <div className="rounded-2xl bg-gradient-to-r from-slate-900/90 via-slate-900/60 to-slate-950/90 border border-slate-800/80 p-5 shadow-lg backdrop-blur-xl">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="space-y-1.5">
              <div className="flex flex-wrap items-center gap-2">
                <nav aria-label="Case Breadcrumb" className="inline-flex items-center gap-1.5 text-xs text-slate-400 mr-2">
                  <Link
                    to="/cases"
                    className="inline-flex items-center gap-1 text-slate-400 hover:text-indigo-400 font-medium transition-colors"
                    id="case-back-link"
                  >
                    <ArrowLeft className="h-3 w-3" />
                    <span>Cases</span>
                  </Link>
                  <span className="text-slate-600">/</span>
                  <Link
                    to={`/cases/${caseId}/overview`}
                    className="text-slate-400 hover:text-indigo-400 font-medium transition-colors max-w-[200px] sm:max-w-[320px] truncate"
                    id="case-breadcrumb-name"
                    title={caseData?.name || 'Case Overview'}
                  >
                    {caseData?.name || (isLoading ? 'Loading...' : 'Case Overview')}
                  </Link>
                  <span className="text-slate-600">/</span>
                  <span className="text-indigo-400 font-semibold" aria-current="page" id="case-breadcrumb-section">
                    {currentSectionName}
                  </span>
                </nav>

                {caseData && (
                  <div className="flex items-center gap-1.5">
                    <Badge variant={statusVariant} size="xs" dot>
                      {caseData.status.replace(/_/g, ' ').toUpperCase()}
                    </Badge>
                    <Badge variant={priorityVariant} size="xs">
                      {caseData.priority.toUpperCase()} PRIORITY
                    </Badge>
                  </div>
                )}
              </div>

              <div className="flex items-center gap-3">
                <h1 className="text-xl font-bold text-slate-100 tracking-tight" id="case-workspace-title">
                  {caseData?.name || (isLoading ? 'Loading case...' : 'Case Workspace')}
                </h1>
                {caseData?.caseNumber && (
                  <span className="text-xs font-mono text-slate-400 px-2 py-0.5 rounded bg-slate-800/60 border border-slate-700/50">
                    {caseData.caseNumber}
                  </span>
                )}
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={fetchCase}
                disabled={isLoading}
                className="p-2 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 transition-colors"
                title="Refresh case metadata"
                aria-label="Refresh case"
              >
                <RefreshCw className={cn('h-4 w-4', isLoading && 'animate-spin')} />
              </button>
            </div>
          </div>

          {/* 8-Tab Horizontal Navigation Bar */}
          <div className="mt-5 border-t border-slate-800/60 pt-2 -mb-1 overflow-x-auto scrollbar-none">
            <nav className="flex items-center gap-1 min-w-max" aria-label="Case workspace tabs">
              {CASE_TABS.map((tab) => {
                const Icon = tab.icon;
                return (
                  <NavLink
                    key={tab.id}
                    to={tab.path}
                    className={({ isActive }) =>
                      cn(
                        'relative flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-medium transition-all duration-200',
                        isActive
                          ? 'text-indigo-400 bg-indigo-500/10'
                          : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
                      )
                    }
                  >
                    {({ isActive }) => (
                      <>
                        <Icon className={cn('h-3.5 w-3.5', isActive ? 'text-indigo-400' : 'text-slate-400')} />
                        <span>{tab.label}</span>
                        {isActive && (
                          <motion.div
                            layoutId="case-tab-active-indicator"
                            className="absolute bottom-0 left-2 right-2 h-0.5 bg-indigo-500 rounded-full"
                            transition={{ type: 'spring', stiffness: 380, damping: 30 }}
                          />
                        )}
                      </>
                    )}
                  </NavLink>
                );
              })}
            </nav>
          </div>
        </div>

        {/* Content Area */}
        {isLoading && !caseData ? (
          <div className="flex h-64 items-center justify-center rounded-2xl border border-slate-800/60 bg-slate-900/30">
            <Spinner size="lg" />
          </div>
        ) : error ? (
          <div className="rounded-2xl border border-rose-500/20 bg-rose-500/10 p-6 text-center space-y-3">
            <div className="h-10 w-10 mx-auto rounded-xl bg-rose-500/20 flex items-center justify-center text-rose-400">
              <AlertCircle className="h-5 w-5" />
            </div>
            <h3 className="text-sm font-semibold text-rose-300">Unable to load case</h3>
            <p className="text-xs text-rose-400/90 max-w-md mx-auto">{error}</p>
            <div className="pt-2">
              <button
                type="button"
                onClick={() => navigate('/cases')}
                className="px-4 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition-colors"
              >
                Return to Cases
              </button>
            </div>
          </div>
        ) : (
          <Outlet />
        )}
      </div>
    </CaseWorkspaceContext.Provider>
  );
}
