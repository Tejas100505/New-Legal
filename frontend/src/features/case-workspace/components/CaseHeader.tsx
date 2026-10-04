import { Link } from 'react-router-dom';
import {
  FolderGit2, CheckSquare, ShieldAlert, Network,
  History, MessageSquareCode, FileBarChart2, Calendar,
  Tag, Clock
} from 'lucide-react';
import { Badge } from '@/components/atoms/Badge';
import type { LegalCase } from '@/types';

interface CaseHeaderProps {
  caseData: LegalCase | null;
  caseId: string;
  totalDocs?: number;
}

export function CaseHeader({ caseData, caseId, totalDocs }: CaseHeaderProps) {
  const formatDate = (isoString?: string) => {
    if (!isoString) return '—';
    try {
      return new Date(isoString).toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      });
    } catch {
      return isoString;
    }
  };

  const priorityVariant = caseData?.priority === 'critical' ? 'danger'
    : caseData?.priority === 'high' ? 'warning'
    : caseData?.priority === 'medium' ? 'info'
    : 'default';

  const statusVariant = caseData?.status === 'completed' ? 'success'
    : caseData?.status === 'in_progress' ? 'warning'
    : caseData?.status === 'under_review' ? 'purple'
    : caseData?.status === 'created' ? 'info'
    : 'default';

  const launchLinks = [
    { label: 'Evidence', path: 'evidence', icon: FolderGit2, badge: totalDocs !== undefined ? `${totalDocs}` : undefined },
    { label: 'Review Queue', path: 'review', icon: CheckSquare },
    { label: 'Findings', path: 'findings', icon: ShieldAlert },
    { label: 'Relationships', path: 'relationships', icon: Network },
    { label: 'Timeline', path: 'timeline', icon: History },
    { label: 'Ask AI', path: 'ask', icon: MessageSquareCode },
    { label: 'Report', path: 'report', icon: FileBarChart2 },
  ];

  return (
    <div className="rounded-2xl border border-slate-800/80 bg-slate-900/40 backdrop-blur-sm p-5 space-y-4 shadow-sm" id="case-home-header">
      {/* ── Top Bar: Title, Case Number & Status Badges ────────────── */}
      <div className="flex flex-col md:flex-row md:items-start justify-between gap-4 border-b border-slate-800/60 pb-4">
        <div className="space-y-1.5 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-mono text-indigo-400 font-semibold px-2 py-0.5 rounded bg-indigo-500/10 border border-indigo-500/20" id="case-home-number">
              {caseData?.caseNumber || (caseId ? `CASE-${caseId.slice(0, 8).toUpperCase()}` : 'MATTER')}
            </span>
            {caseData?.status && (
              <Badge variant={statusVariant} size="xs" dot>
                {caseData.status.replace(/_/g, ' ').toUpperCase()}
              </Badge>
            )}
            {caseData?.priority && (
              <Badge variant={priorityVariant} size="xs">
                {caseData.priority.toUpperCase()} PRIORITY
              </Badge>
            )}
          </div>

          <h1 className="text-xl sm:text-2xl font-bold text-slate-100 tracking-tight truncate" title={caseData?.name} id="case-home-title">
            {caseData?.name || 'Case Matter Overview'}
          </h1>

          {caseData?.description ? (
            <p className="text-xs text-slate-400 max-w-3xl leading-relaxed pt-0.5">
              {caseData.description}
            </p>
          ) : null}
        </div>

        {/* Matter Metadata Meta Column */}
        <div className="flex items-center gap-4 text-xs text-slate-400 shrink-0 flex-wrap">
          <div className="flex items-center gap-1.5" title="Matter Ingestion Date">
            <Calendar className="h-3.5 w-3.5 text-slate-500" />
            <span>Opened: <strong className="text-slate-300 font-medium">{formatDate(caseData?.createdAt)}</strong></span>
          </div>
          {caseData?.updatedAt && (
            <div className="flex items-center gap-1.5" title="Last Record Modification">
              <Clock className="h-3.5 w-3.5 text-slate-500" />
              <span>Updated: <strong className="text-slate-300 font-medium">{formatDate(caseData.updatedAt)}</strong></span>
            </div>
          )}
          {caseData?.tags && Array.isArray(caseData.tags) && caseData.tags.length > 0 && (
            <div className="flex items-center gap-1.5">
              <Tag className="h-3.5 w-3.5 text-slate-500" />
              <div className="flex items-center gap-1">
                {caseData.tags.map((t, idx) => (
                  <span key={idx} className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700/60 font-mono">
                    {t}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── Launchpad Action Links ─────────────────────────────────── */}
      <div>
        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block mb-2">
          Investigation Launchpad
        </span>
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2">
          {launchLinks.map((link) => {
            const Icon = link.icon;
            return (
              <Link
                key={link.path}
                to={`/cases/${caseId}/${link.path}`}
                className="flex items-center justify-between gap-1.5 px-3 py-2 rounded-xl bg-slate-950/60 hover:bg-slate-800/80 border border-slate-800 hover:border-slate-700 text-slate-300 hover:text-white text-xs font-medium transition-all group shadow-sm"
                title={`Open ${link.label}`}
                id={`launchpad-link-${link.path}`}
              >
                <div className="flex items-center gap-2 truncate">
                  <Icon className="h-3.5 w-3.5 text-indigo-400 group-hover:text-indigo-300 shrink-0 transition-colors" />
                  <span className="truncate">{link.label}</span>
                </div>
                {link.badge && (
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 group-hover:text-slate-200 shrink-0">
                    {link.badge}
                  </span>
                )}
              </Link>
            );
          })}
        </div>
      </div>
    </div>
  );
}
