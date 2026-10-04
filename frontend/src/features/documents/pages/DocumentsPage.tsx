/**
 * DocumentsPage — full document management with library, filters, and preview panel.
 */

import { useState, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Upload, Grid3x3, List, Filter, Search, Tag,
  X, CloudUpload, CheckCircle2, AlertCircle, File,
  Clock, Loader2,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatDate, formatFileSize } from '@/lib/utils';
import { PageShell } from '@/components/templates/PageShell';
import { Badge } from '@/components/atoms/Badge';
import { ProgressBar } from '@/components/atoms/ProgressBar';
import { FileIcon } from '@/components/molecules/FileIcon';
import type { LegalDocument } from '@/types';
import api from '@/lib/api';

type ViewMode = 'grid' | 'list';
type FilterStatus = 'all' | 'uploaded' | 'processing' | 'analyzed' | 'reviewed' | 'flagged' | 'quota_paused';

const statusConfig: Record<string, { variant: 'default' | 'success' | 'warning' | 'danger' | 'info' | 'purple'; label: string }> = {
  uploaded: { variant: 'warning', label: 'Queued' },
  processing: { variant: 'warning', label: 'Processing (30–60s)' },
  ocr_processing: { variant: 'warning', label: 'Processing (30–60s)' },
  ocr_complete: { variant: 'info', label: 'OCR Done' },
  analyzed: { variant: 'success', label: 'Analyzed' },
  reviewed: { variant: 'purple', label: 'Reviewed' },
  flagged: { variant: 'danger', label: 'Flagged' },
  error: { variant: 'danger', label: 'Error' },
  quota_paused: { variant: 'warning', label: 'Quota Paused' },
};

interface DocumentsPageProps {
  caseId?: string;
  caseName?: string;
}

export function DocumentsPage({ caseId, caseName }: DocumentsPageProps = {}) {
  const navigate = useNavigate();
  const [viewMode, setViewMode] = useState<ViewMode>('list');
  const [filterStatus, setFilterStatus] = useState<FilterStatus>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedDoc, setSelectedDoc] = useState<LegalDocument | null>(null);
  const [showUpload, setShowUpload] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [uploadFiles, setUploadFiles] = useState<{
    name: string;
    size: number;
    progress: number;
    status: 'uploading' | 'processing' | 'done' | 'error';
    message?: string;
    docId?: string;
  }[]>([]);
  const [documents, setDocuments] = useState<LegalDocument[]>([]);
  const [, setLoadingDocs] = useState(true);
  const [isRetrying, setIsRetrying] = useState(false);

  const mapDocResponse = (d: any): LegalDocument => {
    const metadata = d.doc_metadata || {};
    const privilege = metadata.privilege || {};
    const risk = metadata.risk || {};
    
    let docType: any = 'pdf';
    if (d.content_type.includes('docx') || d.original_filename.endsWith('.docx')) docType = 'docx';
    else if (d.content_type.includes('email') || d.content_type.includes('rfc822') || d.original_filename.endsWith('.eml')) docType = 'email';
    else if (d.content_type.includes('text') || d.original_filename.endsWith('.txt')) docType = 'txt';

    return {
      id: d.id,
      name: d.original_filename,
      type: docType,
      size: d.file_size,
      status: d.status === 'ocr_processing' ? 'processing' : d.status,
      caseId: d.case_id || 'case_unknown',
      caseName: caseName || d.case_name || (caseId ? `Case ${caseId.slice(0, 8)}` : 'All Documents'),
      ocrAccuracy: metadata.confidence_score ?? null,
      ocrConfidence: metadata.confidence_score != null ? (metadata.confidence_score > 0.85 ? 'high' : 'medium') : 'medium',
      pageCount: d.page_count || 1,
      entityCount: metadata.entities ? Object.values(metadata.entities).flat().length : 0,
      uploadedBy: d.uploaded_by ? String(d.uploaded_by).slice(0, 8) : 'Owner',
      uploadedAt: d.created_at || new Date().toISOString(),
      processedAt: d.updated_at || null,
      tags: metadata.tags || (metadata.document_type ? [metadata.document_type] : []),
      version: metadata.version || 1,
      isPrivileged: privilege.is_privileged || false,
      riskLevel: (risk.overall_risk || 'none').toLowerCase() as any,
      extractedEntities: metadata.entities ? Object.entries(metadata.entities).flatMap(([type, texts]) => 
        (texts as string[]).map((text, i) => ({
          id: `${type}-${i}`,
          type,
          text,
          confidence: 1.0
        }))
      ) : [],
      doc_metadata: metadata,
    };
  };

  const fetchDocuments = useCallback(async () => {
    try {
      setLoadingDocs(true);
      const params: Record<string, string> = {};
      if (caseId) params.case_id = caseId;
      const response = await api.get('/documents', { params });
      const docs = response.data.documents.map(mapDocResponse);
      setDocuments(docs);
    } catch (err) {
      console.error("Failed to load documents:", err);
      setDocuments([]);
    } finally {
      setLoadingDocs(false);
    }
  }, [caseId]);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  // Real-time polling while any document is undergoing background AI processing
  useEffect(() => {
    const hasPendingDocs = documents.some((d) =>
      ['processing', 'ocr_processing', 'uploaded'].includes(d.status)
    );
    const hasPendingUploads = uploadFiles.some((f) => f.status === 'processing');

    if (!hasPendingDocs && !hasPendingUploads) return;

    const interval = setInterval(async () => {
      try {
        const params: Record<string, string> = {};
        if (caseId) params.case_id = caseId;
        const response = await api.get('/documents', { params });
        const rawDocs = response.data.documents || [];
        const mapped = rawDocs.map(mapDocResponse);
        setDocuments(mapped);

        // Update upload cards with dynamic stage messaging as processing proceeds
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
            if (match && match.status === 'ocr_complete') {
              return { ...f, message: 'Stage 2/3: OCR complete. Screening attorney-client privilege & evaluating risk...' };
            }
            if (match && (match.status === 'ocr_processing' || match.status === 'processing')) {
              return { ...f, message: 'Stage 1/3: Ingested. Extracting text & running entity recognition (30–60s)...' };
            }
            return f;
          })
        );
      } catch (err) {
        console.error('Error polling documents status:', err);
      }
    }, 4000);

    return () => clearInterval(interval);
  }, [documents, uploadFiles, caseId]);

  const allTags = [...new Set(documents.flatMap((d) => d.tags))];

  const filteredDocs = documents.filter((doc) => {
    if (filterStatus !== 'all' && doc.status !== filterStatus) return false;
    if (searchQuery && !doc.name.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    if (selectedTags.length > 0 && !selectedTags.some((t) => doc.tags.includes(t))) return false;
    return true;
  });

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
    
    // Add to state
    setUploadFiles((prev) => [...prev, ...newFiles]);
    setShowUpload(true);
    
    const currentLength = uploadFiles.length;

    if (files.length > 1) {
      const formData = new FormData();
      files.forEach((file) => {
        formData.append('files', file);
      });

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
                  message: 'File stored. Running 10-stage AI legal review (typically 30–60s)...',
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
        setUploadFiles((prev) =>
          prev.map((f, i) =>
            i >= currentLength && i < currentLength + files.length
              ? { ...f, status: 'error', message: 'Batch upload failed. Please check file format and connection.' }
              : f
          )
        );
      }
      return;
    }

    // Single-file upload fallback
    for (let idx = 0; idx < files.length; idx++) {
      const file = files[idx];
      const totalIdx = currentLength + idx;
      
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
                prev.map((f, i) => i === totalIdx ? { ...f, progress: percentCompleted } : f)
              );
            }
          }
        });
        
        const uploadedDoc = uploadRes.data;
        const docId = uploadedDoc?.id || (Array.isArray(uploadedDoc) ? uploadedDoc[0]?.id : undefined);

        setUploadFiles((prev) =>
          prev.map((f, i) =>
            i === totalIdx
              ? {
                  ...f,
                  progress: 100,
                  status: 'processing',
                  docId,
                  message: 'File stored. Running 10-stage AI legal review (typically 30–60s)...',
                }
              : f
          )
        );
        
        fetchDocuments();
        
      } catch (err) {
        console.error("Upload failed", err);
        setUploadFiles((prev) =>
          prev.map((f, i) => i === totalIdx ? { ...f, status: 'error', message: 'Upload failed. Please check file format and connection.' } : f)
        );
      }
    }
  }

  return (
    <PageShell
      title="Documents"
      description="Upload, manage, and review legal documents with AI-powered analysis."
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
              'hover:brightness-110 transition-all duration-200'
            )}
          >
            <Upload className="h-4 w-4" />
            Upload
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
            <div className={cn(
              'rounded-xl p-5 mb-4',
              'bg-slate-900/50 backdrop-blur-xl border border-slate-800/50'
            )}>
              <label
                className={cn(
                  'flex flex-col items-center justify-center py-12 px-6',
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
                <p className="text-xs text-slate-500">PDF, DOCX, TXT, EML, XLSX — up to 100 MB per file</p>
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

      {/* Real-time processing banner when documents are undergoing background AI review */}
      {documents.some((d) => ['processing', 'ocr_processing', 'uploaded'].includes(d.status)) && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center gap-3 p-4 mb-4 rounded-xl bg-indigo-500/10 border border-indigo-500/30 text-indigo-200"
        >
          <Loader2 className="h-5 w-5 animate-spin text-indigo-400 shrink-0" />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-indigo-300">
                AI Document Review in Progress
              </span>
              <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                Typically 30–60s
              </span>
            </div>
            <p className="text-[11px] text-indigo-200/80 mt-0.5 leading-relaxed">
              Extracting text, identifying legal entities, and screening for attorney-client privilege. This background review typically takes 30–60 seconds per document. This page updates automatically.
            </p>
          </div>
        </motion.div>
      )}

      {/* Filters Bar */}
      <div className={cn(
        'flex flex-col sm:flex-row sm:items-center gap-3 p-4 rounded-xl mb-4',
        'bg-slate-900/50 backdrop-blur-xl border border-slate-800/50'
      )}>
        {/* Search */}
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search documents..."
            className="w-full pl-10 pr-4 py-2 rounded-lg bg-slate-800/60 border border-slate-700/50 text-sm text-slate-200 placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 transition-all"
          />
        </div>

        {/* Status Filter */}
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-slate-500" />
          {(['all', 'analyzed', 'processing', 'flagged', 'reviewed', 'quota_paused'] as FilterStatus[]).map((status) => (
            <button
              key={status}
              onClick={() => setFilterStatus(status)}
              className={cn(
                'px-3 py-1.5 rounded-lg text-xs font-medium transition-colors',
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
            className={cn('p-1.5 rounded-md transition-colors', viewMode === 'list' ? 'bg-slate-700 text-slate-200' : 'text-slate-500')}
            aria-label="List view"
          >
            <List className="h-4 w-4" />
          </button>
          <button
            onClick={() => setViewMode('grid')}
            className={cn('p-1.5 rounded-md transition-colors', viewMode === 'grid' ? 'bg-slate-700 text-slate-200' : 'text-slate-500')}
            aria-label="Grid view"
          >
            <Grid3x3 className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Tags */}
      <div className="flex flex-wrap gap-2 mb-4">
        {allTags.map((tag) => (
          <button
            key={tag}
            onClick={() => setSelectedTags((prev) => prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag])}
            className={cn(
              'flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium transition-colors',
              selectedTags.includes(tag)
                ? 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20'
                : 'bg-slate-800/40 text-slate-500 hover:text-slate-300 border border-transparent'
            )}
          >
            <Tag className="h-3 w-3" />
            {tag}
          </button>
        ))}
        {selectedTags.length > 0 && (
          <button
            onClick={() => setSelectedTags([])}
            className="flex items-center gap-1 px-2 py-1 text-xs text-slate-500 hover:text-slate-300"
          >
            <X className="h-3 w-3" />
            Clear
          </button>
        )}
      </div>

      {/* Document Library + Preview */}
      <div className="flex gap-4">
        {/* Document List */}
        <div className={cn('flex-1 min-w-0', selectedDoc && 'hidden lg:block')}>
          {viewMode === 'list' ? (
            <div className="rounded-xl border border-slate-800/50 overflow-hidden">
              {/* Table header */}
              <div className="grid grid-cols-[1fr_120px_100px_100px_80px] gap-4 px-4 py-3 bg-slate-900/80 border-b border-slate-800/50 text-xs font-semibold text-slate-500 uppercase tracking-wider">
                <span>Document</span>
                <span>Case</span>
                <span>Status</span>
                <span>OCR</span>
                <span>Size</span>
              </div>
              {filteredDocs.map((doc, i) => (
                <motion.div
                  key={doc.id}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.03 }}
                  onClick={() => setSelectedDoc(doc)}
                  className={cn(
                    'grid grid-cols-[1fr_120px_100px_100px_80px] gap-4 px-4 py-3 items-center',
                    'border-b border-slate-800/30 cursor-pointer transition-colors',
                    selectedDoc?.id === doc.id ? 'bg-indigo-500/5' : 'hover:bg-slate-800/20'
                  )}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <FileIcon type={doc.type} size="sm" />
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-slate-200 truncate">{doc.name}</p>
                      <p className="text-xs text-slate-600 truncate">{doc.tags.join(', ')}</p>
                    </div>
                  </div>
                  <span className="text-xs text-slate-500 truncate">{doc.caseName.split('—')[0].trim()}</span>
                  <Badge variant={statusConfig[doc.status]?.variant || 'default'} size="xs" dot pulse={doc.status === 'processing'}>
                    {statusConfig[doc.status]?.label || doc.status}
                  </Badge>
                  <div>
                    {doc.ocrAccuracy > 0 ? (
                      <div className="flex items-center gap-1.5">
                        <ProgressBar value={doc.ocrAccuracy} size="xs" variant={doc.ocrAccuracy > 95 ? 'success' : 'warning'} className="w-12" />
                        <span className="text-xs text-slate-400">{doc.ocrAccuracy}%</span>
                      </div>
                    ) : (
                      <span className="text-xs text-slate-600">—</span>
                    )}
                  </div>
                  <span className="text-xs text-slate-500">{formatFileSize(doc.size)}</span>
                </motion.div>
              ))}
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
              {filteredDocs.map((doc, i) => (
                <motion.div
                  key={doc.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.04 }}
                  onClick={() => setSelectedDoc(doc)}
                  className={cn(
                    'rounded-xl p-4 cursor-pointer',
                    'bg-slate-900/50 border border-slate-800/50',
                    'hover:border-indigo-500/20 hover:-translate-y-0.5',
                    'transition-all duration-300',
                    selectedDoc?.id === doc.id && 'border-indigo-500/30 shadow-lg shadow-indigo-500/5'
                  )}
                >
                  <div className="flex items-start gap-3 mb-3">
                    <FileIcon type={doc.type} />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-slate-200 truncate">{doc.name}</p>
                      <p className="text-xs text-slate-500 mt-0.5">{doc.caseName}</p>
                    </div>
                  </div>
                  <div className="flex items-center justify-between">
                    <Badge variant={statusConfig[doc.status]?.variant || 'default'} size="xs">
                      {statusConfig[doc.status]?.label || doc.status}
                    </Badge>
                    <span className="text-xs text-slate-600">{formatFileSize(doc.size)}</span>
                  </div>
                  {doc.ocrAccuracy > 0 && (
                    <ProgressBar value={doc.ocrAccuracy} size="xs" className="mt-3" variant={doc.ocrAccuracy > 95 ? 'success' : 'warning'} />
                  )}
                </motion.div>
              ))}
            </div>
          )}
        </div>

        {/* Preview Panel */}
        <AnimatePresence>
          {selectedDoc && (
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              className={cn(
                'w-full lg:w-[400px] shrink-0',
                'rounded-xl p-5',
                'bg-slate-900/50 backdrop-blur-xl border border-slate-800/50',
                'overflow-y-auto max-h-[calc(100vh-12rem)]'
              )}
            >
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-semibold text-slate-200">Document Details</h3>
                <button
                  onClick={() => setSelectedDoc(null)}
                  className="p-1 rounded-lg text-slate-500 hover:text-slate-300 hover:bg-slate-800/50 transition-colors"
                  aria-label="Close preview"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              {/* File info */}
              <div className="flex items-center gap-3 mb-4 p-3 rounded-lg bg-slate-800/30">
                <FileIcon type={selectedDoc.type} size="lg" />
                <div className="min-w-0">
                  <p className="text-sm font-medium text-slate-200 break-words">{selectedDoc.name}</p>
                  <p className="text-xs text-slate-500">{formatFileSize(selectedDoc.size)} • v{selectedDoc.version}</p>
                </div>
              </div>

              {/* Status & Risk */}
              <div className="flex gap-2 mb-4">
                <Badge variant={statusConfig[selectedDoc.status]?.variant || 'default'} size="sm" dot>
                  {statusConfig[selectedDoc.status]?.label || selectedDoc.status}
                </Badge>
                <Badge variant={selectedDoc.riskLevel === 'critical' ? 'danger' : selectedDoc.riskLevel === 'high' ? 'warning' : 'default'} size="sm">
                  Risk: {selectedDoc.riskLevel}
                </Badge>
                {selectedDoc.isPrivileged && <Badge variant="purple" size="sm">Privileged</Badge>}
              </div>

              {/* Quota Paused Notice & Fast Safe Resume */}
              {selectedDoc.status === 'quota_paused' && (
                <div className="mb-4 p-3 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-200">
                  <div className="flex items-center gap-1.5 font-semibold text-xs text-amber-300 mb-1">
                    <AlertCircle className="h-4 w-4 text-amber-400 shrink-0" />
                    Pipeline Paused (Gemini LLM Quota)
                  </div>
                  <p className="text-[11px] text-amber-300/80 leading-relaxed mb-2">
                    Daily LLM quota reached. All upstream extracted text, OCR, and vector embeddings are safely preserved in database.
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
                    className="w-full py-1.5 px-3 rounded-lg bg-amber-500 hover:bg-amber-400 disabled:opacity-50 text-slate-950 font-semibold text-xs flex items-center justify-center gap-1.5 transition-all shadow cursor-pointer"
                  >
                    {isRetrying ? 'Resuming Pipeline...' : 'Resume Pipeline (Skip Completed Stages)'}
                  </button>
                </div>
              )}

              {/* Action Buttons */}
              <div className="space-y-2 mb-4">
                <button
                  onClick={() => {
                    const targetCaseId = caseId || (selectedDoc.caseId !== 'case_unknown' ? selectedDoc.caseId : undefined);
                    navigate(`/documents/${selectedDoc.id}`, {
                      state: {
                        caseId: targetCaseId,
                        caseName: selectedDoc.caseName,
                        returnTab: 'evidence',
                      },
                    });
                  }}
                  id="launch-review-workspace-btn"
                  className="w-full py-2 rounded-lg bg-indigo-500 hover:bg-indigo-600 text-white font-medium text-xs flex items-center justify-center gap-1.5 transition-all shadow-md active:scale-95 cursor-pointer"
                >
                  Launch Review Workspace
                </button>
                <button
                  onClick={async () => {
                    if (window.confirm(`Are you sure you want to delete "${selectedDoc.name}"?`)) {
                      try {
                        await api.delete(`/documents/${selectedDoc.id}`);
                        setSelectedDoc(null);
                        fetchDocuments();
                      } catch (err) {
                        console.error("Failed to delete document", err);
                      }
                    }
                  }}
                  className="w-full py-1.5 rounded-lg bg-red-500/10 hover:bg-red-500/20 text-red-400 font-medium text-xs flex items-center justify-center gap-1.5 transition-all cursor-pointer border border-red-500/20"
                >
                  Delete Document
                </button>
              </div>

              {/* Metadata */}
              <div className="space-y-3 mb-4">
                <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Metadata</h4>
                <MetadataRow label="Case" value={selectedDoc.caseName} />
                <MetadataRow label="Type" value={selectedDoc.type.toUpperCase()} />
                <MetadataRow label="Pages" value={String(selectedDoc.pageCount)} />
                <MetadataRow label="Entities" value={String(selectedDoc.entityCount)} />
                <MetadataRow label="Uploaded" value={formatDate(selectedDoc.uploadedAt)} />
                {selectedDoc.processedAt && <MetadataRow label="Processed" value={formatDate(selectedDoc.processedAt)} />}
              </div>

              {/* OCR Results */}
              {selectedDoc.ocrAccuracy > 0 && (
                <div className="mb-4">
                  <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">OCR Results</h4>
                  <div className="p-3 rounded-lg bg-slate-800/30">
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-xs text-slate-400">Accuracy</span>
                      <span className="text-xs font-semibold text-slate-200">{selectedDoc.ocrAccuracy}%</span>
                    </div>
                    <ProgressBar value={selectedDoc.ocrAccuracy} variant={selectedDoc.ocrAccuracy > 95 ? 'success' : 'warning'} />
                  </div>
                </div>
              )}

              {/* Entity Highlights */}
              <div className="mb-4">
                <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                  Entities ({(selectedDoc as any).extractedEntities?.length || 0})
                </h4>
                <div className="space-y-1.5">
                  {((selectedDoc as any).extractedEntities || []).slice(0, 6).map((entity: any) => (
                    <div key={entity.id} className="flex items-center gap-2 p-2 rounded-lg bg-slate-800/20">
                      <Badge variant={entity.type === 'PERSON' ? 'info' : entity.type === 'ORG' ? 'purple' : entity.type === 'MONEY' ? 'success' : 'default'} size="xs">
                        {entity.type}
                      </Badge>
                      <span className="text-xs text-slate-300 truncate">{entity.text}</span>
                      <span className="text-[10px] text-slate-600 ml-auto">{Math.round(entity.confidence * 100)}%</span>
                    </div>
                  ))}
                  {!(selectedDoc as any).extractedEntities?.length && (
                    <p className="text-xs text-slate-500 italic">No entities extracted yet.</p>
                  )}
                </div>
              </div>

              {/* Tags */}
              <div className="mb-4">
                <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Tags</h4>
                <div className="flex flex-wrap gap-1.5">
                  {selectedDoc.tags.map((tag) => (
                    <Badge key={tag} variant="outline" size="xs">{tag}</Badge>
                  ))}
                  {selectedDoc.tags.length === 0 && <span className="text-xs text-slate-500 italic">No tags</span>}
                </div>
              </div>

              {/* Version History */}
              <div>
                <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Version History</h4>
                <div className="space-y-2">
                  <div className="flex items-start gap-2 p-2.5 rounded-lg bg-slate-800/20">
                    <Clock className="h-3.5 w-3.5 text-slate-500 mt-0.5 shrink-0" />
                    <div className="min-w-0">
                      <p className="text-xs font-medium text-slate-300">v{selectedDoc.version} — Initial Upload</p>
                      <p className="text-[10px] text-slate-600">{selectedDoc.uploadedBy} • {formatDate(selectedDoc.uploadedAt)}</p>
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </PageShell>
  );
}

function MetadataRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-xs text-slate-500">{label}</span>
      <span className="text-xs font-medium text-slate-300 text-right max-w-[200px] truncate">{value}</span>
    </div>
  );
}
