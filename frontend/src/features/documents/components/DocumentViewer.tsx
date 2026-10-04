import { Group, Panel, Separator } from 'react-resizable-panels';
import { useDocumentViewerStore } from '../store/documentViewerStore';
import { DocumentRenderer } from './DocumentRenderer';
import { SummaryPanel } from './panels/SummaryPanel';
import { RiskPanel } from './panels/RiskPanel';
import { ReasoningPanel } from './panels/ReasoningPanel';
import { AnnotationLayer } from './AnnotationLayer';
import { DocumentSearch } from './DocumentSearch';
import { VersionCompare } from './VersionCompare';
import { CommentsPanel } from './panels/CommentsPanel';
import { FileText, ShieldAlert, GitCommit, Search, Edit3, MessageSquare } from 'lucide-react';
import type { ViewerTab } from '@/types';

interface DocumentViewerProps {
  currentPage: number;
  onPageChange: (page: number) => void;
  doc?: any;
}

export function DocumentViewer({ currentPage, onPageChange, doc }: DocumentViewerProps) {
  const currentTab = useDocumentViewerStore((s) => s.currentTab);
  const setCurrentTab = useDocumentViewerStore((s) => s.setCurrentTab);
  const isCompare = useDocumentViewerStore((s) => s.isCompareMode);

  const renderSidePanel = () => {
    switch (currentTab) {
      case 'risk':
        return <RiskPanel doc={doc} />;
      case 'reasoning':
        return <ReasoningPanel doc={doc} />;
      case 'annotations':
        return <AnnotationLayer />;
      case 'search':
        return <DocumentSearch onJumpToPage={onPageChange} doc={doc} />;
      case 'discussion':
        return <CommentsPanel documentId={doc?.id || ''} />;
      case 'summary':
      default:
        return <SummaryPanel doc={doc} />;
    }
  };

  return (
    <div className="flex-1 min-h-0 bg-slate-950/50 rounded-xl border border-slate-800/80 overflow-hidden">
      <Group orientation="horizontal">
        {/* Left Panel: Document Viewport */}
        <Panel defaultSize={60} minSize={30}>
          <div className="h-full flex flex-col p-4">
            <DocumentRenderer currentPage={currentPage} doc={doc} />
          </div>
        </Panel>

        {/* Resizable Split Handle */}
        <Separator className="w-1.5 bg-slate-900 hover:bg-indigo-500/55 transition-colors cursor-col-resize" />

        {/* Right Panel: Side by Side Analysis Tabs */}
        <Panel defaultSize={40} minSize={20}>
          <div className="h-full flex flex-col p-4 gap-4 overflow-y-auto min-w-[280px]">
            {/* Scrollable Horizontal Tabs Navigation */}
            <div className="flex bg-slate-900 border border-slate-800 rounded-lg p-0.5 shrink-0 overflow-x-auto gap-0.5">
              {([
                { id: 'summary', label: 'Summary', icon: FileText },
                { id: 'risk', label: 'Risk', icon: ShieldAlert },
                { id: 'reasoning', label: 'Reasoning', icon: GitCommit },
                { id: 'annotations', label: 'Notes', icon: Edit3 },
                { id: 'search', label: 'Search', icon: Search },
                { id: 'discussion', label: 'Discussion', icon: MessageSquare },
              ] as Array<{ id: ViewerTab; label: string; icon: React.ElementType }>).map((t) => {
                const Icon = t.icon;
                const active = currentTab === t.id;
                return (
                  <button
                    key={t.id}
                    onClick={() => setCurrentTab(t.id)}
                    className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 px-2.5 rounded-md text-[11px] font-semibold transition-all whitespace-nowrap ${
                      active
                        ? 'bg-slate-800 text-slate-100 shadow-sm border border-slate-700/50'
                        : 'text-slate-500 hover:text-slate-300'
                    }`}
                  >
                    <Icon className="h-3.5 w-3.5" />
                    {t.label}
                  </button>
                );
              })}
            </div>

            {/* If compare mode is enabled, show the diffs card at the top of the side panel */}
            {isCompare && (
              <div className="shrink-0 mb-1">
                <VersionCompare />
              </div>
            )}

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
