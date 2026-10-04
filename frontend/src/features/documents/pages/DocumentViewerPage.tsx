import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { PageShell } from '@/components/templates/PageShell';
import { DocumentToolbar } from '../components/DocumentToolbar';
import { DocumentViewer } from '../components/DocumentViewer';
import { ArrowLeft, Loader2 } from 'lucide-react';
import api from '@/lib/api';

export function DocumentViewerPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [currentPage, setCurrentPage] = useState(1);
  const [doc, setDoc] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);

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
          onClick={() => navigate('/cases')}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold"
        >
          <ArrowLeft className="h-4 w-4" /> Back to Cases
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
          onClick={() => navigate(doc.case_id ? `/cases/${doc.case_id}/evidence` : '/cases')}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-750 text-slate-300 text-xs font-semibold border border-slate-700/50 transition-colors cursor-pointer"
        >
          <ArrowLeft className="h-4 w-4" /> {doc.case_id ? 'Back to Case' : 'Back to Cases'}
        </button>
      }
    >
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
