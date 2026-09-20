import { useCallback, useState } from 'react';
import { motion } from 'framer-motion';
import { CloudUpload, File, CheckCircle2, AlertCircle, X } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import api from '@/lib/api';
import { formatFileSize, cn } from '@/lib/utils';

interface UploadedFile {
  file: File;
  id?: string;
  status: 'pending' | 'uploading' | 'done' | 'error';
  progress: number;
  error?: string;
}

export function Upload() {
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [dragActive, setDragActive] = useState(false);

  const handleFiles = useCallback((fileList: FileList | null) => {
    if (!fileList) return;
    const newFiles: UploadedFile[] = Array.from(fileList).map((file) => ({
      file,
      status: 'pending' as const,
      progress: 0,
    }));
    setFiles((prev) => [...prev, ...newFiles]);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    handleFiles(e.dataTransfer.files);
  }, [handleFiles]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setDragActive(false);
  }, []);

  const removeFile = useCallback((index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const uploadAll = useCallback(async () => {
    const pending = files.filter((f) => f.status === 'pending');
    for (let i = 0; i < pending.length; i++) {
      const fileEntry = pending[i];
      const fileIndex = files.indexOf(fileEntry);

      setFiles((prev) =>
        prev.map((f, idx) =>
          idx === fileIndex ? { ...f, status: 'uploading' as const, progress: 30 } : f
        )
      );

      try {
        const formData = new FormData();
        formData.append('file', fileEntry.file);

        const res = await api.post('/documents/upload', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });

        setFiles((prev) =>
          prev.map((f, idx) =>
            idx === fileIndex
              ? { ...f, status: 'done' as const, progress: 100, id: res.data.id }
              : f
          )
        );
      } catch (err: unknown) {
        const errorMessage = err instanceof Error ? err.message : 'Upload failed';
        setFiles((prev) =>
          prev.map((f, idx) =>
            idx === fileIndex
              ? { ...f, status: 'error' as const, progress: 0, error: errorMessage }
              : f
          )
        );
      }
    }
  }, [files]);

  const pendingCount = files.filter((f) => f.status === 'pending').length;

  return (
    <motion.div
      className="space-y-6 max-w-3xl mx-auto"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
    >
      <div>
        <h1 className="text-2xl font-bold text-slate-100">Upload Documents</h1>
        <p className="text-sm text-slate-500 mt-1">
          Upload legal documents for AI-powered e-discovery analysis.
        </p>
      </div>

      {/* ── Drop Zone ────────────────────────────────────────────────── */}
      <Card hover={false}>
        <CardContent>
          <label
            htmlFor="file-upload"
            className={cn(
              'flex flex-col items-center justify-center py-16 px-6',
              'border-2 border-dashed rounded-xl cursor-pointer',
              'transition-all duration-300',
              dragActive
                ? 'border-indigo-500 bg-indigo-500/5 shadow-lg shadow-indigo-500/10'
                : 'border-slate-700 hover:border-slate-500 hover:bg-slate-900/30'
            )}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
          >
            <div className={cn(
              'h-16 w-16 rounded-2xl flex items-center justify-center mb-4 transition-colors',
              dragActive
                ? 'bg-indigo-500/10'
                : 'bg-slate-800/50'
            )}>
              <CloudUpload className={cn(
                'h-8 w-8 transition-colors',
                dragActive ? 'text-indigo-400' : 'text-slate-500'
              )} />
            </div>
            <p className="text-sm font-medium text-slate-300 mb-1">
              {dragActive ? 'Drop files here' : 'Drag & drop files, or click to browse'}
            </p>
            <p className="text-xs text-slate-500">
              PDF, DOCX, TXT, EML — up to 100 MB per file
            </p>
            <input
              id="file-upload"
              type="file"
              className="hidden"
              multiple
              accept=".pdf,.docx,.txt,.eml"
              onChange={(e) => handleFiles(e.target.files)}
            />
          </label>
        </CardContent>
      </Card>

      {/* ── File List ────────────────────────────────────────────────── */}
      {files.length > 0 && (
        <Card>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm font-medium text-slate-300">
                {files.length} file{files.length !== 1 ? 's' : ''} selected
              </p>
              {pendingCount > 0 && (
                <Button onClick={uploadAll} size="sm">
                  Upload {pendingCount} file{pendingCount !== 1 ? 's' : ''}
                </Button>
              )}
            </div>

            {files.map((entry, index) => (
              <motion.div
                key={`${entry.file.name}-${index}`}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                className="flex items-center gap-3 p-3 rounded-lg bg-slate-900/50 border border-slate-800/30"
              >
                <File className="h-5 w-5 text-slate-500 shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-200 truncate">
                    {entry.file.name}
                  </p>
                  <p className="text-xs text-slate-500">
                    {formatFileSize(entry.file.size)}
                    {entry.error && (
                      <span className="text-red-400 ml-2">• {entry.error}</span>
                    )}
                  </p>
                  {entry.status === 'uploading' && (
                    <div className="mt-1.5 h-1 w-full bg-slate-800 rounded-full overflow-hidden">
                      <motion.div
                        className="h-full bg-gradient-to-r from-indigo-500 to-violet-500 rounded-full"
                        initial={{ width: 0 }}
                        animate={{ width: `${entry.progress}%` }}
                        transition={{ duration: 0.3 }}
                      />
                    </div>
                  )}
                </div>
                {entry.status === 'done' && (
                  <CheckCircle2 className="h-5 w-5 text-emerald-400 shrink-0" />
                )}
                {entry.status === 'error' && (
                  <AlertCircle className="h-5 w-5 text-red-400 shrink-0" />
                )}
                {entry.status === 'pending' && (
                  <button
                    onClick={() => removeFile(index)}
                    className="p-1 rounded hover:bg-slate-800 text-slate-500 hover:text-slate-300 transition-colors"
                  >
                    <X className="h-4 w-4" />
                  </button>
                )}
              </motion.div>
            ))}
          </CardContent>
        </Card>
      )}
    </motion.div>
  );
}
