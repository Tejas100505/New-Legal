import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Users, UserPlus, Mail } from 'lucide-react';
import { useCollaborationStore } from '@/stores/collaborationStore';

export function ShareCaseModal({ 
  caseId, 
  caseName, 
  show, 
  onClose 
}: { 
  caseId: string; 
  caseName: string; 
  show: boolean; 
  onClose: () => void; 
}) {
  const { assignCase, assignments } = useCollaborationStore();
  const [email, setEmail] = useState('');
  const [role, setRole] = useState<'reviewer' | 'viewer' | 'owner'>('reviewer');

  const currentAssignments = assignments.filter(a => a.caseId === caseId);

  const handleInvite = (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;
    
    // Session-only sharing — assignments are stored in client state and not persisted to the server.
    assignCase({ caseId, userId: email, role });
    setEmail('');
  };

  return (
    <AnimatePresence>
      {show && (
        <>
          <motion.div 
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50"
            onClick={onClose}
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.95 }}
            className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-md bg-slate-900 border border-slate-800 rounded-xl shadow-2xl z-50 overflow-hidden"
          >
            <div className="flex items-center justify-between px-5 py-4 border-b border-slate-800/50 bg-slate-900/80">
              <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
                <Users className="h-4 w-4 text-indigo-400" /> Share Case
              </h3>
              <button onClick={onClose} className="text-slate-500 hover:text-slate-300 transition-colors">
                <X className="h-4 w-4" />
              </button>
            </div>
            
            <div className="p-5 space-y-6">
              <div>
                <p className="text-xs text-slate-400 mb-1">Invite team members to collaborate on <strong className="text-slate-200">{caseName}</strong>.</p>
                <p className="text-[10px] text-amber-500/80 mb-3">⚠ Sharing is session-only and not yet persisted to the server.</p>
                <form onSubmit={handleInvite} className="flex gap-2">
                  <div className="relative flex-1">
                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
                    <input 
                      type="email" 
                      value={email} 
                      onChange={e => setEmail(e.target.value)} 
                      placeholder="Email address..."
                      className="w-full pl-9 pr-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
                    />
                  </div>
                  <select 
                    value={role} 
                    onChange={e => setRole(e.target.value as any)}
                    className="bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 px-2 py-2 focus:border-indigo-500 focus:outline-none"
                  >
                    <option value="reviewer">Reviewer</option>
                    <option value="viewer">Viewer</option>
                    <option value="owner">Owner</option>
                  </select>
                  <button type="submit" className="px-3 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors">
                    <UserPlus className="h-3.5 w-3.5" /> Invite
                  </button>
                </form>
              </div>

              <div>
                <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">Current Members</h4>
                <div className="space-y-2 max-h-40 overflow-y-auto custom-scrollbar">
                  {currentAssignments.length === 0 && <p className="text-xs text-slate-500">No members shared yet.</p>}
                  {currentAssignments.map((a, idx) => (
                    <div key={idx} className="flex items-center justify-between p-2 rounded-lg bg-slate-950/50 border border-slate-800/50">
                      <span className="text-xs font-medium text-slate-300">{a.userId}</span>
                      <span className="text-[10px] text-slate-500 uppercase font-semibold bg-slate-800 px-2 py-1 rounded">{a.role}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
