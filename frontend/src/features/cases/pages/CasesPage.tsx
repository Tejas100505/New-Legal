/**
 * CasesPage — Legal Matter Management Dashboard.
 *
 * Professional e-discovery matter portal with real-time case telemetry,
 * workload summary strip, multi-facet filtering, full-text search,
 * sorting controls, and seamless New Case wizard integration.
 */

import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  Plus, FileText, Search,
  ArrowRight, Loader2, ShieldCheck, Flag,
  Briefcase, Building2, AlertTriangle, Lock,
  ShieldAlert, Clock, X, SlidersHorizontal, CheckCircle2,
  FolderOpen, Hash,
} from 'lucide-react';
import { cn, formatDate } from '@/lib/utils';
import { PageShell } from '@/components/templates/PageShell';
import { Badge } from '@/components/atoms/Badge';
import { ShareCaseModal } from '../components/ShareCaseModal';
import { NewCaseModal } from '../components/NewCaseModal';
import type { LegalCase, CaseStatus, CasePriority } from '@/types';
import api from '@/lib/api';

type FilterTab = 'all' | 'active' | 'processing' | 'needs_review' | 'completed';
type SortOption = 'last_activity' | 'recently_created' | 'document_count' | 'needs_attention';

const priorityVariants: Record<CasePriority, 'danger' | 'warning' | 'info' | 'success'> = {
  critical: 'danger',
  high: 'warning',
  medium: 'info',
  low: 'success',
};

function getCaseWorkflowStatus(c: LegalCase): {
  label: string;
  variant: 'default' | 'success' | 'warning' | 'danger' | 'info' | 'purple' | 'outline';
  dot?: boolean;
  pulse?: boolean;
} {
  const docCount = c.documentCount ?? 0;
  const processingCount = c.processingCount ?? 0;
  const flaggedCount = c.flaggedCount ?? 0;
  const highRiskCount = c.highRiskCount ?? 0;
  const reviewedCount = c.reviewedCount ?? 0;

  if (docCount === 0) {
    return { label: 'Awaiting Evidence', variant: 'outline', dot: true };
  }
  if (processingCount > 0) {
    return { label: 'Processing Evidence', variant: 'info', dot: true, pulse: true };
  }
  if (c.status === 'completed' || (docCount > 0 && reviewedCount === docCount && processingCount === 0)) {
    return { label: 'Completed', variant: 'success', dot: true };
  }
  if (flaggedCount > 0 || highRiskCount > 0) {
    return { label: 'Needs Attention', variant: 'warning', dot: true };
  }
  if (docCount > 0 && reviewedCount < docCount) {
    return { label: 'Needs Review', variant: 'purple', dot: true };
  }
  return { label: 'Active', variant: 'info', dot: true };
}

function caseNeedsAttention(c: LegalCase): boolean {
  const flagged = c.flaggedCount ?? 0;
  const highRisk = c.highRiskCount ?? 0;
  const processing = c.processingCount ?? 0;
  const docs = c.documentCount ?? 0;
  const reviewed = c.reviewedCount ?? 0;
  return flagged > 0 || highRisk > 0 || processing > 0 || (docs > 0 && reviewed < docs);
}

export function CasesPage() {
  const navigate = useNavigate();

  // Search & Filter state
  const [searchQuery, setSearchQuery] = useState('');
  const [activeTab, setActiveTab] = useState<FilterTab>('all');
  const [sortBy, setSortBy] = useState<SortOption>('last_activity');

  // Modals
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [shareCaseId, setShareCaseId] = useState<string | null>(null);
  const [shareCaseName, setShareCaseName] = useState<string>('');

  // Data loading state
  const [cases, setCases] = useState<LegalCase[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    fetchCases();
  }, []);

  async function fetchCases() {
    setIsLoading(true);
    try {
      const firstPageRes = await api.get('/cases?page=1&page_size=100');
      const totalCases = firstPageRes.data?.total || 0;
      let casesList = firstPageRes.data?.cases || [];

      if (totalCases > 100) {
        const remainingPages = Math.ceil(totalCases / 100);
        const pageReqs = [];
        for (let p = 2; p <= remainingPages; p++) {
          pageReqs.push(api.get(`/cases?page=${p}&page_size=100`).catch(() => ({ data: { cases: [] } })));
        }
        const extraRes = await Promise.all(pageReqs);
        for (const res of extraRes) {
          if (res.data?.cases) {
            casesList = casesList.concat(res.data.cases);
          }
        }
      }

      // Map API response to expected LegalCase format using real case telemetry
      const mapped: LegalCase[] = casesList.map((c: any) => {
        return {
          id: c.id,
          name: c.name,
          caseNumber: c.case_number || (c.id ? `CASE-${c.id.split('-')[0].toUpperCase()}` : 'CASE-UNKNOWN'),
          matterNumber: c.matter_number || undefined,
          client: c.client || '',
          caseType: c.case_type || '',
          description: c.description || '',
          status: c.status as CaseStatus,
          priority: (c.priority || 'medium') as CasePriority,
          riskLevel: (c.risk_level || 'none') as any,
          createdAt: c.created_at,
          updatedAt: c.updated_at,
          tags: c.tags || [],
          documentCount: c.document_count ?? 0,
          evidenceCount: c.document_count ?? 0,
          reviewedCount: c.reviewed_count ?? 0,
          flaggedCount: c.flagged_count ?? 0,
          privilegedCount: c.privileged_count ?? 0,
          highRiskCount: c.high_risk_count ?? 0,
          processingCount: c.processing_count ?? 0,
          lastActivity: c.last_activity || c.updated_at || c.created_at,
          assignedTo: c.assigned_to || '',
          dueDate: c.due_date || '',
        };
      });
      setCases(mapped);
    } catch (err) {
      console.error('Failed to load cases:', err);
    } finally {
      setIsLoading(false);
    }
  }

  async function handleDeleteCase(caseId: string, e: React.MouseEvent) {
    e.stopPropagation();
    if (!window.confirm('Are you sure you want to delete this legal matter and all associated evidence?')) return;
    try {
      await api.delete(`/cases/${caseId}`);
      fetchCases();
    } catch (err) {
      console.error('Failed to delete case:', err);
    }
  }

  // Workload summary strip calculations (derived strictly from real case data)
  const metrics = useMemo(() => {
    const total = cases.length;
    const active = cases.filter(c => c.status !== 'completed' && c.status !== 'archived').length;
    const processingCases = cases.filter(c => (c.processingCount ?? 0) > 0).length;
    const totalProcessingDocs = cases.reduce((acc, c) => acc + (c.processingCount ?? 0), 0);
    const needsReview = cases.filter(c => caseNeedsAttention(c)).length;
    const completed = cases.filter(c => c.status === 'completed' || (c.documentCount > 0 && (c.reviewedCount ?? 0) === c.documentCount && (c.processingCount ?? 0) === 0)).length;

    return { total, active, processingCases, totalProcessingDocs, needsReview, completed };
  }, [cases]);

  // Filtered and sorted case list
  const filteredAndSortedCases = useMemo(() => {
    return cases
      .filter((c) => {
        // Tab filtering
        if (activeTab === 'active') {
          if (c.status === 'completed' || c.status === 'archived') return false;
        } else if (activeTab === 'processing') {
          if ((c.processingCount ?? 0) === 0) return false;
        } else if (activeTab === 'needs_review') {
          if (!caseNeedsAttention(c)) return false;
        } else if (activeTab === 'completed') {
          const isCompleted = c.status === 'completed' || (c.documentCount > 0 && (c.reviewedCount ?? 0) === c.documentCount && (c.processingCount ?? 0) === 0);
          if (!isCompleted) return false;
        }

        // Full-text search across matter metadata
        if (searchQuery.trim()) {
          const q = searchQuery.toLowerCase().trim();
          const nameMatch = c.name?.toLowerCase().includes(q);
          const matterMatch = c.matterNumber?.toLowerCase().includes(q) || c.caseNumber?.toLowerCase().includes(q);
          const clientMatch = c.client?.toLowerCase().includes(q);
          const typeMatch = c.caseType?.toLowerCase().includes(q);
          const descMatch = c.description?.toLowerCase().includes(q);
          if (!nameMatch && !matterMatch && !clientMatch && !typeMatch && !descMatch) {
            return false;
          }
        }

        return true;
      })
      .sort((a, b) => {
        if (sortBy === 'last_activity') {
          const timeA = new Date(a.lastActivity || a.updatedAt || a.createdAt || 0).getTime();
          const timeB = new Date(b.lastActivity || b.updatedAt || b.createdAt || 0).getTime();
          return timeB - timeA;
        }
        if (sortBy === 'recently_created') {
          const timeA = new Date(a.createdAt || 0).getTime();
          const timeB = new Date(b.createdAt || 0).getTime();
          return timeB - timeA;
        }
        if (sortBy === 'document_count') {
          return (b.documentCount ?? 0) - (a.documentCount ?? 0);
        }
        if (sortBy === 'needs_attention') {
          const weightA = (a.flaggedCount ?? 0) * 10 + (a.highRiskCount ?? 0) * 10 + (a.processingCount ?? 0) * 2 + ((a.documentCount ?? 0) - (a.reviewedCount ?? 0));
          const weightB = (b.flaggedCount ?? 0) * 10 + (b.highRiskCount ?? 0) * 10 + (b.processingCount ?? 0) * 2 + ((b.documentCount ?? 0) - (b.reviewedCount ?? 0));
          return weightB - weightA;
        }
        return 0;
      });
  }, [cases, activeTab, searchQuery, sortBy]);

  return (
    <PageShell
      title="Cases"
      description="Your legal matters and investigations"
      actions={
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowCreateModal(true)}
            id="new-case-header-btn"
            className={cn(
              'flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold',
              'bg-indigo-600 hover:bg-indigo-500 text-white',
              'shadow-lg shadow-indigo-600/25 hover:shadow-indigo-500/40',
              'transition-all duration-200 cursor-pointer'
            )}
          >
            <Plus className="h-4 w-4" />
            <span>New Case</span>
          </button>
        </div>
      }
    >
      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-24 text-slate-500">
          <Loader2 className="h-8 w-8 animate-spin mb-3 text-indigo-500" />
          <p className="text-sm font-medium">Loading legal matters and telemetry...</p>
        </div>
      ) : cases.length === 0 ? (
        /* Empty state: 0 cases in entire database */
        <div className="text-center py-20 px-6 rounded-2xl border border-dashed border-slate-800 bg-slate-900/30">
          <div className="h-14 w-14 rounded-2xl bg-indigo-500/10 flex items-center justify-center text-indigo-400 mx-auto mb-4">
            <FolderOpen className="h-7 w-7" />
          </div>
          <h3 className="text-lg font-bold text-slate-100 mb-1.5">No legal matters yet</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto mb-6 leading-relaxed">
            Create a matter and upload your evidence to begin an e-discovery investigation with real-time entity extraction, timeline synthesis, and question answering.
          </p>
          <button
            onClick={() => setShowCreateModal(true)}
            id="empty-create-case-btn"
            className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold shadow-lg shadow-indigo-600/30 transition-all cursor-pointer"
          >
            + Create New Case
          </button>
        </div>
      ) : cases.length === 1 ? (
        /* Single prominent legal matter card matching Phase 7E spec */
        <div className="max-w-5xl mx-auto py-2">
          {(() => {
            const c = cases[0];
            const statusConfig = getCaseWorkflowStatus(c);
            return (
              <motion.div
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.25 }}
              >
                <div
                  onClick={() => navigate(`/cases/${c.id}/overview`)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      navigate(`/cases/${c.id}/overview`);
                    }
                  }}
                  aria-label={`Open legal matter ${c.name}`}
                  className="group relative flex flex-col justify-between rounded-3xl p-8 text-left bg-slate-900/60 backdrop-blur-2xl border border-slate-800/80 hover:border-indigo-500/50 shadow-2xl shadow-indigo-500/5 hover:shadow-indigo-500/10 hover:-translate-y-0.5 transition-all duration-300 cursor-pointer"
                >
                  <div>
                    {/* Top Row: Badges & Actions */}
                    <div className="flex items-center justify-between gap-3 mb-5">
                      <div className="flex items-center gap-2 flex-wrap">
                        <Badge
                          variant={statusConfig.variant}
                          size="sm"
                          dot={statusConfig.dot}
                          pulse={statusConfig.pulse}
                        >
                          {statusConfig.label}
                        </Badge>
                        <Badge variant={priorityVariants[c.priority]} size="sm">
                          {c.priority.toUpperCase()} PRIORITY
                        </Badge>
                        {(c.matterNumber || c.caseNumber) && (
                          <span className="flex items-center gap-1 font-mono text-xs text-slate-300 bg-slate-800/80 px-2.5 py-1 rounded-lg border border-slate-700/60">
                            <Hash className="h-3.5 w-3.5 text-slate-400" />
                            {c.matterNumber || c.caseNumber}
                          </span>
                        )}
                        {c.client && (
                          <span className="flex items-center gap-1.5 text-xs font-medium text-slate-300 bg-slate-800/60 px-2.5 py-1 rounded-lg border border-slate-700/40">
                            <Building2 className="h-3.5 w-3.5 text-indigo-400 shrink-0" />
                            <span>{c.client}</span>
                          </span>
                        )}
                        {c.caseType && (
                          <span className="text-xs font-medium px-2.5 py-1 rounded-lg bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
                            {c.caseType}
                          </span>
                        )}
                      </div>

                      <div className="flex items-center gap-2 shrink-0">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setShareCaseId(c.id);
                            setShareCaseName(c.name);
                          }}
                          className="px-3 py-1 bg-slate-800/80 hover:bg-indigo-500/20 text-slate-400 hover:text-indigo-400 rounded-lg text-xs font-semibold transition-colors cursor-pointer"
                        >
                          Share
                        </button>
                        <button
                          onClick={(e) => handleDeleteCase(c.id, e)}
                          className="px-3 py-1 bg-slate-800/80 hover:bg-rose-500/20 text-slate-400 hover:text-rose-400 rounded-lg text-xs font-semibold transition-colors cursor-pointer"
                        >
                          Delete
                        </button>
                      </div>
                    </div>

                    {/* Case / Matter Name */}
                    <h2 className="text-2xl sm:text-3xl font-bold text-slate-100 group-hover:text-indigo-300 transition-colors mb-3 leading-snug">
                      {c.name}
                    </h2>

                    {/* Description */}
                    {c.description && (
                      <p className="text-sm text-slate-400 leading-relaxed mb-6">
                        {c.description}
                      </p>
                    )}

                    {/* Needs Attention / Processing Notification if applicable */}
                    {((c.flaggedCount ?? 0) > 0 || (c.highRiskCount ?? 0) > 0) && (
                      <div className="mb-6 p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center gap-2.5 text-xs text-amber-300">
                        <AlertTriangle className="h-4 w-4 text-amber-400 shrink-0" />
                        <span className="font-medium">
                          Attention required: {c.flaggedCount} flagged documents
                          {(c.highRiskCount ?? 0) > 0 && ` · ${c.highRiskCount} high risk indicators`}
                        </span>
                      </div>
                    )}
                  </div>

                  {/* ── Telemetry Matrix & Card Footer ────────────────────────── */}
                  <div className="pt-6 border-t border-slate-800/70 space-y-6">
                    {/* 6 Large Metrics */}
                    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
                      {/* Document count */}
                      <div className="flex flex-col p-3 rounded-xl bg-slate-900/50 border border-slate-800/60">
                        <div className="flex items-center gap-1.5 text-slate-400 text-xs mb-1">
                          <FileText className="h-3.5 w-3.5 text-slate-400" />
                          <span>Documents</span>
                        </div>
                        <span className="text-xl font-bold text-slate-100">{c.documentCount}</span>
                        <span className="text-[10px] text-slate-500 mt-0.5">Total records</span>
                      </div>

                      {/* Reviewed count */}
                      <div className="flex flex-col p-3 rounded-xl bg-emerald-500/5 border border-emerald-500/20">
                        <div className="flex items-center gap-1.5 text-emerald-400 text-xs mb-1">
                          <ShieldCheck className="h-3.5 w-3.5" />
                          <span>Reviewed</span>
                        </div>
                        <span className="text-xl font-bold text-slate-100">{c.reviewedCount ?? 0}</span>
                        <span className="text-[10px] text-emerald-400/80 mt-0.5">
                          {c.documentCount > 0 ? `${((c.reviewedCount ?? 0) / c.documentCount * 100).toFixed(0)}% complete` : '0%'}
                        </span>
                      </div>

                      {/* Privileged count */}
                      <div className="flex flex-col p-3 rounded-xl bg-purple-500/5 border border-purple-500/20">
                        <div className="flex items-center gap-1.5 text-purple-400 text-xs mb-1">
                          <Lock className="h-3.5 w-3.5" />
                          <span>Privileged</span>
                        </div>
                        <span className="text-xl font-bold text-slate-100">{c.privilegedCount ?? 0}</span>
                        <span className="text-[10px] text-purple-400/80 mt-0.5">Protected items</span>
                      </div>

                      {/* High Risk count */}
                      <div className="flex flex-col p-3 rounded-xl bg-rose-500/5 border border-rose-500/20">
                        <div className="flex items-center gap-1.5 text-rose-400 text-xs mb-1">
                          <AlertTriangle className="h-3.5 w-3.5" />
                          <span>High Risk</span>
                        </div>
                        <span className="text-xl font-bold text-slate-100">{c.highRiskCount ?? 0}</span>
                        <span className="text-[10px] text-rose-400/80 mt-0.5">Critical exposures</span>
                      </div>

                      {/* Flagged count */}
                      <div className="flex flex-col p-3 rounded-xl bg-amber-500/5 border border-amber-500/20">
                        <div className="flex items-center gap-1.5 text-amber-400 text-xs mb-1">
                          <Flag className="h-3.5 w-3.5" />
                          <span>Flagged</span>
                        </div>
                        <span className="text-xl font-bold text-slate-100">{c.flaggedCount ?? 0}</span>
                        <span className="text-[10px] text-amber-400/80 mt-0.5">Attorney action</span>
                      </div>

                      {/* Last Activity */}
                      <div className="flex flex-col p-3 rounded-xl bg-slate-900/50 border border-slate-800/60">
                        <div className="flex items-center gap-1.5 text-slate-400 text-xs mb-1">
                          <Clock className="h-3.5 w-3.5" />
                          <span>Activity</span>
                        </div>
                        <span className="text-xs font-semibold text-slate-200 mt-1 truncate">
                          {formatDate(c.lastActivity || c.updatedAt || c.createdAt)}
                        </span>
                        <span className="text-[10px] text-slate-500 mt-0.5">Last pipeline event</span>
                      </div>
                    </div>

                    {/* Footer Row: Open Case CTA */}
                    <div className="flex items-center justify-between pt-2">
                      <div className="text-xs text-slate-500">
                        Click to enter case workspace, view all 423 documents, knowledge graph, timeline, and AI Q&A.
                      </div>
                      <div className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold shadow-lg shadow-indigo-600/30 transition-all">
                        <span>Open Case</span>
                        <ArrowRight className="h-4 w-4 group-hover:translate-x-1 transition-transform" />
                      </div>
                    </div>
                  </div>
                </div>
              </motion.div>
            );
          })()}
        </div>
      ) : (
        /* Multi-case portfolio view when 2+ matters exist */
        <>
          {/* ── Summary / Workload Strip ────────────────────────────────────────── */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3.5 mb-6">
            {/* Total Matters */}
            <button
              onClick={() => setActiveTab('all')}
              className={cn(
                'flex flex-col text-left p-4 rounded-2xl border transition-all duration-200 cursor-pointer',
                activeTab === 'all'
                  ? 'bg-slate-800/90 border-indigo-500/50 shadow-md shadow-indigo-500/10'
                  : 'bg-slate-900/60 border-slate-800/80 hover:border-slate-700/80 hover:bg-slate-850/60'
              )}
            >
              <div className="flex items-center justify-between w-full mb-2">
                <span className="text-xs font-medium text-slate-400">Total Matters</span>
                <div className="h-8 w-8 rounded-lg bg-indigo-500/10 flex items-center justify-center text-indigo-400">
                  <Briefcase className="h-4 w-4" />
                </div>
              </div>
              <div className="text-2xl font-bold text-slate-100">{metrics.total}</div>
              <span className="text-[11px] text-slate-500 mt-1">All managed legal cases</span>
            </button>

            {/* Active Matters */}
            <button
              onClick={() => setActiveTab('active')}
              className={cn(
                'flex flex-col text-left p-4 rounded-2xl border transition-all duration-200 cursor-pointer',
                activeTab === 'active'
                  ? 'bg-slate-800/90 border-blue-500/50 shadow-md shadow-blue-500/10'
                  : 'bg-slate-900/60 border-slate-800/80 hover:border-slate-700/80 hover:bg-slate-850/60'
              )}
            >
              <div className="flex items-center justify-between w-full mb-2">
                <span className="text-xs font-medium text-slate-400">Active Matters</span>
                <div className="h-8 w-8 rounded-lg bg-blue-500/10 flex items-center justify-center text-blue-400">
                  <CheckCircle2 className="h-4 w-4" />
                </div>
              </div>
              <div className="text-2xl font-bold text-slate-100">{metrics.active}</div>
              <span className="text-[11px] text-slate-500 mt-1">Open investigations</span>
            </button>

            {/* Processing Evidence */}
            <button
              onClick={() => setActiveTab('processing')}
              className={cn(
                'flex flex-col text-left p-4 rounded-2xl border transition-all duration-200 cursor-pointer',
                activeTab === 'processing'
                  ? 'bg-slate-800/90 border-indigo-500/50 shadow-md shadow-indigo-500/10'
                  : 'bg-slate-900/60 border-slate-800/80 hover:border-slate-700/80 hover:bg-slate-850/60'
              )}
            >
              <div className="flex items-center justify-between w-full mb-2">
                <span className="text-xs font-medium text-slate-400">Processing Evidence</span>
                <div className="h-8 w-8 rounded-lg bg-indigo-500/10 flex items-center justify-center text-indigo-400">
                  <Loader2 className={cn('h-4 w-4', metrics.processingCases > 0 && 'animate-spin')} />
                </div>
              </div>
              <div className="flex items-baseline gap-2">
                <div className="text-2xl font-bold text-slate-100">{metrics.processingCases}</div>
                {metrics.totalProcessingDocs > 0 && (
                  <span className="text-xs text-indigo-400 font-medium">({metrics.totalProcessingDocs} docs)</span>
                )}
              </div>
              <span className="text-[11px] text-slate-500 mt-1">
                {metrics.processingCases > 0 ? 'Active AI pipeline ingestion' : 'No active ingestions'}
              </span>
            </button>

            {/* Needs Attention */}
            <button
              onClick={() => setActiveTab('needs_review')}
              className={cn(
                'flex flex-col text-left p-4 rounded-2xl border transition-all duration-200 cursor-pointer',
                activeTab === 'needs_review'
                  ? 'bg-slate-800/90 border-amber-500/50 shadow-md shadow-amber-500/10'
                  : 'bg-slate-900/60 border-slate-800/80 hover:border-slate-700/80 hover:bg-slate-850/60'
              )}
            >
              <div className="flex items-center justify-between w-full mb-2">
                <span className="text-xs font-medium text-slate-400">Needs Review</span>
                <div className={cn(
                  'h-8 w-8 rounded-lg flex items-center justify-center',
                  metrics.needsReview > 0 ? 'bg-amber-500/10 text-amber-400' : 'bg-slate-800 text-slate-500'
                )}>
                  <ShieldAlert className="h-4 w-4" />
                </div>
              </div>
              <div className="text-2xl font-bold text-slate-100">{metrics.needsReview}</div>
              <span className="text-[11px] text-slate-500 mt-1">Flagged or unreviewed items</span>
            </button>
          </div>

          {/* ── Filter / Search / View Controls ──────────────────────────────────── */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-3.5 mb-6">
            {/* Filter Tabs */}
            <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0 scrollbar-none">
              <button
                onClick={() => setActiveTab('all')}
                className={cn(
                  'px-3.5 py-1.5 rounded-xl text-xs font-medium transition-all shrink-0 cursor-pointer',
                  activeTab === 'all'
                    ? 'bg-indigo-600 text-white shadow-sm shadow-indigo-600/30'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 bg-slate-900/40 border border-slate-800/60'
                )}
              >
                All Cases ({metrics.total})
              </button>
              <button
                onClick={() => setActiveTab('active')}
                className={cn(
                  'px-3.5 py-1.5 rounded-xl text-xs font-medium transition-all shrink-0 cursor-pointer',
                  activeTab === 'active'
                    ? 'bg-indigo-600 text-white shadow-sm shadow-indigo-600/30'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 bg-slate-900/40 border border-slate-800/60'
                )}
              >
                Active ({metrics.active})
              </button>
              <button
                onClick={() => setActiveTab('processing')}
                className={cn(
                  'px-3.5 py-1.5 rounded-xl text-xs font-medium transition-all shrink-0 cursor-pointer flex items-center gap-1.5',
                  activeTab === 'processing'
                    ? 'bg-indigo-600 text-white shadow-sm shadow-indigo-600/30'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 bg-slate-900/40 border border-slate-800/60'
                )}
              >
                {metrics.processingCases > 0 && <span className="h-1.5 w-1.5 rounded-full bg-indigo-400 animate-ping" />}
                Processing ({metrics.processingCases})
              </button>
              <button
                onClick={() => setActiveTab('needs_review')}
                className={cn(
                  'px-3.5 py-1.5 rounded-xl text-xs font-medium transition-all shrink-0 cursor-pointer flex items-center gap-1.5',
                  activeTab === 'needs_review'
                    ? 'bg-indigo-600 text-white shadow-sm shadow-indigo-600/30'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 bg-slate-900/40 border border-slate-800/60'
                )}
              >
                {metrics.needsReview > 0 && <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />}
                Needs Review ({metrics.needsReview})
              </button>
              <button
                onClick={() => setActiveTab('completed')}
                className={cn(
                  'px-3.5 py-1.5 rounded-xl text-xs font-medium transition-all shrink-0 cursor-pointer',
                  activeTab === 'completed'
                    ? 'bg-indigo-600 text-white shadow-sm shadow-indigo-600/30'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 bg-slate-900/40 border border-slate-800/60'
                )}
              >
                Completed ({metrics.completed})
              </button>
            </div>

            {/* Search & Sort Area */}
            <div className="flex items-center gap-2.5 w-full md:w-auto">
              {/* Search Input */}
              <div className="relative flex-1 md:w-64">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-500" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search cases, matters, clients..."
                  className="w-full pl-9 pr-8 py-2 rounded-xl bg-slate-900/60 border border-slate-800/80 text-xs text-slate-200 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 transition-all"
                />
                {searchQuery && (
                  <button
                    onClick={() => setSearchQuery('')}
                    className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors cursor-pointer"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                )}
              </div>

              {/* Sort Dropdown */}
              <div className="flex items-center gap-1.5 bg-slate-900/60 border border-slate-800/80 rounded-xl px-2.5 py-1.5">
                <SlidersHorizontal className="h-3.5 w-3.5 text-slate-500 shrink-0" />
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value as SortOption)}
                  className="bg-transparent text-xs text-slate-300 focus:outline-none cursor-pointer pr-1"
                >
                  <option value="last_activity" className="bg-slate-900 text-slate-200">Sort: Last Activity</option>
                  <option value="recently_created" className="bg-slate-900 text-slate-200">Sort: Recently Created</option>
                  <option value="document_count" className="bg-slate-900 text-slate-200">Sort: Document Count</option>
                  <option value="needs_attention" className="bg-slate-900 text-slate-200">Sort: Needs Attention</option>
                </select>
              </div>
            </div>
          </div>

          {/* ── Cases Grid ──────────────────────────────────────────────────────── */}
          {filteredAndSortedCases.length === 0 ? (
            /* Empty state: cases exist but no match for active filter/search */
            <div className="text-center py-16 px-4 rounded-2xl border border-dashed border-slate-800 bg-slate-900/20">
              <FileText className="h-10 w-10 text-slate-600 mx-auto mb-3" />
              <h3 className="text-sm font-semibold text-slate-300 mb-1">No matching matters found</h3>
              <p className="text-xs text-slate-500 max-w-sm mx-auto mb-4">
                {searchQuery
                  ? `No cases matched "${searchQuery}". Try a different search term or clear the filter.`
                  : 'No cases match the selected status category.'}
              </p>
              <button
                onClick={() => {
                  setSearchQuery('');
                  setActiveTab('all');
                }}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl text-xs font-medium transition-colors cursor-pointer"
              >
                Reset Filters
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
          {filteredAndSortedCases.map((c, i) => {
            const statusConfig = getCaseWorkflowStatus(c);
            const needsAttention = caseNeedsAttention(c);

            return (
              <motion.div
                key={c.id}
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: Math.min(i * 0.02, 0.25) }}
              >
                <div
                  onClick={() => navigate(`/cases/${c.id}/overview`)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      navigate(`/cases/${c.id}/overview`);
                    }
                  }}
                  aria-label={`Open legal matter ${c.name}`}
                  className={cn(
                    'group relative flex flex-col justify-between rounded-2xl p-5 h-full text-left',
                    'bg-slate-900/60 backdrop-blur-xl border border-slate-800/80',
                    'hover:border-indigo-500/40 hover:shadow-xl hover:shadow-indigo-500/5',
                    'hover:-translate-y-0.5 transition-all duration-200 cursor-pointer focus:outline-none focus:ring-2 focus:ring-indigo-500/50',
                    needsAttention && 'border-slate-800/90 hover:border-amber-500/30'
                  )}
                >
                  <div>
                    {/* Top Status & Priority Row */}
                    <div className="flex items-center justify-between gap-2 mb-3">
                      <div className="flex items-center gap-1.5 flex-wrap">
                        <Badge
                          variant={statusConfig.variant}
                          size="xs"
                          dot={statusConfig.dot}
                          pulse={statusConfig.pulse}
                        >
                          {statusConfig.label}
                        </Badge>
                        <Badge variant={priorityVariants[c.priority]} size="xs">
                          {c.priority.toUpperCase()}
                        </Badge>
                      </div>

                      <div className="flex items-center gap-1 shrink-0">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setShareCaseId(c.id);
                            setShareCaseName(c.name);
                          }}
                          className="px-2 py-0.5 bg-slate-800/80 hover:bg-indigo-500/20 text-slate-400 hover:text-indigo-400 rounded-lg text-[10px] font-semibold transition-colors cursor-pointer"
                        >
                          Share
                        </button>
                        <button
                          onClick={(e) => handleDeleteCase(c.id, e)}
                          className="px-2 py-0.5 bg-slate-800/80 hover:bg-rose-500/20 text-slate-400 hover:text-rose-400 rounded-lg text-[10px] font-semibold transition-colors cursor-pointer"
                        >
                          Delete
                        </button>
                      </div>
                    </div>

                    {/* Case / Matter Name */}
                    <h3 className="text-base font-bold text-slate-100 leading-snug line-clamp-2 group-hover:text-indigo-300 transition-colors mb-2">
                      {c.name}
                    </h3>

                    {/* Legal Metadata Line (Matter # · Client · Practice Area) */}
                    <div className="flex flex-wrap items-center gap-2 text-xs text-slate-400 mb-3">
                      {(c.matterNumber || c.caseNumber) && (
                        <span className="flex items-center gap-1 font-mono text-[11px] text-slate-400 bg-slate-800/60 px-2 py-0.5 rounded-md border border-slate-700/40">
                          <Hash className="h-3 w-3 text-slate-500" />
                          {c.matterNumber || c.caseNumber}
                        </span>
                      )}

                      {c.client && (
                        <span className="flex items-center gap-1 text-[11px] font-medium text-slate-300 truncate max-w-[170px]">
                          <Building2 className="h-3 w-3 text-slate-500 shrink-0" />
                          <span className="truncate">{c.client}</span>
                        </span>
                      )}

                      {c.caseType && (
                        <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700/50">
                          {c.caseType}
                        </span>
                      )}
                    </div>

                    {/* Description preview */}
                    {c.description && (
                      <p className="text-xs text-slate-400/90 line-clamp-2 mb-4 leading-relaxed">
                        {c.description}
                      </p>
                    )}

                    {/* Needs Attention / Ingestion Alert Strip */}
                    {((c.flaggedCount ?? 0) > 0 || (c.highRiskCount ?? 0) > 0) ? (
                      <div className="mb-4 px-2.5 py-1.5 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center gap-2 text-[11px] text-amber-300">
                        <AlertTriangle className="h-3.5 w-3.5 text-amber-400 shrink-0" />
                        <span className="font-medium">
                          Attention required: {c.flaggedCount} flagged
                          {(c.highRiskCount ?? 0) > 0 && ` · ${c.highRiskCount} high risk`}
                        </span>
                      </div>
                    ) : (c.processingCount ?? 0) > 0 ? (
                      <div className="mb-4 px-2.5 py-1.5 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center gap-2 text-[11px] text-indigo-300 animate-pulse">
                        <Loader2 className="h-3.5 w-3.5 text-indigo-400 shrink-0 animate-spin" />
                        <span className="font-medium">
                          Processing evidence: {c.processingCount} documents in analysis pipeline
                        </span>
                      </div>
                    ) : null}
                  </div>

                  {/* ── Telemetry Matrix & Card Footer ────────────────────────── */}
                  <div className="pt-3.5 border-t border-slate-800/60 mt-auto space-y-3">
                    {/* Real Telemetry Grid */}
                    <div className="grid grid-cols-3 gap-2 text-xs">
                      {/* Document count */}
                      <div className="flex items-center gap-1.5 text-slate-400 bg-slate-900/40 p-1.5 rounded-lg border border-slate-800/40">
                        <FileText className="h-3.5 w-3.5 text-slate-500 shrink-0" />
                        <span className="font-semibold text-slate-200">{c.documentCount}</span>
                        <span className="text-[10px] text-slate-500">docs</span>
                      </div>

                      {/* Reviewed count */}
                      <div className={cn(
                        'flex items-center gap-1.5 p-1.5 rounded-lg border',
                        (c.reviewedCount ?? 0) > 0
                          ? 'text-emerald-400 bg-emerald-500/5 border-emerald-500/20'
                          : 'text-slate-500 bg-slate-900/40 border-slate-800/40'
                      )}>
                        <ShieldCheck className="h-3.5 w-3.5 shrink-0" />
                        <span className="font-semibold text-slate-200">{c.reviewedCount ?? 0}</span>
                        <span className="text-[10px] text-slate-500">rvwd</span>
                      </div>

                      {/* Flagged count */}
                      <div className={cn(
                        'flex items-center gap-1.5 p-1.5 rounded-lg border',
                        (c.flaggedCount ?? 0) > 0
                          ? 'text-amber-400 bg-amber-500/5 border-amber-500/20'
                          : 'text-slate-500 bg-slate-900/40 border-slate-800/40'
                      )}>
                        <Flag className="h-3.5 w-3.5 shrink-0" />
                        <span className="font-semibold text-slate-200">{c.flaggedCount ?? 0}</span>
                        <span className="text-[10px] text-slate-500">flag</span>
                      </div>

                      {/* Privileged count */}
                      <div className={cn(
                        'flex items-center gap-1.5 p-1.5 rounded-lg border',
                        (c.privilegedCount ?? 0) > 0
                          ? 'text-purple-400 bg-purple-500/5 border-purple-500/20'
                          : 'text-slate-500 bg-slate-900/40 border-slate-800/40'
                      )}>
                        <Lock className="h-3.5 w-3.5 shrink-0" />
                        <span className="font-semibold text-slate-200">{c.privilegedCount ?? 0}</span>
                        <span className="text-[10px] text-slate-500">priv</span>
                      </div>

                      {/* High Risk count */}
                      <div className={cn(
                        'flex items-center gap-1.5 p-1.5 rounded-lg border',
                        (c.highRiskCount ?? 0) > 0
                          ? 'text-rose-400 bg-rose-500/5 border-rose-500/20'
                          : 'text-slate-500 bg-slate-900/40 border-slate-800/40'
                      )}>
                        <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
                        <span className="font-semibold text-slate-200">{c.highRiskCount ?? 0}</span>
                        <span className="text-[10px] text-slate-500">risk</span>
                      </div>

                      {/* Processing count */}
                      <div className={cn(
                        'flex items-center gap-1.5 p-1.5 rounded-lg border',
                        (c.processingCount ?? 0) > 0
                          ? 'text-indigo-400 bg-indigo-500/5 border-indigo-500/20 animate-pulse'
                          : 'text-slate-500 bg-slate-900/40 border-slate-800/40'
                      )}>
                        <Loader2 className={cn('h-3.5 w-3.5 shrink-0', (c.processingCount ?? 0) > 0 && 'animate-spin')} />
                        <span className="font-semibold text-slate-200">{c.processingCount ?? 0}</span>
                        <span className="text-[10px] text-slate-500">proc</span>
                      </div>
                    </div>

                    {/* Footer Row: Last Activity + Open Case action */}
                    <div className="flex items-center justify-between pt-1">
                      <div className="flex items-center gap-1.5 text-slate-500 text-[11px]">
                        <Clock className="h-3 w-3 shrink-0" />
                        <span>{formatDate(c.lastActivity || c.updatedAt || c.createdAt)}</span>
                      </div>

                      <div className="flex items-center gap-1 text-xs font-semibold text-indigo-400 group-hover:text-indigo-300 transition-colors">
                        <span>Open Case</span>
                        <ArrowRight className="h-3.5 w-3.5 group-hover:translate-x-0.5 transition-transform" />
                      </div>
                    </div>
                  </div>
                </div>
              </motion.div>
            );
          })}
        </div>
          )}
        </>
      )}

      {/* ── New Case Wizard Modal (Phase 7C) ─────────────────────────────────── */}
      <NewCaseModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onSuccess={fetchCases}
      />

      {/* ── Share Case Modal ─────────────────────────────────────────────────── */}
      <ShareCaseModal
        caseId={shareCaseId || ''}
        caseName={shareCaseName}
        show={!!shareCaseId}
        onClose={() => setShareCaseId(null)}
      />
    </PageShell>
  );
}
