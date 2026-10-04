/**
 * CasesPage — case management with filters, cards, and create modal.
 */

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Plus, Calendar, FileText, Search, Filter,
  AlertTriangle, X, ArrowUpRight, Loader2,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatDate } from '@/lib/utils';
import { PageShell } from '@/components/templates/PageShell';
import { Badge } from '@/components/atoms/Badge';
import { ShareCaseModal } from '../components/ShareCaseModal';
import type { CaseStatus, CasePriority } from '@/types';
import api from '@/lib/api';

const statusVariants: Record<CaseStatus, 'info' | 'warning' | 'purple' | 'default' | 'success'> = {
  created: 'info',
  in_progress: 'warning',
  under_review: 'purple',
  completed: 'success',
  archived: 'default',
};

const priorityVariants: Record<CasePriority, 'danger' | 'warning' | 'info' | 'success'> = {
  critical: 'danger',
  high: 'warning',
  medium: 'info',
  low: 'success',
};

// Internal minimal type mapping for UI
interface LegalCase {
  id: string;
  name: string;
  caseNumber: string;
  description: string;
  status: CaseStatus;
  priority: CasePriority;
  riskLevel: 'critical' | 'high' | 'medium' | 'low' | 'none';
  createdAt: string;
  updatedAt: string;
  tags: string[];
  documentCount: number;
  evidenceCount: number;
}

export function CasesPage() {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<CaseStatus | 'all'>('all');
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState('');
  const [newDesc, setNewDesc] = useState('');
  
  const [shareCaseId, setShareCaseId] = useState<string | null>(null);
  const [shareCaseName, setShareCaseName] = useState<string>('');

  const [cases, setCases] = useState<LegalCase[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    fetchCases();
  }, []);

  async function fetchCases() {
    setIsLoading(true);
    try {
      const [casesRes, docsRes] = await Promise.all([
        api.get('/cases'),
        api.get('/documents?page_size=1000').catch(() => ({ data: { documents: [] } })),
      ]);
      const rawDocs = docsRes.data?.documents || [];
      const casesList = casesRes.data?.cases || [];

      // Map API response to expected LegalCase format with real document aggregates
      const mapped: LegalCase[] = casesList.map((c: any) => {
        // Match documents by case_id, or if there's only 1 primary case associate all current inquiry docs
        const caseDocs = rawDocs.filter((d: any) => d.case_id === c.id || (!d.case_id && casesList.length === 1));
        const docCount = caseDocs.length;
        const hasCritical = caseDocs.some((d: any) => d.doc_metadata?.risk?.overall_risk === 'CRITICAL');
        const hasHigh = caseDocs.some((d: any) => d.doc_metadata?.risk?.overall_risk === 'HIGH');
        const hasMed = caseDocs.some((d: any) => d.doc_metadata?.risk?.overall_risk === 'MEDIUM');
        const riskLevel = hasCritical ? 'critical' : hasHigh ? 'high' : hasMed ? 'medium' : (docCount > 0 ? 'low' : 'none');
        const evidenceCount = caseDocs.reduce((sum: number, d: any) => sum + (d.doc_metadata?.entities?.length || 1), 0);

        return {
          id: c.id,
          name: c.name,
          caseNumber: c.case_number || `CASE-${c.id.split('-')[0].toUpperCase()}`,
          description: c.description || '',
          status: c.status as CaseStatus,
          priority: (c.priority || 'high') as CasePriority,
          riskLevel,
          createdAt: c.created_at,
          updatedAt: c.updated_at,
          tags: c.tags || [],
          documentCount: docCount,
          evidenceCount,
        };
      });
      setCases(mapped);
    } catch (err) {
      console.error('Failed to load cases:', err);
    } finally {
      setIsLoading(false);
    }
  }

  const filteredCases = cases.filter((c) => {
    if (statusFilter !== 'all' && c.status !== statusFilter) return false;
    if (searchQuery && !c.name.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    return true;
  });

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    try {
      await api.post('/cases', { name: newName, description: newDesc });
      setShowCreate(false);
      setNewName('');
      setNewDesc('');
      fetchCases();
    } catch (err) {
      console.error('Failed to create case:', err);
    }
  }

  async function handleDeleteCase(caseId: string, e: React.MouseEvent) {
    e.stopPropagation();
    if (!window.confirm("Are you sure you want to delete this case and its documents?")) return;
    try {
      await api.delete(`/cases/${caseId}`);
      fetchCases();
    } catch (err) {
      console.error('Failed to delete case:', err);
    }
  }

  return (
    <PageShell
      title="Cases"
      description="Manage your legal cases and matters with AI-powered analysis."
      actions={
        <button
          onClick={() => setShowCreate(!showCreate)}
          className={cn(
            'flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium',
            'bg-gradient-to-r from-indigo-500 to-violet-500 text-white',
            'shadow-lg shadow-indigo-500/20 hover:shadow-indigo-500/40',
            'hover:brightness-110 transition-all duration-200'
          )}
        >
          <Plus className="h-4 w-4" />
          New Case
        </button>
      }
    >
      {/* Create Case Modal */}
      <AnimatePresence>
        {showCreate && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <div className="rounded-xl p-5 bg-slate-900/50 backdrop-blur-xl border border-indigo-500/20 shadow-lg shadow-indigo-500/5 mb-4">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-semibold text-slate-200">Create New Case</h3>
                <button onClick={() => setShowCreate(false)} className="p-1 text-slate-500 hover:text-slate-300"><X className="h-4 w-4" /></button>
              </div>
              <form onSubmit={handleCreate} className="space-y-4">
                <div>
                  <label htmlFor="case-name" className="block text-sm font-medium text-slate-300 mb-1.5">Case Name</label>
                  <input id="case-name" type="text" value={newName} onChange={(e) => setNewName(e.target.value)}
                    placeholder="e.g., Smith v. Jones — Document Review"
                    className="w-full px-4 py-2.5 rounded-lg bg-slate-900/80 border border-slate-700 text-slate-100 text-sm placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 transition-all" required />
                </div>
                <div>
                  <label htmlFor="case-desc" className="block text-sm font-medium text-slate-300 mb-1.5">Description</label>
                  <textarea id="case-desc" value={newDesc} onChange={(e) => setNewDesc(e.target.value)}
                    placeholder="Brief description of the case..." rows={2}
                    className="w-full px-4 py-2.5 rounded-lg bg-slate-900/80 border border-slate-700 text-slate-100 text-sm placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 transition-all resize-none" />
                </div>
                <div className="flex gap-3">
                  <button type="submit" className="px-4 py-2 rounded-lg bg-gradient-to-r from-indigo-500 to-violet-500 text-white text-sm font-medium shadow-lg shadow-indigo-500/20 hover:brightness-110 transition-all">
                    Create Case
                  </button>
                  <button type="button" onClick={() => setShowCreate(false)} className="px-4 py-2 rounded-lg text-sm text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 transition-colors">
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row sm:items-center gap-3 mb-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
          <input type="text" value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search cases..."
            className="w-full pl-10 pr-4 py-2 rounded-lg bg-slate-900/60 border border-slate-800/50 text-sm text-slate-200 placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 transition-all" />
        </div>
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-slate-500" />
          {(['all', 'created', 'in_progress', 'under_review', 'completed', 'archived'] as const).map((status) => (
            <button key={status} onClick={() => setStatusFilter(status)}
              className={cn('px-3 py-1.5 rounded-lg text-xs font-medium transition-colors capitalize',
                statusFilter === status ? 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50')}>
              {status === 'all' ? 'All' : status.replace(/_/g, ' ')}
            </button>
          ))}
        </div>
      </div>

      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-20 text-slate-400">
          <Loader2 className="h-8 w-8 animate-spin mb-4 text-indigo-500" />
          <p>Loading cases...</p>
        </div>
      ) : cases.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-slate-500 bg-slate-900/30 rounded-xl border border-slate-800/50 border-dashed">
          <FileText className="h-10 w-10 mb-3 text-slate-600" />
          <p className="text-sm font-medium text-slate-400">No cases found</p>
          <p className="text-xs mt-1">Create a new case to get started.</p>
        </div>
      ) : filteredCases.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-slate-500">
          <Search className="h-10 w-10 mb-3 text-slate-600" />
          <p className="text-sm font-medium text-slate-400">No cases match your filters</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filteredCases.map((c, i) => (
            <motion.div key={c.id} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}>
              <div 
                onClick={() => navigate(`/cases/${c.id}/overview`)}
                className={cn(
                  'group rounded-xl p-5 h-full',
                  'bg-slate-900/50 backdrop-blur-xl border border-slate-800/50',
                  'hover:border-indigo-500/20 hover:shadow-xl hover:shadow-indigo-500/5',
                  'hover:-translate-y-0.5 transition-all duration-300 cursor-pointer'
                )}
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1 min-w-0 pr-2">
                    <h3 className="text-sm font-semibold text-slate-100 leading-snug">{c.name}</h3>
                    <p className="text-[10px] text-slate-600 font-mono mt-0.5">{c.caseNumber}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <button 
                      onClick={(e) => { e.stopPropagation(); setShareCaseId(c.id); setShareCaseName(c.name); }}
                      className="px-2 py-1 bg-slate-800 hover:bg-indigo-500/20 text-slate-400 hover:text-indigo-400 rounded text-[10px] font-semibold transition-colors"
                    >
                      Share
                    </button>
                    <button 
                      onClick={(e) => handleDeleteCase(c.id, e)}
                      className="px-2 py-1 bg-slate-800 hover:bg-red-500/20 text-slate-400 hover:text-red-400 rounded text-[10px] font-semibold transition-colors"
                    >
                      Delete
                    </button>
                    <ArrowUpRight className="h-4 w-4 text-slate-700 group-hover:text-indigo-400 transition-colors shrink-0" />
                  </div>
                </div>

                <p className="text-xs text-slate-500 line-clamp-2 mb-3">{c.description}</p>

                <div className="flex flex-wrap gap-1.5 mb-3">
                  <Badge variant={statusVariants[c.status] || 'default'} size="xs" dot>{c.status.replace(/_/g, ' ')}</Badge>
                  <Badge variant={priorityVariants[c.priority]} size="xs">{c.priority}</Badge>
                  {c.riskLevel !== 'none' && (
                    <Badge variant={c.riskLevel === 'critical' ? 'danger' : c.riskLevel === 'high' ? 'warning' : 'default'} size="xs">
                      {c.riskLevel} risk
                    </Badge>
                  )}
                </div>

                <div className="flex items-center gap-4 pt-3 border-t border-slate-800/30">
                  <div className="flex items-center gap-1.5 text-xs text-slate-500">
                    <FileText className="h-3.5 w-3.5" />
                    <span>{c.documentCount.toLocaleString()} docs</span>
                  </div>
                  <div className="flex items-center gap-1.5 text-xs text-slate-500">
                    <AlertTriangle className="h-3.5 w-3.5" />
                    <span>{c.evidenceCount} evidence</span>
                  </div>
                  <div className="flex items-center gap-1.5 text-xs text-slate-500 ml-auto">
                    <Calendar className="h-3.5 w-3.5" />
                    <span>{formatDate(c.createdAt)}</span>
                  </div>
                </div>

                <div className="flex flex-wrap gap-1 mt-3">
                  {c.tags.map((tag) => (
                    <span key={tag} className="px-1.5 py-0.5 rounded text-[10px] bg-slate-800/60 text-slate-500">{tag}</span>
                  ))}
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      )}

      <ShareCaseModal 
        caseId={shareCaseId || ''} 
        caseName={shareCaseName} 
        show={!!shareCaseId} 
        onClose={() => setShareCaseId(null)} 
      />
    </PageShell>
  );
}
