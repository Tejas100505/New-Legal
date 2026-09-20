import { Badge } from '@/components/atoms/Badge';
import { GitCompare, PlusCircle, MinusCircle, HelpCircle } from 'lucide-react';

export function VersionCompare() {
  const diffs: any[] = [];

  if (!diffs || diffs.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center text-center gap-2 p-6 text-slate-500">
        <HelpCircle className="h-8 w-8 text-slate-700" />
        <p className="text-xs font-semibold">No version differences found</p>
      </div>
    );
  }

  return (
    <div className="bg-slate-900/40 rounded-lg p-4 border border-slate-850 flex flex-col gap-4 overflow-y-auto">
      <div className="flex items-center gap-2 border-b border-slate-800 pb-2">
        <GitCompare className="h-4 w-4 text-amber-400" />
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-300">
          Version Diffs (v3 vs v2)
        </span>
      </div>

      <div className="flex flex-col gap-3">
        {diffs.map((diff: any, i: number) => {
          const isAddition = diff.type === 'addition';
          const isDeletion = diff.type === 'deletion';
          
          return (
            <div 
              key={i} 
              className={`p-3 rounded-lg border text-xs flex flex-col gap-1.5 ${
                isAddition 
                  ? 'bg-emerald-950/15 border-emerald-500/20 text-emerald-300' 
                  : isDeletion
                  ? 'bg-red-950/15 border-red-500/20 text-red-300'
                  : 'bg-amber-950/15 border-amber-500/20 text-amber-300'
              }`}
            >
              <div className="flex justify-between items-center">
                <span className="text-[9px] font-bold uppercase tracking-wider inline-flex items-center gap-1">
                  {isAddition ? (
                    <PlusCircle className="h-3.5 w-3.5 text-emerald-400" />
                  ) : (
                    <MinusCircle className="h-3.5 w-3.5 text-red-400" />
                  )}
                  {diff.type} · Page {diff.pageNumber}
                </span>
                <Badge variant={isAddition ? 'success' : isDeletion ? 'danger' : 'warning'} size="xs">
                  {diff.type.toUpperCase()}
                </Badge>
              </div>

              <p className="font-semibold text-slate-200 leading-normal">{diff.description}</p>
              
              {diff.oldText && (
                <div className="bg-slate-950/60 p-2 rounded border border-slate-850 text-[11px] text-slate-400 mt-1">
                  <span className="text-[9px] font-bold uppercase tracking-wider text-red-400 block mb-0.5">Removed Excerpt</span>
                  <span className="line-through">"{diff.oldText}"</span>
                </div>
              )}
              {diff.newText && (
                <div className="bg-slate-950/60 p-2 rounded border border-slate-850 text-[11px] text-slate-300 mt-1">
                  <span className="text-[9px] font-bold uppercase tracking-wider text-emerald-400 block mb-0.5">Inserted Excerpt</span>
                  <span>"{diff.newText}"</span>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
