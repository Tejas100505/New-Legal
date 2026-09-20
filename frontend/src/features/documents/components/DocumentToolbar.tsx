import { useDocumentViewerStore } from '../store/documentViewerStore';
import { 
  Eye, EyeOff, Brain, Shield, 
  GitCompare, ZoomIn, ZoomOut, ChevronLeft, ChevronRight, UserPlus
} from 'lucide-react';
import { useCollaborationStore } from '@/stores/collaborationStore';
import { useState } from 'react';

interface DocumentToolbarProps {
  fileName: string;
  pageCount: number;
  currentPage: number;
  onPageChange: (page: number) => void;
}

export function DocumentToolbar({ fileName, pageCount, currentPage, onPageChange }: DocumentToolbarProps) {
  const showOcr = useDocumentViewerStore((s) => s.showOcrOverlay);
  const toggleOcr = useDocumentViewerStore((s) => s.toggleOcrOverlay);
  const showEntities = useDocumentViewerStore((s) => s.showEntityHighlights);
  const toggleEntities = useDocumentViewerStore((s) => s.toggleEntityHighlights);
  const showPrivilege = useDocumentViewerStore((s) => s.showPrivilegeMarkers);
  const togglePrivilege = useDocumentViewerStore((s) => s.togglePrivilegeMarkers);
  const isCompare = useDocumentViewerStore((s) => s.isCompareMode);
  const toggleCompare = useDocumentViewerStore((s) => s.toggleCompareMode);

  const { createReviewRequest } = useCollaborationStore();
  const [requested, setRequested] = useState(false);

  const handleRequestReview = () => {
    createReviewRequest({
      documentId: 'doc_001', // Mock ID for now
      requesterId: 'You',
      reviewerId: 'Senior Counsel',
    });
    setRequested(true);
    setTimeout(() => setRequested(false), 3000);
  };

  return (
    <div className="bg-slate-900/50 backdrop-blur-xl border border-slate-800/80 rounded-xl p-3 flex flex-wrap items-center justify-between gap-3 text-slate-255">
      {/* File Info */}
      <div className="flex items-center gap-2">
        <span className="text-xs font-bold text-slate-100 truncate max-w-[200px]" title={fileName}>
          {fileName}
        </span>
      </div>

      {/* Toggles */}
      <div className="flex items-center gap-1.5 flex-wrap">
        {/* OCR Overlay */}
        <button
          onClick={toggleOcr}
          className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold border transition-all ${
            showOcr 
              ? 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30' 
              : 'bg-slate-850 hover:bg-slate-800 text-slate-400 border-slate-800'
          }`}
          title="Toggle OCR Text Overlay"
        >
          {showOcr ? <Eye className="h-3.5 w-3.5" /> : <EyeOff className="h-3.5 w-3.5" />}
          OCR Overlay
        </button>

        {/* Entity Highlights */}
        <button
          onClick={toggleEntities}
          className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold border transition-all ${
            showEntities 
              ? 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30' 
              : 'bg-slate-850 hover:bg-slate-800 text-slate-400 border-slate-800'
          }`}
          title="Toggle Entity Highlighting"
        >
          <Brain className="h-3.5 w-3.5" />
          Entity Highlights
        </button>

        {/* Privilege Markers */}
        <button
          onClick={togglePrivilege}
          className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold border transition-all ${
            showPrivilege 
              ? 'bg-purple-500/10 text-purple-400 border-purple-500/30' 
              : 'bg-slate-850 hover:bg-slate-800 text-slate-400 border-slate-800'
          }`}
          title="Toggle Privilege Overlay Markers"
        >
          <Shield className="h-3.5 w-3.5" />
          Privilege Markers
        </button>

        {/* Version Compare Mode */}
        <button
          onClick={toggleCompare}
          className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold border transition-all ${
            isCompare 
              ? 'bg-amber-500/10 text-amber-400 border-amber-500/30' 
              : 'bg-slate-850 hover:bg-slate-800 text-slate-400 border-slate-800'
          }`}
          title="Compare with Previous Versions"
        >
          <GitCompare className="h-3.5 w-3.5" />
          Compare Version
        </button>

        <span className="w-px h-4 bg-slate-800 mx-1"></span>

        {/* Request Review */}
        <button
          onClick={handleRequestReview}
          disabled={requested}
          className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold border transition-all ${
            requested
              ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
              : 'bg-indigo-600 hover:bg-indigo-500 text-white border-indigo-500'
          }`}
          title="Request Peer Review"
        >
          <UserPlus className="h-3.5 w-3.5" />
          {requested ? 'Requested' : 'Request Review'}
        </button>
      </div>

      {/* Pagination & Zoom */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1">
          <button className="p-1 rounded hover:bg-slate-800 text-slate-500 hover:text-slate-300">
            <ZoomOut className="h-4 w-4" />
          </button>
          <span className="text-[10px] text-slate-500 font-mono">100%</span>
          <button className="p-1 rounded hover:bg-slate-800 text-slate-500 hover:text-slate-300">
            <ZoomIn className="h-4 w-4" />
          </button>
        </div>

        <span className="text-slate-700">|</span>

        <div className="flex items-center gap-2">
          <button
            onClick={() => onPageChange(currentPage - 1)}
            disabled={currentPage <= 1}
            className="p-1 rounded hover:bg-slate-800 disabled:opacity-30 disabled:hover:bg-transparent text-slate-400"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          <span className="text-xs text-slate-300 font-medium">
            Page {currentPage} of {pageCount}
          </span>
          <button
            onClick={() => onPageChange(currentPage + 1)}
            disabled={currentPage >= pageCount}
            className="p-1 rounded hover:bg-slate-800 disabled:opacity-30 disabled:hover:bg-transparent text-slate-400"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
