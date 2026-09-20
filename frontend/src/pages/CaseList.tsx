import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { FolderOpen, Plus, Calendar, FileText } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { StatusBadge, type StatusType } from '@/components/ui/StatusBadge';
import api from '@/lib/api';
import { formatDate } from '@/lib/utils';

interface CaseData {
  id: string;
  name: string;
  description: string | null;
  status: string;
  document_count: number;
  created_at: string;
  updated_at: string;
}

export function CaseList() {
  const [cases, setCases] = useState<CaseData[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState('');
  const [newDesc, setNewDesc] = useState('');
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    fetchCases();
  }, []);

  async function fetchCases() {
    try {
      const res = await api.get('/cases');
      setCases(res.data.cases);
    } catch {
      // Backend may not be running — show empty state
    } finally {
      setLoading(false);
    }
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!newName.trim()) return;
    setCreating(true);
    try {
      await api.post('/cases', { name: newName.trim(), description: newDesc.trim() || null });
      setNewName('');
      setNewDesc('');
      setShowCreate(false);
      await fetchCases();
    } catch {
      // Handle error
    } finally {
      setCreating(false);
    }
  }

  return (
    <motion.div
      className="space-y-6"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.4 }}
    >
      {/* ── Header ───────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Legal Cases</h1>
          <p className="text-sm text-slate-500 mt-1">Manage your e-discovery cases and organize documents.</p>
        </div>
        <Button onClick={() => setShowCreate(!showCreate)} variant="primary" size="md">
          <Plus className="h-4 w-4" />
          New Case
        </Button>
      </div>

      {/* ── Create Case Form ─────────────────────────────────────────── */}
      {showCreate && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          exit={{ opacity: 0, height: 0 }}
        >
          <Card glow>
            <CardContent>
              <form onSubmit={handleCreate} className="space-y-4">
                <div>
                  <label htmlFor="case-name" className="block text-sm font-medium text-slate-300 mb-1.5">
                    Case Name
                  </label>
                  <input
                    id="case-name"
                    type="text"
                    value={newName}
                    onChange={(e) => setNewName(e.target.value)}
                    placeholder="e.g., Smith v. Jones — Document Review"
                    className="w-full px-4 py-2.5 rounded-lg bg-slate-900/80 border border-slate-700 text-slate-100 text-sm placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500/50 transition-all"
                    required
                  />
                </div>
                <div>
                  <label htmlFor="case-description" className="block text-sm font-medium text-slate-300 mb-1.5">
                    Description (optional)
                  </label>
                  <textarea
                    id="case-description"
                    value={newDesc}
                    onChange={(e) => setNewDesc(e.target.value)}
                    placeholder="Brief description of the case..."
                    rows={2}
                    className="w-full px-4 py-2.5 rounded-lg bg-slate-900/80 border border-slate-700 text-slate-100 text-sm placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500/50 transition-all resize-none"
                  />
                </div>
                <div className="flex gap-3">
                  <Button type="submit" loading={creating}>Create Case</Button>
                  <Button type="button" variant="ghost" onClick={() => setShowCreate(false)}>Cancel</Button>
                </div>
              </form>
            </CardContent>
          </Card>
        </motion.div>
      )}

      {/* ── Cases Grid ───────────────────────────────────────────────── */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-40 rounded-xl bg-slate-900/30 animate-pulse" />
          ))}
        </div>
      ) : cases.length === 0 ? (
        <Card hover={false}>
          <CardContent className="flex flex-col items-center justify-center py-16 text-center">
            <div className="h-16 w-16 rounded-2xl bg-slate-800/50 flex items-center justify-center mb-4">
              <FolderOpen className="h-8 w-8 text-slate-600" />
            </div>
            <h3 className="text-lg font-semibold text-slate-300 mb-2">No cases yet</h3>
            <p className="text-sm text-slate-500 max-w-sm mb-6">
              Create your first case to start organizing documents for e-discovery review.
            </p>
            <Button onClick={() => setShowCreate(true)}>
              <Plus className="h-4 w-4" />
              Create First Case
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {cases.map((c, i) => (
            <motion.div
              key={c.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
            >
              <Card className="h-full">
                <CardContent className="space-y-3">
                  <div className="flex items-start justify-between">
                    <h3 className="text-sm font-semibold text-slate-100 leading-snug pr-2">
                      {c.name}
                    </h3>
                    <StatusBadge status={c.status as StatusType} size="sm" pulse={false} />
                  </div>
                  {c.description && (
                    <p className="text-xs text-slate-500 line-clamp-2">{c.description}</p>
                  )}
                  <div className="flex items-center gap-4 pt-2 border-t border-slate-800/30">
                    <div className="flex items-center gap-1.5 text-xs text-slate-500">
                      <FileText className="h-3.5 w-3.5" />
                      <span>{c.document_count} docs</span>
                    </div>
                    <div className="flex items-center gap-1.5 text-xs text-slate-500">
                      <Calendar className="h-3.5 w-3.5" />
                      <span>{formatDate(c.created_at)}</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>
      )}
    </motion.div>
  );
}
