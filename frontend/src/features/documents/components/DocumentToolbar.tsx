import { useState } from 'react';
import { useDocumentViewerStore } from '../store/documentViewerStore';
import { 
  Eye, EyeOff, Brain, Shield, 
  ZoomIn, ZoomOut, ChevronLeft, ChevronRight, Download, Loader2
} from 'lucide-react';
import api from '@/lib/api';

interface DocumentToolbarProps {
  fileName: string;
  pageCount: number;
  currentPage: number;
  onPageChange: (page: number) => void;
  documentId?: string;
}

export function DocumentToolbar({ fileName, pageCount, currentPage, onPageChange, documentId }: DocumentToolbarProps) {
  const showOcr = useDocumentViewerStore((s) => s.showOcrOverlay);
  const toggleOcr = useDocumentViewerStore((s) => s.toggleOcrOverlay);
  const showEntities = useDocumentViewerStore((s) => s.showEntityHighlights);
  const toggleEntities = useDocumentViewerStore((s) => s.toggleEntityHighlights);
  const showPrivilege = useDocumentViewerStore((s) => s.showPrivilegeMarkers);
  const togglePrivilege = useDocumentViewerStore((s) => s.togglePrivilegeMarkers);

  const [isDownloading, setIsDownloading] = useState(false);

  const handleDownload = async () => {
    if (!documentId) return;
    try {
      setIsDownloading(true);
      const res = await api.get(`/documents/${documentId}/download`, {
        responseType: 'blob',
      });
      const blob = new Blob([res.data]);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', fileName || 'document');
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Failed to download document:', err);
      alert('Failed to download document file.');
    } finally {
      setIsDownloading(false);
    }
  };

  return (
    <div className="bg-slate-900/50 backdrop-blur-xl border border-slate-800/80 rounded-xl p-3 flex flex-wrap items-center justify-between gap-3 text-slate-200">
      {/* File Info */}
      <div className="flex items-center gap-2">
        <span className="text-xs font-bold text-slate-100 truncate max-w-[240px]" title={fileName}>
          {fileName}
        </span>
      </div>

      {/* Viewport Overlay Toggles */}
      <div className="flex items-center gap-1.5 flex-wrap">
        {/* OCR Overlay */}
        <button
          onClick={toggleOcr}
          className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold border transition-all cursor-pointer ${
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
          className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold border transition-all cursor-pointer ${
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
          className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold border transition-all cursor-pointer ${
            showPrivilege 
              ? 'bg-purple-500/10 text-purple-400 border-purple-500/30' 
              : 'bg-slate-850 hover:bg-slate-800 text-slate-400 border-slate-800'
          }`}
          title="Toggle Privilege Overlay Markers"
        >
          <Shield className="h-3.5 w-3.5" />
          Privilege Markers
        </button>

        <span className="w-px h-4 bg-slate-800 mx-1"></span>

        {/* Download Original File */}
        <button
          onClick={handleDownload}
          disabled={isDownloading || !documentId}
          id="doc-toolbar-download-btn"
          className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold border border-slate-700 bg-slate-800 hover:bg-slate-750 text-slate-200 transition-all cursor-pointer disabled:opacity-50"
          title="Download original uploaded file"
        >
          {isDownloading ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin text-indigo-400" />
          ) : (
            <Download className="h-3.5 w-3.5 text-indigo-400" />
          )}
          Download Original
        </button>
      </div>

      {/* Pagination & Zoom Controls */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1">
          <button className="p-1 rounded hover:bg-slate-800 text-slate-500 hover:text-slate-300" aria-label="Zoom out">
            <ZoomOut className="h-4 w-4" />
          </button>
          <span className="text-[10px] text-slate-500 font-mono">100%</span>
          <button className="p-1 rounded hover:bg-slate-800 text-slate-500 hover:text-slate-300" aria-label="Zoom in">
            <ZoomIn className="h-4 w-4" />
          </button>
        </div>

        <span className="text-slate-700">|</span>

        <div className="flex items-center gap-2">
          <button
            onClick={() => onPageChange(currentPage - 1)}
            disabled={currentPage <= 1}
            className="p-1 rounded hover:bg-slate-800 disabled:opacity-30 disabled:hover:bg-transparent text-slate-400 cursor-pointer disabled:cursor-not-allowed"
            aria-label="Previous page"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          <span className="text-xs text-slate-300 font-medium">
            Page {currentPage} of {pageCount}
          </span>
          <button
            onClick={() => onPageChange(currentPage + 1)}
            disabled={currentPage >= pageCount}
            className="p-1 rounded hover:bg-slate-800 disabled:opacity-30 disabled:hover:bg-transparent text-slate-400 cursor-pointer disabled:cursor-not-allowed"
            aria-label="Next page"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
