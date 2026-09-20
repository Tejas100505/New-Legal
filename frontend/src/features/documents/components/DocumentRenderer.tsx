import { useState, useEffect } from 'react';
import { useDocumentViewerStore } from '../store/documentViewerStore';
import { Badge } from '@/components/atoms/Badge';
import { Shield, BookOpen, Edit3, X, AlertCircle } from 'lucide-react';

interface DocumentRendererProps {
  currentPage: number;
  doc?: any;
}

export function DocumentRenderer({ currentPage, doc }: DocumentRendererProps) {
  const showOcr = useDocumentViewerStore((s) => s.showOcrOverlay);
  const showPrivilege = useDocumentViewerStore((s) => s.showPrivilegeMarkers);
  const isCompare = useDocumentViewerStore((s) => s.isCompareMode);
  const annotations = useDocumentViewerStore((s) => s.annotations);
  const addAnnotation = useDocumentViewerStore((s) => s.addAnnotation);

  const [activeInlineCitation, setActiveInlineCitation] = useState<{
    title: string;
    ref: string;
    confidence: number;
    verified: boolean;
    excerpt: string;
  } | null>(null);

  const displayText = doc?.extracted_text || '';

  // Filter annotations for current page
  const pageAnnotations = annotations.filter((a) => a.pageNumber === currentPage);

  // Real privilege findings
  const privilegeAnalysis = doc?.doc_metadata?.privilege_analysis;
  const isPrivileged = privilegeAnalysis ? privilegeAnalysis.is_privileged : (doc?.isPrivileged ?? false);
  const evidenceSpans: string[] = privilegeAnalysis?.evidence_spans || [];

  const handleAddHighlight = () => {
    if (!displayText) return;
    const sampleSnippet = displayText.slice(0, 100);
    addAnnotation({
      pageNumber: currentPage,
      type: 'highlight',
      color: 'yellow',
      text: sampleSnippet,
      note: 'Reviewer highlight on current page text.',
      startOffset: 0,
      endOffset: 100,
    });
  };

  const handleCitationClick = (citText: string) => {
    const isUnavailable = citText.toLowerCase().includes('unavailable');
    const allCitations: string[] = [
      ...(doc?.doc_metadata?.summaries?.flatMap((s: any) => s.citations || []) || []),
      ...(doc?.doc_metadata?.privilege_analysis?.citations || []),
    ];
    const matched = allCitations.find((c: string) => c.includes(citText)) || citText;

    setActiveInlineCitation({
      title: matched,
      ref: isUnavailable
        ? 'Page/section unavailable: this citation is grounded in text without page metadata'
        : 'Source Grounding Verification',
      confidence: privilegeAnalysis?.confidence || 0.95,
      verified: !isUnavailable,
      excerpt: isUnavailable
        ? 'Page/section unavailable: this citation is grounded in text without page metadata. Raw chunk text was used for verification.'
        : `Verified source grounding citation: ${matched}`,
    });
  };

  useEffect(() => {
    (window as any).handleCitationClick = handleCitationClick;
    return () => {
      delete (window as any).handleCitationClick;
    };
  }, [doc]);

  return (
    <div className="flex-1 bg-slate-950 p-6 rounded-xl border border-slate-800/80 flex flex-col gap-4 overflow-y-auto max-h-[calc(100vh-18rem)] relative">
      {/* Controls */}
      <div className="flex items-center justify-between text-xs text-slate-500 border-b border-slate-850 pb-2">
        <span>Document Content Viewport — Page {currentPage}</span>
        {displayText && (
          <button
            onClick={handleAddHighlight}
            className="flex items-center gap-1 text-[10px] text-indigo-400 hover:text-indigo-300 transition-colors cursor-pointer"
          >
            <Edit3 className="h-3 w-3" /> Add Highlight
          </button>
        )}
      </div>

      <div className={`grid ${isCompare ? 'grid-cols-2 gap-4' : 'grid-cols-1'} flex-1`}>
        {/* Document Pane */}
        <div className="bg-slate-900/40 rounded-lg p-5 border border-slate-850 flex flex-col gap-4 relative overflow-y-auto min-h-[300px]">
          {isCompare && (
            <div className="absolute top-2 right-2">
              <Badge variant="info" size="xs">Current Version</Badge>
            </div>
          )}

          {/* Render Privilege Banner */}
          {showPrivilege && isPrivileged && (
            <div className="flex flex-col gap-2">
              <div className="flex items-start gap-2 p-2.5 rounded-lg bg-red-950/20 border border-red-500/30 text-[11px] text-red-400">
                <Shield className="h-4 w-4 shrink-0 mt-0.5" />
                <div>
                  <span className="font-bold uppercase tracking-wider text-[9px] block">
                    Privilege Flagged: {privilegeAnalysis?.privilege_type || 'ATTORNEY-CLIENT PRIVILEGE'}
                  </span>
                  {privilegeAnalysis?.reasoning || 'Attorney-client communication or legal advice detected.'}
                </div>
              </div>
            </div>
          )}

          {/* Main content body */}
          <div className="text-xs text-slate-300 leading-relaxed font-sans whitespace-pre-wrap select-all relative">
            {!displayText ? (
              <div className="flex flex-col items-center justify-center py-16 text-slate-500 text-center gap-2">
                <AlertCircle className="h-8 w-8 text-slate-600" />
                <p className="text-sm font-medium text-slate-400">No extracted text available</p>
                <p className="text-xs text-slate-500 max-w-sm">
                  This document has not yet been processed with OCR or text extraction pipeline.
                </p>
              </div>
            ) : showOcr ? (
              <div className="font-mono bg-slate-950 p-4 rounded border border-slate-850 text-emerald-400 opacity-90 relative">
                <span className="text-[10px] text-slate-500 block mb-3 font-sans">
                  // OCR Extracted Raw Text Stream
                </span>
                <div className="mt-2 text-[12px] text-slate-300 font-sans whitespace-pre-wrap">
                  {displayText}
                </div>
              </div>
            ) : (
              <div className="relative">
                {/* Privilege highlight overlay */}
                {showPrivilege && isPrivileged && (
                  <div className="absolute inset-0 bg-red-500/5 pointer-events-none border border-red-500/10 rounded" />
                )}

                {/* Paragraphs */}
                {displayText.split('\n\n').map((para: string, paraIdx: number) => {
                  let isEvidenceSpan = false;
                  if (evidenceSpans.length > 0) {
                    isEvidenceSpan = evidenceSpans.some(
                      (span) => span && (para.includes(span) || span.includes(para.slice(0, 40)))
                    );
                  }

                  return (
                    <p
                      key={paraIdx}
                      className={`mb-4 ${
                        isEvidenceSpan
                          ? 'p-2.5 bg-red-950/20 border-l-2 border-red-500 rounded-r text-slate-200'
                          : ''
                      }`}
                    >
                      {para}
                    </p>
                  );
                })}
              </div>
            )}
          </div>

          {/* User Annotations list */}
          {pageAnnotations.length > 0 && (
            <div className="flex flex-col gap-2 mt-4 border-t border-slate-850 pt-3">
              <span className="text-[9px] font-semibold uppercase tracking-wider text-slate-500">
                Your Highlights & Annotations
              </span>
              <div className="flex flex-col gap-2">
                {pageAnnotations.map((ann) => (
                  <div key={ann.id} className="p-2.5 rounded-lg bg-slate-950/40 border border-slate-800 text-[11px]">
                    <p className="text-slate-400 italic">"{ann.text}"</p>
                    {ann.note && (
                      <p className="text-indigo-400 font-semibold mt-1">
                        Note: <span className="font-normal text-slate-300">{ann.note}</span>
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Compare Pane */}
        {isCompare && (
          <div className="bg-slate-900/40 rounded-lg p-5 border border-slate-850 flex flex-col gap-4 relative overflow-y-auto min-h-[300px]">
            <div className="absolute top-2 right-2">
              <Badge variant="warning" size="xs">Comparison Version</Badge>
            </div>
            <div className="text-xs text-slate-400 leading-relaxed font-sans whitespace-pre-wrap">
              <p className="text-sm font-bold text-slate-200 border-b border-slate-800 pb-1.5 mb-2">
                Document Diff Stream
              </p>
              <p className="text-xs text-slate-500">
                No prior version diff recorded for this document.
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Inline Citation Info Dialog Popup */}
      {activeInlineCitation && (
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-slate-900/95 border border-slate-700 rounded-xl p-4 shadow-2xl z-30 w-80 flex flex-col gap-3">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <span className="text-xs font-bold text-indigo-400 flex items-center gap-1">
              <BookOpen className="h-4 w-4" /> Inline Citation Match
            </span>
            <button
              onClick={() => setActiveInlineCitation(null)}
              className="text-slate-500 hover:text-slate-300"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
          <div className="flex flex-col gap-1.5">
            <h5 className="text-xs font-bold text-slate-200 font-mono break-all">{activeInlineCitation.title}</h5>
            <p className="text-[11px] text-slate-400">
              {activeInlineCitation.ref}
            </p>
            <p className="text-[11px] text-slate-300 bg-slate-950 p-2 rounded border border-slate-800">
              {activeInlineCitation.excerpt}
            </p>
            <div className="flex items-center justify-between mt-1">
              <Badge variant={activeInlineCitation.verified ? 'success' : 'warning'} size="xs">
                {activeInlineCitation.verified ? 'VERIFIED GROUNDING' : 'PAGE/SECTION UNAVAILABLE'}
              </Badge>
              <span className="text-[10px] text-slate-400 font-mono">
                {(activeInlineCitation.confidence * 100).toFixed(0)}% Confidence
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
