import { useState, useRef } from 'react';
import { Send, User as UserIcon, MessageSquare } from 'lucide-react';
import { useCollaborationStore } from '@/stores/collaborationStore';
import { useAuthStore } from '@/features/auth/store';
import { formatDate } from '@/lib/utils';

export function CommentsPanel({ documentId }: { documentId: string }) {
  const { comments, addComment, setTyping, typingUsers } = useCollaborationStore();
  const user = useAuthStore((s) => s.user);
  const [text, setText] = useState('');
  
  const typingRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Filter comments for this doc
  const docComments = comments.filter(c => c.documentId === documentId);
  const isSomeoneTyping = typingUsers[documentId];

  const handleTextChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setText(e.target.value);
    
    // Typing indicator logic
    setTyping(documentId, true);
    if (typingRef.current) clearTimeout(typingRef.current);
    typingRef.current = setTimeout(() => setTyping(documentId, false), 1500);
  };

  const handleSend = () => {
    if (!text.trim() || !user) return;

    // Simple mention parsing
    const mentions = text.match(/@\w+/g)?.map(m => m.substring(1)) || [];
    
    addComment({
      documentId,
      userId: user.id,
      userName: user.name || user.email || 'Authenticated User',
      text: text.trim(),
      mentions
    });
    
    setText('');
    setTyping(documentId, false);
    if (typingRef.current) clearTimeout(typingRef.current);
  };

  // Render text with highlighted mentions
  const renderTextWithMentions = (content: string) => {
    const parts = content.split(/(@\w+)/g);
    return parts.map((part, i) => {
      if (part.startsWith('@')) {
        return <span key={i} className="text-indigo-400 font-semibold">{part}</span>;
      }
      return <span key={i}>{part}</span>;
    });
  };

  return (
    <div className="flex flex-col h-full bg-slate-900/50 rounded-xl border border-slate-800/50 overflow-hidden">
      <div className="px-4 py-3 border-b border-slate-800/50 flex items-center justify-between bg-slate-900/80">
        <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
          <MessageSquare className="h-4 w-4 text-indigo-400" />
          Discussion
        </h3>
        <span className="text-xs text-slate-500 font-medium">{docComments.length} comments</span>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar">
        {docComments.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center space-y-2 opacity-50">
            <MessageSquare className="h-8 w-8 text-slate-600" />
            <p className="text-xs text-slate-400">No comments yet. Start the discussion!</p>
          </div>
        ) : (
          docComments.map((c) => (
            <div key={c.id} className="flex gap-3">
              <div className="h-8 w-8 rounded-full bg-slate-800 flex items-center justify-center shrink-0">
                <UserIcon className="h-4 w-4 text-slate-400" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-baseline justify-between mb-1">
                  <span className="text-xs font-bold text-slate-200">{c.userName}</span>
                  <span className="text-[10px] text-slate-500">{formatDate(c.createdAt)}</span>
                </div>
                <div className="text-xs text-slate-300 leading-relaxed bg-slate-950/50 p-2.5 rounded-lg border border-slate-800/50">
                  {renderTextWithMentions(c.text)}
                </div>
              </div>
            </div>
          ))
        )}
        {isSomeoneTyping && (
          <div className="flex items-center gap-2 text-[10px] text-slate-500 italic animate-pulse">
            <div className="flex gap-0.5">
              <span className="h-1 w-1 bg-slate-500 rounded-full animate-bounce" />
              <span className="h-1 w-1 bg-slate-500 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }} />
              <span className="h-1 w-1 bg-slate-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
            </div>
            Someone is typing...
          </div>
        )}
      </div>

      <div className="p-3 border-t border-slate-800/50 bg-slate-900">
        <div className="relative">
          <textarea
            value={text}
            onChange={handleTextChange}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            placeholder={user ? "Type a comment, use @ to mention..." : "Sign in to add a comment..."}
            disabled={!user}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-3 pr-10 py-2.5 text-xs text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-indigo-500/50 resize-none min-h-[80px]"
          />
          <button
            onClick={handleSend}
            disabled={!text.trim() || !user}
            className="absolute bottom-2.5 right-2.5 p-1.5 rounded-md bg-indigo-600 text-white hover:bg-indigo-500 disabled:opacity-50 disabled:hover:bg-indigo-600 transition-colors"
          >
            <Send className="h-3 w-3" />
          </button>
        </div>
      </div>
    </div>
  );
}
