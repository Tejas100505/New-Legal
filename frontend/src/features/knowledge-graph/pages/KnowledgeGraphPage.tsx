import { useState, useEffect } from 'react';
import { PageShell } from '@/components/templates/PageShell';
import { GraphCanvas as Canvas } from '../components/GraphCanvas';
import { GraphFilterPanel } from '../components/GraphFilterPanel';
import { GraphToolbar } from '../components/GraphToolbar';
import { NodeDetailPanel } from '../components/NodeDetailPanel';
import { PathFinderModal } from '../components/PathFinderModal';
import { ReactFlowProvider } from '@xyflow/react';
import { cn } from '@/lib/utils';

interface KnowledgeGraphPageProps {
  caseId?: string;
}

export function KnowledgeGraphPage({ caseId }: KnowledgeGraphPageProps = {}) {
  const [layoutTrigger, setLayoutTrigger] = useState(0);
  const [isPathFinderOpen, setIsPathFinderOpen] = useState(false);
  const [isMaximized, setIsMaximized] = useState(false);
  const [showFiltersInMaximized, setShowFiltersInMaximized] = useState(false);

  const handleApplyLayout = () => {
    setLayoutTrigger((prev) => prev + 1);
  };

  // Attach Escape key listener only when maximized
  useEffect(() => {
    if (!isMaximized) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        setIsMaximized(false);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isMaximized]);

  // Prevent background page scrolling when maximized and clean up on unmount
  useEffect(() => {
    if (isMaximized) {
      const originalOverflow = document.body.style.overflow;
      document.body.style.overflow = 'hidden';
      return () => {
        document.body.style.overflow = originalOverflow;
      };
    }
  }, [isMaximized]);

  return (
    <PageShell
      title="Knowledge Graph"
      description="Enterprise intelligence relationship map. Discover connected entities, paths of separation, and hidden evidence link dimensions."
      fullWidth
    >
      <ReactFlowProvider>
        <div 
          id="knowledge-graph-container"
          className={cn(
            "transition-all duration-300",
            isMaximized
              ? "fixed inset-0 z-50 p-3 sm:p-4 bg-slate-100 dark:bg-slate-950 flex flex-col gap-3 overflow-hidden"
              : "flex flex-col gap-4 h-[calc(100vh-12rem)]"
          )}
        >
          {/* Top Toolbar */}
          <GraphToolbar 
            onOpenPathFinder={() => setIsPathFinderOpen(true)}
            onApplyLayout={handleApplyLayout}
            isMaximized={isMaximized}
            onToggleMaximize={() => setIsMaximized((prev) => !prev)}
            showFilters={showFiltersInMaximized}
            onToggleFilters={() => setShowFiltersInMaximized((prev) => !prev)}
          />

          {isMaximized ? (
            /* Maximized View: Canvas takes entire available space with optional floating drawers */
            <div className="flex-1 rounded-xl border border-slate-200 dark:border-slate-800/80 bg-white dark:bg-slate-950 overflow-hidden relative min-h-0">
              <Canvas 
                layoutTrigger={layoutTrigger} 
                caseId={caseId} 
                isMaximized={isMaximized}
                onToggleMaximize={() => setIsMaximized(false)}
              />

              {/* Floating Filter Panel Overlay in Maximized Mode */}
              {showFiltersInMaximized && (
                <div className="absolute left-3 top-3 bottom-3 z-30 shadow-2xl animate-in slide-in-from-left duration-200">
                  <GraphFilterPanel 
                    isOverlay 
                    onClose={() => setShowFiltersInMaximized(false)} 
                  />
                </div>
              )}

              {/* Floating Entity Details Overlay in Maximized Mode (only when node selected) */}
              <div className="absolute right-3 top-3 bottom-3 z-30 pointer-events-none">
                <div className="pointer-events-auto h-full">
                  <NodeDetailPanel isOverlay />
                </div>
              </div>
            </div>
          ) : (
            /* Normal 3-Column Layout */
            <div className="flex-1 flex gap-4 min-h-0">
              {/* Left Filter Panel */}
              <GraphFilterPanel />

              {/* Central Canvas */}
              <div className="flex-1 rounded-xl border border-slate-200 dark:border-slate-800/80 bg-white dark:bg-slate-950 overflow-hidden relative">
                <Canvas 
                  layoutTrigger={layoutTrigger} 
                  caseId={caseId} 
                  isMaximized={false}
                  onToggleMaximize={() => setIsMaximized(true)}
                />
              </div>

              {/* Right Node Detail Panel */}
              <NodeDetailPanel />
            </div>
          )}

          {/* Modals */}
          <PathFinderModal 
            isOpen={isPathFinderOpen} 
            onClose={() => setIsPathFinderOpen(false)} 
          />
        </div>
      </ReactFlowProvider>
    </PageShell>
  );
}
