import { useState, useEffect } from 'react';
import { useParams, useNavigate, useLocation, Link } from 'react-router-dom';
import { PageShell } from '@/components/templates/PageShell';
import { DocumentToolbar } from '../components/DocumentToolbar';
import { DocumentViewer } from '../components/DocumentViewer';
import { ArrowLeft, Loader2, ChevronRight } from 'lucide-react';
import api from '@/lib/api';

export function DocumentViewerPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const navState = (location.state as { caseId?: string; caseName?: string; returnTab?: string }) || {};

  const [currentPage, setCurrentPage] = useState(1);
  const [doc, setDoc] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Active case context: prefer router state, fallback to doc.case_id from backend API
  const activeCaseId = navState.caseId || doc?.case_id;
  const returnTab = navState.returnTab || 'evidence';
  const returnUrl = activeCaseId ? `/cases/${activeCaseId}/${returnTab}` : '/cases';
  const returnLabel = activeCaseId
    ? `Back to Case (${returnTab.charAt(0).toUpperCase() + returnTab.slice(1)})`
    : 'Back to Cases';

  const handleBack = () => {
    navigate(returnUrl);
  };

  useEffect(() => {
    if (id) {
      setIsLoading(true);
      api.get(`/documents/${id}`)
        .then((res) => setDoc(res.data))
        .catch(() => setDoc(null))
        .finally(() => setIsLoading(false));
    }
  }, [id]);

  if (isLoading) {
    return (
      <PageShell title="Document Viewer" description="Loading document workspace...">
        <div className="flex flex-col items-center justify-center py-20 text-slate-400">
          <Loader2 className="h-8 w-8 animate-spin mb-3 text-indigo-500" />
          <p className="text-sm">Loading document content and AI annotations...</p>
        </div>
      </PageShell>
    );
  }

  if (!doc) {
    return (
      <PageShell title="Document Viewer" description="Document not found.">
        <div className="p-4 rounded-lg bg-red-950/20 text-red-400 border border-red-500/20 mb-4">
          Document with reference ID could not be loaded. Please return to the document library.
        </div>
        <button
          onClick={handleBack}
          id="doc-viewer-error-back-button"
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold"
        >
          <ArrowLeft className="h-4 w-4" /> {returnLabel}
        </button>
      </PageShell>
    );
  }

  return (
    <PageShell
      title="Enterprise Document Review & Analysis Workspace"
      description="Side-by-side workspace with inline legal reasoning, entity classification, and version comparison."
      fullWidth
      actions={
        <button
          onClick={handleBack}
          id="doc-viewer-back-button"
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-750 text-slate-300 text-xs font-semibold border border-slate-700/50 transition-colors cursor-pointer"
        >
          <ArrowLeft className="h-4 w-4" /> {returnLabel}
        </button>
      }
    >
      {activeCaseId && (
        <nav aria-label="Document Breadcrumbs" className="flex items-center gap-1.5 text-xs text-slate-400 -mt-2 mb-3">
          <Link to="/cases" className="hover:text-indigo-400 font-medium transition-colors">Cases</Link>
          <ChevronRight className="h-3 w-3 text-slate-600" />
          <Link to={`/cases/${activeCaseId}/overview`} className="hover:text-indigo-400 font-medium transition-colors max-w-[240px] truncate">
            {navState.caseName || 'Case Workspace'}
          </Link>
          <ChevronRight className="h-3 w-3 text-slate-600" />
          <Link to={returnUrl} className="hover:text-indigo-400 font-medium transition-colors capitalize">
            {returnTab}
          </Link>
          <ChevronRight className="h-3 w-3 text-slate-600" />
          <span className="text-slate-200 font-semibold truncate max-w-[240px]" aria-current="page">
            {doc.original_filename || doc.filename || 'Document'}
          </span>
        </nav>
      )}
      <div className="flex flex-col gap-4 h-[calc(100vh-12rem)]">
        {/* Document Action Toolbar */}
        <DocumentToolbar
          fileName={doc.original_filename || doc.filename || doc.name || 'Document'}
          pageCount={doc.page_count || doc.pageCount || 1}
          currentPage={currentPage}
          onPageChange={setCurrentPage}
          documentId={doc.id}
        />

        {/* Modular Side-by-Side Panels Viewer */}
        <DocumentViewer
          currentPage={currentPage}
          onPageChange={setCurrentPage}
          doc={doc}
        />
      </div>
    </PageShell>
  );
}
