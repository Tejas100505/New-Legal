import React, { useState, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  X,
  Upload,
  FileText,
  CheckCircle2,
  AlertCircle,
  Loader2,
  FolderPlus,
  ArrowRight,
  ArrowLeft,
  Trash2,
} from 'lucide-react';
import api from '@/lib/api';
import { cn } from '@/lib/utils';

interface NewCaseModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

interface QueuedFile {
  id: string;
  file: File;
  name: string;
  size: number;
  status: 'queued' | 'uploading' | 'success' | 'error';
  progress: number;
  error?: string;
}

const CASE_TYPES = [
  'Commercial Litigation',
  'Regulatory / Compliance Defense',
  'Antitrust & Market Practices',
  'Internal Fraud / Forensic Investigation',
  'Contract & Breach Dispute',
  'Intellectual Property / Trade Secret',
  'Labor & Employment Dispute',
  'General E-Discovery Matter',
];

export function NewCaseModal({ isOpen, onClose, onSuccess }: NewCaseModalProps) {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Wizard Step
  const [step, setStep] = useState<1 | 2 | 3>(1);

  // Step 1: Matter Details
  const [name, setName] = useState('');
  const [matterNumber, setMatterNumber] = useState('');
  const [client, setClient] = useState('');
  const [caseType, setCaseType] = useState('Commercial Litigation');
  const [priority, setPriority] = useState<'low' | 'medium' | 'high' | 'critical'>('medium');
  const [description, setDescription] = useState('');
  const [nameError, setNameError] = useState('');

  // Step 2: Documents
  const [queuedFiles, setQueuedFiles] = useState<QueuedFile[]>([]);
  const [isDragActive, setIsDragActive] = useState(false);

  // Step 3: Execution state
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingStatus, setProcessingStatus] = useState<string>('');
  const [createdCaseId, setCreatedCaseId] = useState<string | null>(null);
  const [submissionError, setSubmissionError] = useState<string | null>(null);
  const [uploadResults, setUploadResults] = useState<{
    total: number;
    success: number;
    failed: number;
  }>({ total: 0, success: 0, failed: 0 });

  const resetForm = useCallback(() => {
    setStep(1);
    setName('');
    setMatterNumber('');
    setClient('');
    setCaseType('Commercial Litigation');
    setPriority('medium');
    setDescription('');
    setNameError('');
    setQueuedFiles([]);
    setIsProcessing(false);
    setProcessingStatus('');
    setCreatedCaseId(null);
    setSubmissionError(null);
    setUploadResults({ total: 0, success: 0, failed: 0 });
  }, []);

  const handleClose = () => {
    if (isProcessing) return; // Prevent closing mid-execution
    resetForm();
    onClose();
  };

  const handleStep1Submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setNameError('Case / Matter name is required.');
      return;
    }
    setNameError('');
    setStep(2);
  };

  const handleFilesSelected = (filesList: FileList | File[]) => {
    const incoming = Array.from(filesList).map((f) => ({
      id: `${f.name}-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
      file: f,
      name: f.name,
      size: f.size,
      status: 'queued' as const,
      progress: 0,
    }));
    setQueuedFiles((prev) => [...prev, ...incoming]);
  };

  const removeFile = (id: string) => {
    setQueuedFiles((prev) => prev.filter((f) => f.id !== id));
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const executeCaseCreationAndUpload = async () => {
    setIsProcessing(true);
    setSubmissionError(null);
    setStep(3);

    let newCaseUuid: string | null = null;

    try {
      // 1. Create Case Record
      setProcessingStatus('Creating legal matter record in database...');
      const casePayload = {
        name: name.trim(),
        case_number: matterNumber.trim() || undefined,
        matter_number: matterNumber.trim() || undefined,
        client: client.trim() || undefined,
        case_type: caseType || undefined,
        description: description.trim() || undefined,
        priority,
      };

      const caseRes = await api.post('/cases', casePayload);
      const createdCase = caseRes.data;
      newCaseUuid = createdCase.id;
      setCreatedCaseId(newCaseUuid);

      // 2. Upload Documents if queued
      if (queuedFiles.length > 0 && newCaseUuid) {
        setProcessingStatus(`Uploading ${queuedFiles.length} evidence document(s)...`);

        const formData = new FormData();
        queuedFiles.forEach((qf) => {
          formData.append('files', qf.file);
        });

        // Set files to uploading
        setQueuedFiles((prev) => prev.map((f) => ({ ...f, status: 'uploading', progress: 50 })));

        try {
          const uploadRes = await api.post<any[]>(
            `/documents/upload-multiple?case_id=${encodeURIComponent(newCaseUuid)}`,
            formData,
            {
              headers: { 'Content-Type': 'multipart/form-data' },
              onUploadProgress: (progressEvent: any) => {
                if (progressEvent.total) {
                  const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
                  setQueuedFiles((prev) =>
                    prev.map((f) => (f.status === 'uploading' ? { ...f, progress: percent } : f))
                  );
                }
              },
            }
          );

          const returnedDocs = Array.isArray(uploadRes.data) ? uploadRes.data : [];
          let successCount = 0;
          let failCount = 0;

          setQueuedFiles((prev) =>
            prev.map((qf) => {
              const match = returnedDocs.find(
                (d: any) => d.filename === qf.name || d.original_filename === qf.name
              );
              if (match && match.status !== 'error') {
                successCount++;
                return { ...qf, status: 'success', progress: 100 };
              } else {
                failCount++;
                return {
                  ...qf,
                  status: 'error',
                  progress: 100,
                  error: match?.error || match?.message || 'File upload rejected by storage backend.',
                };
              }
            })
          );

          setUploadResults({
            total: queuedFiles.length,
            success: successCount,
            failed: failCount,
          });

          setProcessingStatus('Documents uploaded. Starting Case Intelligence Analysis...');
        } catch (uploadErr: any) {
          setQueuedFiles((prev) =>
            prev.map((f) => ({
              ...f,
              status: 'error',
              error: uploadErr?.response?.data?.detail || 'Batch upload network error.',
            }))
          );
          setUploadResults({
            total: queuedFiles.length,
            success: 0,
            failed: queuedFiles.length,
          });
          setProcessingStatus('Case created, but document batch failed to upload.');
        }
      } else {
        setProcessingStatus('Matter created successfully.');
      }

      // Notify caller of success
      if (onSuccess) onSuccess();

      // Automatically navigate to new case overview
      setTimeout(() => {
        if (newCaseUuid) {
          resetForm();
          onClose();
          navigate(`/cases/${newCaseUuid}/overview`);
        }
      }, 1200);
    } catch (err: any) {
      console.error('New Case Creation Failed:', err);
      setIsProcessing(false);
      setSubmissionError(
        err?.response?.data?.detail || err?.message || 'Failed to create legal matter. Please check inputs.'
      );
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
      <motion.div
        initial={{ opacity: 0, scale: 0.96 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.96 }}
        className="w-full max-w-2xl bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]"
      >
        {/* Header */}
        <div className="px-6 py-5 border-b border-slate-800 flex items-center justify-between bg-slate-950/40">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
              <FolderPlus className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-100 tracking-tight">Create New Matter</h2>
              <p className="text-xs text-slate-400">
                Configure case parameters and upload initial evidence documents.
              </p>
            </div>
          </div>
          <button
            onClick={handleClose}
            disabled={isProcessing}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors disabled:opacity-50"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Step Progress Indicator */}
        <div className="px-6 py-3 bg-slate-950/20 border-b border-slate-800/60 flex items-center justify-between text-xs">
          <div className="flex items-center gap-2">
            <span
              className={cn(
                'flex items-center justify-center w-5 h-5 rounded-full font-semibold',
                step >= 1 ? 'bg-indigo-600 text-white' : 'bg-slate-800 text-slate-400'
              )}
            >
              1
            </span>
            <span className={step === 1 ? 'text-slate-100 font-medium' : 'text-slate-400'}>Matter Details</span>
          </div>
          <div className="w-8 h-px bg-slate-800" />
          <div className="flex items-center gap-2">
            <span
              className={cn(
                'flex items-center justify-center w-5 h-5 rounded-full font-semibold',
                step >= 2 ? 'bg-indigo-600 text-white' : 'bg-slate-800 text-slate-400'
              )}
            >
              2
            </span>
            <span className={step === 2 ? 'text-slate-100 font-medium' : 'text-slate-400'}>Document Upload</span>
          </div>
          <div className="w-8 h-px bg-slate-800" />
          <div className="flex items-center gap-2">
            <span
              className={cn(
                'flex items-center justify-center w-5 h-5 rounded-full font-semibold',
                step === 3 ? 'bg-indigo-600 text-white' : 'bg-slate-800 text-slate-400'
              )}
            >
              3
            </span>
            <span className={step === 3 ? 'text-slate-100 font-medium' : 'text-slate-400'}>Processing & Launch</span>
          </div>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto flex-1">
          {submissionError && (
            <div className="mb-4 p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-start gap-2.5 text-xs text-rose-300">
              <AlertCircle className="h-4 w-4 shrink-0 text-rose-400 mt-0.5" />
              <div>{submissionError}</div>
            </div>
          )}

          {/* STEP 1: MATTER DETAILS */}
          {step === 1 && (
            <form id="matter-details-form" onSubmit={handleStep1Submit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                  Case / Matter Name <span className="text-rose-400">*</span>
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => {
                    setName(e.target.value);
                    if (nameError) setNameError('');
                  }}
                  placeholder="e.g. Project Orion Commercial Contract Dispute"
                  className={cn(
                    'w-full bg-slate-950 border rounded-xl px-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none transition-colors',
                    nameError ? 'border-rose-500 focus:border-rose-500' : 'border-slate-800 focus:border-indigo-500'
                  )}
                  autoFocus
                />
                {nameError && <p className="mt-1 text-xs text-rose-400">{nameError}</p>}
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
                    Matter / Case Number
                  </label>
                  <input
                    type="text"
                    value={matterNumber}
                    onChange={(e) => setMatterNumber(e.target.value)}
                    placeholder="e.g. MAT-2026-0042"
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
                    Client / Organization
                  </label>
                  <input
                    type="text"
                    value={client}
                    onChange={(e) => setClient(e.target.value)}
                    placeholder="e.g. Zenith Dynamics Corp."
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
                    Case Type / Practice Area
                  </label>
                  <select
                    value={caseType}
                    onChange={(e) => setCaseType(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
                  >
                    {CASE_TYPES.map((ct) => (
                      <option key={ct} value={ct}>
                        {ct}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
                    Priority Level
                  </label>
                  <select
                    value={priority}
                    onChange={(e) => setPriority(e.target.value as any)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
                  >
                    <option value="low">Low Priority</option>
                    <option value="medium">Medium Priority</option>
                    <option value="high">High Priority</option>
                    <option value="critical">Critical Priority</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
                  Matter Description / Scope
                </label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={3}
                  placeholder="Outline case facts, key custodians, or legal issues for AI context..."
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 resize-none"
                />
              </div>
            </form>
          )}

          {/* STEP 2: DOCUMENT UPLOAD */}
          {step === 2 && (
            <div className="space-y-4">
              {/* Dropzone */}
              <div
                onDragOver={(e) => {
                  e.preventDefault();
                  setIsDragActive(true);
                }}
                onDragLeave={() => setIsDragActive(false)}
                onDrop={(e) => {
                  e.preventDefault();
                  setIsDragActive(false);
                  if (e.dataTransfer.files) handleFilesSelected(e.dataTransfer.files);
                }}
                onClick={() => fileInputRef.current?.click()}
                className={cn(
                  'border-2 border-dashed rounded-2xl p-6 text-center cursor-pointer transition-all',
                  isDragActive
                    ? 'border-indigo-500 bg-indigo-500/10'
                    : 'border-slate-800 hover:border-slate-700 bg-slate-950/40 hover:bg-slate-950/70'
                )}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  accept=".pdf,.docx,.doc,.txt,.csv,.msg,.eml,.png,.jpg,.jpeg,.tiff"
                  onChange={(e) => {
                    if (e.target.files) handleFilesSelected(e.target.files);
                  }}
                  className="hidden"
                />
                <div className="mx-auto w-12 h-12 rounded-xl bg-indigo-500/10 flex items-center justify-center text-indigo-400 mb-3">
                  <Upload className="h-6 w-6" />
                </div>
                <h3 className="text-sm font-semibold text-slate-100 mb-1">
                  Drag & drop case documents here, or click to browse
                </h3>
                <p className="text-xs text-slate-500 max-w-sm mx-auto">
                  Supports PDF, DOCX, TXT, CSV, EML/MSG email containers, and scanned documents up to 50MB.
                </p>
              </div>

              {/* Queued Document List */}
              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs text-slate-400 font-medium px-1">
                  <span>Selected Documents ({queuedFiles.length})</span>
                  {queuedFiles.length > 0 && (
                    <button
                      type="button"
                      onClick={() => setQueuedFiles([])}
                      className="text-rose-400 hover:text-rose-300 text-xs"
                    >
                      Clear all
                    </button>
                  )}
                </div>

                {queuedFiles.length === 0 ? (
                  <div className="p-4 rounded-xl bg-slate-950/40 border border-slate-800/60 text-center text-xs text-slate-500">
                    No documents selected yet. You may proceed and upload documents later from the Evidence tab.
                  </div>
                ) : (
                  <div className="max-h-48 overflow-y-auto space-y-2 pr-1">
                    {queuedFiles.map((qf) => (
                      <div
                        key={qf.id}
                        className="flex items-center justify-between p-2.5 rounded-xl bg-slate-950 border border-slate-800/80 text-xs"
                      >
                        <div className="flex items-center gap-2.5 truncate mr-3">
                          <FileText className="h-4 w-4 text-indigo-400 shrink-0" />
                          <span className="text-slate-200 font-medium truncate">{qf.name}</span>
                          <span className="text-slate-500 shrink-0">({formatFileSize(qf.size)})</span>
                        </div>
                        <button
                          type="button"
                          onClick={() => removeFile(qf.id)}
                          className="p-1 rounded text-slate-500 hover:text-rose-400 hover:bg-slate-800 transition-colors"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* STEP 3: EXECUTION & PROGRESS */}
          {step === 3 && (
            <div className="py-6 text-center space-y-6">
              <div className="relative mx-auto w-16 h-16 flex items-center justify-center">
                {isProcessing ? (
                  <Loader2 className="h-10 w-10 text-indigo-400 animate-spin" />
                ) : uploadResults.failed > 0 && uploadResults.success === 0 ? (
                  <AlertCircle className="h-10 w-10 text-rose-400" />
                ) : (
                  <CheckCircle2 className="h-10 w-10 text-emerald-400" />
                )}
              </div>

              <div>
                <h3 className="text-base font-bold text-slate-100 mb-1.5">
                  {isProcessing ? 'Processing Legal Matter' : 'Matter Workspace Ready'}
                </h3>
                <p className="text-xs text-slate-400 max-w-md mx-auto">{processingStatus}</p>
              </div>

              {/* Real-time file upload indicators */}
              {queuedFiles.length > 0 && (
                <div className="max-h-44 overflow-y-auto space-y-2 text-left bg-slate-950/60 p-3 rounded-xl border border-slate-800/60 text-xs">
                  {queuedFiles.map((qf) => (
                    <div key={qf.id} className="flex items-center justify-between py-1 border-b border-slate-900/60 last:border-0">
                      <span className="text-slate-300 truncate max-w-[280px]">{qf.name}</span>
                      <div className="flex items-center gap-2">
                        {qf.status === 'uploading' && (
                          <span className="text-amber-400 flex items-center gap-1">
                            <Loader2 className="h-3 w-3 animate-spin" /> Uploading ({qf.progress}%)
                          </span>
                        )}
                        {qf.status === 'success' && (
                          <span className="text-emerald-400 flex items-center gap-1">
                            <CheckCircle2 className="h-3.5 w-3.5" /> Stored
                          </span>
                        )}
                        {qf.status === 'error' && (
                          <span className="text-rose-400 flex items-center gap-1 font-medium" title={qf.error}>
                            <AlertCircle className="h-3.5 w-3.5" /> Failed
                          </span>
                        )}
                        {qf.status === 'queued' && (
                          <span className="text-slate-500">Queued</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Modal Footer / Navigation Buttons */}
        <div className="px-6 py-4 bg-slate-950/60 border-t border-slate-800 flex items-center justify-between">
          {step === 1 && (
            <>
              <button
                type="button"
                onClick={handleClose}
                className="px-4 py-2 rounded-xl text-sm font-medium text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                form="matter-details-form"
                className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-500/20 transition-all"
              >
                Continue to Upload
                <ArrowRight className="h-4 w-4" />
              </button>
            </>
          )}

          {step === 2 && (
            <>
              <button
                type="button"
                onClick={() => setStep(1)}
                className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-medium text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition-colors"
              >
                <ArrowLeft className="h-4 w-4" />
                Back to Details
              </button>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={executeCaseCreationAndUpload}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-500/20 transition-all"
                >
                  {queuedFiles.length > 0 ? (
                    <>
                      Create Matter & Analyze ({queuedFiles.length} files)
                      <ArrowRight className="h-4 w-4" />
                    </>
                  ) : (
                    <>
                      Create Matter Without Files
                      <ArrowRight className="h-4 w-4" />
                    </>
                  )}
                </button>
              </div>
            </>
          )}

          {step === 3 && (
            <div className="w-full flex justify-end">
              {createdCaseId && (
                <button
                  type="button"
                  onClick={() => {
                    resetForm();
                    onClose();
                    navigate(`/cases/${createdCaseId}/overview`);
                  }}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-500/20 transition-all"
                >
                  Go to Case Workspace
                  <ArrowRight className="h-4 w-4" />
                </button>
              )}
            </div>
          )}
        </div>
      </motion.div>
    </div>
  );
}
