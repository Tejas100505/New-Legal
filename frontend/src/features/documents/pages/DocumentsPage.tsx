/**
 * DocumentsPage — full document management with library, filters, server-side pagination, and intelligence preview.
 */

import { useState, useCallback, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Upload, Grid3x3, List, Filter, Search,
  X, CloudUpload, CheckCircle2, AlertCircle, File,
  Loader2, ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight,
  ShieldAlert, Eye
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatDate, formatFileSize } from '@/lib/utils';
import { PageShell } from '@/components/templates/PageShell';
import { Badge } from '@/components/atoms/Badge';
import { ProgressBar } from '@/components/atoms/ProgressBar';
import { FileIcon } from '@/components/molecules/FileIcon';
import type { LegalDocument } from '@/types';
import api from '@/lib/api';

type ViewMode = 'list' | 'grid';
type FilterStatus = 'all' | 'uploaded' | 'processing' | 'analyzed' | 'reviewed' | 'flagged' | 'quota_paused';

const statusConfig: Record<string, { variant: 'default' | 'success' | 'warning' | 'danger' | 'info' | 'purple'; label: string }> = {
  uploaded: { variant: 'warning', label: 'Queued' },
  validating: { variant: 'warning', label: 'Validating' },
  processing: { variant: 'warning', label: 'Processing' },
  ocr_processing: { variant: 'warning', label: 'OCR Processing' },
  chunking: { variant: 'warning', label: 'Chunking' },
  embedding: { variant: 'warning', label: 'Embedding' },
  analyzing: { variant: 'warning', label: 'Analyzing' },
  reviewed: { variant: 'purple', label: 'Reviewed' },
  flagged: { variant: 'danger', label: 'Flagged' },
  error: { variant: 'danger', label: 'Error' },
  quota_paused: { variant: 'warning', label: 'Quota Paused' },
};

interface DocumentsPageProps {
  caseId?: string;
  caseName?: string;
}

export function DocumentsPage({ caseId: propCaseId, caseName }: DocumentsPageProps = {}) {
  const routeParams = useParams<{ caseId?: string }>();
  const caseId = propCaseId || routeParams.caseId;
  const navigate = useNavigate();
  const [viewMode, setViewMode] = useState<ViewMode>('list');
  const [filterStatus, setFilterStatus] = useState<FilterStatus>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedDoc, setSelectedDoc] = useState<LegalDocument | null>(null);
  const [showUpload, setShowUpload] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [uploadFiles, setUploadFiles] = useState<{
    name: string;
    size: number;
    progress: number;
    status: 'uploading' | 'processing' | 'done' | 'error';
    message?: string;
    docId?: string;
  }[]>([]);
  const [documents, setDocuments] = useState<LegalDocument[]>([]);
  const [totalDocs, setTotalDocs] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [loadingDocs, setLoadingDocs] = useState(true);
  const [isRetrying, setIsRetrying] = useState(false);

  const mapDocResponse = useCallback((d: any): LegalDocument => {
    const metadata = d.doc_metadata || {};
    const privilege = metadata.privilege_analysis || metadata.privilege || {};
    const risk = metadata.risk_analysis || metadata.risk || {};
    
    let docType: any = 'pdf';
    const ctype = (d.content_type || '').toLowerCase();
    const fname = (d.original_filename || '').toLowerCase();
    if (ctype.includes('docx') || fname.endsWith('.docx')) docType = 'docx';
    else if (ctype.includes('email') || ctype.includes('rfc822') || fname.endsWith('.eml')) docType = 'email';
    else if (ctype.includes('text') || fname.endsWith('.txt')) docType = 'txt';

    const rawConfidence = metadata.confidence_score ?? metadata.pipeline?.ocr?.confidence ?? null;
    const ocrAccuracy = rawConfidence != null ? Math.round(Number(rawConfidence) * 100) : 0;

    const isPriv = Boolean(privilege.is_privileged ?? d.is_privileged);
    const riskTier = (risk.risk_level || risk.overall_risk || (isPriv ? 'critical' : 'low')).toLowerCase();

    return {
      id: d.id,
      name: d.original_filename || d.filename || 'Document',
      type: docType,
      size: d.file_size || 0,
      status: d.status,
      caseId: d.case_id || caseId || 'case_unknown',
      caseName: caseName || d.case_name || (caseId ? `Case ${caseId.slice(0, 8)}` : 'All Documents'),
      ocrAccuracy,
      ocrConfidence: rawConfidence != null ? (rawConfidence > 0.85 ? 'high' : 'medium') : 'medium',
      pageCount: d.page_count || 1,
      entityCount: metadata.entities ? Object.values(metadata.entities).flat().length : 0,
      uploadedBy: d.uploaded_by ? String(d.uploaded_by).slice(0, 8) : 'Owner',
      uploadedAt: d.created_at || new Date().toISOString(),
      processedAt: d.updated_at || null,
      tags: metadata.tags || (metadata.document_type ? [metadata.document_type] : []),
      version: metadata.version || 1,
      isPrivileged: isPriv,
      riskLevel: riskTier as any,
      extractedEntities: metadata.entities ? Object.entries(metadata.entities).flatMap(([type, texts]) => 
        (Array.isArray(texts) ? texts : []).map((text, i) => ({
          id: `${type}-${i}`,
          type,
          text,
          confidence: 1.0
        }))
      ) : [],
      doc_metadata: metadata,
    };
  }, [caseId, caseName]);

  const fetchDocuments = useCallback(async () => {
    try {
      setLoadingDocs(true);
      const params: Record<string, any> = {
        page,
        page_size: pageSize,
        include_content: false,
      };
      if (caseId) params.case_id = caseId;
      const response = await api.get('/documents', { params });
      const rawDocs = response.data.documents || [];
      const docs = rawDocs.map(mapDocResponse);
      setDocuments(docs);
      setTotalDocs(response.data.total ?? docs.length);
    } catch (err) {
      console.error("Failed to load documents:", err);
      setDocuments([]);
      setTotalDocs(0);
    } finally {
      setLoadingDocs(false);
    }
  }, [caseId, page, pageSize, mapDocResponse]);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  // Reset page to 1 when caseId changes
  useEffect(() => {
    setPage(1);
  }, [caseId]);

  // Real-time polling while any document is undergoing background AI processing
  useEffect(() => {
    const hasPendingDocs = documents.some((d) =>
      ['processing', 'ocr_processing', 'validating', 'chunking', 'embedding', 'analyzing', 'uploaded'].includes(d.status)
    );
    const hasPendingUploads = uploadFiles.some((f) => f.status === 'processing');

    if (!hasPendingDocs && !hasPendingUploads) return;

    const interval = setInterval(async () => {
      try {
        const params: Record<string, any> = {
          page,
          page_size: pageSize,
          include_content: false,
        };
        if (caseId) params.case_id = caseId;
        const response = await api.get('/documents', { params });
        const rawDocs = response.data.documents || [];
        const mapped = rawDocs.map(mapDocResponse);
        setDocuments(mapped);
        setTotalDocs(response.data.total ?? mapped.length);

        setUploadFiles((prev) =>
          prev.map((f) => {
            if (f.status !== 'processing') return f;
            const match = mapped.find((d: any) => d.id === f.docId || d.name === f.name);
            if (match && ['analyzed', 'reviewed', 'flagged'].includes(match.status)) {
              return { ...f, status: 'done', message: 'Analysis complete. Document indexed and risk assessed.' };
            }
            if (match && match.status === 'error') {
              return { ...f, status: 'error', message: 'Analysis encountered an error.' };
            }
            return f;
          })
        );
      } catch (err) {
        console.error('Error polling documents status:', err);
      }
    }, 4000);

    return () => clearInterval(interval);
  }, [documents, uploadFiles, caseId, page, pageSize]);

  const filteredDocs = documents.filter((doc) => {
    if (filterStatus !== 'all' && doc.status !== filterStatus) return false;
    if (searchQuery && !doc.name.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    return true;
  });

  const totalPages = Math.max(1, Math.ceil(totalDocs / pageSize));
  const startItem = totalDocs === 0 ? 0 : (page - 1) * pageSize + 1;
  const endItem = Math.min(totalDocs, page * pageSize);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    const files = Array.from(e.dataTransfer.files);
    handleRealUpload(files);
  }, [uploadFiles.length, fetchDocuments]);

  async function handleRealUpload(files: File[]) {
    const newFiles = files.map((f) => ({
      name: f.name,
      size: f.size,
      progress: 0,
      status: 'uploading' as const,
    }));
    
    setUploadFiles((prev) => [...prev, ...newFiles]);
    setShowUpload(true);
    const currentLength = uploadFiles.length;

    if (files.length > 1) {
      const formData = new FormData();
      files.forEach((file) => formData.append('files', file));
      const uploadUrl = caseId
        ? `/documents/upload-multiple?case_id=${encodeURIComponent(caseId)}`
        : '/documents/upload-multiple';

      try {
        const uploadRes = await api.post<any[]>(uploadUrl, formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
          onUploadProgress: (progressEvent) => {
            if (progressEvent.total) {
              const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
              setUploadFiles((prev) =>
                prev.map((f, i) =>
                  i >= currentLength && i < currentLength + files.length
                    ? { ...f, progress: percentCompleted }
                    : f
                )
              );
            }
          },
        });

        const uploadedDocs = Array.isArray(uploadRes.data) ? uploadRes.data : [];
        setUploadFiles((prev) =>
          prev.map((f, i) => {
            if (i >= currentLength && i < currentLength + files.length) {
              const fileIdx = i - currentLength;
              const originalFile = files[fileIdx];
              const match =
                uploadedDocs.find((d: any) => d.original_filename === originalFile?.name) ||
                uploadedDocs[fileIdx];

              if (match && match.id) {
                return {
                  ...f,
                  progress: 100,
                  status: 'processing',
                  docId: match.id,
                  message: 'File stored. Running AI legal analysis pipeline...',
                };
              } else {
                return {
                  ...f,
                  status: 'error',
                  message: 'Upload failed or rejected by storage service.',
                };
              }
            }
            return f;
          })
        );
        fetchDocuments();
      } catch (err) {
        console.error('Batch upload failed', err);
      }
      return;
    }

    // Single-file upload
    if (files.length === 1) {
      const file = files[0];
      const formData = new FormData();
      formData.append('file', file);
      try {
        const uploadUrl = caseId ? `/documents/upload?case_id=${encodeURIComponent(caseId)}` : '/documents/upload';
        const uploadRes = await api.post(uploadUrl, formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
          onUploadProgress: (progressEvent) => {
            if (progressEvent.total) {
              const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
              setUploadFiles((prev) =>
                prev.map((f, i) => i === currentLength ? { ...f, progress: percentCompleted } : f)
              );
            }
          }
        });
        const uploadedDoc = uploadRes.data;
        const docId = uploadedDoc?.id;
        setUploadFiles((prev) =>
          prev.map((f, i) =>
            i === currentLength
              ? {
                  ...f,
                  progress: 100,
                  status: 'processing',
                  docId,
                  message: 'File stored. Running AI legal review...',
                }
              : f
          )
        );
        fetchDocuments();
      } catch (err) {
        console.error("Upload failed", err);
      }
    }
  }

  const navigateToViewer = (doc: LegalDocument) => {
    const targetCaseId = caseId || (doc.caseId !== 'case_unknown' ? doc.caseId : undefined);
    navigate(`/documents/${doc.id}`, {
      state: {
        caseId: targetCaseId,
        caseName: doc.caseName,
        returnTab: 'evidence',
      },
    });
  };

  return (
    <PageShell
      title="Documents & Evidence Library"
      description={`Case corpus index containing ${totalDocs} legal documents, filings, and evidence files.`}
      fullWidth
      actions={
        <div className="flex items-center gap-2">
          <button
            id="documents-upload-button"
            onClick={() => setShowUpload(!showUpload)}
            className={cn(
              'flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium',
              'bg-gradient-to-r from-indigo-500 to-violet-500 text-white',
              'shadow-lg shadow-indigo-500/20 hover:shadow-indigo-500/40',
              'hover:brightness-110 transition-all duration-200 cursor-pointer'
            )}
          >
            <Upload className="h-4 w-4" />
            Upload Evidence
          </button>
        </div>
      }
    >
      {/* Upload Area */}
      <AnimatePresence>
        {showUpload && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <div className="rounded-xl p-5 mb-4 bg-slate-900/50 backdrop-blur-xl border border-slate-800/50">
              <label
                className={cn(
                  'flex flex-col items-center justify-center py-10 px-6',
                  'border-2 border-dashed rounded-xl cursor-pointer transition-all duration-300',
                  dragActive
                    ? 'border-indigo-500 bg-indigo-500/5 shadow-lg shadow-indigo-500/10'
                    : 'border-slate-700 hover:border-slate-500 hover:bg-slate-900/30'
                )}
                onDrop={handleDrop}
                onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
                onDragLeave={() => setDragActive(false)}
              >
                <CloudUpload className={cn('h-10 w-10 mb-3', dragActive ? 'text-indigo-400' : 'text-slate-500')} />
                <p className="text-sm font-medium text-slate-300 mb-1">
                  {dragActive ? 'Drop files here' : 'Drag & drop files, or click to browse'}
                </p>
                <p className="text-xs text-slate-500">PDF, DOCX, TXT, EML — automatic text extraction & privilege screening</p>
                <input type="file" className="hidden" multiple accept=".pdf,.docx,.txt,.eml,.xlsx" onChange={(e) => e.target.files && handleRealUpload(Array.from(e.target.files))} />
              </label>

              {/* Upload Progress */}
              {uploadFiles.length > 0 && (
                <div className="mt-4 space-y-2">
                  {uploadFiles.map((f, i) => (
                    <div key={i} className="flex flex-col gap-1.5 p-3 rounded-lg bg-slate-800/40 border border-slate-700/50">
                      <div className="flex items-center gap-3">
                        <File className="h-4 w-4 text-slate-400 shrink-0" />
                        <div className="flex-1 min-w-0">
                          <p className="text-xs font-medium text-slate-200 truncate">{f.name}</p>
                          <p className="text-[10px] text-slate-400">
                            {formatFileSize(f.size)} • {f.status === 'uploading' ? `Uploading (${f.progress}%)` : f.status === 'processing' ? 'Running AI legal analysis...' : f.status === 'done' ? 'Completed' : 'Error'}
                          </p>
                        </div>
                        {f.status === 'uploading' && (
                          <span className="text-xs font-mono text-indigo-400">{f.progress}%</span>
                        )}
                        {f.status === 'processing' && (
                          <div className="flex items-center gap-1.5 text-xs text-amber-400 font-medium">
                            <Loader2 className="h-3.5 w-3.5 animate-spin" />
                            <span className="text-[11px]">Analyzing...</span>
                          </div>
                        )}
                        {f.status === 'done' && <CheckCircle2 className="h-4 w-4 text-emerald-400" />}
                        {f.status === 'error' && <AlertCircle className="h-4 w-4 text-red-400" />}
                      </div>
                      {f.status === 'uploading' && (
                        <ProgressBar value={f.progress} size="xs" variant="default" />
                      )}
                      {f.message && (
                        <p className={cn(
                          'text-[10px] pl-7',
                          f.status === 'error' ? 'text-rose-400' : 'text-slate-400'
                        )}>
                          {f.message}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Filters Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center gap-3 p-4 rounded-xl mb-4 bg-slate-900/50 backdrop-blur-xl border border-slate-800/50">
        {/* Search */}
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search documents on this page..."
            className="w-full pl-10 pr-4 py-2 rounded-lg bg-slate-800/60 border border-slate-700/50 text-sm text-slate-200 placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 transition-all"
          />
        </div>

        {/* Status Filter */}
        <div className="flex items-center gap-1.5 flex-wrap">
          <Filter className="h-4 w-4 text-slate-500 mr-1" />
          {(['all', 'reviewed', 'flagged', 'quota_paused'] as FilterStatus[]).map((status) => (
            <button
              key={status}
              onClick={() => setFilterStatus(status)}
              className={cn(
                'px-3 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer',
                filterStatus === status
                  ? 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              )}
            >
              {status === 'all' ? 'All' : status === 'quota_paused' ? 'Quota Paused' : status.charAt(0).toUpperCase() + status.slice(1)}
            </button>
          ))}
        </div>

        {/* View toggle */}
        <div className="flex items-center gap-1 bg-slate-800/50 rounded-lg p-0.5">
          <button
            onClick={() => setViewMode('list')}
            className={cn('p-1.5 rounded-md transition-colors cursor-pointer', viewMode === 'list' ? 'bg-slate-700 text-slate-200' : 'text-slate-500')}
            aria-label="List view"
          >
            <List className="h-4 w-4" />
          </button>
          <button
            onClick={() => setViewMode('grid')}
            className={cn('p-1.5 rounded-md transition-colors cursor-pointer', viewMode === 'grid' ? 'bg-slate-700 text-slate-200' : 'text-slate-500')}
            aria-label="Grid view"
          >
            <Grid3x3 className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Document Library + Preview Drawer */}
      <div className="flex gap-4">
        {/* Document List / Grid */}
        <div className={cn('flex-1 min-w-0', selectedDoc && 'hidden xl:block')}>
          {loadingDocs ? (
            <div className="rounded-xl border border-slate-800/50 p-16 text-center flex flex-col items-center justify-center space-y-3">
              <Loader2 className="h-8 w-8 text-indigo-500 animate-spin" />
              <p className="text-xs text-slate-400">Loading case documents (Page {page})...</p>
            </div>
          ) : viewMode === 'list' ? (
            <div className="rounded-xl border border-slate-800/50 overflow-hidden bg-slate-900/30">
              {/* Table header */}
              <div className="grid grid-cols-[1fr_90px_100px_100px_90px_70px_80px_90px] gap-3 px-4 py-3 bg-slate-900/80 border-b border-slate-800/60 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                <span>Document</span>
                <span>Type</span>
                <span>Status</span>
                <span>Privilege</span>
                <span>Risk</span>
                <span>Pages</span>
                <span>Size</span>
                <span className="text-right">Action</span>
              </div>

              {filteredDocs.length === 0 ? (
                <div className="p-12 text-center text-slate-500 text-xs">
                  No documents found matching current filter criteria on this page.
                </div>
              ) : (
                filteredDocs.map((doc, i) => (
                  <motion.div
                    key={doc.id}
                    initial={{ opacity: 0, y: 5 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.015 }}
                    onClick={() => setSelectedDoc(doc)}
                    className={cn(
                      'grid grid-cols-[1fr_90px_100px_100px_90px_70px_80px_90px] gap-3 px-4 py-3 items-center',
                      'border-b border-slate-800/30 cursor-pointer transition-colors',
                      selectedDoc?.id === doc.id ? 'bg-indigo-500/10' : 'hover:bg-slate-800/30'
                    )}
                  >
                    {/* Document Name */}
                    <div className="flex items-center gap-2.5 min-w-0">
                      <FileIcon type={doc.type} size="sm" />
                      <div className="min-w-0">
                        <p className="text-xs font-medium text-slate-200 truncate" title={doc.name}>
                          {doc.name}
                        </p>
                        <p className="text-[10px] text-slate-500 truncate">
                          {formatDate(doc.uploadedAt)}
                        </p>
                      </div>
                    </div>

                    {/* File Type */}
                    <Badge variant="outline" size="xs" className="uppercase font-mono">
                      {doc.type}
                    </Badge>

                    {/* Status */}
                    <div>
                      <Badge
                        variant={statusConfig[doc.status]?.variant || 'default'}
                        size="xs"
                        dot
                      >
                        {statusConfig[doc.status]?.label || doc.status}
                      </Badge>
                    </div>

                    {/* Privilege */}
                    <div>
                      {doc.isPrivileged ? (
                        <Badge variant="danger" size="xs" className="flex items-center gap-1">
                          <ShieldAlert className="h-3 w-3" /> Privileged
                        </Badge>
                      ) : (
                        <span className="text-[11px] text-slate-500">—</span>
                      )}
                    </div>

                    {/* Risk */}
                    <div>
                      <Badge
                        variant={
                          doc.riskLevel === 'critical'
                            ? 'danger'
                            : doc.riskLevel === 'high'
                            ? 'warning'
                            : 'default'
                        }
                        size="xs"
                        className="uppercase"
                      >
                        {doc.riskLevel}
                      </Badge>
                    </div>

                    {/* Pages */}
                    <span className="text-xs text-slate-400">{doc.pageCount} p.</span>

                    {/* Size */}
                    <span className="text-xs text-slate-400 font-mono">{formatFileSize(doc.size)}</span>

                    {/* Direct Review Link */}
                    <div className="text-right">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          navigateToViewer(doc);
                        }}
                        className="px-2.5 py-1 rounded bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-300 border border-indigo-500/20 text-xs font-medium transition-colors cursor-pointer inline-flex items-center gap-1"
                      >
                        <Eye className="h-3 w-3" /> Review
                      </button>
                    </div>
                  </motion.div>
                ))
              )}
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
              {filteredDocs.map((doc, i) => (
                <motion.div
                  key={doc.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.02 }}
                  onClick={() => setSelectedDoc(doc)}
                  className={cn(
                    'rounded-xl p-4 cursor-pointer',
                    'bg-slate-900/50 border border-slate-800/50',
                    'hover:border-indigo-500/20 hover:-translate-y-0.5',
                    'transition-all duration-200',
                    selectedDoc?.id === doc.id && 'border-indigo-500/40 shadow-lg shadow-indigo-500/5'
                  )}
                >
                  <div className="flex items-start gap-3 mb-3">
                    <FileIcon type={doc.type} />
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-semibold text-slate-200 truncate" title={doc.name}>{doc.name}</p>
                      <p className="text-[10px] text-slate-500 mt-0.5">{formatDate(doc.uploadedAt)}</p>
                    </div>
                  </div>
                  <div className="flex items-center justify-between pt-2 border-t border-slate-800/60">
                    <div className="flex items-center gap-1.5">
                      <Badge variant={statusConfig[doc.status]?.variant || 'default'} size="xs">
                        {statusConfig[doc.status]?.label || doc.status}
                      </Badge>
                      {doc.isPrivileged && (
                        <Badge variant="danger" size="xs">Privileged</Badge>
                      )}
                    </div>
                    <span className="text-xs text-slate-400 font-mono">{formatFileSize(doc.size)}</span>
                  </div>
                </motion.div>
              ))}
            </div>
          )}

          {/* ── Server-Side Pagination Bar ───────────────────────────────── */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 p-4 mt-4 rounded-xl bg-slate-900/40 border border-slate-800/50 text-xs text-slate-400">
            <div>
              Showing <span className="font-semibold text-slate-200">{startItem}–{endItem}</span> of{' '}
              <span className="font-semibold text-slate-200">{totalDocs}</span> documents in matter
            </div>

            <div className="flex items-center gap-4">
              {/* Page Size Selector */}
              <div className="flex items-center gap-2">
                <span>Per page:</span>
                <select
                  value={pageSize}
                  onChange={(e) => {
                    setPageSize(Number(e.target.value));
                    setPage(1);
                  }}
                  className="bg-slate-800 border border-slate-700 text-xs text-slate-200 rounded-lg px-2 py-1 focus:outline-none focus:ring-1 focus:ring-indigo-500 cursor-pointer"
                >
                  <option value={25}>25</option>
                  <option value={50}>50</option>
                  <option value={100}>100</option>
                </select>
              </div>

              {/* Navigation Controls */}
              <div className="flex items-center gap-1">
                <button
                  type="button"
                  onClick={() => setPage(1)}
                  disabled={page <= 1}
                  className="p-1.5 rounded-lg border border-slate-800 bg-slate-850 hover:bg-slate-800 text-slate-300 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer transition-colors"
                  title="First page"
                >
                  <ChevronsLeft className="h-3.5 w-3.5" />
                </button>
                <button
                  type="button"
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page <= 1}
                  className="p-1.5 rounded-lg border border-slate-800 bg-slate-850 hover:bg-slate-800 text-slate-300 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer transition-colors"
                  title="Previous page"
                >
                  <ChevronLeft className="h-3.5 w-3.5" />
                </button>

                <span className="px-3 py-1 font-medium text-slate-200">
                  Page {page} of {totalPages}
                </span>

                <button
                  type="button"
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page >= totalPages}
                  className="p-1.5 rounded-lg border border-slate-800 bg-slate-850 hover:bg-slate-800 text-slate-300 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer transition-colors"
                  title="Next page"
                >
                  <ChevronRight className="h-3.5 w-3.5" />
                </button>
                <button
                  type="button"
                  onClick={() => setPage(totalPages)}
                  disabled={page >= totalPages}
                  className="p-1.5 rounded-lg border border-slate-800 bg-slate-850 hover:bg-slate-800 text-slate-300 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer transition-colors"
                  title="Last page"
                >
                  <ChevronsRight className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Selected Document Preview Drawer */}
        <AnimatePresence>
          {selectedDoc && (
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              className={cn(
                'w-full xl:w-[380px] shrink-0',
                'rounded-xl p-5',
                'bg-slate-900/60 backdrop-blur-xl border border-slate-800/80',
                'overflow-y-auto max-h-[calc(100vh-14rem)] space-y-4'
              )}
            >
              <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">Document Overview</h3>
                <button
                  onClick={() => setSelectedDoc(null)}
                  className="p-1 rounded-lg text-slate-500 hover:text-slate-300 hover:bg-slate-800/50 transition-colors cursor-pointer"
                  aria-label="Close preview"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              {/* File Info */}
              <div className="flex items-center gap-3 p-3 rounded-lg bg-slate-800/40 border border-slate-800">
                <FileIcon type={selectedDoc.type} size="md" />
                <div className="min-w-0">
                  <p className="text-xs font-semibold text-slate-200 break-words">{selectedDoc.name}</p>
                  <p className="text-[10px] text-slate-400">{formatFileSize(selectedDoc.size)} • {selectedDoc.pageCount} pages</p>
                </div>
              </div>

              {/* Status Badges */}
              <div className="flex flex-wrap gap-2">
                <Badge variant={statusConfig[selectedDoc.status]?.variant || 'default'} size="sm" dot>
                  {statusConfig[selectedDoc.status]?.label || selectedDoc.status}
                </Badge>
                {selectedDoc.isPrivileged && <Badge variant="danger" size="sm">Privileged</Badge>}
                <Badge variant={selectedDoc.riskLevel === 'critical' ? 'danger' : selectedDoc.riskLevel === 'high' ? 'warning' : 'default'} size="sm">
                  Risk: {selectedDoc.riskLevel.toUpperCase()}
                </Badge>
              </div>

              {/* Quota Paused Notice */}
              {selectedDoc.status === 'quota_paused' && (
                <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-200 space-y-2">
                  <div className="flex items-center gap-1.5 font-semibold text-xs text-amber-300">
                    <AlertCircle className="h-4 w-4 text-amber-400 shrink-0" />
                    Pipeline Paused (Gemini LLM Quota)
                  </div>
                  <p className="text-[11px] text-amber-300/80 leading-relaxed">
                    Daily LLM quota reached. All upstream extracted text and OCR results are preserved.
                  </p>
                  <button
                    onClick={async () => {
                      try {
                        setIsRetrying(true);
                        await api.post(`/documents/${selectedDoc.id}/retry`);
                        await fetchDocuments();
                      } catch (err: any) {
                        alert(err?.response?.data?.detail || "Failed to retry document");
                      } finally {
                        setIsRetrying(false);
                      }
                    }}
                    disabled={isRetrying}
                    className="w-full py-1.5 px-3 rounded-lg bg-amber-500 hover:bg-amber-400 disabled:opacity-50 text-slate-950 font-semibold text-xs flex items-center justify-center gap-1.5 transition-all cursor-pointer"
                  >
                    {isRetrying ? 'Resuming Pipeline...' : 'Resume Pipeline'}
                  </button>
                </div>
              )}

              {/* Launch Review Action Button */}
              <div className="pt-2">
                <button
                  onClick={() => navigateToViewer(selectedDoc)}
                  id="launch-review-workspace-btn"
                  className="w-full py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs flex items-center justify-center gap-1.5 transition-all shadow-md cursor-pointer"
                >
                  <Eye className="h-4 w-4" />
                  Launch Document Intelligence
                </button>
              </div>

              {/* Metadata Details */}
              <div className="space-y-2 pt-2 border-t border-slate-800 text-xs">
                <div className="flex justify-between text-slate-400">
                  <span>File Type:</span>
                  <span className="font-mono text-slate-200 uppercase">{selectedDoc.type}</span>
                </div>
                <div className="flex justify-between text-slate-400">
                  <span>Page Count:</span>
                  <span className="font-medium text-slate-200">{selectedDoc.pageCount}</span>
                </div>
                <div className="flex justify-between text-slate-400">
                  <span>Uploaded:</span>
                  <span className="text-slate-200">{formatDate(selectedDoc.uploadedAt)}</span>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </PageShell>
  );
}
