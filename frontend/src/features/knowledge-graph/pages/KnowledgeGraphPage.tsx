import { useState } from 'react';
import { PageShell } from '@/components/templates/PageShell';
import { GraphCanvas as Canvas } from '../components/GraphCanvas';
import { GraphFilterPanel } from '../components/GraphFilterPanel';
import { GraphToolbar } from '../components/GraphToolbar';
import { NodeDetailPanel } from '../components/NodeDetailPanel';
import { PathFinderModal } from '../components/PathFinderModal';
import { ReactFlowProvider } from '@xyflow/react';

interface KnowledgeGraphPageProps {
  caseId?: string;
}

export function KnowledgeGraphPage({ caseId }: KnowledgeGraphPageProps = {}) {
  const [layoutTrigger, setLayoutTrigger] = useState(0);
  const [isPathFinderOpen, setIsPathFinderOpen] = useState(false);

  const handleApplyLayout = () => {
    setLayoutTrigger((prev) => prev + 1);
  };

  return (
    <PageShell
      title="Knowledge Graph"
      description="Enterprise intelligence relationship map. Discover connected entities, paths of separation, and hidden evidence link dimensions."
      fullWidth
    >
      <ReactFlowProvider>
        <div className="flex flex-col gap-4 h-[calc(100vh-12rem)]">
          {/* Top Toolbar */}
          <GraphToolbar 
            onOpenPathFinder={() => setIsPathFinderOpen(true)}
            onApplyLayout={handleApplyLayout}
          />

          <div className="flex-1 flex gap-4 min-h-0">
            {/* Left Filter Panel */}
            <GraphFilterPanel />

            {/* Central Canvas */}
            <div className="flex-1 rounded-xl border border-slate-800/80 bg-slate-950 overflow-hidden relative">
              <Canvas layoutTrigger={layoutTrigger} caseId={caseId} />
            </div>

            {/* Right Node Detail Panel */}
            <NodeDetailPanel />
          </div>

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
