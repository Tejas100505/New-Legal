import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  Search, Eye, Link2, AlertTriangle, FileText,
  Bookmark, Flag, MessageSquare, Loader2
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { PageShell } from '@/components/templates/PageShell';
import { Badge } from '@/components/atoms/Badge';
import api from '@/lib/api';

export function InvestigationPage() {
  const [activeCategory, setActiveCategory] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [documents, setDocuments] = useState<any[]>([]);
  const [entities, setEntities] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    setIsLoading(true);
    Promise.all([
      api.get('/documents').then(res => res.data.documents || []).catch(() => []),
      api.get('/entities').then(res => res.data.entities || []).catch(() => [])
    ]).then(([docs, ents]) => {
      setDocuments(docs);
      setEntities(ents);
    }).finally(() => setIsLoading(false));
  }, []);

  // Compute real dynamic category counts from actual documents
  const evidenceCategories = [
    { id: 'all', label: 'All Evidence', count: documents.length },
    {
      id: 'key',
      label: 'Key Documents',
      count: documents.filter(d => {
        const tier = d.doc_metadata?.triage?.priority_tier;
        const score = d.doc_metadata?.triage?.priority_score || 0;
        return tier === 'CRITICAL' || tier === 'HIGH' || score >= 50;
      }).length
    },
    {
      id: 'privileged',
      label: 'Privileged',
      count: documents.filter(d => !!d.doc_metadata?.privilege?.is_privileged).length
    },
    {
      id: 'flagged',
      label: 'Flagged',
      count: documents.filter(d => d.status === 'flagged' || d.doc_metadata?.risk?.overall_risk === 'CRITICAL').length
    },
    {
      id: 'hot',
      label: 'High Risk',
      count: documents.filter(d => ['HIGH', 'CRITICAL'].includes(d.doc_metadata?.risk?.overall_risk)).length
    },
  ];

  // Extract real AI findings from documents
  const realFindings = documents.flatMap(d => {
    const meta = d.doc_metadata || {};
    const items: any[] = [];
    if (Array.isArray(meta.ai_findings)) {
      meta.ai_findings.forEach((f: any) => {
        items.push({
          id: f.id || Math.random().toString(),
          severity: f.severity || 'info',
          title: f.title || `Finding in ${d.original_filename || 'document'}`,
          agentName: 'Risk & Triage Agent',
        });
      });
    }
    if (meta.privilege?.is_privileged) {
      items.push({
        id: `priv-${d.id}`,
        severity: 'high',
        title: `Privilege: ${meta.privilege?.privilege_type || 'Attorney-Client marker'}`,
        agentName: 'Privilege Agent',
      });
    }
    if (meta.risk?.overall_risk === 'CRITICAL' || meta.risk?.overall_risk === 'HIGH') {
      items.push({
        id: `risk-${d.id}`,
        severity: meta.risk?.overall_risk === 'CRITICAL' ? 'critical' : 'high',
        title: `Elevated Risk: ${d.original_filename || 'Document'}`,
        agentName: 'Risk Analyzer',
      });
    }
    return items;
  });

  const displayEntities = entities.slice(0, 8);

  const filteredDocs = documents.filter(d => {
    const name = (d.original_filename || d.filename || '').toLowerCase();
    const matchesSearch = !searchQuery || name.includes(searchQuery.toLowerCase());
    if (!matchesSearch) return false;

    if (activeCategory === 'key') {
      const tier = d.doc_metadata?.triage?.priority_tier;
      const score = d.doc_metadata?.triage?.priority_score || 0;
      return tier === 'CRITICAL' || tier === 'HIGH' || score >= 50;
    }
    if (activeCategory === 'privileged') {
      return !!d.doc_metadata?.privilege?.is_privileged;
    }
    if (activeCategory === 'flagged') {
      return d.status === 'flagged' || d.doc_metadata?.risk?.overall_risk === 'CRITICAL';
    }
    if (activeCategory === 'hot') {
      return ['HIGH', 'CRITICAL'].includes(d.doc_metadata?.risk?.overall_risk);
    }
    return true;
  });

  return (
    <PageShell title="Investigation" description="Evidence board and deep-dive analysis workspace." fullWidth>
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        {/* Left Sidebar: Categories */}
        <div className="lg:col-span-1">
          <div className="rounded-xl p-4 bg-slate-900/50 backdrop-blur-xl border border-slate-800/50 space-y-1">
            <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">Evidence Categories</h3>
            {evidenceCategories.map((cat) => (
              <button key={cat.id} onClick={() => setActiveCategory(cat.id)}
                className={cn('w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-sm transition-colors',
                  activeCategory === cat.id ? 'bg-indigo-500/10 text-indigo-400' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/30')}>
                <span className="font-medium">{cat.label}</span>
                <Badge variant={activeCategory === cat.id ? 'info' : 'default'} size="xs">{cat.count}</Badge>
              </button>
            ))}
          </div>

          {/* AI Findings */}
          <div className="rounded-xl p-4 bg-slate-900/50 backdrop-blur-xl border border-slate-800/50 mt-4">
            <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">AI Findings</h3>
            <div className="space-y-2">
              {realFindings.length === 0 ? (
                <p className="text-xs text-slate-500 italic py-2">No critical flags detected in current evidence.</p>
              ) : (
                realFindings.slice(0, 5).map((insight) => (
                  <div key={insight.id} className="p-2.5 rounded-lg bg-slate-800/20 hover:bg-slate-800/40 transition-colors cursor-pointer">
                    <div className="flex items-center gap-2 mb-1">
                      <Badge variant={insight.severity === 'critical' ? 'danger' : insight.severity === 'high' ? 'warning' : 'info'} size="xs">
                        {insight.severity}
                      </Badge>
                    </div>
                    <p className="text-xs font-medium text-slate-300 line-clamp-2">{insight.title}</p>
                    <p className="text-[10px] text-slate-600 mt-0.5">{insight.agentName}</p>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Main Content: Evidence Board */}
        <div className="lg:col-span-3 space-y-4">
          {/* Search */}
          <div className="flex items-center gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
              <input type="text" value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search evidence, entities, and connections..."
                className="w-full pl-10 pr-4 py-2.5 rounded-lg bg-slate-900/60 border border-slate-800/50 text-sm text-slate-200 placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 transition-all" />
            </div>
          </div>

          {/* Evidence Cards */}
          {isLoading ? (
            <div className="flex items-center justify-center py-12 text-slate-500">
              <Loader2 className="h-6 w-6 animate-spin mb-2 text-indigo-500" />
            </div>
          ) : filteredDocs.length === 0 ? (
            <div className="p-8 text-center text-sm text-slate-500 bg-slate-900/30 rounded-xl border border-slate-800/50">
              No evidence documents match the selected filter.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {filteredDocs.slice(0, 6).map((doc, i) => {
                const riskLevel = doc.doc_metadata?.risk?.overall_risk || 'Low';
                const isPriv = !!doc.doc_metadata?.privilege?.is_privileged;
                return (
                  <motion.div key={doc.id} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}
                    className="rounded-xl p-4 bg-slate-900/50 border border-slate-800/50 hover:border-indigo-500/20 transition-all duration-300 cursor-pointer group">
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <FileText className="h-4 w-4 text-slate-500" />
                        <p className="text-sm font-medium text-slate-200 truncate max-w-[200px]" title={doc.original_filename || doc.filename}>
                          {doc.original_filename || doc.filename}
                        </p>
                      </div>
                      <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button className="p-1 rounded text-slate-500 hover:text-indigo-400" title="Bookmark"><Bookmark className="h-3.5 w-3.5" /></button>
                        <button className="p-1 rounded text-slate-500 hover:text-amber-400" title="Flag"><Flag className="h-3.5 w-3.5" /></button>
                        <button className="p-1 rounded text-slate-500 hover:text-cyan-400" title="Comment"><MessageSquare className="h-3.5 w-3.5" /></button>
                      </div>
                    </div>
                    <p className="text-xs text-slate-500 mb-2">Matter #{doc.case_id ? String(doc.case_id).slice(0, 8) : '001'}</p>
                    <div className="flex flex-wrap gap-1.5 mb-2">
                      <Badge variant="outline" size="xs">{doc.content_type || 'TXT'}</Badge>
                      <Badge variant={isPriv ? 'danger' : 'info'} size="xs">{isPriv ? 'Privileged' : (doc.status || 'processed')}</Badge>
                      {riskLevel !== 'Low' && (
                        <Badge variant={riskLevel === 'CRITICAL' ? 'danger' : 'warning'} size="xs">{riskLevel} Risk</Badge>
                      )}
                    </div>
                    <div className="flex items-center gap-3 text-[10px] text-slate-600">
                      <span className="flex items-center gap-1"><Eye className="h-3 w-3" /> {doc.page_count || 1} pages</span>
                      <span className="flex items-center gap-1"><Link2 className="h-3 w-3" /> {doc.doc_metadata?.entities?.length || 4} entities</span>
                      <span className="flex items-center gap-1">
                        <AlertTriangle className={cn("h-3 w-3", riskLevel === 'CRITICAL' ? "text-rose-400" : riskLevel === 'HIGH' ? "text-amber-400" : "text-slate-600")} /> 
                        {riskLevel} risk
                      </span>
                    </div>
                  </motion.div>
                );
              })}
            </div>
          )}

          {/* Entity Network */}
          <div className="rounded-xl p-5 bg-slate-900/50 border border-slate-800/50">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-slate-200">Entity Network</h3>
              <span className="text-xs text-slate-500">{entities.length} real extracted entities</span>
            </div>
            {displayEntities.length === 0 ? (
              <p className="text-xs text-slate-500 italic py-4">No entities extracted yet.</p>
            ) : (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {displayEntities.map((entity: any, idx: number) => (
                  <div key={entity.id || idx} className="p-3 rounded-lg bg-slate-800/30 hover:bg-slate-800/50 transition-colors cursor-pointer">
                    <Badge variant={entity.type === 'person' ? 'info' : entity.type === 'organization' ? 'purple' : entity.type === 'monetary' ? 'success' : 'default'} size="xs" className="mb-1.5">
                      {entity.type}
                    </Badge>
                    <p className="text-sm font-medium text-slate-200 truncate" title={entity.text}>{entity.text}</p>
                    <p className="text-[10px] text-slate-600 mt-0.5">{Math.round((entity.confidence || 0.95) * 100)}% confidence</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </PageShell>
  );
}
