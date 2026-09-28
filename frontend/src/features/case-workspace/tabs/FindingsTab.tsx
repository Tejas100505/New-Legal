import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  ShieldAlert,
  Lock,
  AlertTriangle,
  Search,
  CheckCircle2,
  FileCheck2,
} from 'lucide-react';
import api from '@/lib/api';
import { Spinner } from '@/components/atoms/Spinner';
import { useCaseWorkspace } from '../CaseWorkspaceContext';
import { FindingCard, type FindingItem, type FindingCategory } from '../components/FindingCard';

export function FindingsTab() {
  const { caseId, caseData } = useCaseWorkspace();
  const [selectedCategory, setSelectedCategory] = useState<FindingCategory | 'all'>('all');
  const [searchQuery, setSearchQuery] = useState('');

  // Fetch documents for the case with metadata (no heavy content)
  const { data, isLoading, error } = useQuery({
    queryKey: ['case-findings', caseId],
    queryFn: async () => {
      const res = await api.get('/documents', {
        params: {
          case_id: caseId,
          page_size: 1000,
          include_content: false,
        },
      });
      return res.data?.documents || [];
    },
    enabled: Boolean(caseId),
    staleTime: 60000,
  });

  // Extract structured findings from real metadata
  const allFindings = useMemo<FindingItem[]>(() => {
    if (!data || !Array.isArray(data)) return [];

    const findings: FindingItem[] = [];

    for (const doc of data) {
      const meta = doc.doc_metadata || {};
      const pa = meta.privilege_analysis || {};
      const ra = meta.risk_analysis || meta.risk || {};
      const triage = meta.triage || {};

      // 1. Privilege Findings (Substantive PrivilegeAgent determination only)
      const isPriv = pa.is_privileged === true;
      if (isPriv) {
        let privType: string | null = null;
        if (Array.isArray(pa.detections)) {
          const matched = pa.detections.find((d: any) => d.detected);
          if (matched) privType = matched.privilege_type;
        }
        if (!privType) {
          privType = 'Legal Counsel / Work Product Protection';
        }

        findings.push({
          id: doc.id,
          filename: doc.original_filename || doc.filename,
          category: 'privilege',
          title: `Privilege Protection: ${privType}`,
          badgeLabel: 'Privileged',
          badgeVariant: 'purple',
          details: {
            privilegeType: privType,
            privilegeReasoning: pa.reasoning || null,
            confidence: pa.confidence ?? null,
            evidenceSpans: pa.evidence_spans || null,
            documentType: meta.document_type || null,
          },
        });
      }

      // 2. Risk Findings (High / Critical)
      const assessments = ra.assessments || [];
      const highReasons: string[] = [];
      let maxRiskLevel: string | null = null;

      if (Array.isArray(assessments)) {
        for (const a of assessments) {
          const lvl = (a.risk_level || '').toUpperCase();
          if (lvl === 'HIGH' || lvl === 'CRITICAL') {
            maxRiskLevel = lvl;
            const categoryLabel = a.category || 'Risk Exposure';
            const reason = a.reason || 'High risk pattern identified';
            highReasons.push(`${categoryLabel}: ${reason}`);
          }
        }
      }

      const overallRisk = (ra.risk_level || ra.overall_risk || '').toUpperCase();
      if (!highReasons.length && (overallRisk === 'HIGH' || overallRisk === 'CRITICAL')) {
        maxRiskLevel = overallRisk;
        highReasons.push(ra.summary || 'Significant operational or compliance exposure detected.');
      }

      if (highReasons.length > 0) {
        findings.push({
          id: doc.id,
          filename: doc.original_filename || doc.filename,
          category: 'risk',
          title: `${maxRiskLevel || 'HIGH'} Risk Exposure`,
          badgeLabel: maxRiskLevel || 'High Risk',
          badgeVariant: 'danger',
          details: {
            riskLevel: maxRiskLevel,
            riskScore: ra.risk_score ?? ra.score ?? null,
            riskReasons: highReasons,
            documentType: meta.document_type || null,
          },
        });
      }

      // 3. Triage / Escalation Findings
      const isEscalated =
        doc.status === 'flagged' ||
        meta.is_escalated === true ||
        triage.escalation_flag === true;

      if (isEscalated) {
        findings.push({
          id: doc.id,
          filename: doc.original_filename || doc.filename,
          category: 'escalation',
          title: 'Mandatory Review Required',
          badgeLabel: 'Triage Escalated',
          badgeVariant: 'warning',
          details: {
            escalationReason: triage.escalation_reason || triage.reasoning || null,
            priorityTier: triage.priority_tier || 'CRITICAL',
            priorityScore: triage.priority_score ?? null,
            recommendedAction: triage.recommended_action || 'IMMEDIATE_HUMAN_REVIEW',
            documentType: meta.document_type || null,
          },
        });
      }
    }

    return findings;
  }, [data]);

  // Aggregate Category Counts
  const counts = useMemo(() => {
    const priv = allFindings.filter((f) => f.category === 'privilege').length;
    const risk = allFindings.filter((f) => f.category === 'risk').length;
    const esc = allFindings.filter((f) => f.category === 'escalation').length;
    return {
      total: allFindings.length,
      privilege: priv,
      risk,
      escalation: esc,
    };
  }, [allFindings]);

  // Filtered & Searched Findings
  const filteredFindings = useMemo(() => {
    return allFindings.filter((finding) => {
      // Category Filter
      if (selectedCategory !== 'all' && finding.category !== selectedCategory) {
        return false;
      }

      // Search Query Filter
      if (searchQuery.trim()) {
        const query = searchQuery.toLowerCase();
        const matchesFilename = finding.filename.toLowerCase().includes(query);
        const matchesType = finding.details.privilegeType?.toLowerCase().includes(query) || false;
        const matchesReasoning =
          finding.details.privilegeReasoning?.toLowerCase().includes(query) ||
          finding.details.escalationReason?.toLowerCase().includes(query) ||
          finding.details.riskReasons?.some((r) => r.toLowerCase().includes(query)) ||
          false;

        return matchesFilename || matchesType || matchesReasoning;
      }

      return true;
    });
  }, [allFindings, selectedCategory, searchQuery]);

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center p-12 space-y-3" id="case-findings-tab">
        <Spinner size="lg" />
        <p className="text-sm text-slate-400">Loading consolidated case findings…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 rounded-2xl border border-rose-500/30 bg-rose-500/10 text-rose-300 text-sm">
        Failed to load findings. Please reload the workspace or verify network connection.
      </div>
    );
  }

  return (
    <div className="space-y-6" id="case-findings-tab">
      {/* ── Top Summary Metric Bar ───────────────────────────────── */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="p-3.5 rounded-xl border border-slate-800/80 bg-slate-900/60 flex items-center justify-between">
          <div>
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
              Total Findings
            </span>
            <span className="text-xl font-bold text-slate-100 font-mono">
              {counts.total}
            </span>
          </div>
          <div className="h-9 w-9 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 shrink-0">
            <FileCheck2 className="h-4 w-4" />
          </div>
        </div>

        <div className="p-3.5 rounded-xl border border-slate-800/80 bg-slate-900/60 flex items-center justify-between">
          <div>
            <span className="text-[11px] font-semibold text-violet-400 uppercase tracking-wider block">
              Privileged
            </span>
            <span className="text-xl font-bold text-slate-100 font-mono">
              {counts.privilege}
            </span>
          </div>
          <div className="h-9 w-9 rounded-lg bg-violet-500/10 border border-violet-500/20 flex items-center justify-center text-violet-400 shrink-0">
            <Lock className="h-4 w-4" />
          </div>
        </div>

        <div className="p-3.5 rounded-xl border border-slate-800/80 bg-slate-900/60 flex items-center justify-between">
          <div>
            <span className="text-[11px] font-semibold text-rose-400 uppercase tracking-wider block">
              High / Critical Risk
            </span>
            <span className="text-xl font-bold text-slate-100 font-mono">
              {counts.risk}
            </span>
          </div>
          <div className="h-9 w-9 rounded-lg bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-400 shrink-0">
            <ShieldAlert className="h-4 w-4" />
          </div>
        </div>

        <div className="p-3.5 rounded-xl border border-slate-800/80 bg-slate-900/60 flex items-center justify-between">
          <div>
            <span className="text-[11px] font-semibold text-amber-400 uppercase tracking-wider block">
              Triage Escalated
            </span>
            <span className="text-xl font-bold text-slate-100 font-mono">
              {counts.escalation}
            </span>
          </div>
          <div className="h-9 w-9 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400 shrink-0">
            <AlertTriangle className="h-4 w-4" />
          </div>
        </div>
      </div>

      {/* ── Filter Bar & Search ──────────────────────────────────── */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3.5 rounded-2xl border border-slate-800/80 bg-slate-900/60 backdrop-blur-md">
        {/* Category Filter Pills */}
        <div className="flex flex-wrap items-center gap-1.5">
          <button
            type="button"
            id="filter-btn-all"
            onClick={() => setSelectedCategory('all')}
            className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
              selectedCategory === 'all'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'bg-slate-800/60 hover:bg-slate-800 text-slate-400 hover:text-slate-200'
            }`}
          >
            All Findings ({counts.total})
          </button>
          <button
            type="button"
            id="filter-btn-privilege"
            onClick={() => setSelectedCategory('privilege')}
            className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
              selectedCategory === 'privilege'
                ? 'bg-violet-600 text-white shadow-sm'
                : 'bg-slate-800/60 hover:bg-slate-800 text-slate-400 hover:text-slate-200'
            }`}
          >
            Privileged ({counts.privilege})
          </button>
          <button
            type="button"
            id="filter-btn-risk"
            onClick={() => setSelectedCategory('risk')}
            className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
              selectedCategory === 'risk'
                ? 'bg-rose-600 text-white shadow-sm'
                : 'bg-slate-800/60 hover:bg-slate-800 text-slate-400 hover:text-slate-200'
            }`}
          >
            High Risk ({counts.risk})
          </button>
          <button
            type="button"
            id="filter-btn-escalation"
            onClick={() => setSelectedCategory('escalation')}
            className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
              selectedCategory === 'escalation'
                ? 'bg-amber-600 text-white shadow-sm'
                : 'bg-slate-800/60 hover:bg-slate-800 text-slate-400 hover:text-slate-200'
            }`}
          >
            Escalations ({counts.escalation})
          </button>
        </div>

        {/* Search Input */}
        <div className="relative w-full sm:w-64">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-500" />
          <input
            type="text"
            placeholder="Search findings…"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 rounded-xl bg-slate-950/70 border border-slate-800 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-indigo-500/50"
          />
        </div>
      </div>

      {/* ── Findings List Grid ───────────────────────────────────── */}
      {counts.total === 0 ? (
        <div className="p-12 text-center rounded-2xl border border-slate-800/80 bg-slate-900/40 space-y-3">
          <div className="h-12 w-12 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 mx-auto">
            <CheckCircle2 className="h-6 w-6" />
          </div>
          <h3 className="text-base font-bold text-slate-100">
            No Findings Requiring Review
          </h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto leading-relaxed">
            All processed documents in {caseData?.name || 'this case'} are currently cleared without privilege claims, high risk exposure, or triage escalation flags.
          </p>
        </div>
      ) : filteredFindings.length === 0 ? (
        <div className="p-8 text-center rounded-2xl border border-slate-800/80 bg-slate-900/40 text-slate-400 text-xs">
          No findings match the current filter or search criteria.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" id="findings-grid">
          {filteredFindings.map((finding) => (
            <FindingCard key={`${finding.id}-${finding.category}`} finding={finding} />
          ))}
        </div>
      )}
    </div>
  );
}
