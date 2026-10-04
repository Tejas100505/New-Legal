import { Link } from 'react-router-dom';
import { Users, Network, ArrowUpRight, ChevronRight, User, Building2 } from 'lucide-react';
import { Badge } from '@/components/atoms/Badge';

interface KeyEntitiesStripProps {
  caseId: string;
  topEntities?: Array<{
    name: string;
    type: string;
    weighted_degree?: number;
    top_edges?: Array<{
      target: string;
      weight: number;
      relation?: string;
      shared_docs: number;
    }>;
  }>;
  hasSummary?: boolean;
}

export function KeyEntitiesStrip({ caseId, topEntities = [], hasSummary = false }: KeyEntitiesStripProps) {
  const displayedEntities = (topEntities || []).slice(0, 6);

  return (
    <div className="rounded-2xl border border-slate-800/80 bg-slate-900/40 p-5 backdrop-blur-sm space-y-4 shadow-sm" id="key-entities-section">
      {/* ── Section Header ────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800/60 pb-3">
        <div className="flex items-center gap-2.5">
          <div className="h-8 w-8 rounded-lg bg-violet-500/10 border border-violet-500/20 flex items-center justify-center text-violet-400">
            <Users className="h-4 w-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-semibold text-slate-100">Key People & Organizations</h3>
              <Badge variant="purple" size="xs">
                {topEntities.length > 0 ? `${topEntities.length} Primary Actors` : 'Entity Network'}
              </Badge>
            </div>
            <p className="text-[11px] text-slate-400">Centrality-ranked communicators, custodians, and organizational nodes</p>
          </div>
        </div>

        <Link
          to={`/cases/${caseId}/relationships`}
          className="text-xs text-indigo-400 hover:text-indigo-300 font-medium inline-flex items-center gap-1 transition-colors self-start sm:self-auto"
          id="key-entities-open-graph"
        >
          <span>Open Full Knowledge Graph</span>
          <ArrowUpRight className="h-3 w-3" />
        </Link>
      </div>

      {/* ── Content Grid or Honest Empty State ─────────────────────── */}
      {displayedEntities.length === 0 ? (
        <div className="p-6 rounded-xl bg-slate-950/40 border border-slate-800 text-center space-y-3" id="key-entities-empty">
          <Network className="h-6 w-6 text-slate-500 mx-auto" />
          <div className="space-y-1">
            <p className="text-xs font-semibold text-slate-300">
              {hasSummary ? 'No significant entity clusters detected' : 'Entity centrality summary available upon synthesis'}
            </p>
            <p className="text-[11px] text-slate-500 max-w-md mx-auto">
              Generate the Case Intelligence Summary to extract weighted centrality scores and actor networks, or explore the raw knowledge graph directly.
            </p>
          </div>
          <Link
            to={`/cases/${caseId}/relationships`}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium transition-colors border border-slate-700/60"
          >
            <span>Explore Raw Relationships Graph</span>
            <ChevronRight className="h-3.5 w-3.5" />
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {displayedEntities.map((ent, idx) => {
              const isPerson = ent.type.toLowerCase() === 'person';
              return (
                <div
                  key={idx}
                  className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800/80 hover:border-slate-700/90 space-y-2 transition-all group shadow-sm flex flex-col justify-between"
                >
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-1.5 truncate">
                        {isPerson ? (
                          <User className="h-3.5 w-3.5 text-indigo-400 shrink-0" />
                        ) : (
                          <Building2 className="h-3.5 w-3.5 text-violet-400 shrink-0" />
                        )}
                        <span className="font-semibold text-slate-100 text-xs truncate" title={ent.name}>
                          {ent.name}
                        </span>
                      </div>
                      <Badge
                        variant={isPerson ? 'info' : 'purple'}
                        size="xs"
                        className="uppercase text-[9px] shrink-0"
                      >
                        {ent.type}
                      </Badge>
                    </div>

                    {ent.weighted_degree !== undefined && (
                      <div className="text-[11px] text-slate-400 flex items-center justify-between">
                        <span>Centrality Score</span>
                        <span className="font-mono text-slate-200 font-semibold">{ent.weighted_degree.toFixed(1)}</span>
                      </div>
                    )}

                    {ent.top_edges && ent.top_edges.length > 0 && (
                      <div className="pt-1.5 border-t border-slate-800/60 space-y-1">
                        <span className="text-[10px] text-slate-500 uppercase tracking-wider block">Top Connections:</span>
                        <div className="space-y-0.5">
                          {ent.top_edges.slice(0, 2).map((edge, eIdx) => (
                            <div key={eIdx} className="text-[11px] text-slate-400 flex items-center justify-between">
                              <span className="truncate max-w-[130px]" title={edge.target}>• {edge.target}</span>
                              <span className="font-mono text-slate-500 text-[10px]">{edge.shared_docs} docs</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

                  <div className="pt-2 border-t border-slate-800/50 flex justify-end">
                    <Link
                      to={`/cases/${caseId}/relationships`}
                      className="text-[11px] text-indigo-400 hover:text-indigo-300 font-medium inline-flex items-center gap-0.5 group-hover:underline"
                    >
                      <span>View in Graph</span>
                      <ChevronRight className="h-3 w-3" />
                    </Link>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="flex justify-between items-center text-xs text-slate-400 pt-1">
            <span className="text-[11px] text-slate-500">
              Ranked by eigenvector & weighted degree centrality across {topEntities.length} actors
            </span>
            <Link
              to={`/cases/${caseId}/relationships`}
              className="text-xs text-indigo-400 hover:text-indigo-300 font-medium inline-flex items-center gap-1"
            >
              <span>View all relationships →</span>
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
