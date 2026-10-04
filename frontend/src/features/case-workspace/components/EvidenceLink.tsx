import { Link, useParams, useLocation } from 'react-router-dom';
import { FileText, ExternalLink } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface EvidenceLinkProps {
  documentId: string;
  filename: string;
  caseId?: string;
  returnTab?: string;
  className?: string;
  showIcon?: boolean;
  showExternalIcon?: boolean;
  variant?: 'default' | 'subtle' | 'badge';
  title?: string;
}

export function EvidenceLink({
  documentId,
  filename,
  caseId,
  returnTab,
  className,
  showIcon = true,
  showExternalIcon = true,
  variant = 'default',
  title,
}: EvidenceLinkProps) {
  const defaultTitle = title || `View source document: ${filename}`;
  const routeParams = useParams<{ caseId?: string }>();
  const location = useLocation();

  const activeCaseId = caseId || routeParams.caseId;
  const currentTab = location.pathname.split('/').filter(Boolean).pop() || 'evidence';
  const activeReturnTab = returnTab || (currentTab !== activeCaseId ? currentTab : 'evidence');

  const navState = activeCaseId ? { caseId: activeCaseId, returnTab: activeReturnTab } : undefined;

  if (variant === 'badge') {
    return (
      <Link
        to={`/documents/${documentId}`}
        state={navState}
        title={defaultTitle}
        className={cn(
          'inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-medium font-mono',
          'bg-slate-800/80 hover:bg-slate-800 text-slate-300 hover:text-indigo-300 border border-slate-700/60 hover:border-indigo-500/40',
          'transition-all duration-150 group max-w-full truncate',
          className
        )}
      >
        {showIcon && <FileText className="h-3 w-3 text-slate-400 group-hover:text-indigo-400 shrink-0" />}
        <span className="truncate">{filename}</span>
        {showExternalIcon && (
          <ExternalLink className="h-2.5 w-2.5 opacity-60 group-hover:opacity-100 text-indigo-400 shrink-0 ml-0.5" />
        )}
      </Link>
    );
  }

  if (variant === 'subtle') {
    return (
      <Link
        to={`/documents/${documentId}`}
        state={navState}
        title={defaultTitle}
        className={cn(
          'inline-flex items-center gap-1 text-[11px] text-slate-400 hover:text-indigo-300 transition-colors group truncate',
          className
        )}
      >
        {showIcon && <FileText className="h-3 w-3 shrink-0 text-slate-500 group-hover:text-indigo-400" />}
        <span className="truncate">{filename}</span>
        {showExternalIcon && <ExternalLink className="h-2.5 w-2.5 shrink-0 opacity-60 group-hover:opacity-100" />}
      </Link>
    );
  }

  return (
    <Link
      to={`/documents/${documentId}`}
      state={navState}
      title={defaultTitle}
      className={cn(
        'inline-flex items-center gap-1.5 text-xs font-semibold text-slate-200 hover:text-indigo-300 transition-colors group truncate',
        className
      )}
    >
      {showIcon && (
        <FileText className="h-3.5 w-3.5 text-slate-400 shrink-0 group-hover:text-indigo-400 transition-colors" />
      )}
      <span className="truncate">{filename}</span>
      {showExternalIcon && (
        <ExternalLink className="h-3 w-3 opacity-60 group-hover:opacity-100 text-indigo-400 transition-opacity shrink-0 ml-0.5" />
      )}
    </Link>
  );
}
