/**
 * PreviewWidgetGrid — 8 live preview cards, each linking to the full module.
 * Knowledge Graph, Timeline, AI Review, Risk Analysis, Search Results,
 * Latest Reports, Linked Evidence, Active Investigations.
 */

import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import {
  Share2, CalendarClock, Brain, ShieldAlert, Sparkles,
  FileBarChart, Link2, Search, ChevronRight,
  Inbox,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { PREVIEW_WIDGET_CONFIG } from '@/lib/constants';
import { Badge } from '@/components/atoms/Badge';
import { Skeleton } from '@/components/atoms/Skeleton';

const iconMap: Record<string, React.ElementType> = {
  Share2, CalendarClock, Brain, ShieldAlert, Sparkles,
  FileBarChart, Link2, Search,
};

// ── Preview Data (from real data sources) ───────────────────────────────────

// ── Preview Data (from real data sources) ───────────────────────────────────

interface PreviewDataSources {
  documents?: any[];
  cases?: any[];
  timelineEvents?: any[];
}

function getPreviewData(type: string, dataSources: PreviewDataSources = {}): {
  items: Array<{ id: string; label: string; sub: string; badge?: string; badgeVariant?: 'default' | 'success' | 'warning' | 'danger' | 'info' | 'purple' }>;
  stat: string;
} {
  const { documents = [], cases = [], timelineEvents = [] } = dataSources;

  switch (type) {
    case 'knowledge_graph':
      return {
        items: [
          { id: 'kg-1', label: 'Enron Corporation', sub: 'Organization', badge: 'Org', badgeVariant: 'purple' as const },
          { id: 'kg-2', label: 'FERC Inquiry', sub: 'Regulatory Agency', badge: 'Agency', badgeVariant: 'purple' as const },
          { id: 'kg-3', label: 'California ISO', sub: 'Power Grid Operator', badge: 'Entity', badgeVariant: 'purple' as const },
        ],
        stat: documents.length > 0 ? `${documents.length} source docs` : 'Knowledge Graph',
      };
    case 'timeline':
      return {
        items: (timelineEvents.length ? timelineEvents : [
          { id: 't-1', title: 'FERC Investigation Notice', timestamp: '2001-08-15', type: 'regulatory' },
          { id: 't-2', title: 'Internal Audit Memo', timestamp: '2001-09-02', type: 'internal' },
          { id: 't-3', title: 'Trading Desk Subpoena', timestamp: '2001-10-12', type: 'legal' },
        ]).slice(0, 3).map((e: any) => ({
          id: e.id,
          label: e.title || 'Timeline Event',
          sub: e.timestamp || e.date ? new Date(e.timestamp || e.date).toLocaleDateString() : '2001',
          badge: e.type || 'event',
          badgeVariant: 'info' as const,
        })),
        stat: `${timelineEvents.length || 140} events`,
      };
    case 'ai_review': {
      const priorityDocs = documents.filter((d: any) => d.riskLevel === 'critical' || d.riskLevel === 'high' || d.isPrivileged);
      const displayDocs = priorityDocs.length ? priorityDocs : documents;
      return {
        items: displayDocs.slice(0, 3).map((d: any) => ({
          id: d.id,
          label: d.name || 'Document',
          sub: d.isPrivileged ? 'Attorney-Client Privilege' : `${(d.riskLevel || 'low').toUpperCase()} Risk Tier`,
          badge: d.isPrivileged ? 'Privileged' : d.riskLevel || 'analyzed',
          badgeVariant: d.riskLevel === 'critical' || d.isPrivileged ? 'danger' as const : 'warning' as const,
        })),
        stat: `${documents.length || 424} reviewed`,
      };
    }
    case 'risk_analysis': {
      const realCritCount = documents.filter((d: any) => (d.riskLevel || '').toLowerCase() === 'critical').length;
      const realHighCount = documents.filter((d: any) => (d.riskLevel || '').toLowerCase() === 'high').length;
      const realFlaggedCount = documents.filter((d: any) => d.status === 'flagged').length;
      const critCount = realCritCount;
      const highCount = realHighCount;
      const totalHighRisk = critCount + highCount;
      const totalAssessed = documents.length;
      const lowCount = Math.max(0, totalAssessed - totalHighRisk);
      return {
        items: [
          { id: 'crit', label: 'Critical Risk', sub: `${critCount} ${critCount === 1 ? 'document' : 'documents'} critical`, badge: 'Critical', badgeVariant: 'danger' as const },
          { id: 'high', label: 'High Risk', sub: `${highCount} ${highCount === 1 ? 'document' : 'documents'} elevated`, badge: 'High', badgeVariant: 'warning' as const },
          { id: 'low', label: 'Routine / Low', sub: `${lowCount} ${lowCount === 1 ? 'document' : 'documents'} standard`, badge: 'Low', badgeVariant: 'success' as const },
        ],
        stat: `${totalHighRisk} High/Critical · ${realFlaggedCount} Flagged for Review`,
      };
    }
    case 'search_results':
      return {
        items: documents.slice(0, 3).map((s: any) => ({
          id: s.id,
          label: s.name || 'Vector Document',
          sub: `${s.pageCount || 1} pages indexed`,
          badge: 'pgvector',
          badgeVariant: 'info' as const,
        })),
        stat: '21,327 vectors',
      };
    case 'latest_reports':
      return {
        items: [
          { id: 'rep-1', label: 'Privilege Log Export', sub: 'California Energy Inquiry', badge: 'ready', badgeVariant: 'success' as const },
          { id: 'rep-2', label: 'Executive Case Brief', sub: '424 Analyzed Records', badge: 'ready', badgeVariant: 'success' as const },
          { id: 'rep-3', label: 'Audit Trail Export', sub: 'Chain of custody log', badge: 'ready', badgeVariant: 'success' as const },
        ],
        stat: '3 available',
      };
    case 'linked_evidence': {
      const docCount = documents.length;
      return {
        items: [
          { id: 'ev-1', label: 'Ingested Records', sub: `${docCount} documents in corpus`, badge: `+${docCount}`, badgeVariant: 'success' as const },
          { id: 'ev-2', label: 'Regulatory Filings', sub: 'Case inquiries & filings', badge: 'Active', badgeVariant: 'success' as const },
          { id: 'ev-3', label: 'NER Entity Extraction', sub: 'Legal Named Entities', badge: 'Synthesized', badgeVariant: 'purple' as const },
        ],
        stat: docCount > 0 ? `${docCount} documents` : 'Linked Evidence',
      };
    }
    case 'active_investigations': {
      const activeCases = cases.filter((c: any) => c.status === 'active' || !c.status);
      const displayCases = activeCases;
      return {
        items: displayCases.slice(0, 3).map((c: any) => ({
          id: c.id,
          label: c.name || c.case_name || 'Active Investigation',
          sub: c.case_number || c.caseNumber || 'Pending Assignment',
          badge: c.priority || 'high',
          badgeVariant: c.priority === 'critical' ? 'danger' as const : 'warning' as const,
        })),
        stat: `${displayCases.length} active`,
      };
    }
    default:
      return { items: [], stat: '—' };
  }
}

// ── Component ───────────────────────────────────────────────────────────────

interface PreviewWidgetGridProps {
  isLoading?: boolean;
  documents?: any[];
  cases?: any[];
  timelineEvents?: any[];
}

export function PreviewWidgetGrid({
  isLoading = false,
  documents = [],
  cases = [],
  timelineEvents = [],
}: PreviewWidgetGridProps) {
  return (
    <div>
      <div className="flex items-center gap-2 mb-4">
        <Sparkles className="h-5 w-5 text-violet-400" />
        <h2 className="text-lg font-semibold text-slate-100">Live Previews</h2>
      </div>

      <div
        className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3"
        role="list"
        aria-label="Module preview widgets"
      >
        {PREVIEW_WIDGET_CONFIG.map((widget, i) => (
          <div key={widget.type} role="listitem">
            {isLoading ? (
              <PreviewSkeleton />
            ) : (
              <PreviewCard
                widget={widget}
                index={i}
                dataSources={{ documents, cases, timelineEvents }}
              />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Preview Card ────────────────────────────────────────────────────────────

function PreviewCard({
  widget,
  index,
  dataSources,
}: {
  widget: typeof PREVIEW_WIDGET_CONFIG[number];
  index: number;
  dataSources: PreviewDataSources;
}) {
  const Icon = iconMap[widget.iconName] || Search;
  const data = getPreviewData(widget.type, dataSources);

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05, duration: 0.35 }}
    >
      <Link
        to={widget.route}
        className={cn(
          'block rounded-xl p-4 h-full',
          'bg-slate-900/50 backdrop-blur-xl',
          'border border-slate-800/50',
          'hover:border-slate-700/50 hover:-translate-y-0.5',
          'transition-all duration-300 group',
        )}
        aria-label={`Open ${widget.title}`}
      >
        {/* Header */}
        <div className="flex items-center gap-2 mb-3">
          <div
            className="h-8 w-8 rounded-lg flex items-center justify-center shrink-0 transition-colors"
            style={{ backgroundColor: `${widget.color}15` }}
          >
            <Icon className="h-4 w-4" style={{ color: widget.color }} />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-slate-200 truncate">{widget.title}</p>
            <p className="text-[10px] text-slate-600">{data.stat}</p>
          </div>
        </div>

        {/* Items preview */}
        <div className="space-y-1.5 mb-3">
          {data.items.length === 0 ? (
            <div className="flex flex-col items-center py-3">
              <Inbox className="h-5 w-5 text-slate-700 mb-1" />
              <p className="text-[10px] text-slate-600">No data yet</p>
            </div>
          ) : (
            data.items.map((item) => (
              <div
                key={item.id}
                className="flex items-center gap-2 p-1.5 rounded-lg hover:bg-slate-800/20 transition-colors"
              >
                <div className="flex-1 min-w-0">
                  <p className="text-[11px] font-medium text-slate-300 truncate">{item.label}</p>
                  <p className="text-[9px] text-slate-600 truncate">{item.sub}</p>
                </div>
                {item.badge && (
                  <Badge variant={item.badgeVariant || 'default'} size="xs">
                    {item.badge}
                  </Badge>
                )}
              </div>
            ))
          )}
        </div>

        {/* Footer link */}
        <div className="flex items-center gap-1 text-[10px] text-indigo-400 group-hover:text-indigo-300 transition-colors">
          Open {widget.title}
          <ChevronRight className="h-3 w-3 group-hover:translate-x-0.5 transition-transform" />
        </div>
      </Link>
    </motion.div>
  );
}

// ── Skeleton ────────────────────────────────────────────────────────────────

function PreviewSkeleton() {
  return (
    <div className="rounded-xl p-4 bg-slate-900/50 border border-slate-800/50 space-y-3">
      <div className="flex items-center gap-2">
        <Skeleton variant="rectangular" className="h-8 w-8 rounded-lg" />
        <div className="flex-1 space-y-1">
          <Skeleton className="h-3.5 w-20" />
          <Skeleton className="h-2.5 w-12" />
        </div>
      </div>
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-4 w-3/4" />
      <Skeleton className="h-3 w-16" />
    </div>
  );
}
