import { useState, useEffect, useCallback } from 'react';
import {
  FileBarChart,
  Plus,
  Download,
  FileText,
  ShieldAlert,
  FileCheck,
  AlertTriangle,
  Eye,
  Loader2,
  Layers,
  X,
} from 'lucide-react';
import { formatDate, formatFileSize } from '@/lib/utils';
import { PageShell } from '@/components/templates/PageShell';
import { Badge } from '@/components/atoms/Badge';
import api from '@/lib/api';

const templates = [
  {
    type: 'executive_summary',
    title: 'Executive Summary',
    desc: 'High-level synthesis of case posture, key entities, timeline milestones, and major evidence findings.',
    badge: 'Case-Wide',
    icon: FileText,
  },
  {
    type: 'review_summary',
    title: 'Review Summary',
    desc: 'Corpus review progress, reviewed/flagged document classification breakdown, and unresolved items.',
    badge: 'Review Audit',
    icon: FileCheck,
  },
  {
    type: 'privilege_log',
    title: 'Privilege Log',
    desc: 'Formal legal privilege log listing privileged documents, custodians, privilege types, and legal basis.',
    badge: 'Privilege Compliance',
    icon: ShieldAlert,
  },
  {
    type: 'risk_assessment',
    title: 'Risk Assessment',
    desc: 'Comprehensive risk matrix detailing legal liabilities, severity tiers, and affected evidence sources.',
    badge: 'Liability Exposure',
    icon: AlertTriangle,
  },
];

interface ReportsPageProps {
  caseId?: string;
  caseName?: string;
}

export function ReportsPage({ caseId, caseName }: ReportsPageProps = {}) {
  const [reports, setReports] = useState<any[]>([]);
  const [auditLogs, setAuditLogs] = useState<any[]>([]);
  const [generatingType, setGeneratingType] = useState<string | null>(null);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const [activePreview, setActivePreview] = useState<any | null>(null);
  const [selectedFormat, setSelectedFormat] = useState<string>('pdf');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Load report history and audit logs
  const loadHistory = useCallback(async () => {
    try {
      const historyUrl = caseId
        ? `/reports/history?case_id=${encodeURIComponent(caseId)}`
        : '/reports/history';
      const histRes = await api.get(historyUrl);
      if (histRes.data?.reports) {
        setReports(histRes.data.reports);
      }
    } catch (err) {
      console.warn('Could not load report history:', err);
    }

    try {
      const logsRes = await api.get('/reports/audit-logs');
      setAuditLogs(logsRes.data.audit_logs || []);
    } catch (err) {
      console.warn('Could not load audit logs:', err);
    }
  }, [caseId]);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  // Generate Report (JSON for Preview + Record in DB Audit History)
  const handleGenerate = async (type: string) => {
    setGeneratingType(type);
    setErrorMessage(null);
    try {
      const exportUrl = caseId
        ? `/reports/export?format=json&report_type=${encodeURIComponent(type)}&case_id=${encodeURIComponent(caseId)}`
        : `/reports/export?format=json&report_type=${encodeURIComponent(type)}`;

      const response = await api.post(exportUrl);
      const data = response.data || {};
      const payloadStr = JSON.stringify(data);
      const byteSize = new Blob([payloadStr]).size;
      const totalDocs = data?.corpus_stats?.total_documents ?? data?.key_metrics?.documents_analyzed ?? 0;

      const generatedReport = {
        id: `rpt_${Date.now()}`,
        name: data.title || `${type.replace('_', ' ').toUpperCase()} Report`,
        type: type,
        format: 'json',
        status: 'completed',
        caseId: data?.case_id || caseId || 'unassigned',
        caseName: data?.case_name || caseName || (caseId ? `Case ${String(caseId).slice(0, 8)}` : 'Platform-wide Review'),
        generatedAt: data?.generated_at || new Date().toISOString(),
        size: byteSize,
        pageCount: Math.max(1, Math.ceil(totalDocs / 15)),
        rawData: data,
        metrics: data?.corpus_stats || data?.key_metrics || {},
      };

      setReports((prev) => [generatedReport, ...prev]);
      setActivePreview(generatedReport);
      // Refresh audit logs
      loadHistory();
    } catch (err: any) {
      console.error('Report generation failed:', err);
      const detail = err.response?.data?.detail || err.message || 'Report generation failed.';
      setErrorMessage(`Generation Error: ${detail}`);
    } finally {
      setGeneratingType(null);
    }
  };

  // Direct Backend Export Download
  const handleDownload = async (reportType: string, format: string, reportName?: string) => {
    const downloadKey = `${reportType}_${format}`;
    setDownloadingId(downloadKey);
    setErrorMessage(null);

    try {
      const exportUrl = caseId
        ? `/reports/export?format=${format}&report_type=${encodeURIComponent(reportType)}&case_id=${encodeURIComponent(caseId)}`
        : `/reports/export?format=${format}&report_type=${encodeURIComponent(reportType)}`;

      const res = await api.post(exportUrl, {}, { responseType: 'blob' });

      const mimeTypes: Record<string, string> = {
        pdf: 'application/pdf',
        docx: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        csv: 'text/csv',
        markdown: 'text/markdown',
        json: 'application/json',
      };
      const extMap: Record<string, string> = {
        pdf: 'pdf',
        docx: 'docx',
        csv: 'csv',
        markdown: 'md',
        json: 'json',
      };

      let downloadFileName = '';
      const disposition = res.headers?.['content-disposition'] || (res.headers as any)?.get?.('content-disposition');
      if (disposition && typeof disposition === 'string') {
        const match = disposition.match(/filename=["']?([^"';]+)["']?/i);
        if (match && match[1]) {
          downloadFileName = match[1].trim();
        }
      }

      if (!downloadFileName) {
        const prefix = caseName ? `${caseName.replace(/[^a-z0-9_-]/gi, '_').toLowerCase()}_` : '';
        const baseName = (reportName || `${reportType}`).replace(/[^a-z0-9_-]/gi, '_').toLowerCase();
        downloadFileName = `${prefix}${baseName}.${extMap[format] || format}`;
      }

      const rawContentType = res.headers?.['content-type'];
      const contentType = typeof rawContentType === 'string' ? rawContentType : (mimeTypes[format] || 'application/octet-stream');
      const blob = res.data instanceof Blob ? res.data : new Blob([res.data], { type: contentType });
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = downloadFileName;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      setTimeout(() => {
        window.URL.revokeObjectURL(downloadUrl);
      }, 15000);

      // Refresh audit logs after successful export
      loadHistory();
    } catch (err: any) {
      console.error('Download export failed:', err);
      let detail = 'Export download failed. Please verify server status.';
      if (err.response?.data instanceof Blob) {
        try {
          const text = await err.response.data.text();
          const parsed = JSON.parse(text);
          if (parsed.detail) {
            detail = parsed.detail;
          }
        } catch {
          if (err.response?.status === 401 || err.response?.status === 403) {
            detail = 'Unauthorized to export this case report.';
          } else if (err.response?.status === 404) {
            detail = 'Report data not found.';
          }
        }
      } else if (err.response?.data?.detail) {
        detail = err.response.data.detail;
      } else if (err.message) {
        detail = `Export failed: ${err.message}`;
      }
      setErrorMessage(detail);
    } finally {
      setDownloadingId(null);
    }
  };

  // Open Preview for historical or existing report
  const handleOpenPreview = async (report: any) => {
    if (report.rawData) {
      setActivePreview(report);
      return;
    }
    // Fetch full json for preview if not in local cache
    try {
      const exportUrl = `/reports/export?format=json&report_type=${encodeURIComponent(report.type || 'review_summary')}&case_id=${encodeURIComponent(report.caseId || caseId || '')}`;
      const res = await api.post(exportUrl);
      const enriched = {
        ...report,
        rawData: res.data,
      };
      setActivePreview(enriched);
    } catch (err) {
      console.error('Failed to load report preview:', err);
      setActivePreview(report);
    }
  };

  return (
    <PageShell
      title="Reports & Privilege Exports"
      description="Generate and export formal legal reports, structured privilege logs, risk matrices, and case executive summaries backed by live case records."
    >
      {/* Error Alert */}
      {errorMessage && (
        <div className="mb-6 p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            <span>{errorMessage}</span>
          </div>
          <button onClick={() => setErrorMessage(null)} className="text-rose-400 hover:text-rose-200">
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* Global Export Format Selector */}
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3 bg-slate-900/40 border border-slate-800/60 p-3.5 rounded-xl">
        <div className="flex items-center gap-2">
          <Layers className="h-4 w-4 text-indigo-400" />
          <span className="text-xs font-semibold text-slate-300">Default Export Format:</span>
        </div>
        <div className="flex items-center gap-1.5 bg-slate-950 p-1 rounded-lg border border-slate-800">
          {(['pdf', 'docx', 'csv', 'markdown', 'json'] as const).map((fmt) => (
            <button
              key={fmt}
              onClick={() => setSelectedFormat(fmt)}
              className={`px-2.5 py-1 rounded text-xs font-medium uppercase transition-all ${
                selectedFormat === fmt
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
            >
              {fmt}
            </button>
          ))}
        </div>
      </div>

      {/* Report Templates */}
      <div className="mb-8">
        <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">Available Legal Templates</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {templates.map((tpl) => {
            const Icon = tpl.icon;
            const isGenerating = generatingType === tpl.type;
            const isDownloading = downloadingId === `${tpl.type}_${selectedFormat}`;

            return (
              <div
                key={tpl.type}
                className="rounded-xl p-5 bg-slate-900/50 border border-slate-800/50 hover:border-indigo-500/30 transition-all flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400">
                      <Icon className="h-5 w-5" />
                    </div>
                    <Badge variant="purple" size="xs">
                      {tpl.badge}
                    </Badge>
                  </div>
                  <h4 className="text-sm font-semibold text-slate-200 mb-1.5">{tpl.title}</h4>
                  <p className="text-xs text-slate-400 leading-relaxed mb-4">{tpl.desc}</p>
                </div>

                <div className="flex flex-col gap-2 pt-2 border-t border-slate-800/40">
                  <button
                    id={`generate-${tpl.type}`}
                    onClick={() => handleGenerate(tpl.type)}
                    disabled={isGenerating || isDownloading}
                    className="w-full flex items-center justify-center gap-1.5 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-sm transition-all disabled:opacity-50 cursor-pointer"
                  >
                    {isGenerating ? (
                      <>
                        <Loader2 className="h-3.5 w-3.5 animate-spin" /> Generating...
                      </>
                    ) : (
                      <>
                        <Plus className="h-3.5 w-3.5" /> Generate & Preview
                      </>
                    )}
                  </button>
                  <button
                    id={`download-${tpl.type}`}
                    onClick={() => handleDownload(tpl.type, selectedFormat, tpl.title)}
                    disabled={isGenerating || isDownloading}
                    className="w-full flex items-center justify-center gap-1.5 py-1.5 rounded-lg bg-slate-800/60 hover:bg-slate-800 text-slate-300 text-xs font-medium transition-all disabled:opacity-50 cursor-pointer"
                  >
                    {isDownloading ? (
                      <>
                        <Loader2 className="h-3.5 w-3.5 animate-spin" /> Exporting...
                      </>
                    ) : (
                      <>
                        <Download className="h-3.5 w-3.5 text-indigo-400" /> Download {selectedFormat.toUpperCase()}
                      </>
                    )}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Generated Reports & Case History */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
            Case Reports & Generated Exports
          </h3>
          <span className="text-xs text-slate-500">{reports.length} total generated</span>
        </div>

        <div className="rounded-xl border border-slate-800/50 overflow-hidden bg-slate-900/40">
          <div className="grid grid-cols-[1fr_160px_130px_100px_180px] gap-4 px-4 py-3 bg-slate-900/80 border-b border-slate-800/50 text-xs font-semibold text-slate-500 uppercase tracking-wider">
            <span>Report Title</span>
            <span>Matter / Case</span>
            <span>Generated</span>
            <span>Status</span>
            <span className="text-right">Export Actions</span>
          </div>

          <div className="divide-y divide-slate-800/30">
            {reports.length === 0 ? (
              <div className="p-8 text-center text-xs text-slate-500">
                No reports generated for this matter yet. Select a template above to generate a report.
              </div>
            ) : (
              reports.map((report) => (
                <div
                  key={report.id}
                  className="grid grid-cols-[1fr_160px_130px_100px_180px] gap-4 px-4 py-3.5 items-center hover:bg-slate-800/10 transition-colors"
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <FileBarChart className="h-4.5 w-4.5 text-indigo-400 shrink-0" />
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-slate-200 truncate">{report.name}</p>
                      <p className="text-[11px] text-slate-500">
                        {report.type ? report.type.replace('_', ' ').toUpperCase() : 'CASE REPORT'}
                        {report.size ? ` • ${formatFileSize(report.size)}` : ''}
                      </p>
                    </div>
                  </div>

                  <span className="text-xs text-slate-400 truncate">
                    {report.caseName || 'Platform-wide'}
                  </span>

                  <span className="text-xs text-slate-500">
                    {formatDate(report.generatedAt)}
                  </span>

                  <div>
                    <Badge variant="success" size="xs" dot>
                      COMPLETED
                    </Badge>
                  </div>

                  <div className="flex items-center justify-end gap-1.5">
                    <button
                      onClick={() => handleOpenPreview(report)}
                      className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs flex items-center gap-1 transition-colors cursor-pointer"
                      title="Preview Report"
                    >
                      <Eye className="h-3.5 w-3.5 text-indigo-400" />
                      <span>Preview</span>
                    </button>
                    <button
                      onClick={() => handleDownload(report.type || 'review_summary', 'pdf', report.name)}
                      className="p-1.5 rounded bg-slate-800 hover:bg-indigo-600 hover:text-white text-slate-300 transition-colors cursor-pointer"
                      title="Download PDF"
                    >
                      <Download className="h-3.5 w-3.5" />
                    </button>
                    <button
                      onClick={() => handleDownload(report.type || 'review_summary', 'docx', report.name)}
                      className="px-1.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-[10px] font-bold text-slate-300 transition-colors cursor-pointer"
                      title="Download DOCX"
                    >
                      DOCX
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Interactive Report Preview Modal / Drawer */}
      {activePreview && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in">
          <div className="w-full max-w-4xl max-h-[85vh] flex flex-col rounded-2xl bg-slate-900 border border-slate-800 shadow-2xl overflow-hidden">
            {/* Modal Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-900/90">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-xl bg-indigo-500/10 text-indigo-400">
                  <FileText className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-slate-100">{activePreview.name}</h3>
                  <p className="text-xs text-slate-400">
                    Matter: <span className="text-slate-200 font-medium">{activePreview.caseName}</span> • Generated:{' '}
                    {formatDate(activePreview.generatedAt)}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <div className="flex items-center gap-1 bg-slate-800/80 p-1 rounded-lg">
                  {(['pdf', 'docx', 'csv', 'markdown', 'json'] as const).map((fmt) => (
                    <button
                      key={fmt}
                      onClick={() => handleDownload(activePreview.type || 'review_summary', fmt, activePreview.name)}
                      className="px-2 py-1 rounded text-[11px] font-semibold uppercase text-slate-300 hover:bg-indigo-600 hover:text-white transition-all cursor-pointer"
                    >
                      {fmt}
                    </button>
                  ))}
                </div>
                <button
                  id="close-preview-modal"
                  aria-label="Close Preview"
                  onClick={() => setActivePreview(null)}
                  className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors cursor-pointer"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
            </div>

            {/* Modal Body */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6 custom-scrollbar">
              {/* Metrics Header */}
              {activePreview.rawData?.corpus_stats && (
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800/70">
                    <p className="text-[11px] font-medium text-slate-400 uppercase">Documents</p>
                    <p className="text-lg font-bold text-slate-100 mt-0.5">
                      {activePreview.rawData.corpus_stats.total_documents}
                    </p>
                  </div>
                  <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800/70">
                    <p className="text-[11px] font-medium text-slate-400 uppercase">Reviewed</p>
                    <p className="text-lg font-bold text-emerald-400 mt-0.5">
                      {activePreview.rawData.corpus_stats.reviewed_documents}
                    </p>
                  </div>
                  <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800/70">
                    <p className="text-[11px] font-medium text-slate-400 uppercase">Privileged</p>
                    <p className="text-lg font-bold text-amber-400 mt-0.5">
                      {activePreview.rawData.corpus_stats.privileged_documents}
                    </p>
                  </div>
                  <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800/70">
                    <p className="text-[11px] font-medium text-slate-400 uppercase">High Risk</p>
                    <p className="text-lg font-bold text-rose-400 mt-0.5">
                      {activePreview.rawData.corpus_stats.high_risk_documents ?? 0}
                    </p>
                  </div>
                </div>
              )}

              {/* Privilege Log Table Preview */}
              {activePreview.type === 'privilege_log' && (
                <div>
                  <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2.5">
                    Privilege Log Entries ({activePreview.rawData?.privilege_log?.length || 0})
                  </h4>
                  {activePreview.rawData?.privilege_log?.length > 0 ? (
                    <div className="rounded-xl border border-slate-800 overflow-hidden bg-slate-950/40">
                      <table className="w-full text-left text-xs">
                        <thead className="bg-slate-900/80 text-slate-400 border-b border-slate-800 font-semibold">
                          <tr>
                            <th className="px-3.5 py-2.5">Document</th>
                            <th className="px-3.5 py-2.5">Date</th>
                            <th className="px-3.5 py-2.5">Custodian</th>
                            <th className="px-3.5 py-2.5">Privilege Type</th>
                            <th className="px-3.5 py-2.5">Legal Basis</th>
                            <th className="px-3.5 py-2.5">Withholding</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/40 text-slate-300">
                          {activePreview.rawData.privilege_log.map((row: any, idx: number) => (
                            <tr key={idx} className="hover:bg-slate-800/20">
                              <td className="px-3.5 py-2.5 font-medium text-slate-200">{row.document}</td>
                              <td className="px-3.5 py-2.5 text-slate-400 whitespace-nowrap">{row.date}</td>
                              <td className="px-3.5 py-2.5 text-slate-400">{row.author_custodian}</td>
                              <td className="px-3.5 py-2.5">
                                <Badge variant="warning" size="xs">
                                  {row.privilege_type}
                                </Badge>
                              </td>
                              <td className="px-3.5 py-2.5 text-slate-400 max-w-xs truncate" title={row.legal_basis}>
                                {row.legal_basis}
                              </td>
                              <td className="px-3.5 py-2.5 text-rose-400 font-semibold">{row.withholding_status}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <div className="p-6 rounded-xl bg-slate-950/40 border border-slate-800 text-center text-xs text-slate-500">
                      No privileged documents identified in this matter.
                    </div>
                  )}
                </div>
              )}

              {/* Risk Assessment Preview */}
              {activePreview.type === 'risk_assessment' && (
                <div>
                  <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2.5">
                    Identified Risk Items ({activePreview.rawData?.risks?.length || 0})
                  </h4>
                  {activePreview.rawData?.risks?.length > 0 ? (
                    <div className="rounded-xl border border-slate-800 overflow-hidden bg-slate-950/40">
                      <table className="w-full text-left text-xs">
                        <thead className="bg-slate-900/80 text-slate-400 border-b border-slate-800 font-semibold">
                          <tr>
                            <th className="px-3.5 py-2.5">Severity</th>
                            <th className="px-3.5 py-2.5">Category</th>
                            <th className="px-3.5 py-2.5">Reason / Explanation</th>
                            <th className="px-3.5 py-2.5">Source Document</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/40 text-slate-300">
                          {activePreview.rawData.risks.map((r: any, idx: number) => {
                            const sev = (r.severity || r.risk_level || 'MEDIUM').toUpperCase();
                            return (
                              <tr key={idx} className="hover:bg-slate-800/20">
                                <td className="px-3.5 py-2.5">
                                  <Badge variant={sev === 'CRITICAL' || sev === 'HIGH' ? 'danger' : 'warning'} size="xs">
                                    {sev}
                                  </Badge>
                                </td>
                                <td className="px-3.5 py-2.5 font-medium text-slate-200">{r.category}</td>
                                <td className="px-3.5 py-2.5 text-slate-400">{r.explanation || r.reason}</td>
                                <td className="px-3.5 py-2.5 text-slate-500 whitespace-nowrap">{r.source_document}</td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <div className="p-6 rounded-xl bg-slate-950/40 border border-slate-800 text-center text-xs text-slate-500">
                      No elevated risks identified in this matter.
                    </div>
                  )}
                </div>
              )}

              {/* Executive Summary Preview */}
              {(activePreview.type === 'executive_summary' || activePreview.type === 'review_summary') && (
                <div className="space-y-4">
                  {activePreview.rawData?.executive_summary && (
                    <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800">
                      <h4 className="text-xs font-semibold text-indigo-400 uppercase tracking-wider mb-2">
                        Executive Summary Narrative
                      </h4>
                      <p className="text-xs text-slate-300 leading-relaxed whitespace-pre-wrap">
                        {activePreview.rawData.executive_summary}
                      </p>
                    </div>
                  )}

                  {activePreview.rawData?.executive_sections?.legal && (
                    <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800">
                      <h4 className="text-xs font-semibold text-indigo-400 uppercase tracking-wider mb-2">
                        Legal Posture & Strategy
                      </h4>
                      <p className="text-xs text-slate-300 leading-relaxed whitespace-pre-wrap">
                        {activePreview.rawData.executive_sections.legal}
                      </p>
                    </div>
                  )}

                  {activePreview.rawData?.top_entities?.length > 0 && (
                    <div>
                      <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                        Key Case Entities
                      </h4>
                      <div className="flex flex-wrap gap-2">
                        {activePreview.rawData.top_entities.map((e: any, idx: number) => (
                          <div
                            key={idx}
                            className="px-2.5 py-1.5 rounded-lg bg-slate-800/80 border border-slate-700/60 text-xs text-slate-200 flex items-center gap-1.5"
                          >
                            <span className="font-semibold text-indigo-300">{e.name}</span>
                            <span className="text-[10px] text-slate-400">({e.type})</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {activePreview.rawData?.timeline?.length > 0 && (
                    <div>
                      <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                        Key Timeline Milestones
                      </h4>
                      <div className="rounded-xl border border-slate-800 overflow-hidden bg-slate-950/40 divide-y divide-slate-800/40">
                        {activePreview.rawData.timeline.slice(0, 8).map((ev: any, idx: number) => (
                          <div key={idx} className="p-3 text-xs flex items-start gap-3">
                            <span className="font-mono text-indigo-400 font-semibold shrink-0">{ev.date}</span>
                            <span className="text-slate-300 flex-1">{ev.description}</span>
                            <span className="text-slate-500 text-[11px] shrink-0">{ev.source_document}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Audit Logs Table */}
      <div className="mt-8">
        <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">System Compliance Audit Trail</h3>
        <div className="rounded-xl border border-slate-800/50 overflow-hidden bg-slate-900/40">
          <div className="grid grid-cols-[150px_160px_1fr_120px_100px] gap-4 px-4 py-3 bg-slate-900/80 border-b border-slate-800/50 text-xs font-semibold text-slate-500 uppercase tracking-wider">
            <span>Timestamp</span>
            <span>Action</span>
            <span>User</span>
            <span>Resource</span>
            <span>Status</span>
          </div>
          <div className="divide-y divide-slate-800/30 max-h-[260px] overflow-y-auto custom-scrollbar">
            {auditLogs.length === 0 ? (
              <div className="p-4 text-center text-xs text-slate-500">No system audit logs recorded yet.</div>
            ) : (
              auditLogs.map((log) => (
                <div
                  key={log.id}
                  className="grid grid-cols-[150px_160px_1fr_120px_100px] gap-4 px-4 py-3 items-center text-xs text-slate-400 hover:bg-slate-800/10 transition-colors"
                >
                  <span className="font-mono text-[11px]">{formatDate(log.timestamp)}</span>
                  <span className="font-semibold text-slate-200">{log.action}</span>
                  <span className="text-slate-300 truncate">{log.user_email || 'system@legal.com'}</span>
                  <span className="truncate">{log.resource_type}</span>
                  <div>
                    <Badge variant="success" size="xs">
                      SUCCESS
                    </Badge>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </PageShell>
  );
}
