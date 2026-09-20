import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import {
  Activity,
  Database,
  FileText,
  FolderOpen,
  Server,
  Upload,
  Zap,
  ArrowUpRight,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { StatusBadge, type StatusType } from '@/components/ui/StatusBadge';
import api from '@/lib/api';
import { Link } from 'react-router-dom';

interface DependencyStatus {
  name: string;
  status: string;
  latency_ms: number | null;
  error: string | null;
}

interface HealthData {
  status: string;
  version: string;
  environment: string;
  uptime_seconds: number;
  dependencies: DependencyStatus[];
}

const fadeInUp = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.5 },
};

const staggerContainer = {
  animate: { transition: { staggerChildren: 0.1 } },
};

export function Dashboard() {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchHealth() {
      try {
        const response = await api.get('/health');
        setHealth(response.data);
        setError(null);
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : 'Failed to fetch health status';
        setError(message);
      } finally {
        setLoading(false);
      }
    }
    fetchHealth();
    const interval = setInterval(fetchHealth, 30000); // Poll every 30s
    return () => clearInterval(interval);
  }, []);

  function formatUptime(seconds: number): string {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);
    if (h > 0) return `${h}h ${m}m ${s}s`;
    if (m > 0) return `${m}m ${s}s`;
    return `${s}s`;
  }

  return (
    <motion.div
      className="space-y-6"
      variants={staggerContainer}
      initial="initial"
      animate="animate"
    >
      {/* ── Hero Section ─────────────────────────────────────────────── */}
      <motion.div {...fadeInUp}>
        <div className="relative rounded-2xl overflow-hidden bg-gradient-to-br from-indigo-500/10 via-slate-900/50 to-violet-500/10 border border-indigo-500/10 p-8">
          <div className="bg-grid-pattern absolute inset-0 opacity-30" />
          <div className="relative z-10">
            <div className="flex items-center gap-2 mb-2">
              <Zap className="h-5 w-5 text-indigo-400" />
              <span className="text-xs font-semibold text-indigo-400 uppercase tracking-wider">
                Platform Overview
              </span>
            </div>
            <h1 className="text-3xl font-bold mb-2">
              <span className="gradient-text">Agentic AI</span>{' '}
              <span className="text-slate-100">E-Discovery Platform</span>
            </h1>
            <p className="text-slate-400 max-w-2xl text-sm leading-relaxed">
              Enterprise-grade legal document review powered by 6 specialized AI agents.
              Upload documents, run automated analysis, detect privilege, and generate
              comprehensive review reports — all in one platform.
            </p>
          </div>
        </div>
      </motion.div>

      {/* ── Quick Actions ────────────────────────────────────────────── */}
      <motion.div {...fadeInUp} className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Link to="/upload" className="group">
          <Card className="h-full">
            <CardContent className="flex items-center gap-4 py-2">
              <div className="h-12 w-12 rounded-xl bg-indigo-500/10 flex items-center justify-center group-hover:bg-indigo-500/20 transition-colors">
                <Upload className="h-6 w-6 text-indigo-400" />
              </div>
              <div className="flex-1">
                <h3 className="text-sm font-semibold text-slate-100">Upload Documents</h3>
                <p className="text-xs text-slate-500">PDF, DOCX, TXT, EML</p>
              </div>
              <ArrowUpRight className="h-4 w-4 text-slate-600 group-hover:text-indigo-400 transition-colors" />
            </CardContent>
          </Card>
        </Link>

        <Link to="/cases" className="group">
          <Card className="h-full">
            <CardContent className="flex items-center gap-4 py-2">
              <div className="h-12 w-12 rounded-xl bg-violet-500/10 flex items-center justify-center group-hover:bg-violet-500/20 transition-colors">
                <FolderOpen className="h-6 w-6 text-violet-400" />
              </div>
              <div className="flex-1">
                <h3 className="text-sm font-semibold text-slate-100">Manage Cases</h3>
                <p className="text-xs text-slate-500">Organize & track</p>
              </div>
              <ArrowUpRight className="h-4 w-4 text-slate-600 group-hover:text-violet-400 transition-colors" />
            </CardContent>
          </Card>
        </Link>

        <div className="group cursor-not-allowed opacity-60">
          <Card hover={false}>
            <CardContent className="flex items-center gap-4 py-2">
              <div className="h-12 w-12 rounded-xl bg-cyan-500/10 flex items-center justify-center">
                <Activity className="h-6 w-6 text-cyan-400" />
              </div>
              <div className="flex-1">
                <h3 className="text-sm font-semibold text-slate-100">Run Analysis</h3>
                <p className="text-xs text-slate-500">Coming in Part 2</p>
              </div>
              <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-slate-800 text-slate-400">
                Soon
              </span>
            </CardContent>
          </Card>
        </div>
      </motion.div>

      {/* ── System Health ────────────────────────────────────────────── */}
      <motion.div {...fadeInUp}>
        <Card glow={health?.status === 'healthy'}>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Server className="h-5 w-5 text-indigo-400" />
              System Health
            </CardTitle>
            {health && (
              <StatusBadge status={health.status as StatusType} />
            )}
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="flex items-center gap-3 text-slate-400 text-sm">
                <div className="h-4 w-4 border-2 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin" />
                Checking system health...
              </div>
            ) : error ? (
              <div className="text-red-400 text-sm">
                <p>Unable to reach backend: {error}</p>
                <p className="text-xs text-slate-500 mt-1">
                  Make sure the FastAPI server is running on port 8000.
                </p>
              </div>
            ) : health ? (
              <div className="space-y-4">
                {/* Version & Uptime */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div>
                    <p className="text-xs text-slate-500 mb-1">Version</p>
                    <p className="text-sm font-mono text-slate-200">v{health.version}</p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500 mb-1">Environment</p>
                    <p className="text-sm font-mono text-slate-200 capitalize">{health.environment}</p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500 mb-1">Uptime</p>
                    <p className="text-sm font-mono text-slate-200">{formatUptime(health.uptime_seconds)}</p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500 mb-1">Status</p>
                    <StatusBadge status={health.status as StatusType} size="sm" />
                  </div>
                </div>

                {/* Dependencies */}
                <div className="border-t border-slate-800/50 pt-4">
                  <p className="text-xs text-slate-500 mb-3 uppercase tracking-wider font-semibold">Dependencies</p>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {health.dependencies.map((dep) => (
                      <div
                        key={dep.name}
                        className="flex items-center justify-between p-3 rounded-lg bg-slate-900/50 border border-slate-800/30"
                      >
                        <div className="flex items-center gap-3">
                          <Database className="h-4 w-4 text-slate-500" />
                          <div>
                            <p className="text-sm font-medium text-slate-200 capitalize">{dep.name}</p>
                            {dep.error && (
                              <p className="text-xs text-red-400 truncate max-w-48">{dep.error}</p>
                            )}
                          </div>
                        </div>
                        <div className="flex items-center gap-3">
                          {dep.latency_ms !== null && (
                            <span className="text-xs font-mono text-slate-500">
                              {dep.latency_ms.toFixed(1)}ms
                            </span>
                          )}
                          <StatusBadge status={dep.status as StatusType} size="sm" />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ) : null}
          </CardContent>
        </Card>
      </motion.div>

      {/* ── Pipeline Overview ────────────────────────────────────────── */}
      <motion.div {...fadeInUp}>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5 text-violet-400" />
              Processing Pipeline
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {[
                'Upload', 'Validate', 'OCR', 'Metadata', 'Classify',
                'Chunk', 'Embed', 'Retrieve', 'Extract', 'Timeline',
                'Summarize', 'Privilege', 'Risk', 'QA', 'Report',
              ].map((step, i) => (
                <div
                  key={step}
                  className="flex items-center gap-2"
                >
                  <span className="px-3 py-1.5 text-xs font-medium rounded-lg bg-slate-800/80 text-slate-300 border border-slate-700/50">
                    {step}
                  </span>
                  {i < 14 && (
                    <span className="text-slate-700">→</span>
                  )}
                </div>
              ))}
            </div>
            <p className="text-xs text-slate-500 mt-4">
              Full pipeline implementation coming in Parts 2 & 3.
            </p>
          </CardContent>
        </Card>
      </motion.div>
    </motion.div>
  );
}
