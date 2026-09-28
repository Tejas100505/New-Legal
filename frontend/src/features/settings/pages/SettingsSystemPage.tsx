import { useQuery } from '@tanstack/react-query';
import { PageShell } from '@/components/templates/PageShell';
import { SettingsSubNav } from '../components/SettingsSubNav';
import { Badge } from '@/components/atoms/Badge';
import { Spinner } from '@/components/atoms/Spinner';
import api from '@/lib/api';
import {
  Server,
  Database,
  Cpu,
  CheckCircle2,
  AlertTriangle,
  Clock,
  RefreshCw,
} from 'lucide-react';

interface DependencyStatus {
  name: string;
  status: string;
  latency_ms?: number;
  error?: string;
}

interface HealthResponse {
  status: 'healthy' | 'degraded' | 'unhealthy';
  version: string;
  environment: string;
  uptime_seconds: number;
  dependencies: DependencyStatus[];
}

export function SettingsSystemPage() {
  const { data: health, isLoading, isRefetching, refetch } = useQuery<HealthResponse>({
    queryKey: ['system-health'],
    queryFn: async () => {
      const res = await api.get('/health');
      return res.data;
    },
    refetchInterval: 30000,
  });

  const formatUptime = (seconds: number) => {
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    return `${hrs}h ${mins}m ${secs}s`;
  };

  return (
    <PageShell
      title="System Health & Infrastructure"
      description="Service connectivity, database latency, and LLM runtime configurations."
    >
      <SettingsSubNav />

      <div className="space-y-6" id="settings-system-content">
        {/* Top Status Bar */}
        <div className="p-5 rounded-2xl border border-slate-800/80 bg-slate-900/60 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div
              className={`h-10 w-10 rounded-xl flex items-center justify-center ${
                health?.status === 'healthy'
                  ? 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-400'
                  : 'bg-amber-500/10 border border-amber-500/20 text-amber-400'
              }`}
            >
              {health?.status === 'healthy' ? (
                <CheckCircle2 className="h-5 w-5" />
              ) : (
                <AlertTriangle className="h-5 w-5" />
              )}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-slate-100">
                  {health?.status === 'healthy' ? 'All Systems Operational' : 'Degraded Infrastructure'}
                </h3>
                {health && (
                  <Badge
                    variant={health.status === 'healthy' ? 'success' : 'warning'}
                    size="xs"
                    dot
                  >
                    {health.status.toUpperCase()}
                  </Badge>
                )}
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Version {health?.version || '1.0.0'} • Environment: {health?.environment || 'production'}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {health && (
              <div className="text-right text-xs font-mono text-slate-400 hidden sm:block">
                <span className="flex items-center gap-1 justify-end">
                  <Clock className="h-3 w-3 text-slate-500" />
                  Uptime: {formatUptime(health.uptime_seconds)}
                </span>
              </div>
            )}
            <button
              onClick={() => refetch()}
              disabled={isRefetching}
              className="p-2 rounded-xl bg-slate-800/80 hover:bg-slate-800 border border-slate-700/60 text-slate-300 hover:text-white transition-all cursor-pointer"
              title="Refresh Health Status"
            >
              <RefreshCw className={`h-4 w-4 ${isRefetching ? 'animate-spin text-indigo-400' : ''}`} />
            </button>
          </div>
        </div>

        {/* Infrastructure Dependencies */}
        <div className="space-y-3">
          <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-2">
            <Server className="h-3.5 w-3.5 text-indigo-400" />
            Core Dependencies (PostgreSQL & Redis)
          </h3>

          {isLoading ? (
            <div className="p-8 flex justify-center">
              <Spinner size="md" />
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
              {(health?.dependencies || []).map((dep) => (
                <div
                  key={dep.name}
                  className="p-4 rounded-xl border border-slate-800/80 bg-slate-900/40 flex items-center justify-between"
                >
                  <div className="flex items-center gap-3">
                    <div className="h-9 w-9 rounded-lg bg-slate-800/80 border border-slate-700/60 flex items-center justify-center text-slate-300">
                      <Database className="h-4 w-4 text-cyan-400" />
                    </div>
                    <div>
                      <h4 className="text-sm font-bold text-slate-200 capitalize">
                        {dep.name}
                      </h4>
                      <span className="text-[11px] font-mono text-slate-500">
                        {dep.latency_ms !== undefined ? `${dep.latency_ms.toFixed(1)} ms latency` : 'Connected'}
                      </span>
                    </div>
                  </div>
                  <Badge variant={dep.status === 'up' ? 'success' : 'danger'} size="xs" dot>
                    {dep.status.toUpperCase()}
                  </Badge>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* AI Model Runtime & Verification Parameters */}
        <div className="space-y-3">
          <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-2">
            <Cpu className="h-3.5 w-3.5 text-indigo-400" />
            AI Model Runtimes & Verification Gates
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
            <div className="p-4 rounded-xl border border-slate-800/80 bg-slate-900/40 space-y-2.5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-200">Synthesis & Summarization</span>
                <Badge variant="purple" size="xs">Active LLM</Badge>
              </div>
              <div className="space-y-1 text-xs">
                <div className="flex justify-between text-slate-400">
                  <span>Model ID:</span>
                  <span className="font-mono text-indigo-300">gemini-3.5-flash-lite</span>
                </div>
                <div className="flex justify-between text-slate-400">
                  <span>Sampling Temperature:</span>
                  <span className="font-mono text-slate-300">0.1 (Deterministic)</span>
                </div>
                <div className="flex justify-between text-slate-400">
                  <span>Top-P Nucleus:</span>
                  <span className="font-mono text-slate-300">0.95</span>
                </div>
              </div>
            </div>

            <div className="p-4 rounded-xl border border-slate-800/80 bg-slate-900/40 space-y-2.5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-200">Dense Vector Embeddings</span>
                <Badge variant="outline" size="xs">Embedding</Badge>
              </div>
              <div className="space-y-1 text-xs">
                <div className="flex justify-between text-slate-400">
                  <span>Model ID:</span>
                  <span className="font-mono text-indigo-300">text-embedding-004</span>
                </div>
                <div className="flex justify-between text-slate-400">
                  <span>Vector Dimensions:</span>
                  <span className="font-mono text-slate-300">768-D Float32</span>
                </div>
                <div className="flex justify-between text-slate-400">
                  <span>Similarity Metric:</span>
                  <span className="font-mono text-slate-300">Cosine Distance</span>
                </div>
              </div>
            </div>

            <div className="p-4 rounded-xl border border-slate-800/80 bg-slate-900/40 space-y-2.5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-200">Gate A & Gate B Grounding</span>
                <Badge variant="success" size="xs">Deterministic</Badge>
              </div>
              <div className="space-y-1 text-xs">
                <div className="flex justify-between text-slate-400">
                  <span>Gate A Check:</span>
                  <span className="text-slate-300">Citation Syntax Validation</span>
                </div>
                <div className="flex justify-between text-slate-400">
                  <span>Gate B Threshold (τ):</span>
                  <span className="font-mono text-emerald-400">≥ 0.55 Token Overlap</span>
                </div>
                <div className="flex justify-between text-slate-400">
                  <span>Failure Strategy:</span>
                  <span className="text-amber-400">Honest Answer Suppression</span>
                </div>
              </div>
            </div>

            <div className="p-4 rounded-xl border border-slate-800/80 bg-slate-900/40 space-y-2.5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-200">Rate Limits & SlowAPI Guardrails</span>
                <Badge variant="outline" size="xs">Throttle</Badge>
              </div>
              <div className="space-y-1 text-xs">
                <div className="flex justify-between text-slate-400">
                  <span>Case Grounded Q&A:</span>
                  <span className="font-mono text-slate-300">10 requests / min / IP</span>
                </div>
                <div className="flex justify-between text-slate-400">
                  <span>Document Ingestion:</span>
                  <span className="font-mono text-slate-300">60 uploads / min / IP</span>
                </div>
                <div className="flex justify-between text-slate-400">
                  <span>Enforcement Layer:</span>
                  <span className="text-slate-300">FastAPI Route Middleware</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </PageShell>
  );
}
