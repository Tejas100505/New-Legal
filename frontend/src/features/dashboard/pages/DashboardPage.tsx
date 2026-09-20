/**
 * DashboardPage — enterprise dashboard integrating:
 * - Hero banner
 * - Pipeline Visualizer (10-stage flow)
 * - Agent Status Panel (14 agents with full monitoring)
 * - Analytics Grid (11 metrics)
 * - Preview Widget Grid (8 live previews)
 * - Widget rows for Risk, Evidence, Timeline, Activity, Recent Uploads.
 */

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import {
  Zap, AlertTriangle, Clock,
  Brain, Upload, Activity, Bell, ChevronRight,
  Inbox
} from 'lucide-react';
import {
  Tooltip as ReTooltip, ResponsiveContainer,
  PieChart, Pie, Cell,
} from 'recharts';
import { cn } from '@/lib/utils';
import { formatDate, formatFileSize } from '@/lib/utils';
import { MetricCard } from '@/components/molecules/MetricCard';
import { Badge } from '@/components/atoms/Badge';
import { SkeletonMetricCard } from '@/components/atoms/Skeleton';
import { FileIcon } from '@/components/molecules/FileIcon';
import { useAuthStore } from '@/features/auth/store';
import { useAgentStore } from '@/stores/agentStore';
import { useAnalyticsStore } from '@/stores/analyticsStore';
import { useAgentUpdates } from '@/features/agents/hooks/useAgentUpdates';
import { PipelineVisualizer } from '@/features/agents/components/PipelineVisualizer';
import { AgentStatusPanel } from '@/features/agents/components/AgentStatusPanel';
import { AgentDetailModal } from '@/features/agents/components/AgentDetailModal';
import { AnalyticsGrid } from '@/features/analytics/components/AnalyticsGrid';
import { PreviewWidgetGrid } from '@/features/dashboard/components/PreviewWidgetGrid';
import { ROUTES, RISK_COLORS, ALL_AGENT_IDS } from '@/lib/constants';
import type { AgentId, LegalCase, LegalDocument, TimelineEvent } from '@/types';
import api from '@/lib/api';

const stagger = {
  animate: { transition: { staggerChildren: 0.06 } },
};

const fadeUp = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.4 },
};



export function DashboardPage() {
  const { user } = useAuthStore();
  const agents = useAgentStore((s) => s.agents);
  const analytics = useAnalyticsStore((s) => s.analytics);
  const retryAgent = useAgentStore((s) => s.retryAgent);

  const [loading, setLoading] = useState(true);
  const [selectedAgent, setSelectedAgent] = useState<AgentId | null>(null);

  const [cases, setCases] = useState<LegalCase[]>([]);
  const [documents, setDocuments] = useState<LegalDocument[]>([]);
  const [timelineEvents, setTimelineEvents] = useState<TimelineEvent[]>([]);

  // Subscribe to agent updates for screen reader announcements
  useAgentUpdates();

  const [activities, setActivities] = useState<any[]>([]);

  useEffect(() => {
    useAgentStore.getState().initializeAgents();
    useAnalyticsStore.getState().refreshAnalytics();

    async function fetchData() {
      setLoading(true);
      // Fetch documents immediately for instant metric cards and risk analysis
      api.get('/documents?page_size=1000')
        .then((res) => {
          const rawDocs = res.data.documents || [];
          setDocuments(rawDocs.map((d: any) => {
            const meta = d.doc_metadata || {};
            const ra = meta.risk_analysis || {};
            const rawRisk = (ra.risk_level || meta.risk_level || meta.priority_tier || meta.risk?.overall_risk || 'low').toLowerCase();
            const isPriv = !!(meta.is_privileged || meta.privilege_analysis?.is_privileged || meta.privilege?.is_privileged);
            return {
              id: d.id,
              name: d.original_filename,
              type: d.original_filename.split('.').pop() || 'pdf',
              size: d.file_size,
              status: d.status,
              caseId: d.case_id,
              caseName: d.case_name || d.case?.name || meta.case_name || 'Active Investigation',
              ocrAccuracy: meta.confidence_score || 0.99,
              ocrConfidence: 'high',
              pageCount: d.page_count || 1,
              entityCount: 0,
              uploadedBy: 'User',
              uploadedAt: d.created_at,
              processedAt: d.updated_at,
              tags: [],
              version: 1,
              isPrivileged: isPriv,
              riskLevel: rawRisk,
              doc_metadata: meta,
            };
          }));
          setLoading(false);
        })
        .catch((err) => {
          console.error("Dashboard documents fetch error", err);
          setLoading(false);
        });

      api.get('/cases')
        .then((res) => setCases(res.data.cases || []))
        .catch((err) => console.error("Cases fetch error", err));

      api.get('/timeline')
        .then((res) => setTimelineEvents((res.data.events || res.data || []).filter((e: any) => e.source !== 'mock_fallback')))
        .catch((err) => console.error("Timeline fetch error", err));

      api.get('/reports/audit-logs')
        .then((res) => setActivities(res.data.audit_logs || []))
        .catch((err) => console.error("Audit logs fetch error", err));
    }
    fetchData();
  }, []);

  const greeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good morning';
    if (hour < 17) return 'Good afternoon';
    return 'Good evening';
  };

  const agentSummary = {
    running: Object.values(agents).filter((a) => a.status === 'running').length,
    completed: Object.values(agents).filter((a) => a.status === 'completed').length,
    failed: Object.values(agents).filter((a) => a.status === 'failed').length,
  };

  const activeCasesCount = cases.length;
  const criticalRiskDocs = documents.filter((d: any) => (d.riskLevel || '').toLowerCase() === 'critical').length;
  const highRiskDocs = documents.filter((d: any) => (d.riskLevel || '').toLowerCase() === 'high').length;
  const highRiskDocsCount = criticalRiskDocs + highRiskDocs;
  const flaggedDocsCount = documents.filter((d: any) => d.status === 'flagged').length;
  const privilegedDocsCount = documents.filter((d: any) => d.isPrivileged).length;
  const lowRiskDocsCount = Math.max(0, documents.length - highRiskDocsCount);

  const derivedMetrics = [
    { id: 'm1', label: 'Active Cases', value: activeCasesCount, change: 0, changeLabel: '', trend: 'neutral' as const, icon: 'FolderOpen', color: 'indigo' as const },
    { id: 'm2', label: 'Documents Processed', value: documents.length, change: 0, changeLabel: '', trend: 'neutral' as const, icon: 'FileText', color: 'cyan' as const },
    { id: 'm3', label: 'High & Critical Risk', value: highRiskDocsCount, change: 0, changeLabel: `${flaggedDocsCount} flagged for review`, trend: 'neutral' as const, icon: 'AlertTriangle', color: 'rose' as const },
    { id: 'm4', label: 'Flagged for Review', value: flaggedDocsCount, change: 0, changeLabel: 'Workflow escalation status', trend: 'neutral' as const, icon: 'Eye', color: 'amber' as const },
    { id: 'm5', label: 'OCR Accuracy', value: analytics.ocrAccuracy.value !== null ? `${analytics.ocrAccuracy.value.toFixed(1)}%` : 'N/A', change: 0, changeLabel: analytics.ocrAccuracy.value !== null ? '' : 'Pending measurement', trend: 'neutral' as const, icon: 'CheckCircle', color: 'emerald' as const },
    { id: 'm6', label: 'Storage Usage', value: analytics.storageUsage.value !== null ? `${analytics.storageUsage.value} ${analytics.storageUsage.unit}` : (documents.length > 0 ? formatFileSize(documents.reduce((acc: number, d: any) => acc + (d.size || 0), 0)) : '0 B'), change: 0, changeLabel: '', trend: 'neutral' as const, icon: 'Brain', color: 'blue' as const },
  ];

  const riskChartData = [
    { name: 'Critical', value: criticalRiskDocs, color: RISK_COLORS.critical || '#ef4444' },
    { name: 'High', value: highRiskDocs, color: RISK_COLORS.high || '#f59e0b' },
    { name: 'Low', value: lowRiskDocsCount, color: RISK_COLORS.low || '#10b981' },
  ];

  const emptyState = (message: string) => (
    <div className="flex flex-col items-center justify-center py-10 text-slate-500 bg-slate-800/20 rounded-lg border border-slate-800 border-dashed">
      <Inbox className="h-8 w-8 mb-2 opacity-50" />
      <p className="text-xs">{message}</p>
    </div>
  );

  return (
    <motion.div
      className="space-y-6"
      variants={stagger}
      initial="initial"
      animate="animate"
      id="main-content"
    >
      {/* ── Hero ─────────────────────────────────────────────────── */}
      <motion.div {...fadeUp}>
        <div className="relative rounded-2xl overflow-hidden bg-gradient-to-br from-indigo-500/10 via-slate-900/50 to-violet-500/10 border border-indigo-500/10 p-6 md:p-8">
          <div className="bg-grid-pattern absolute inset-0 opacity-30" />
          <div className="relative z-10">
            <div className="flex items-center gap-2 mb-2">
               <Zap className="h-5 w-5 text-indigo-400" />
               <span className="text-xs font-semibold text-indigo-400 uppercase tracking-wider">
                 {greeting()}, {user?.name?.split(' ')[0] || 'Counselor'}
               </span>
             </div>
             <h1 className="text-2xl md:text-3xl font-bold mb-2">
               <span className="gradient-text">Agentic AI</span>{' '}
               <span className="text-slate-100">E-Discovery Platform</span>
             </h1>
             <p className="text-slate-400 max-w-2xl text-sm leading-relaxed">
               {ALL_AGENT_IDS.length} specialized AI agents are monitoring your cases.{' '}
               {agentSummary.running > 0 ? `${agentSummary.running} currently running, ` : ''}
               {agentSummary.completed > 0 ? `${agentSummary.completed} completed, ` : ''}
               {agentSummary.failed > 0 ? `${agentSummary.failed} need attention` : 'all systems operational.'}
             </p>
           </div>
         </div>
       </motion.div>

       {/* ── Onboarding Banner for New Users with 0 Cases ──────────── */}
       {!loading && cases.length === 0 && (
         <motion.div {...fadeUp}>
           <div className="p-6 rounded-2xl bg-gradient-to-r from-indigo-500/10 via-purple-500/10 to-slate-900/50 border border-indigo-500/30 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
             <div className="space-y-1">
               <div className="flex items-center gap-2">
                 <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                   Getting Started
                 </span>
                 <h3 className="text-base font-semibold text-slate-100">Welcome to E-Discovery AI</h3>
               </div>
               <p className="text-xs text-slate-400 max-w-xl">
                 You currently have no active cases in your workspace. Create your first case matter to begin uploading discovery files, running OCR, privilege screening, and automated risk analysis.
               </p>
             </div>
             <Link
               to="/cases"
               className="px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-lg shadow-indigo-600/30 flex items-center gap-1.5 shrink-0 transition-all"
             >
               <span>Create Your First Case</span>
               <ChevronRight className="h-4 w-4" />
             </Link>
           </div>
         </motion.div>
       )}

       {/* ── Pipeline Visualizer ───────────────────────────────────── */}
       <motion.div {...fadeUp}>
         <PipelineVisualizer />
       </motion.div>

       {/* ── Agent Status Panel (14 agents) ────────────────────────── */}
       <motion.div {...fadeUp}>
         <AgentStatusPanel
           onViewDetails={(id) => setSelectedAgent(id)}
           isLoading={loading}
         />
       </motion.div>

       {/* ── Dashboard Analytics (11 metrics) ──────────────────────── */}
       <motion.div {...fadeUp}>
         <AnalyticsGrid isLoading={loading} />
       </motion.div>

       {/* ── Preview Widget Grid (8 previews) ──────────────────────── */}
       <motion.div {...fadeUp}>
         <PreviewWidgetGrid
           isLoading={loading}
           documents={documents}
           cases={cases}
           timelineEvents={timelineEvents}
         />
       </motion.div>

       {/* ── Overview Cards (Derived) ──────────────────────────────── */}
       <motion.div {...fadeUp}>
         <div id="overview-metric-cards" className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
           {loading
             ? Array.from({ length: 6 }).map((_, i) => <SkeletonMetricCard key={i} />)
             : derivedMetrics.map((metric, i) => (
                 <MetricCard key={metric.id} metric={metric as any} index={i} />
               ))
           }
         </div>
       </motion.div>

       {/* ── Widget Row 1: AI Insights + Risk + Evidence ──────────── */}
       <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
         {/* AI Insights Widget */}
         <motion.div {...fadeUp} className="lg:col-span-2">
           <WidgetCard title="AI Insights" icon={<Brain className="h-4.5 w-4.5 text-violet-400" />} linkTo={ROUTES.AI_REVIEW} linkLabel="View All">
             <div className="space-y-3">
               <div className="p-3 rounded-lg bg-slate-800/30 border border-slate-700/30">
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <span className="text-xs font-semibold text-slate-200">Privilege Review: Legal Counsel & Work Product</span>
                    <Badge variant={privilegedDocsCount > 0 ? "danger" : "default"} size="xs">
                      {privilegedDocsCount} {privilegedDocsCount === 1 ? 'Privileged' : 'Privileged'}
                    </Badge>
                  </div>
                  <p className="text-xs text-slate-400 leading-relaxed">
                    {privilegedDocsCount} {privilegedDocsCount === 1 ? 'document' : 'documents'} identified with potential legal privilege markers, legal counsel correspondence, or litigation work-product protections.
                  </p>
               </div>
               <div className="p-3 rounded-lg bg-slate-800/30 border border-slate-700/30">
                 <div className="flex items-center justify-between gap-2 mb-1">
                   <span className="text-xs font-semibold text-slate-200">Contract Restructuring & Volumetric Demand Adders</span>
                   <Badge variant="warning" size="xs">High Priority</Badge>
                 </div>
                 <p className="text-xs text-slate-400 leading-relaxed">
                   Supply area deal restructuring detected on NGPL pipeline involving 400,000 MMBtu/day volume terms and Sonat Erath volumetric adders.
                 </p>
               </div>
                <div className="p-3 rounded-lg bg-slate-800/30 border border-slate-700/30">
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <span className="text-xs font-semibold text-slate-200">Knowledge Graph & Named Entity Synthesis</span>
                    <Badge variant="info" size="xs">
                      {analytics.evidenceCount.value != null ? `${analytics.evidenceCount.value.toLocaleString()} Entities` : 'Entity Synthesis'}
                    </Badge>
                  </div>
                  <p className="text-xs text-slate-400 leading-relaxed">
                    Cross-document named entity resolution mapping relationships across legal counsel, regulatory inquiries, and corporate entities.
                  </p>
                </div>
             </div>
           </WidgetCard>
         </motion.div>

         {/* Risk Summary Widget */}
         <motion.div {...fadeUp}>
           <WidgetCard title="Risk Summary" icon={<AlertTriangle className="h-4.5 w-4.5 text-amber-400" />}>
             {riskChartData.length === 0 ? emptyState('No documents to analyze for risk.') : (
               <>
                 <div className="flex items-center justify-center h-[180px]">
                   <ResponsiveContainer width="100%" height="100%">
                     <PieChart>
                       <Pie data={riskChartData} cx="50%" cy="50%" innerRadius={45} outerRadius={70} paddingAngle={3} dataKey="value">
                         {riskChartData.map((entry, i) => (
                           <Cell key={i} fill={entry.color} stroke="transparent" />
                         ))}
                       </Pie>
                       <ReTooltip
                         contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '0.75rem', fontSize: '0.75rem', color: '#e2e8f0' }}
                       />
                     </PieChart>
                   </ResponsiveContainer>
                 </div>
                  <div className="flex flex-wrap items-center justify-between gap-2 mt-2 pt-2 border-t border-slate-800/60">
                    <div className="flex flex-wrap gap-2">
                      {riskChartData.map((r) => (
                        <div key={r.name} className="flex items-center gap-1.5 text-xs text-slate-400">
                          <span className="h-2 w-2 rounded-full" style={{ backgroundColor: r.color }} />
                          {r.name} ({r.value})
                        </div>
                      ))}
                    </div>
                    <span className="text-[11px] text-amber-400/90 font-medium">
                      {flaggedDocsCount} flagged for review
                    </span>
                  </div>
                </>
             )}
           </WidgetCard>
         </motion.div>
       </div>

       {/* ── Widget Row 2: Timeline + Activity ────────────────────── */}
       <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
         {/* Timeline Preview Widget */}
         <motion.div {...fadeUp}>
           <WidgetCard title="Timeline Preview" icon={<Clock className="h-4.5 w-4.5 text-emerald-400" />} linkTo={ROUTES.TIMELINE} linkLabel="Full Timeline">
             {timelineEvents.length === 0 ? emptyState('No timeline events recorded yet.') : (
               <div className="space-y-3">
                 {timelineEvents.slice(0, 4).map((event, i) => (
                   <div key={event.id} className="flex items-start gap-3">
                     <div className="flex flex-col items-center">
                       <div className="h-2.5 w-2.5 rounded-full bg-indigo-500 mt-1.5" />
                       {i < Math.min(timelineEvents.length - 1, 3) && <div className="w-px h-full min-h-[32px] bg-slate-800" />}
                     </div>
                     <div className="flex-1 min-w-0 pb-3">
                       <p className="text-sm font-medium text-slate-200">{event.title}</p>
                       <p className="text-xs text-slate-500 mt-0.5 line-clamp-1">{event.description}</p>
                       <p className="text-[10px] text-slate-600 mt-1">{formatDate(event.timestamp)}</p>
                     </div>
                   </div>
                 ))}
               </div>
             )}
           </WidgetCard>
         </motion.div>
         
         <motion.div {...fadeUp}>
           <WidgetCard title="Activity Feed" icon={<Activity className="h-4.5 w-4.5 text-emerald-400" />}>
             {activities.length === 0 ? emptyState('No recent activity.') : (
               <div className="space-y-2.5">
                 {activities.slice(0, 4).map((act) => (
                   <div key={act.id} className="flex items-start gap-2.5 p-2 rounded-lg bg-slate-800/20 text-xs">
                     <div className="h-2 w-2 rounded-full bg-emerald-400 mt-1.5 shrink-0" />
                     <div className="flex-1 min-w-0">
                       <p className="font-semibold text-slate-200">{act.action}</p>
                       <p className="text-[10px] text-slate-500">{act.user_email || 'System'} • {formatDate(act.timestamp)}</p>
                     </div>
                   </div>
                 ))}
               </div>
             )}
           </WidgetCard>
         </motion.div>
       </div>

       {/* ── Widget Row 3: Recent Uploads + Notifications ─────────────── */}
       <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
         {/* Recent Uploads Widget */}
         <motion.div {...fadeUp}>
           <WidgetCard title="Recent Uploads" icon={<Upload className="h-4.5 w-4.5 text-indigo-400" />} linkTo={ROUTES.DOCUMENTS} linkLabel="All Documents">
             {documents.length === 0 ? emptyState('No documents uploaded yet.') : (
               <div className="space-y-2">
                 {documents.slice(0, 5).map((doc) => (
                   <div key={doc.id} className="flex items-center gap-3 p-2.5 rounded-lg hover:bg-slate-800/30 transition-colors">
                     <FileIcon type={doc.type as any} size="sm" />
                     <div className="flex-1 min-w-0">
                       <p className="text-sm font-medium text-slate-200 truncate">{doc.name}</p>
                       <p className="text-xs text-slate-500">{formatFileSize(doc.size)}</p>
                     </div>
                      <Badge
                        variant={doc.status === 'analyzed' ? 'success' : (doc.status === 'processing' || doc.status === 'quota_paused') ? 'warning' : doc.status === 'flagged' ? 'danger' : 'default'}
                        size="xs"
                        dot
                        pulse={doc.status === 'processing'}
                      >
                        {doc.status.replace('_', ' ')}
                      </Badge>
                   </div>
                 ))}
               </div>
             )}
           </WidgetCard>
         </motion.div>

         <motion.div {...fadeUp}>
           <WidgetCard title="Notifications" icon={<Bell className="h-4.5 w-4.5 text-blue-400" />}>
             {emptyState('You have no new notifications.')}
           </WidgetCard>
         </motion.div>
       </div>

       {/* ── Agent Detail Modal ────────────────────────────────────── */}
       <AgentDetailModal
         agentId={selectedAgent}
         state={selectedAgent ? agents[selectedAgent] : null}
         isOpen={selectedAgent !== null}
         onClose={() => setSelectedAgent(null)}
         onRetry={(id) => {
           retryAgent(id);
           setSelectedAgent(null);
         }}
       />
     </motion.div>
  );
}

// ── Widget Card Helper ──────────────────────────────────────────────────────

interface WidgetCardProps {
  title: string;
  icon: React.ReactNode;
  children: React.ReactNode;
  linkTo?: string;
  linkLabel?: string;
  badge?: string;
}

function WidgetCard({ title, icon, children, linkTo, linkLabel, badge }: WidgetCardProps) {
  return (
    <div className={cn(
      'rounded-xl p-5 h-full',
      'bg-slate-900/50 backdrop-blur-xl',
      'border border-slate-800/50',
      'shadow-lg shadow-black/20',
      'transition-all duration-300',
      'hover:border-slate-700/50'
    )}>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          {icon}
          <h3 className="text-sm font-semibold text-slate-200">{title}</h3>
          {badge && <Badge variant="info" size="xs">{badge}</Badge>}
        </div>
        {linkTo && linkLabel && (
          <Link
            to={linkTo}
            className="flex items-center gap-1 text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
          >
            {linkLabel}
            <ChevronRight className="h-3 w-3" />
          </Link>
        )}
      </div>
      {children}
    </div>
  );
}
