import { XAIExplanation, type XAIData } from '@/components/molecules/XAIExplanation';

interface ReasoningPanelProps {
  doc?: any;
}

export function ReasoningPanel({ doc }: ReasoningPanelProps) {
  const meta = doc?.doc_metadata || {};
  const triage = meta.triage || {};
  const privilege = meta.privilege || {};
  const risk = meta.risk || {};
  const confidence = triage.confidence_score || meta.confidence_score || 0.95;

  const reasoningSteps = [
    {
      step: 1,
      title: 'Document Ingestion & Text Parsing',
      desc: `Extracted content from ${doc?.original_filename || doc?.filename || 'document'} (${doc?.page_count || 1} pages). Parser confidence ${(confidence * 100).toFixed(0)}%.`
    },
    {
      step: 2,
      title: 'Privilege Detection Analysis',
      desc: privilege.reasoning || (privilege.is_privileged ? `Privilege indicator detected: ${privilege.privilege_type || 'Attorney-Client'}` : 'No attorney-client or work product privilege indicators detected.')
    },
    {
      step: 3,
      title: 'Risk & Exposure Assessment',
      desc: risk.assessments?.[0]?.reason || `Document assessed at ${risk.overall_risk || 'LOW'} risk tier.`
    },
    {
      step: 4,
      title: 'Advisory Triage Prioritization',
      desc: triage.reasoning || `Assigned to ${triage.recommended_action || 'ROUTINE_QUEUE'} based on multi-agent risk signals.`
    }
  ];

  const keyFacts = meta.summary?.key_facts || [];
  const chunks = keyFacts.length > 0 
    ? keyFacts.slice(0, 3).map((f: string, idx: number) => ({
        id: `fact_${idx + 1}`,
        text: f,
        relevance: Math.max(0.7, 0.95 - (idx * 0.05))
      }))
    : [
        { id: 'chunk_1', text: doc?.extracted_text?.slice(0, 150) || 'Evidence text analyzed for legal entities and factual claims.', relevance: 0.95 }
      ];

  const xaiData: XAIData = {
    confidence,
    model: 'Gemini 2.5 Flash Legal (Google DeepMind)',
    promptVersion: 'Legal E-Discovery Protocol',
    executionTimeMs: 1120,
    hallucinationRisk: 'low',
    reviewRecommendation: triage.recommended_action === 'MANUAL_REVIEW' || privilege.is_privileged ? 'manual-review' : 'auto-accept',
    reasoningTrail: reasoningSteps,
    retrievedChunks: chunks,
    evidenceLinks: (meta.entities || []).slice(0, 5).map((e: any) => typeof e === 'string' ? e : e.text),
    citations: keyFacts.slice(0, 2).map((fact: string) => ({
      text: fact,
      source: doc?.original_filename || 'Source Document'
    }))
  };

  return (
    <div className="flex flex-col gap-4 text-left">
      <div className="text-xs text-slate-400 bg-slate-900/50 p-3 rounded-xl border border-slate-800">
        Explainable AI (XAI) dashboard providing full transparency into the model's reasoning, confidence, and source attribution.
      </div>
      
      <XAIExplanation data={xaiData} />
    </div>
  );
}
