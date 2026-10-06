import { Group, Panel, Separator } from 'react-resizable-panels';
import { useDocumentViewerStore } from '../store/documentViewerStore';
import { DocumentRenderer } from './DocumentRenderer';
import { SummaryPanel } from './panels/SummaryPanel';
import { RiskPanel } from './panels/RiskPanel';
import { EntityPanel } from './panels/EntityPanel';
import { DocumentGraphPanel } from './panels/DocumentGraphPanel';
import { ReasoningPanel } from './panels/ReasoningPanel';
import { DocumentSearch } from './DocumentSearch';
import { FileText, ShieldAlert, GitCommit, Search, Users, Share2 } from 'lucide-react';
import type { ViewerTab } from '@/types';

interface DocumentViewerProps {
  currentPage: number;
  onPageChange: (page: number) => void;
  doc?: any;
  onDocUpdate?: (updatedDoc: any) => void;
}

export function DocumentViewer({ currentPage, onPageChange, doc, onDocUpdate }: DocumentViewerProps) {
  const currentTab = useDocumentViewerStore((s) => s.currentTab);
  const setCurrentTab = useDocumentViewerStore((s) => s.setCurrentTab);

  const renderSidePanel = () => {
    switch (currentTab) {
      case 'risk':
        return <RiskPanel doc={doc} onDocUpdate={onDocUpdate} />;
      case 'entities':
        return <EntityPanel doc={doc} />;
      case 'relationships':
        return <DocumentGraphPanel doc={doc} />;
      case 'reasoning':
        return <ReasoningPanel doc={doc} />;
      case 'search':
        return <DocumentSearch onJumpToPage={onPageChange} doc={doc} />;
      case 'summary':
      default:
        return <SummaryPanel doc={doc} />;
    }
  };

  const tabs: Array<{ id: ViewerTab; label: string; icon: React.ElementType }> = [
    { id: 'summary', label: 'Summary', icon: FileText },
    { id: 'risk', label: 'Privilege & Risk', icon: ShieldAlert },
    { id: 'entities', label: 'Entities', icon: Users },
    { id: 'relationships', label: 'Relationships', icon: Share2 },
    { id: 'reasoning', label: 'Reasoning', icon: GitCommit },
    { id: 'search', label: 'Search', icon: Search },
  ];

  return (
    <div className="flex-1 min-h-0 bg-slate-950/50 rounded-xl border border-slate-800/80 overflow-hidden">
      <Group orientation="horizontal">
        {/* Left Panel: Document Viewport */}
        <Panel defaultSize={58} minSize={30}>
          <div className="h-full flex flex-col p-4">
            <DocumentRenderer currentPage={currentPage} doc={doc} />
          </div>
        </Panel>

        {/* Resizable Split Handle */}
        <Separator className="w-1.5 bg-slate-900 hover:bg-indigo-500/55 transition-colors cursor-col-resize" />

        {/* Right Panel: Side by Side Analysis Tabs */}
        <Panel defaultSize={42} minSize={25}>
          <div className="h-full flex flex-col p-4 gap-3.5 overflow-y-auto min-w-[300px]">
            {/* Horizontal Tabs Navigation */}
            <div className="flex bg-slate-900 border border-slate-800 rounded-lg p-0.5 shrink-0 overflow-x-auto gap-0.5">
              {tabs.map((t) => {
                const Icon = t.icon;
                const active = currentTab === t.id;
                return (
                  <button
                    key={t.id}
                    id={`doc-viewer-tab-${t.id}`}
                    onClick={() => setCurrentTab(t.id)}
                    className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 px-2 rounded-md text-[11px] font-semibold transition-all whitespace-nowrap cursor-pointer ${
                      active
                        ? 'bg-slate-800 text-slate-100 shadow-sm border border-slate-700/50'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <Icon className="h-3.5 w-3.5" />
                    {t.label}
                  </button>
                );
              })}
            </div>

            {/* Selected Tab Analysis Panel Content */}
            <div className="flex-1 overflow-y-auto pr-1">
              {renderSidePanel()}
            </div>
          </div>
        </Panel>
      </Group>
    </div>
  );
}
