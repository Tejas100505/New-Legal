import { motion, AnimatePresence } from 'framer-motion';
import { Check, X, UserPlus } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/atoms/Badge';
import { useCollaborationStore } from '@/stores/collaborationStore';


export function NotificationsDropdown({ show }: { show: boolean }) {
  const { reviewRequests, unreadNotificationsCount, updateReviewRequestStatus } = useCollaborationStore();

  const handleRequestAction = (id: string, action: 'accepted' | 'completed') => {
    updateReviewRequestStatus(id, action);
  };

  return (
    <AnimatePresence>
      {show && (
        <motion.div
          initial={{ opacity: 0, y: -10, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -10, scale: 0.95 }}
          transition={{ duration: 0.2 }}
          className={cn(
            'absolute right-0 top-12 w-[420px] max-h-[500px] overflow-y-auto custom-scrollbar',
            'rounded-xl border border-slate-800/80',
            'bg-slate-900/95 backdrop-blur-2xl',
            'shadow-2xl shadow-black/30 z-50 flex flex-col'
          )}
        >
          <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800/50 shrink-0 sticky top-0 bg-slate-900/95 backdrop-blur-2xl z-10">
            <h3 className="text-sm font-semibold text-slate-200">Notifications & Requests</h3>
            <Badge variant="info" size="xs">{unreadNotificationsCount} unread</Badge>
          </div>

          <div className="divide-y divide-slate-800/30 pb-4">
            {/* Review Requests Section */}
            {reviewRequests.filter(r => r.status === 'pending').map((req) => (
              <div key={req.id} className="px-4 py-3 bg-indigo-500/10 border-l-2 border-indigo-500">
                <div className="flex items-start gap-3">
                  <div className="mt-1 h-6 w-6 rounded-full bg-indigo-500/20 flex items-center justify-center text-indigo-400">
                    <UserPlus className="h-3 w-3" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-slate-200">Review Request</p>
                    <p className="text-xs text-slate-400 mt-0.5 leading-relaxed">
                      User <span className="font-semibold text-slate-300">{req.requesterId}</span> requested your review on Document <span className="font-mono text-slate-300">{req.documentId}</span>.
                    </p>
                    <div className="flex items-center gap-2 mt-2">
                      <button onClick={() => handleRequestAction(req.id, 'accepted')} className="px-3 py-1.5 rounded bg-emerald-500/20 text-emerald-400 text-[10px] font-bold hover:bg-emerald-500/30 transition-all flex items-center gap-1">
                        <Check className="h-3 w-3" /> Accept
                      </button>
                      <button onClick={() => handleRequestAction(req.id, 'completed')} className="px-3 py-1.5 rounded bg-slate-800 text-slate-400 text-[10px] font-bold hover:bg-slate-700 transition-all flex items-center gap-1">
                        <X className="h-3 w-3" /> Decline
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            ))}

            {/* Standard Notifications */}
            <div className="flex flex-col items-center justify-center py-6 text-slate-500">
              <p className="text-xs">No new notifications.</p>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
