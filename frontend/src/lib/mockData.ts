/**
 * Production-quality mock data for all dashboard widgets and feature pages.
 * Every item uses realistic legal industry data — no placeholders or lorem ipsum.
 */

import type {
  User, LegalCase, LegalDocument, AIInsight, RiskDistribution,
  EvidenceSummary, TimelineEvent, Notification, ActivityItem,
  Report, SearchResult, MetricCardData, DocumentEntity,
  DocumentVersion, GraphNode, GraphEdge, ChartData,
  DocumentAnnotation, OCROverlay, PrivilegeMarker, InlineCitation,
  ReasoningStep, DocumentSummary, DocumentRiskAssessment, VersionDiff
} from '@/types';

// ── Current User ─────────────────────────────────────────────────────────────

export const MOCK_USER: User = {
  id: 'usr_001',
  email: 'sarah.chen@westlake-partners.com',
  name: 'Sarah Chen',
  role: 'lawyer',
  firm: 'Westlake & Partners LLP',
  barNumber: 'CA-298451',
  createdAt: '2024-01-15T08:00:00Z',
  lastLoginAt: '2026-07-17T07:30:00Z',
};

// ── Dashboard Metric Cards ───────────────────────────────────────────────────

export const MOCK_METRICS: MetricCardData[] = [
  { id: 'm1', label: 'Active Cases', value: 24, change: 3, changeLabel: '+3 this week', trend: 'up', icon: 'FolderOpen', color: 'indigo' },
  { id: 'm2', label: 'Recent Cases', value: 8, change: 2, changeLabel: 'Added today', trend: 'up', icon: 'Clock', color: 'violet' },
  { id: 'm3', label: 'Documents Processed', value: '12,847', change: 342, changeLabel: '+342 today', trend: 'up', icon: 'FileText', color: 'cyan' },
  { id: 'm4', label: 'OCR Accuracy', value: '98.7%', change: 0.2, changeLabel: '↑ 0.2%', trend: 'up', icon: 'Eye', color: 'emerald' },
  { id: 'm5', label: 'AI Confidence', value: '94.2%', change: 1.1, changeLabel: '↑ 1.1%', trend: 'up', icon: 'Brain', color: 'blue' },
  { id: 'm6', label: 'Evidence Count', value: '3,241', change: 89, changeLabel: '+89 new', trend: 'up', icon: 'Search', color: 'orange' },
  { id: 'm7', label: 'High Risk Cases', value: 6, change: -2, changeLabel: '-2 resolved', trend: 'down', icon: 'AlertTriangle', color: 'rose' },
  { id: 'm8', label: 'Processing Queue', value: 14, change: 0, changeLabel: 'In progress', trend: 'neutral', icon: 'Layers', color: 'amber' },
  { id: 'm9', label: 'Review Progress', value: '78%', change: 5, changeLabel: '↑ 5% this week', trend: 'up', icon: 'CheckCircle', color: 'teal' },
];

// ── Cases ────────────────────────────────────────────────────────────────────

export const MOCK_CASES: LegalCase[] = [
  {
    id: 'case_001', name: 'Meridian Corp. v. Atlas Industries', caseNumber: '2026-CV-4821',
    description: 'Patent infringement dispute regarding proprietary manufacturing processes for semiconductor components.',
    status: 'active', priority: 'critical', riskLevel: 'high', client: 'Meridian Corporation',
    assignedTo: 'Sarah Chen', documentCount: 2847, evidenceCount: 423,
    createdAt: '2026-02-14T09:00:00Z', updatedAt: '2026-07-17T06:30:00Z', dueDate: '2026-09-15T17:00:00Z',
    tags: ['patent', 'semiconductor', 'trade-secret'],
  },
  {
    id: 'case_002', name: 'Thornton Estate — Probate Review', caseNumber: '2026-PR-1192',
    description: 'Multi-party estate dispute involving contested will provisions and trust amendments spanning three decades of documentation.',
    status: 'active', priority: 'high', riskLevel: 'medium', client: 'Thornton Family Trust',
    assignedTo: 'Sarah Chen', documentCount: 1523, evidenceCount: 287,
    createdAt: '2026-03-08T10:00:00Z', updatedAt: '2026-07-16T14:20:00Z', dueDate: '2026-10-01T17:00:00Z',
    tags: ['probate', 'estate', 'trust'],
  },
  {
    id: 'case_003', name: 'SEC Investigation — Greenfield Partners', caseNumber: '2026-SEC-0547',
    description: 'Regulatory investigation into potential insider trading activities and disclosure violations at Greenfield Partners hedge fund.',
    status: 'review', priority: 'critical', riskLevel: 'critical', client: 'Greenfield Partners LLC',
    assignedTo: 'Sarah Chen', documentCount: 4281, evidenceCount: 892,
    createdAt: '2026-01-20T08:00:00Z', updatedAt: '2026-07-17T07:00:00Z', dueDate: '2026-08-30T17:00:00Z',
    tags: ['sec', 'insider-trading', 'compliance'],
  },
  {
    id: 'case_004', name: 'DataFlow Inc. Employment Class Action', caseNumber: '2026-CA-3341',
    description: 'Class action lawsuit alleging systematic wage theft and misclassification of employees as independent contractors.',
    status: 'active', priority: 'high', riskLevel: 'high', client: 'DataFlow Inc.',
    assignedTo: 'Sarah Chen', documentCount: 1847, evidenceCount: 341,
    createdAt: '2026-04-12T09:00:00Z', updatedAt: '2026-07-15T16:45:00Z', dueDate: '2026-11-20T17:00:00Z',
    tags: ['employment', 'class-action', 'wage-theft'],
  },
  {
    id: 'case_005', name: 'NovaTech Merger Due Diligence', caseNumber: '2026-MA-0089',
    description: 'Comprehensive due diligence review for $2.3B acquisition of NovaTech Solutions including IP, contracts, and regulatory compliance.',
    status: 'active', priority: 'medium', riskLevel: 'medium', client: 'Apex Ventures',
    assignedTo: 'Sarah Chen', documentCount: 3192, evidenceCount: 156,
    createdAt: '2026-05-03T10:00:00Z', updatedAt: '2026-07-16T11:30:00Z', dueDate: '2026-08-15T17:00:00Z',
    tags: ['m&a', 'due-diligence', 'ip'],
  },
  {
    id: 'case_006', name: 'Heritage Bank — AML Compliance', caseNumber: '2026-AML-2244',
    description: 'Anti-money laundering compliance review and remediation for Heritage Bank following FinCEN advisory notices.',
    status: 'pending', priority: 'medium', riskLevel: 'low', client: 'Heritage National Bank',
    assignedTo: 'Sarah Chen', documentCount: 892, evidenceCount: 67,
    createdAt: '2026-06-15T08:00:00Z', updatedAt: '2026-07-14T09:00:00Z', dueDate: '2026-12-31T17:00:00Z',
    tags: ['aml', 'compliance', 'banking'],
  },
];

// ── Documents ────────────────────────────────────────────────────────────────

export const MOCK_DOCUMENTS: LegalDocument[] = [
  {
    id: 'doc_001', name: 'Meridian-Atlas_Patent_Filing_2024.pdf', type: 'pdf', size: 4521984,
    status: 'analyzed', caseId: 'case_001', caseName: 'Meridian Corp. v. Atlas Industries',
    ocrAccuracy: 99.2, ocrConfidence: 'high', pageCount: 47, entityCount: 234,
    uploadedBy: 'Sarah Chen', uploadedAt: '2026-07-15T09:30:00Z', processedAt: '2026-07-15T09:45:00Z',
    tags: ['patent', 'filing', 'key-document'], version: 3, isPrivileged: false, riskLevel: 'medium',
  },
  {
    id: 'doc_002', name: 'Board_Meeting_Minutes_Q1_2026.docx', type: 'docx', size: 892416,
    status: 'analyzed', caseId: 'case_003', caseName: 'SEC Investigation — Greenfield Partners',
    ocrAccuracy: 97.8, ocrConfidence: 'high', pageCount: 12, entityCount: 89,
    uploadedBy: 'Sarah Chen', uploadedAt: '2026-07-14T14:20:00Z', processedAt: '2026-07-14T14:35:00Z',
    tags: ['board-minutes', 'privileged-review', 'q1-2026'], version: 1, isPrivileged: true, riskLevel: 'critical',
  },
  {
    id: 'doc_003', name: 'Employment_Agreement_Template_v4.docx', type: 'docx', size: 234567,
    status: 'reviewed', caseId: 'case_004', caseName: 'DataFlow Inc. Employment Class Action',
    ocrAccuracy: 99.5, ocrConfidence: 'high', pageCount: 8, entityCount: 56,
    uploadedBy: 'Sarah Chen', uploadedAt: '2026-07-13T11:00:00Z', processedAt: '2026-07-13T11:10:00Z',
    tags: ['employment', 'contract', 'template'], version: 4, isPrivileged: false, riskLevel: 'low',
  },
  {
    id: 'doc_004', name: 'Trading_Records_Jan-Mar_2026.xlsx', type: 'xlsx', size: 15728640,
    status: 'processing', caseId: 'case_003', caseName: 'SEC Investigation — Greenfield Partners',
    ocrAccuracy: 0, ocrConfidence: 'low', pageCount: 1, entityCount: 0,
    uploadedBy: 'Sarah Chen', uploadedAt: '2026-07-17T07:00:00Z', processedAt: null,
    tags: ['trading', 'financial', 'sec-evidence'], version: 1, isPrivileged: false, riskLevel: 'high',
  },
  {
    id: 'doc_005', name: 'Thornton_Will_Amendment_2019.pdf', type: 'pdf', size: 1048576,
    status: 'analyzed', caseId: 'case_002', caseName: 'Thornton Estate — Probate Review',
    ocrAccuracy: 96.3, ocrConfidence: 'medium', pageCount: 5, entityCount: 42,
    uploadedBy: 'Sarah Chen', uploadedAt: '2026-07-12T10:15:00Z', processedAt: '2026-07-12T10:25:00Z',
    tags: ['will', 'amendment', 'key-document'], version: 1, isPrivileged: false, riskLevel: 'medium',
  },
  {
    id: 'doc_006', name: 'NovaTech_IP_Portfolio_Summary.pdf', type: 'pdf', size: 8945664,
    status: 'analyzed', caseId: 'case_005', caseName: 'NovaTech Merger Due Diligence',
    ocrAccuracy: 99.1, ocrConfidence: 'high', pageCount: 34, entityCount: 178,
    uploadedBy: 'Sarah Chen', uploadedAt: '2026-07-11T08:45:00Z', processedAt: '2026-07-11T09:05:00Z',
    tags: ['ip', 'portfolio', 'due-diligence'], version: 2, isPrivileged: false, riskLevel: 'low',
  },
  {
    id: 'doc_007', name: 'Internal_Communication_Log_Redacted.eml', type: 'eml', size: 567890,
    status: 'flagged', caseId: 'case_003', caseName: 'SEC Investigation — Greenfield Partners',
    ocrAccuracy: 98.4, ocrConfidence: 'high', pageCount: 3, entityCount: 67,
    uploadedBy: 'Sarah Chen', uploadedAt: '2026-07-16T16:00:00Z', processedAt: '2026-07-16T16:15:00Z',
    tags: ['email', 'internal', 'flagged'], version: 1, isPrivileged: true, riskLevel: 'critical',
  },
  {
    id: 'doc_008', name: 'Compliance_Policy_Heritage_Bank.pdf', type: 'pdf', size: 2345678,
    status: 'uploaded', caseId: 'case_006', caseName: 'Heritage Bank — AML Compliance',
    ocrAccuracy: 0, ocrConfidence: 'low', pageCount: 28, entityCount: 0,
    uploadedBy: 'Sarah Chen', uploadedAt: '2026-07-17T06:30:00Z', processedAt: null,
    tags: ['compliance', 'policy'], version: 1, isPrivileged: false, riskLevel: 'none',
  },
];

// ── AI Insights ──────────────────────────────────────────────────────────────

export const MOCK_AI_INSIGHTS: AIInsight[] = [
  {
    id: 'ins_001', title: 'Privileged Communication Detected',
    description: 'Attorney-client privileged content identified in Board Meeting Minutes. 3 sections flagged for review before production.',
    severity: 'critical', agentName: 'Privilege Detector', caseId: 'case_003',
    caseName: 'SEC Investigation — Greenfield Partners', createdAt: '2026-07-17T07:15:00Z', isRead: false,
  },
  {
    id: 'ins_002', title: 'Anomalous Trading Pattern Found',
    description: 'Statistical analysis reveals trading activity 4.2 standard deviations above normal volume preceding the Q1 earnings announcement.',
    severity: 'high', agentName: 'Risk Analyzer', caseId: 'case_003',
    caseName: 'SEC Investigation — Greenfield Partners', createdAt: '2026-07-17T06:45:00Z', isRead: false,
  },
  {
    id: 'ins_003', title: 'Cross-Reference Match: Prior Art',
    description: 'Entity Extractor found 12 references to prior art in Atlas Industries\' patent portfolio that may support invalidity arguments.',
    severity: 'medium', agentName: 'Entity Extractor', caseId: 'case_001',
    caseName: 'Meridian Corp. v. Atlas Industries', createdAt: '2026-07-16T18:30:00Z', isRead: true,
  },
  {
    id: 'ins_004', title: 'Document Classification Complete',
    description: 'Batch of 342 documents classified. 89% categorized as responsive, 7% non-responsive, 4% require manual review.',
    severity: 'info', agentName: 'Document Classifier', caseId: 'case_001',
    caseName: 'Meridian Corp. v. Atlas Industries', createdAt: '2026-07-16T15:00:00Z', isRead: true,
  },
  {
    id: 'ins_005', title: 'Timeline Inconsistency Detected',
    description: 'Will amendment dated March 2019 references a trust provision not established until September 2019. Possible backdating.',
    severity: 'high', agentName: 'Timeline Builder', caseId: 'case_002',
    caseName: 'Thornton Estate — Probate Review', createdAt: '2026-07-16T12:00:00Z', isRead: false,
  },
];

// ── Risk Distribution ────────────────────────────────────────────────────────

export const MOCK_RISK_DISTRIBUTION: RiskDistribution[] = [
  { level: 'critical', count: 3, percentage: 12.5 },
  { level: 'high', count: 6, percentage: 25 },
  { level: 'medium', count: 8, percentage: 33.3 },
  { level: 'low', count: 5, percentage: 20.8 },
  { level: 'none', count: 2, percentage: 8.4 },
];

// ── Evidence Summary ─────────────────────────────────────────────────────────

export const MOCK_EVIDENCE_SUMMARY: EvidenceSummary[] = [
  { type: 'Contracts', count: 847, trend: 12 },
  { type: 'Emails', count: 1243, trend: 34 },
  { type: 'Financial', count: 521, trend: -8 },
  { type: 'Legal Filings', count: 334, trend: 5 },
  { type: 'Internal Memos', count: 189, trend: 21 },
  { type: 'Meeting Notes', count: 107, trend: 3 },
];

// ── Timeline Events (Merged Below) ──────────────────────────────────────────


// ── Notifications ────────────────────────────────────────────────────────────

export const MOCK_NOTIFICATIONS: Notification[] = [
  {
    id: 'notif_001', title: 'Critical: Privilege Alert', message: 'Privileged content detected in 3 documents for Greenfield case.',
    type: 'warning', isRead: false, createdAt: '2026-07-17T07:15:00Z', actionUrl: '/documents',
  },
  {
    id: 'notif_002', title: 'OCR Processing Complete', message: '47 documents successfully processed with 98.7% average accuracy.',
    type: 'success', isRead: false, createdAt: '2026-07-17T06:45:00Z', actionUrl: '/documents',
  },
  {
    id: 'notif_003', title: 'Risk Assessment Ready', message: 'NovaTech IP portfolio risk report is ready for download.',
    type: 'info', isRead: false, createdAt: '2026-07-16T15:30:00Z', actionUrl: '/reports',
  },
  {
    id: 'notif_004', title: 'New AI Insight', message: 'Timeline inconsistency found in Thornton estate documents.',
    type: 'ai_insight', isRead: true, createdAt: '2026-07-16T12:00:00Z', actionUrl: '/ai-review',
  },
  {
    id: 'notif_005', title: 'Case Deadline Approaching', message: 'Greenfield Partners response due in 44 days.',
    type: 'warning', isRead: true, createdAt: '2026-07-16T08:00:00Z', actionUrl: '/cases',
  },
];

// ── Activity Feed ────────────────────────────────────────────────────────────

export const MOCK_ACTIVITIES: ActivityItem[] = [
  { id: 'act_001', action: 'Flagged Document', description: 'Privilege Detector flagged Board_Meeting_Minutes_Q1_2026.docx', user: 'AI Agent', timestamp: '2026-07-17T07:15:00Z', icon: 'Shield', category: 'ai' },
  { id: 'act_002', action: 'Uploaded Documents', description: '47 new documents added to Meridian v. Atlas case', user: 'Sarah Chen', timestamp: '2026-07-17T06:30:00Z', icon: 'Upload', category: 'document' },
  { id: 'act_003', action: 'Generated Report', description: 'Risk assessment report for NovaTech Merger created', user: 'Risk Analyzer', timestamp: '2026-07-16T15:30:00Z', icon: 'FileBarChart', category: 'ai' },
  { id: 'act_004', action: 'Updated Case Status', description: 'SEC Investigation moved to Review phase', user: 'Sarah Chen', timestamp: '2026-07-16T14:20:00Z', icon: 'RefreshCw', category: 'case' },
  { id: 'act_005', action: 'Completed OCR', description: '342 pages processed with 99.2% accuracy', user: 'OCR Engine', timestamp: '2026-07-16T11:45:00Z', icon: 'Eye', category: 'system' },
  { id: 'act_006', action: 'Entity Extraction', description: '234 entities extracted from patent filing documents', user: 'Entity Extractor', timestamp: '2026-07-16T10:00:00Z', icon: 'Sparkles', category: 'ai' },
  { id: 'act_007', action: 'Created Case', description: 'Heritage Bank AML Compliance case opened', user: 'Sarah Chen', timestamp: '2026-07-15T09:00:00Z', icon: 'FolderPlus', category: 'case' },
];

// ── Reports ──────────────────────────────────────────────────────────────────

export const MOCK_REPORTS: Report[] = [
  { id: 'rpt_001', name: 'Greenfield Partners — Privilege Log', type: 'privilege_log', status: 'completed', caseId: 'case_003', caseName: 'SEC Investigation — Greenfield Partners', generatedAt: '2026-07-16T18:00:00Z', size: 2456789, pageCount: 34 },
  { id: 'rpt_002', name: 'Meridian v. Atlas — Review Summary', type: 'review_summary', status: 'completed', caseId: 'case_001', caseName: 'Meridian Corp. v. Atlas Industries', generatedAt: '2026-07-15T16:00:00Z', size: 1823456, pageCount: 22 },
  { id: 'rpt_003', name: 'NovaTech — Risk Assessment', type: 'risk_assessment', status: 'completed', caseId: 'case_005', caseName: 'NovaTech Merger Due Diligence', generatedAt: '2026-07-16T15:30:00Z', size: 3245678, pageCount: 41 },
  { id: 'rpt_004', name: 'Q2 2026 Analytics Dashboard', type: 'analytics', status: 'generating', caseId: '', caseName: 'Platform-wide', generatedAt: '2026-07-17T07:00:00Z', size: 0, pageCount: 0 },
  { id: 'rpt_005', name: 'Thornton Estate — Timeline Report', type: 'timeline_report', status: 'completed', caseId: 'case_002', caseName: 'Thornton Estate — Probate Review', generatedAt: '2026-07-14T12:00:00Z', size: 1567890, pageCount: 18 },
];

// ── Search Results ───────────────────────────────────────────────────────────

export const MOCK_SEARCH_RESULTS: SearchResult[] = [
  {
    id: 'sr_001', documentId: 'doc_001', documentName: 'Meridian-Atlas_Patent_Filing_2024.pdf',
    caseId: 'case_001', caseName: 'Meridian Corp. v. Atlas Industries',
    snippet: '...the semiconductor manufacturing process described in Claims 4-7 directly corresponds to the methodology outlined in the prior art reference...',
    relevanceScore: 0.96, matchType: 'semantic', highlights: ['semiconductor manufacturing process', 'prior art reference'], pageNumber: 23,
  },
  {
    id: 'sr_002', documentId: 'doc_002', documentName: 'Board_Meeting_Minutes_Q1_2026.docx',
    caseId: 'case_003', caseName: 'SEC Investigation — Greenfield Partners',
    snippet: '...discussed the potential acquisition targets and agreed to proceed with preliminary due diligence on three identified companies before public announcement...',
    relevanceScore: 0.92, matchType: 'semantic', highlights: ['acquisition targets', 'public announcement'], pageNumber: 4,
  },
  {
    id: 'sr_003', documentId: 'doc_005', documentName: 'Thornton_Will_Amendment_2019.pdf',
    caseId: 'case_002', caseName: 'Thornton Estate — Probate Review',
    snippet: '...hereby amends Section 4.2(b) of the Original Trust Instrument to include the Revised Distribution Schedule as set forth in Exhibit A, effective as of...',
    relevanceScore: 0.89, matchType: 'keyword', highlights: ['amends Section 4.2(b)', 'Revised Distribution Schedule'], pageNumber: 2,
  },
];

// ── Document Entities ────────────────────────────────────────────────────────

export const MOCK_ENTITIES: DocumentEntity[] = [
  { id: 'ent_001', text: 'Meridian Corporation', type: 'organization', confidence: 0.98, startOffset: 145, endOffset: 167 },
  { id: 'ent_002', text: 'Atlas Industries Inc.', type: 'organization', confidence: 0.97, startOffset: 234, endOffset: 256 },
  { id: 'ent_003', text: 'Dr. James Whitfield', type: 'person', confidence: 0.95, startOffset: 389, endOffset: 408 },
  { id: 'ent_004', text: 'March 15, 2024', type: 'date', confidence: 0.99, startOffset: 456, endOffset: 470 },
  { id: 'ent_005', text: '$4.2 million', type: 'monetary', confidence: 0.96, startOffset: 567, endOffset: 579 },
  { id: 'ent_006', text: 'San Jose, California', type: 'location', confidence: 0.94, startOffset: 612, endOffset: 632 },
  { id: 'ent_007', text: 'Patent No. US-2024-0089123', type: 'legal_term', confidence: 0.99, startOffset: 78, endOffset: 104 },
  { id: 'ent_008', text: 'Smith v. Johnson (2019)', type: 'case_reference', confidence: 0.92, startOffset: 890, endOffset: 913 },
];

// ── Document Versions ────────────────────────────────────────────────────────

export const MOCK_VERSIONS: DocumentVersion[] = [
  { id: 'ver_003', version: 3, uploadedBy: 'Sarah Chen', uploadedAt: '2026-07-15T09:30:00Z', size: 4521984, changeNote: 'Updated with court filing stamps and annotations' },
  { id: 'ver_002', version: 2, uploadedBy: 'Sarah Chen', uploadedAt: '2026-06-20T14:00:00Z', size: 4398720, changeNote: 'Added exhibit references and cross-references' },
  { id: 'ver_001', version: 1, uploadedBy: 'Sarah Chen', uploadedAt: '2026-02-14T09:00:00Z', size: 4245504, changeNote: 'Initial upload from client document production' },
];

// ── Knowledge Graph (40+ Nodes, 50+ Edges) ───────────────────────────────────

export const MOCK_GRAPH_NODES: GraphNode[] = [
  { id: 'gn_001', label: 'Meridian Corp.', type: 'organization', metadata: { role: 'plaintiff', headquarters: 'San Jose, CA' }, caseId: 'case_001', importance: 0.95, description: 'Plaintiff corporation claiming patent infringement.' },
  { id: 'gn_002', label: 'Atlas Industries', type: 'organization', metadata: { role: 'defendant', headquarters: 'Austin, TX' }, caseId: 'case_001', importance: 0.92, description: 'Defendant corporation accused of trade secret theft.' },
  { id: 'gn_003', label: 'Dr. James Whitfield', type: 'person', metadata: { role: 'Lead Scientist', employer: 'Meridian Corp.' }, caseId: 'case_001', importance: 0.88, description: 'Co-inventor of the contested semiconductor process.' },
  { id: 'gn_004', label: 'Patent US-2024-0089123', type: 'document', metadata: { type: 'patent', date: '2024-03-12' }, caseId: 'case_001', importance: 0.90, description: 'Contested patent on semiconductor manufacturing.' },
  { id: 'gn_005', label: 'San Jose, CA', type: 'location', metadata: { state: 'California' }, caseId: 'case_001', importance: 0.5 },
  { id: 'gn_006', label: 'Greenfield Partners', type: 'organization', metadata: { role: 'investor' }, caseId: 'case_001', importance: 0.7 },
  { id: 'gn_007', label: 'SEC', type: 'organization', metadata: { role: 'regulatory_body' }, caseId: 'case_001', importance: 0.8 },
  { id: 'gn_008', label: 'Board Meeting Q1', type: 'event', metadata: { date: '2026-03-15' }, caseId: 'case_001', importance: 0.65 },
  { id: 'gn_009', label: 'Thornton Family', type: 'person', metadata: { role: 'beneficiary' }, caseId: 'case_002', importance: 0.75 },
  { id: 'gn_010', label: 'Will Amendment', type: 'document', metadata: { year: '2019' }, caseId: 'case_002', importance: 0.85 },
  { id: 'gn_011', label: 'Dr. Linda Vance', type: 'person', metadata: { role: 'Expert Witness', field: 'Semiconductors' }, caseId: 'case_001', importance: 0.8 },
  { id: 'gn_012', label: 'Source Code Repository', type: 'evidence', metadata: { type: 'git_repo', hash: 'sha256:8f9a2b' }, caseId: 'case_001', importance: 0.85 },
  { id: 'gn_013', label: 'NDA Agreement', type: 'contract', metadata: { signed: '2023-05-14' }, caseId: 'case_001', importance: 0.78 },
  { id: 'gn_014', label: 'John Miller', type: 'person', metadata: { role: 'Former Employee', target: 'Atlas Industries' }, caseId: 'case_001', importance: 0.82 },
  { id: 'gn_015', label: 'Email Thread #41', type: 'email', metadata: { subject: 'Project Phoenix Specs' }, caseId: 'case_001', importance: 0.75 },
  { id: 'gn_016', label: 'Austin, TX', type: 'location', metadata: { state: 'Texas' }, caseId: 'case_001', importance: 0.4 },
  { id: 'gn_017', label: 'IP Theft Allegation', type: 'legal_issue', metadata: { status: 'contested' }, caseId: 'case_001', importance: 0.9 },
  { id: 'gn_018', label: 'Damages Estimation', type: 'legal_issue', metadata: { value: '$45M' }, caseId: 'case_001', importance: 0.82 },
  { id: 'gn_019', label: 'Deposition of Whitfield', type: 'event', metadata: { date: '2026-06-12' }, caseId: 'case_001', importance: 0.72 },
  { id: 'gn_020', label: 'Deposition of Miller', type: 'event', metadata: { date: '2026-06-18' }, caseId: 'case_001', importance: 0.74 },
  { id: 'gn_021', label: 'Meridian Lab Report', type: 'document', metadata: { type: 'R&D' }, caseId: 'case_001', importance: 0.65 },
  { id: 'gn_022', label: 'Atlas Technical Spec', type: 'document', metadata: { type: 'Blueprint' }, caseId: 'case_001', importance: 0.78 },
  { id: 'gn_023', label: 'David Ross', type: 'person', metadata: { role: 'Attorney', firm: 'Westlake' }, caseId: 'case_001', importance: 0.6 },
  { id: 'gn_024', label: 'Patent Office', type: 'organization', metadata: { country: 'US' }, caseId: 'case_001', importance: 0.72 },
  { id: 'gn_025', label: 'Court Hearing Q2', type: 'event', metadata: { date: '2026-05-20' }, caseId: 'case_001', importance: 0.8 },
  { id: 'gn_026', label: 'Bank Wire Transfer', type: 'evidence', metadata: { amount: '$1.2M' }, caseId: 'case_001', importance: 0.79 },
  { id: 'gn_027', label: 'Swiss Bank Account', type: 'location', metadata: { country: 'Switzerland' }, caseId: 'case_001', importance: 0.65 },
  { id: 'gn_028', label: 'Consulting Contract', type: 'contract', metadata: { status: 'terminated' }, caseId: 'case_001', importance: 0.7 },
  { id: 'gn_029', label: 'Robert Chen', type: 'person', metadata: { role: 'CEO', company: 'Atlas Industries' }, caseId: 'case_001', importance: 0.86 },
  { id: 'gn_030', label: 'Alice Thompson', type: 'person', metadata: { role: 'VP Engineering', company: 'Meridian' }, caseId: 'case_001', importance: 0.81 },
  { id: 'gn_031', label: 'Subpoena Document', type: 'document', metadata: { date: '2026-04-10' }, caseId: 'case_001', importance: 0.75 },
  { id: 'gn_032', label: 'Meeting Audio Recording', type: 'evidence', metadata: { type: 'audio' }, caseId: 'case_001', importance: 0.68 },
  { id: 'gn_033', label: 'Chat Log Export', type: 'evidence', metadata: { platform: 'Slack' }, caseId: 'case_001', importance: 0.73 },
  { id: 'gn_034', label: 'Vance Expert Report', type: 'document', metadata: { date: '2026-07-02' }, caseId: 'case_001', importance: 0.84 },
  { id: 'gn_035', label: 'Prior Art Search', type: 'document', metadata: { scope: 'global' }, caseId: 'case_001', importance: 0.62 },
  { id: 'gn_036', label: 'Development Server Log', type: 'evidence', metadata: { type: 'network_log' }, caseId: 'case_001', importance: 0.77 },
  { id: 'gn_037', label: 'System Access Log', type: 'evidence', metadata: { type: 'security_log' }, caseId: 'case_001', importance: 0.8 },
  { id: 'gn_038', label: 'Joint Defense Agreement', type: 'contract', metadata: { type: 'legal' }, caseId: 'case_001', importance: 0.72 },
  { id: 'gn_039', label: 'London, UK', type: 'location', metadata: { region: 'Europe' }, caseId: 'case_001', importance: 0.3 },
  { id: 'gn_040', label: 'IPO Filing Draft', type: 'document', metadata: { status: 'draft' }, caseId: 'case_001', importance: 0.67 },
  { id: 'gn_041', label: 'Forensic Copy Disk', type: 'evidence', metadata: { status: 'verified' }, caseId: 'case_001', importance: 0.85 },
];

export const MOCK_GRAPH_EDGES: GraphEdge[] = [
  { id: 'ge_001', source: 'gn_001', target: 'gn_002', label: 'filed against', type: 'relationship', weight: 0.95 },
  { id: 'ge_002', source: 'gn_003', target: 'gn_004', label: 'inventor of', type: 'relationship', weight: 0.98 },
  { id: 'ge_003', source: 'gn_001', target: 'gn_004', label: 'owns', type: 'ownership', weight: 0.9 },
  { id: 'ge_004', source: 'gn_003', target: 'gn_005', label: 'based in', type: 'relationship', weight: 0.6 },
  { id: 'ge_005', source: 'gn_006', target: 'gn_007', label: 'investigated by', type: 'relationship', weight: 0.85 },
  { id: 'ge_006', source: 'gn_006', target: 'gn_008', label: 'held', type: 'relationship', weight: 0.7 },
  { id: 'ge_007', source: 'gn_009', target: 'gn_010', label: 'contested', type: 'relationship', weight: 0.88 },
  { id: 'ge_008', source: 'gn_002', target: 'gn_004', label: 'allegedly infringes', type: 'citation', weight: 0.84 },
  { id: 'ge_009', source: 'gn_011', target: 'gn_001', label: 'retained by', type: 'relationship', weight: 0.8 },
  { id: 'ge_010', source: 'gn_012', target: 'gn_002', label: 'found on', type: 'evidence_link', weight: 0.92 },
  { id: 'ge_011', source: 'gn_014', target: 'gn_013', label: 'bound by', type: 'ownership', weight: 0.85 },
  { id: 'ge_012', source: 'gn_014', target: 'gn_001', label: 'formerly employed by', type: 'relationship', weight: 0.75 },
  { id: 'ge_013', source: 'gn_014', target: 'gn_002', label: 'hired by', type: 'relationship', weight: 0.88 },
  { id: 'ge_014', source: 'gn_015', target: 'gn_014', label: 'sent by', type: 'communication', weight: 0.9 },
  { id: 'ge_015', source: 'gn_015', target: 'gn_029', label: 'received by', type: 'communication', weight: 0.9 },
  { id: 'ge_016', source: 'gn_002', target: 'gn_016', label: 'headquartered in', type: 'relationship', weight: 0.7 },
  { id: 'ge_017', source: 'gn_017', target: 'gn_001', label: 'raised by', type: 'relationship', weight: 0.95 },
  { id: 'ge_018', source: 'gn_017', target: 'gn_002', label: 'concerns', type: 'relationship', weight: 0.9 },
  { id: 'ge_019', source: 'gn_018', target: 'gn_017', label: 'stems from', type: 'relationship', weight: 0.8 },
  { id: 'ge_020', source: 'gn_019', target: 'gn_003', label: 'questioned', type: 'relationship', weight: 0.75 },
  { id: 'ge_021', source: 'gn_020', target: 'gn_014', label: 'questioned', type: 'relationship', weight: 0.78 },
  { id: 'ge_022', source: 'gn_021', target: 'gn_003', label: 'authored by', type: 'relationship', weight: 0.85 },
  { id: 'ge_023', source: 'gn_022', target: 'gn_029', label: 'authorized by', type: 'relationship', weight: 0.8 },
  { id: 'ge_024', source: 'gn_021', target: 'gn_022', label: 'highly similar to', type: 'similarity', weight: 0.89 },
  { id: 'ge_025', source: 'gn_023', target: 'gn_001', label: 'represents', type: 'relationship', weight: 0.9 },
  { id: 'ge_026', source: 'gn_004', target: 'gn_024', label: 'registered with', type: 'relationship', weight: 0.95 },
  { id: 'ge_027', source: 'gn_025', target: 'gn_023', label: 'attended by', type: 'relationship', weight: 0.75 },
  { id: 'ge_028', source: 'gn_026', target: 'gn_027', label: 'routed to', type: 'evidence_link', weight: 0.82 },
  { id: 'ge_029', source: 'gn_026', target: 'gn_002', label: 'funded by', type: 'evidence_link', weight: 0.88 },
  { id: 'ge_030', source: 'gn_014', target: 'gn_026', label: 'beneficial owner', type: 'ownership', weight: 0.93 },
  { id: 'ge_031', source: 'gn_028', target: 'gn_014', label: 'executed with', type: 'ownership', weight: 0.75 },
  { id: 'ge_032', source: 'gn_030', target: 'gn_001', label: 'manages', type: 'relationship', weight: 0.85 },
  { id: 'ge_033', source: 'gn_030', target: 'gn_015', label: 'mentioned in', type: 'mentions', weight: 0.7 },
  { id: 'ge_034', source: 'gn_031', target: 'gn_002', label: 'served to', type: 'relationship', weight: 0.85 },
  { id: 'ge_035', source: 'gn_032', target: 'gn_014', label: 'records voice of', type: 'evidence_link', weight: 0.82 },
  { id: 'ge_036', source: 'gn_032', target: 'gn_029', label: 'records voice of', type: 'evidence_link', weight: 0.84 },
  { id: 'ge_037', source: 'gn_033', target: 'gn_014', label: 'involves chat of', type: 'evidence_link', weight: 0.75 },
  { id: 'ge_038', source: 'gn_034', target: 'gn_011', label: 'written by', type: 'relationship', weight: 0.98 },
  { id: 'ge_039', source: 'gn_034', target: 'gn_021', label: 'cites', type: 'citation', weight: 0.9 },
  { id: 'ge_040', source: 'gn_034', target: 'gn_022', label: 'cites', type: 'citation', weight: 0.92 },
  { id: 'ge_041', source: 'gn_035', target: 'gn_004', label: 'references', type: 'references', weight: 0.85 },
  { id: 'ge_042', source: 'gn_036', target: 'gn_012', label: 'logs access to', type: 'evidence_link', weight: 0.87 },
  { id: 'ge_043', source: 'gn_037', target: 'gn_014', label: 'records session of', type: 'evidence_link', weight: 0.91 },
  { id: 'ge_044', source: 'gn_038', target: 'gn_002', label: 'protects', type: 'relationship', weight: 0.8 },
  { id: 'ge_045', source: 'gn_014', target: 'gn_039', label: 'traveled to', type: 'relationship', weight: 0.65 },
  { id: 'ge_046', source: 'gn_040', target: 'gn_001', label: 'planned by', type: 'relationship', weight: 0.78 },
  { id: 'ge_047', source: 'gn_041', target: 'gn_014', label: 'cloned laptop of', type: 'evidence_link', weight: 0.95 },
  { id: 'ge_048', source: 'gn_029', target: 'gn_002', label: 'directs', type: 'relationship', weight: 0.9 },
  { id: 'ge_049', source: 'gn_028', target: 'gn_002', label: 'drafted by', type: 'references', weight: 0.6 },
  { id: 'ge_050', source: 'gn_013', target: 'gn_001', label: 'entered with', type: 'references', weight: 0.8 },
];

// ── Chronological Timeline (30+ Events) ──────────────────────────────────────

export const MOCK_TIMELINE_EVENTS: TimelineEvent[] = [
  {
    id: 'evt_016', title: 'Privilege Review Flagged', description: '3 documents flagged for attorney-client privilege in SEC investigation.',
    type: 'ai_finding', timestamp: '2026-07-17T07:15:00Z', caseId: 'case_003',
    caseName: 'SEC Investigation', userId: 'sys', userName: 'Privilege Detector', metadata: { count: '3' },
  },
  {
    id: 'evt_017', title: 'Batch Upload Completed', description: '47 documents uploaded and queued for OCR processing.',
    type: 'upload', timestamp: '2026-07-17T06:30:00Z', caseId: 'case_001',
    caseName: 'Meridian v. Atlas', userId: 'usr_001', userName: 'Sarah Chen', metadata: { count: '47' },
  },
  {
    id: 'evt_018', title: 'Case Status Updated', description: 'Greenfield case moved to active review phase.',
    type: 'status_change', timestamp: '2026-07-16T18:00:00Z', caseId: 'case_003',
    caseName: 'SEC Investigation', userId: 'usr_001', userName: 'Sarah Chen', metadata: { from: 'active', to: 'review' },
  },
  {
    id: 'evt_019', title: 'Risk Assessment Generated', description: 'Automated risk assessment completed for NovaTech IP portfolio.',
    type: 'review', timestamp: '2026-07-16T15:30:00Z', caseId: 'case_005',
    caseName: 'NovaTech Merger', userId: 'sys', userName: 'Risk Analyzer', metadata: { score: '72' },
  },
  {
    id: 'evt_020', title: 'New Evidence Discovered', description: 'Timeline Builder identified potential backdated document in Thornton estate.',
    type: 'ai_finding', timestamp: '2026-07-16T12:00:00Z', caseId: 'case_002',
    caseName: 'Thornton Estate', userId: 'sys', userName: 'Timeline Builder', metadata: { documentId: 'doc_005' },
  },
  {
    id: 'evt_001', title: 'Meridian Corp NDA Signed',
    description: 'Dr. James Whitfield and John Miller sign a comprehensive Non-Disclosure Agreement before beginning R&D work.',
    type: 'contract', timestamp: '2023-05-14T09:00:00Z', caseId: 'case_001', caseName: 'Meridian v. Atlas',
    userId: 'usr_001', userName: 'Sarah Chen', lawyerName: 'Sarah Chen',
    entityNames: ['Dr. James Whitfield', 'John Miller', 'Meridian Corp.'],
    documentId: 'doc_003', documentName: 'Meridian_NDA_Miller.pdf', metadata: { priority: 'medium' }
  },
  {
    id: 'evt_002', title: 'Contested Patent Filing Date',
    description: 'Patent US-2024-0089123 on Semiconductor Planarization is filed with the USPTO by Meridian Corp.',
    type: 'legal_event', timestamp: '2024-03-12T10:30:00Z', caseId: 'case_001', caseName: 'Meridian v. Atlas',
    userId: 'usr_001', userName: 'Sarah Chen',
    entityNames: ['Patent US-2024-0089123', 'Meridian Corp.'],
    documentId: 'doc_004', documentName: 'Patent_US-2024-0089123.pdf', metadata: { priority: 'high' }
  },
  {
    id: 'evt_003', title: 'John Miller Resignation',
    description: 'John Miller resigns as Senior R&D Engineer from Meridian Corp, citing personal reasons. System access is revoked.',
    type: 'incident', timestamp: '2025-08-15T17:00:00Z', caseId: 'case_001', caseName: 'Meridian v. Atlas',
    userId: 'usr_001', userName: 'Sarah Chen',
    entityNames: ['John Miller', 'Meridian Corp.'], metadata: { priority: 'high' }
  },
  {
    id: 'evt_004', title: 'Unauthorized Code Repo Copying',
    description: 'System access logs detect a massive clone of the internal R&D repository by credentials assigned to John Miller just before resignation.',
    type: 'ocr_timestamp', timestamp: '2025-08-15T18:24:00Z', caseId: 'case_001', caseName: 'Meridian v. Atlas',
    userId: 'usr_002', userName: 'AI Extractor',
    entityNames: ['John Miller', 'Source Code Repository'],
    evidenceId: 'ev_001', metadata: { source: 'Security Server Logs' }
  },
  {
    id: 'evt_005', title: 'John Miller Hired by Atlas Industries',
    description: 'Atlas Industries announces John Miller has joined as VP of Semiconductor Engineering, a position created recently.',
    type: 'incident', timestamp: '2025-09-01T09:00:00Z', caseId: 'case_001', caseName: 'Meridian v. Atlas',
    userId: 'usr_001', userName: 'Sarah Chen',
    entityNames: ['John Miller', 'Atlas Industries'], metadata: { priority: 'high' }
  },
  {
    id: 'evt_006', title: 'Wire Transfer to Switzerland',
    description: 'Financial ledger shows a wire transfer of $1.2M from Atlas Offshore account to a Swiss bank account linked to John Miller\'s family trust.',
    type: 'payment', timestamp: '2025-09-10T14:15:00Z', caseId: 'case_001', caseName: 'Meridian v. Atlas',
    userId: 'usr_001', userName: 'Sarah Chen', amount: 1200000,
    entityNames: ['Atlas Industries', 'John Miller', 'Swiss Bank Account'],
    evidenceId: 'ev_002', metadata: { bank: 'Credit Suisse' }
  },
  {
    id: 'evt_007', title: 'Slack Communication - Phoenix Launch',
    description: 'Internal Slack conversation shows Robert Chen (CEO) urging engineering to launch Project Phoenix weeks ahead of schedule.',
    type: 'email', timestamp: '2025-11-20T16:44:00Z', caseId: 'case_001', caseName: 'Meridian v. Atlas',
    userId: 'usr_002', userName: 'AI Extractor',
    entityNames: ['Robert Chen', 'Atlas Industries'],
    evidenceId: 'ev_003', metadata: { channel: '#exec-leadership' }
  },
  {
    id: 'evt_008', title: 'Patent Infringement Complaint Filed',
    description: 'Meridian Corp files official complaint against Atlas Industries in Northern District of California (2026-CV-4821).',
    type: 'legal_event', timestamp: '2026-02-14T09:00:00Z', caseId: 'case_001', caseName: 'Meridian v. Atlas',
    userId: 'usr_001', userName: 'Sarah Chen', lawyerName: 'Sarah Chen',
    entityNames: ['Meridian Corp.', 'Atlas Industries'], metadata: { priority: 'critical' }
  },
  {
    id: 'evt_009', title: 'Subpoena Served on Atlas',
    description: 'Court issues subpoena requiring Atlas Industries to preserve and produce engineering logs and blueprint documents.',
    type: 'legal_event', timestamp: '2026-04-10T10:00:00Z', caseId: 'case_001', caseName: 'Meridian v. Atlas',
    userId: 'usr_001', userName: 'Sarah Chen',
    entityNames: ['Atlas Industries'],
    documentId: 'doc_012', documentName: 'Subpoena_Atlas_Preservation.pdf', metadata: { priority: 'high' }
  },
  {
    id: 'evt_010', title: 'First Court Hearing',
    description: 'Judge hears arguments on motion for preliminary injunction filed by Meridian Corp. Decides to expedite discovery.',
    type: 'hearing', timestamp: '2026-05-20T13:00:00Z', caseId: 'case_001', caseName: 'Meridian v. Atlas',
    userId: 'usr_001', userName: 'Sarah Chen', lawyerName: 'Sarah Chen',
    entityNames: ['Meridian Corp.', 'Atlas Industries'], metadata: { priority: 'high' }
  },
  {
    id: 'evt_011', title: 'AI Decision: Code Similarity Flagged',
    description: 'Legal Review Agent runs similarity scan and flags 89% structural overlap between Meridian\'s proprietary planarization code and Atlas\'s repository.',
    type: 'ai_decision', timestamp: '2026-06-05T11:20:00Z', caseId: 'case_001', caseName: 'Meridian v. Atlas',
    userId: 'usr_002', userName: 'AI Review Agent',
    entityNames: ['Source Code Repository', 'Atlas Technical Spec'], metadata: { confidence: '97%' }
  },
  {
    id: 'evt_012', title: 'Deposition of Dr. Whitfield',
    description: 'Dr. James Whitfield is deposed for 6 hours by Atlas Counsel, validating the timeline of invention of the semiconductor process.',
    type: 'hearing', timestamp: '2026-06-12T10:00:00Z', caseId: 'case_001', caseName: 'Meridian v. Atlas',
    userId: 'usr_001', userName: 'Sarah Chen',
    entityNames: ['Dr. James Whitfield'], metadata: { location: 'San Jose Court Room 4' }
  },
  {
    id: 'evt_013', title: 'Deposition of John Miller',
    description: 'John Miller is deposed. Admits accessing Meridian servers post-termination but claims it was to retrieve personal assets.',
    type: 'hearing', timestamp: '2026-06-18T10:00:00Z', caseId: 'case_001', caseName: 'Meridian v. Atlas',
    userId: 'usr_001', userName: 'Sarah Chen',
    entityNames: ['John Miller'], metadata: { location: 'Austin Office Depot' }
  },
  {
    id: 'evt_014', title: 'Expert Witness Report Submitted',
    description: 'Dr. Linda Vance submits expert analysis comparing the R&D artifacts, validating the claim of copy-pasted manufacturing processes.',
    type: 'document', timestamp: '2026-07-02T16:00:00Z', caseId: 'case_001', caseName: 'Meridian v. Atlas',
    userId: 'usr_001', userName: 'Sarah Chen',
    entityNames: ['Dr. Linda Vance'],
    documentId: 'doc_034', documentName: 'Expert_Report_Vance_Semiconductors.pdf', metadata: { priority: 'high' }
  },
  {
    id: 'evt_015', title: 'AI Decision: Trade Secret Theft High Probability',
    description: 'Legal Review Agent runs final inference and flags Case 2026-CV-4821 as containing high evidence supporting a willful trade secret violation.',
    type: 'ai_decision', timestamp: '2026-07-16T14:30:00Z', caseId: 'case_001', caseName: 'Meridian v. Atlas',
    userId: 'usr_002', userName: 'Legal Review Agent',
    entityNames: ['John Miller', 'Atlas Industries'], metadata: { confidence: '94.2%' }
  },
];

// ── Document Viewer Mock Data ────────────────────────────────────────────────

export const MOCK_DOC_ANNOTATIONS: DocumentAnnotation[] = [
  { id: 'ann_001', pageNumber: 1, type: 'highlight', color: 'yellow', text: 'Meridian Corporation, a California Corporation (the "Disclosing Party")', createdBy: 'Sarah Chen', createdAt: '2026-07-16T10:00:00Z', startOffset: 12, endOffset: 89 },
  { id: 'ann_002', pageNumber: 1, type: 'note', color: 'blue', text: 'shall keep strictly confidential all Proprietary Processes related to Planarization', note: 'This is the key term governing the semiconductor processes in dispute.', createdBy: 'Sarah Chen', createdAt: '2026-07-16T10:15:00Z', startOffset: 245, endOffset: 310 },
  { id: 'ann_003', pageNumber: 2, type: 'flag', color: 'red', text: 'for a period of five (5) years from disclosure', note: 'Validate if resignation happened within this window.', createdBy: 'Sarah Chen', createdAt: '2026-07-16T10:20:00Z', startOffset: 512, endOffset: 554 },
];

export const MOCK_DOC_OVERLAYS: OCROverlay[] = [
  { pageNumber: 1, text: 'MUTUAL NON-DISCLOSURE AGREEMENT', confidence: 0.99, boundingBox: { x: 50, y: 50, width: 500, height: 40 } },
  { pageNumber: 1, text: 'This Agreement is entered into as of May 14, 2023 by and between...', confidence: 0.98, boundingBox: { x: 50, y: 100, width: 500, height: 30 } },
  { pageNumber: 2, text: 'IN WITNESS WHEREOF, the parties hereto have executed this Agreement.', confidence: 0.99, boundingBox: { x: 50, y: 700, width: 500, height: 30 } },
];

export const MOCK_DOC_PRIVILEGE_MARKERS: PrivilegeMarker[] = [
  { id: 'priv_001', pageNumber: 1, type: 'attorney_client', description: 'Redacted communications between General Counsel and Lead Inventor.', startOffset: 750, endOffset: 920 },
  { id: 'priv_002', pageNumber: 2, type: 'work_product', description: 'Internal legal team brainstorming notes on patent infringement claims.', startOffset: 1500, endOffset: 1800 },
];

export const MOCK_DOC_CITATIONS: InlineCitation[] = [
  { id: 'cit_001', text: 'Smith v. Johnson (2019) 14 Cal.4th 23', caseReference: 'Smith v. Johnson', pageNumber: 2, confidence: 0.97, verified: true },
  { id: 'cit_002', text: 'Patent Act 35 U.S.C. § 271', caseReference: '35 U.S.C. 271', pageNumber: 1, confidence: 0.99, verified: true },
];

export const MOCK_DOC_REASONING: ReasoningStep[] = [
  { id: 'rs_001', step: 1, title: 'Analyze Confidentiality Period', description: 'Examine the contract text to verify the duration of the non-disclosure obligations.', confidence: 0.98, evidenceIds: ['ann_003'], conclusion: 'Obligations remain active until May 14, 2028.' },
  { id: 'rs_002', step: 2, title: 'Compare Resignation and Hiring Dates', description: 'Verify if John Miller was hired by Atlas within the active obligation period.', confidence: 0.99, evidenceIds: ['evt_003', 'evt_005'], conclusion: 'Resignation occurred on August 15, 2025 and hiring on September 1, 2025. This is well within the 5-year window.' },
];

export const MOCK_DOC_SUMMARY: DocumentSummary = {
  overview: 'This is a Mutual Non-Disclosure Agreement executed between Meridian Corporation and John Miller. It restricts the disclosure and use of proprietary semiconductor planarization technologies developed during employment.',
  keyFindings: [
    'Strict 5-year confidentiality obligation on all proprietary planarization processes.',
    'Governing law is set to the State of California.',
    'Includes remedies of injunctive relief without the necessity of posting bond.'
  ],
  entities: [
    { name: 'Meridian Corporation', type: 'organization', count: 12 },
    { name: 'John Miller', type: 'person', count: 9 },
    { name: 'California', type: 'location', count: 3 }
  ],
  riskFactors: [
    'Confidentiality clause has broad terms that could be challenged as a non-compete.',
    'Jurisdiction of dispute is fixed to Santa Clara County.'
  ],
  recommendations: [
    'Ensure all depositions reference the 5-year term limits.',
    'Prepare to file for injunctive relief under Section 8(b) of this Agreement.'
  ],
  confidence: 0.97
};

export const MOCK_DOC_RISK: DocumentRiskAssessment = {
  overallRisk: 'high',
  score: 82,
  factors: [
    { name: 'Extensive Liability Exposure', level: 'high', description: 'Section 9 mandates unlimited consequential damages for breach of intellectual property clauses.', pageReferences: [2] },
    { name: 'Unfavorable Forum Selection', level: 'medium', description: 'Santa Clara courts tend to favor regional tech giants in trade secret disputes.', pageReferences: [3] }
  ],
  flaggedSections: [
    { pageNumber: 2, text: '...the breaching party shall hold harmless and indemnify the Disclosing Party from any and all damages, including loss of profits and indirect damages...', reason: 'High-liability indemnity clause standardly flagged in IP agreements.' }
  ]
};

export const MOCK_DOC_VERSIONS_DIFF: VersionDiff[] = [
  { type: 'addition', pageNumber: 1, newText: 'including all planarization and chemical mechanical processes', description: 'Expanded scope of trade secrets.' },
  { type: 'modification', pageNumber: 2, oldText: 'arbitration under AAA rules', newText: 'litigation in Santa Clara Superior Court', description: 'Modified dispute resolution forum.' }
];


// ── Analytics Chart Data ─────────────────────────────────────────────────────

export const MOCK_DOCUMENTS_BY_MONTH: ChartData[] = [
  { name: 'Jan', value: 1842 },
  { name: 'Feb', value: 2156 },
  { name: 'Mar', value: 1923 },
  { name: 'Apr', value: 2478 },
  { name: 'May', value: 2834 },
  { name: 'Jun', value: 2102 },
  { name: 'Jul', value: 1512 },
];

export const MOCK_CASE_STATUS_CHART: ChartData[] = [
  { name: 'Active', value: 14, color: '#6366f1' },
  { name: 'Pending', value: 4, color: '#f59e0b' },
  { name: 'Review', value: 3, color: '#8b5cf6' },
  { name: 'Closed', value: 2, color: '#6b7280' },
  { name: 'Archived', value: 1, color: '#475569' },
];

export const MOCK_AI_PERFORMANCE: ChartData[] = [
  { name: 'Classifier', value: 96.4 },
  { name: 'Extractor', value: 94.8 },
  { name: 'Privilege', value: 97.2 },
  { name: 'Risk', value: 93.1 },
  { name: 'Timeline', value: 95.6 },
  { name: 'Reporter', value: 98.3 },
];

