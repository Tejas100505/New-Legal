import { useState, useCallback, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FileText, ShieldAlert, ShieldCheck, UserCheck, AlertTriangle, CheckCircle2, Loader2, Search, Hash
} from 'lucide-react';
import { cn, formatFileSize } from '@/lib/utils';
import { Badge } from '@/components/atoms/Badge';
import type { LegalDocument } from '@/types';
import api from '@/lib/api';
import { useCaseWorkspace } from '../CaseWorkspaceContext';

export function ReviewTab() {
  const { caseId, caseData } = useCaseWorkspace();
  const navigate = useNavigate();
  const [documents, setDocuments] = useState<LegalDocument[]>([]);
  const [isLoadingDocs, setIsLoadingDocs] = useState(true);
  const [filterState, setFilterState] = useState<'all' | 'flagged' | 'unreviewed' | 'reviewed'>('unreviewed');
  const [searchQuery, setSearchQuery] = useState('');

  const fetchDocuments = useCallback(async () => {
    setIsLoadingDocs(true);
    try {
      const params: Record<string, string> = { page_size: '1000', include_content: 'false' };
      if (caseId) params.case_id = caseId;
      const res = await api.get('/documents', { params });
      const rawDocs = res.data?.documents || [];
      const mapped: LegalDocument[] = rawDocs.map((d: any) => {
        const privAnalysis = d.doc_metadata?.privilege_analysis || null;
        const isPrivileged = privAnalysis ? Boolean(privAnalysis.is_privileged) : (d.status === 'flagged');
        
        return {
          id: d.id,
          name: d.original_filename || d.filename,
          type: 'pdf',
          size: d.file_size,
          status: d.status,
          caseId: d.case_id || 'case_unknown',
          caseName: d.case_id ? `Case ${d.case_id.slice(0, 8)}` : 'Enterprise Discovery',
          isPrivileged,
          doc_metadata: d.doc_metadata || {},
        } as LegalDocument;
      });

      // Sort by triage priority score
      mapped.sort((a, b) => {
        const scoreA = a.doc_metadata?.triage?.priority_score ?? (a.status === 'flagged' ? 88 : 50);
        const scoreB = b.doc_metadata?.triage?.priority_score ?? (b.status === 'flagged' ? 88 : 50);
        return scoreB - scoreA;
      });

      setDocuments(mapped);
    } catch (err) {
      console.error('Failed to load review documents', err);
    } finally {
      setIsLoadingDocs(false);
    }
  }, [caseId]);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  const filteredDocs = useMemo(() => {
    let result = documents;
    
    if (filterState !== 'all') {
      result = result.filter(doc => {
        const isReviewed = doc.status === 'reviewed' || doc.doc_metadata?.review_status === 'reviewed_by_human';
        const isFlagged = doc.status === 'flagged';
        if (filterState === 'flagged') return isFlagged;
        if (filterState === 'reviewed') return isReviewed;
        if (filterState === 'unreviewed') return !isReviewed;
        return true;
      });
    }

    if (searchQuery.trim()) {
      const lowerQ = searchQuery.toLowerCase();
      result = result.filter(doc => doc.name.toLowerCase().includes(lowerQ) || doc.id.toLowerCase().includes(lowerQ));
    }

    return result;
  }, [documents, filterState, searchQuery]);

  const counts = useMemo(() => {
    const unreviewed = documents.filter(d => d.status !== 'reviewed' && d.doc_metadata?.review_status !== 'reviewed_by_human').length;
    const flagged = documents.filter(d => d.status === 'flagged').length;
    const reviewed = documents.filter(d => d.status === 'reviewed' || d.doc_metadata?.review_status === 'reviewed_by_human').length;
    return { all: documents.length, unreviewed, flagged, reviewed };
  }, [documents]);

  const handleOpenDocument = (docId: string) => {
    navigate(`/documents/${docId}`, {
      state: {
        caseId,
        caseName: caseData?.name || 'Case Workspace',
        returnTab: 'review'
      }
    });
  };

  if (isLoadingDocs) {
    return (
      <div className="flex flex-col items-center justify-center p-12 space-y-3" id="case-review-tab">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-500" />
        <p className="text-sm text-slate-400">Loading document review queue…</p>
      </div>
    );
  }

  return (
    <div className="space-y-6" id="case-review-tab">
      {/* Metrics Bar */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="p-3.5 rounded-xl border border-slate-800/80 bg-slate-900/60 flex items-center justify-between">
          <div>
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">Total Queue</span>
            <span className="text-xl font-bold text-slate-100 font-mono">{counts.all}</span>
          </div>
          <div className="h-9 w-9 rounded-lg bg-slate-800 border border-slate-700/50 flex items-center justify-center text-slate-300 shrink-0">
            <FileText className="h-4 w-4" />
          </div>
        </div>
        <div className="p-3.5 rounded-xl border border-slate-800/80 bg-slate-900/60 flex items-center justify-between">
          <div>
            <span className="text-[11px] font-semibold text-indigo-400 uppercase tracking-wider block">Needs Review</span>
            <span className="text-xl font-bold text-slate-100 font-mono">{counts.unreviewed}</span>
          </div>
          <div className="h-9 w-9 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 shrink-0">
            <UserCheck className="h-4 w-4" />
          </div>
        </div>
        <div className="p-3.5 rounded-xl border border-slate-800/80 bg-slate-900/60 flex items-center justify-between">
          <div>
            <span className="text-[11px] font-semibold text-rose-400 uppercase tracking-wider block">Flagged / Escalated</span>
            <span className="text-xl font-bold text-slate-100 font-mono">{counts.flagged}</span>
          </div>
          <div className="h-9 w-9 rounded-lg bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-400 shrink-0">
            <ShieldAlert className="h-4 w-4" />
          </div>
        </div>
        <div className="p-3.5 rounded-xl border border-slate-800/80 bg-slate-900/60 flex items-center justify-between">
          <div>
            <span className="text-[11px] font-semibold text-emerald-400 uppercase tracking-wider block">Reviewed</span>
            <span className="text-xl font-bold text-slate-100 font-mono">{counts.reviewed}</span>
          </div>
          <div className="h-9 w-9 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 shrink-0">
            <ShieldCheck className="h-4 w-4" />
          </div>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3.5 rounded-2xl border border-slate-800/80 bg-slate-900/60 backdrop-blur-md">
        <div className="flex flex-wrap items-center gap-1.5">
          <button
            onClick={() => setFilterState('all')}
            className={cn('px-3 py-1.5 rounded-xl text-xs font-semibold transition-all cursor-pointer', filterState === 'all' ? 'bg-indigo-600 text-white shadow-sm' : 'bg-slate-800/60 hover:bg-slate-800 text-slate-400 hover:text-slate-200')}
          >
            All Documents
          </button>
          <button
            onClick={() => setFilterState('unreviewed')}
            className={cn('px-3 py-1.5 rounded-xl text-xs font-semibold transition-all cursor-pointer', filterState === 'unreviewed' ? 'bg-indigo-600 text-white shadow-sm' : 'bg-slate-800/60 hover:bg-slate-800 text-slate-400 hover:text-slate-200')}
          >
            Needs Review
          </button>
          <button
            onClick={() => setFilterState('flagged')}
            className={cn('px-3 py-1.5 rounded-xl text-xs font-semibold transition-all cursor-pointer', filterState === 'flagged' ? 'bg-rose-600 text-white shadow-sm' : 'bg-slate-800/60 hover:bg-slate-800 text-slate-400 hover:text-slate-200')}
          >
            Flagged
          </button>
          <button
            onClick={() => setFilterState('reviewed')}
            className={cn('px-3 py-1.5 rounded-xl text-xs font-semibold transition-all cursor-pointer', filterState === 'reviewed' ? 'bg-emerald-600 text-white shadow-sm' : 'bg-slate-800/60 hover:bg-slate-800 text-slate-400 hover:text-slate-200')}
          >
            Reviewed
          </button>
        </div>
        <div className="relative w-full sm:w-64 shrink-0">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <Search className="h-4 w-4 text-slate-500" />
          </div>
          <input
            type="text"
            placeholder="Search filenames or IDs..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-slate-950/50 border border-slate-800 rounded-xl pl-9 pr-3 py-1.5 text-xs text-slate-200 placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 transition-all"
          />
        </div>
      </div>

      {/* Queue List */}
      <div className="bg-slate-900/40 rounded-2xl border border-slate-800/80 overflow-hidden shadow-sm">
        {filteredDocs.length === 0 ? (
          <div className="p-12 text-center text-slate-400 text-sm">
            No documents found matching the current filters.
          </div>
        ) : (
          <div className="divide-y divide-slate-800/60">
            {filteredDocs.map(doc => {
              const triage = doc.doc_metadata?.triage;
              const isReviewed = doc.status === 'reviewed' || doc.doc_metadata?.review_status === 'reviewed_by_human';
              
              return (
                <div key={doc.id} className="p-4 hover:bg-slate-800/40 transition-colors flex flex-col sm:flex-row sm:items-center justify-between gap-4 group">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <FileText className="h-4 w-4 text-slate-400 shrink-0" />
                      <h4 className="text-sm font-semibold text-slate-200 truncate cursor-pointer hover:text-indigo-400 transition-colors" onClick={() => handleOpenDocument(doc.id)}>
                        {doc.name}
                      </h4>
                      {doc.isPrivileged && (
                        <Badge variant="purple" size="xs" className="shrink-0 flex items-center gap-1">
                          <ShieldAlert className="h-3 w-3" /> Privileged
                        </Badge>
                      )}
                      {triage?.escalation_flag && (
                        <Badge variant="warning" size="xs" className="shrink-0 flex items-center gap-1">
                          <AlertTriangle className="h-3 w-3" /> Escalated
                        </Badge>
                      )}
                    </div>
                    
                    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-1.5 text-[11px] text-slate-500 font-mono">
                      <span className="flex items-center gap-1 text-slate-400"><Hash className="h-3 w-3" /> {doc.id.slice(0, 8)}</span>
                      <span>•</span>
                      <span>{doc.size ? formatFileSize(doc.size) : 'Unknown size'}</span>
                      {triage?.priority_tier && (
                        <>
                          <span>•</span>
                          <span className={cn(
                            "font-semibold",
                            triage.priority_tier === 'CRITICAL' ? 'text-rose-400' :
                            triage.priority_tier === 'HIGH' ? 'text-amber-400' : 'text-indigo-400'
                          )}>
                            Priority: {triage.priority_tier} ({triage.priority_score?.toFixed(0)})
                          </span>
                        </>
                      )}
                      {doc.doc_metadata?.document_type && (
                        <>
                          <span>•</span>
                          <span className="uppercase text-slate-400">{doc.doc_metadata.document_type}</span>
                        </>
                      )}
                    </div>

                    {triage?.reasoning && !isReviewed && (
                      <p className="mt-2 text-xs text-slate-400 line-clamp-1 italic max-w-3xl border-l-2 border-slate-700 pl-2">
                        {triage.reasoning}
                      </p>
                    )}
                  </div>

                  <div className="flex items-center gap-3 shrink-0">
                    {isReviewed ? (
                      <div className="flex items-center gap-1.5 text-[11px] text-emerald-400 font-semibold uppercase px-2.5 py-1 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
                        <CheckCircle2 className="h-3.5 w-3.5" /> Reviewed
                      </div>
                    ) : (
                      <div className="flex items-center gap-1.5 text-[11px] text-amber-400 font-semibold uppercase px-2.5 py-1 rounded-lg bg-amber-500/10 border border-amber-500/20">
                        <AlertTriangle className="h-3.5 w-3.5" /> Pending Review
                      </div>
                    )}
                    <button
                      onClick={() => handleOpenDocument(doc.id)}
                      className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition-all shadow-sm flex items-center gap-1.5 cursor-pointer"
                    >
                      Open Document
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
