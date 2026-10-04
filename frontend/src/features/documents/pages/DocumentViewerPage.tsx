import { useState, useEffect } from 'react';
import { useParams, useNavigate, useLocation, Link } from 'react-router-dom';
import { PageShell } from '@/components/templates/PageShell';
import { DocumentToolbar } from '../components/DocumentToolbar';
import { DocumentViewer } from '../components/DocumentViewer';
import { Badge } from '@/components/atoms/Badge';
import { ArrowLeft, Loader2, ChevronRight, CheckCircle2, ShieldAlert } from 'lucide-react';
import { formatFileSize } from '@/lib/utils';
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
      <PageShell title="Document Intelligence" description="Loading document workspace...">
        <div className="flex flex-col items-center justify-center py-24 text-slate-400">
          <Loader2 className="h-8 w-8 animate-spin mb-3 text-indigo-500" />
          <p className="text-sm">Loading document content and intelligence...</p>
        </div>
      </PageShell>
    );
  }

  if (!doc) {
    return (
      <PageShell title="Document Intelligence" description="Document not found.">
        <div className="p-4 rounded-lg bg-red-950/20 text-red-400 border border-red-500/20 mb-4">
          Document with reference ID could not be loaded. Please return to the document library.
        </div>
        <button
          onClick={handleBack}
          id="doc-viewer-error-back-button"
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold cursor-pointer"
        >
          <ArrowLeft className="h-4 w-4" /> {returnLabel}
        </button>
      </PageShell>
    );
  }

  const docName = doc.original_filename || doc.filename || 'Document';
  const isHumanVerified = doc.doc_metadata?.review_status === 'reviewed_by_human';
  const isFlagged = doc.status === 'flagged';
  const fileExtension = docName.includes('.') ? docName.split('.').pop()?.toUpperCase() : (doc.content_type?.split('/')?.pop()?.toUpperCase() || 'FILE');

  return (
    <PageShell
      title={docName}
      description="Document intelligence workspace with extracted text, privilege screening, multi-type summaries, and attorney review."
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
      {/* Authoritative Breadcrumb Navigation */}
      {activeCaseId && (
        <nav aria-label="Document Breadcrumbs" className="flex items-center gap-1.5 text-xs text-slate-400 -mt-2 mb-2">
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
          <span className="text-slate-200 font-semibold truncate max-w-[280px]" aria-current="page">
            {docName}
          </span>
        </nav>
      )}

      {/* Document Metadata Badges Strip */}
      <div className="flex flex-wrap items-center gap-2 -mt-1 mb-2">
        {navState.caseName && (
          <span className="text-xs text-indigo-300 font-medium">
            Matter: {navState.caseName}
          </span>
        )}
        <span className="text-slate-600">•</span>
        <Badge
          variant={
            doc.status === 'reviewed'
              ? 'purple'
              : doc.status === 'flagged'
              ? 'danger'
              : doc.status === 'quota_paused'
              ? 'warning'
              : 'default'
          }
          size="xs"
          className="uppercase font-mono"
        >
          {doc.status}
        </Badge>
        <Badge variant="outline" size="xs">
          {fileExtension}
        </Badge>
        <span className="text-xs text-slate-400">
          {formatFileSize(doc.file_size)}
        </span>
        <span className="text-slate-600">•</span>
        <span className="text-xs text-slate-400">
          {doc.page_count || 1} {doc.page_count === 1 ? 'page' : 'pages'}
        </span>
        {isHumanVerified ? (
          <Badge variant="success" size="xs" className="flex items-center gap-1">
            <CheckCircle2 className="h-2.5 w-2.5" /> Human Verified
          </Badge>
        ) : isFlagged ? (
          <Badge variant="danger" size="xs" className="flex items-center gap-1">
            <ShieldAlert className="h-2.5 w-2.5" /> Flagged for Review
          </Badge>
        ) : null}
      </div>

      <div className="flex flex-col gap-4 h-[calc(100vh-14rem)]">
        {/* Document Action Toolbar */}
        <DocumentToolbar
          fileName={docName}
          pageCount={doc.page_count || 1}
          currentPage={currentPage}
          onPageChange={setCurrentPage}
          documentId={doc.id}
        />

        {/* Modular Side-by-Side Panels Viewer */}
        <DocumentViewer
          currentPage={currentPage}
          onPageChange={setCurrentPage}
          doc={doc}
          onDocUpdate={(updatedDoc) => setDoc(updatedDoc)}
        />
      </div>
    </PageShell>
  );
}
