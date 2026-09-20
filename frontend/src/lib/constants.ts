/**
 * Application constants — navigation config, routes, app metadata.
 */

export const APP_NAME = 'Agentic AI';
export const APP_SUBTITLE = 'Legal Intelligence Platform';
export const APP_VERSION = '2.0.0';

// ── Route Paths ──────────────────────────────────────────────────────────────

export const ROUTES = {
  LOGIN: '/login',
  DASHBOARD: '/',
  CASES: '/cases',
  DOCUMENTS: '/documents',
  INVESTIGATION: '/investigation',
  KNOWLEDGE_GRAPH: '/knowledge-graph',
  TIMELINE: '/timeline',
  AI_REVIEW: '/ai-review',
  SEMANTIC_SEARCH: '/search',
  REPORTS: '/reports',
  ANALYTICS: '/analytics',
  SETTINGS: '/settings',
  AGENTS: '/agents',
} as const;

// ── Route Metadata (for breadcrumbs + header) ────────────────────────────────

export const ROUTE_META: Record<string, { title: string; description: string }> = {
  [ROUTES.DASHBOARD]: { title: 'Dashboard', description: 'Platform overview and insights' },
  [ROUTES.CASES]: { title: 'Cases', description: 'Manage legal cases and matters' },
  [ROUTES.DOCUMENTS]: { title: 'Documents', description: 'Document library and management' },
  [ROUTES.INVESTIGATION]: { title: 'Investigation', description: 'Evidence board and analysis' },
  [ROUTES.KNOWLEDGE_GRAPH]: { title: 'Knowledge Graph', description: 'Entity relationships and connections' },
  [ROUTES.TIMELINE]: { title: 'Timeline', description: 'Chronological case events' },
  [ROUTES.AI_REVIEW]: { title: 'AI Review', description: 'AI-powered document review workspace' },
  [ROUTES.SEMANTIC_SEARCH]: { title: 'Semantic Search', description: 'AI-driven document search' },
  [ROUTES.REPORTS]: { title: 'Reports', description: 'Generated reports and exports' },
  [ROUTES.ANALYTICS]: { title: 'Analytics', description: 'Data insights and trends' },
  [ROUTES.SETTINGS]: { title: 'Settings', description: 'Account and platform settings' },
  [ROUTES.AGENTS]: { title: 'AI Agents', description: 'Monitor all AI agent activity' },
};

// ── Sidebar Navigation Config ────────────────────────────────────────────────

export interface SidebarNavItem {
  label: string;
  path: string;
  iconName: string;
  badge?: string;
  badgeVariant?: 'default' | 'success' | 'warning' | 'danger';
  section: 'main' | 'analysis' | 'output';
}

export const SIDEBAR_NAVIGATION: SidebarNavItem[] = [
  // Main Section
  { label: 'Dashboard', path: ROUTES.DASHBOARD, iconName: 'LayoutDashboard', section: 'main' },
  { label: 'Cases', path: ROUTES.CASES, iconName: 'FolderOpen', badgeVariant: 'default', section: 'main' },
  { label: 'Documents', path: ROUTES.DOCUMENTS, iconName: 'FileText', section: 'main' },
  { label: 'AI Agents', path: ROUTES.AGENTS, iconName: 'Bot', badgeVariant: 'success', section: 'main' },
  // Analysis Section
  { label: 'Investigation', path: ROUTES.INVESTIGATION, iconName: 'Search', section: 'analysis' },
  { label: 'Knowledge Graph', path: ROUTES.KNOWLEDGE_GRAPH, iconName: 'GitBranch', section: 'analysis' },
  { label: 'Timeline', path: ROUTES.TIMELINE, iconName: 'Clock', section: 'analysis' },
  { label: 'AI Review', path: ROUTES.AI_REVIEW, iconName: 'Brain', badgeVariant: 'warning', section: 'analysis' },
  { label: 'Semantic Search', path: ROUTES.SEMANTIC_SEARCH, iconName: 'Sparkles', section: 'analysis' },
  // Output Section
  { label: 'Reports', path: ROUTES.REPORTS, iconName: 'FileBarChart', section: 'output' },
  { label: 'Analytics', path: ROUTES.ANALYTICS, iconName: 'BarChart3', section: 'output' },
];

// ── API Endpoints ────────────────────────────────────────────────────────────

export const API_ENDPOINTS = {
  AUTH: {
    LOGIN: '/auth/login',
    LOGOUT: '/auth/logout',
    ME: '/auth/me',
    REFRESH: '/auth/refresh',
  },
  CASES: {
    LIST: '/cases',
    CREATE: '/cases',
    DETAIL: (id: string) => `/cases/${id}`,
    UPDATE: (id: string) => `/cases/${id}`,
    DELETE: (id: string) => `/cases/${id}`,
  },
  DOCUMENTS: {
    LIST: '/documents',
    UPLOAD: '/documents/upload',
    DETAIL: (id: string) => `/documents/${id}`,
    OCR: (id: string) => `/documents/${id}/ocr`,
    ENTITIES: (id: string) => `/documents/${id}/entities`,
    VERSIONS: (id: string) => `/documents/${id}/versions`,
  },
  AGENTS: {
    LIST: '/agents',
    STATUS: (id: string) => `/agents/${id}/status`,
    RETRY: (id: string) => `/agents/${id}/retry`,
    LOGS: (id: string) => `/agents/${id}/logs`,
    PIPELINE: '/agents/pipeline',
  },
  SEARCH: {
    SEMANTIC: '/search/semantic',
    KEYWORD: '/search/keyword',
  },
  ANALYTICS: {
    DASHBOARD: '/analytics/dashboard',
    CASES: '/analytics/cases',
    DOCUMENTS: '/analytics/documents',
  },
  HEALTH: '/health',
  WEBSOCKET: '/ws',
} as const;

// ── File Type Config ─────────────────────────────────────────────────────────

export const ACCEPTED_FILE_TYPES = {
  'application/pdf': ['.pdf'],
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
  'text/plain': ['.txt'],
  'message/rfc822': ['.eml'],
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
  'application/vnd.openxmlformats-officedocument.presentationml.presentation': ['.pptx'],
} as const;

export const MAX_FILE_SIZE = 100 * 1024 * 1024; // 100MB

// ── Theme Colors ─────────────────────────────────────────────────────────────

export const RISK_COLORS: Record<string, string> = {
  critical: '#ef4444',
  high: '#f97316',
  medium: '#f59e0b',
  low: '#10b981',
  none: '#6b7280',
};

export const STATUS_COLORS: Record<string, string> = {
  active: '#3b82f6',
  pending: '#f59e0b',
  review: '#8b5cf6',
  closed: '#6b7280',
  archived: '#475569',
};

export const AGENT_STATUS_COLORS: Record<string, string> = {
  idle: '#64748b',
  queued: '#f59e0b',
  running: '#6366f1',
  completed: '#10b981',
  failed: '#ef4444',
  retrying: '#f97316',
};

// ── AI Agent Registry (18 Pipeline Agents) ───────────────────────────────────

import type { AgentId, CanonicalAgentId, AgentInfo, PipelineStage } from '@/types';

export const AGENT_REGISTRY: Record<AgentId, AgentInfo> = {
  ingestion: {
    id: 'ingestion', name: 'Document Ingestion Agent', shortName: 'Ingestion',
    description: 'Validates file integrity, detects duplicates via SHA-256, and registers metadata.',
    iconName: 'FileUp', color: '#0284c7', pipelineOrder: 1, pipelineStage: 'document_upload',
  },
  ocr: {
    id: 'ocr', name: 'OCR Agent', shortName: 'OCR',
    description: 'Extracts text and structure from scanned documents and images using optical character recognition.',
    iconName: 'Eye', color: '#6366f1', pipelineOrder: 2, pipelineStage: 'ocr',
  },
  classification: {
    id: 'classification', name: 'Document Classification Agent', shortName: 'Classifier',
    description: 'Categorizes documents by legal type, jurisdictional scope, and privilege indicators.',
    iconName: 'FolderSearch', color: '#8b5cf6', pipelineOrder: 3, pipelineStage: 'indexing',
  },
  chunking: {
    id: 'chunking', name: 'Semantic Chunking Agent', shortName: 'Chunker',
    description: 'Segments documents into semantically coherent chunks with overlap for vector retrieval.',
    iconName: 'Layers', color: '#3b82f6', pipelineOrder: 4, pipelineStage: 'indexing',
  },
  embedding: {
    id: 'embedding', name: 'Vector Embedding Agent', shortName: 'Embeddings',
    description: 'Generates 1024-dimensional dense vector embeddings and indexes them into pgvector.',
    iconName: 'Cpu', color: '#f59e0b', pipelineOrder: 5, pipelineStage: 'indexing',
  },
  retrieval: {
    id: 'retrieval', name: 'RAG Retrieval Agent', shortName: 'Retrieval',
    description: 'Executes hybrid dense vector and cross-encoder retrieval over document chunks.',
    iconName: 'Database', color: '#06b6d4', pipelineOrder: 6, pipelineStage: 'retrieval',
  },
  entity_extraction: {
    id: 'entity_extraction', name: 'Entity Extraction Agent', shortName: 'Entities',
    description: 'Extracts persons, organizations, locations, dates, monetary values, and case numbers.',
    iconName: 'UserSearch', color: '#10b981', pipelineOrder: 7, pipelineStage: 'indexing',
  },
  relationship: {
    id: 'relationship', name: 'Relationship & Graph Agent', shortName: 'Relationships',
    description: 'Constructs NetworkX entity-relationship graphs and synchronizes knowledge topology.',
    iconName: 'GitFork', color: '#14b8a6', pipelineOrder: 8, pipelineStage: 'graph_generation',
  },
  timeline: {
    id: 'timeline', name: 'Timeline Agent', shortName: 'Timeline',
    description: 'Extracts and chronologically sequences dates and legal event narratives.',
    iconName: 'CalendarClock', color: '#10b981', pipelineOrder: 9, pipelineStage: 'timeline_generation',
  },
  summarization: {
    id: 'summarization', name: 'Summarization Agent', shortName: 'Summarizer',
    description: 'Generates cited multi-level legal summaries scored by ROUGE and semantic similarity.',
    iconName: 'FileText', color: '#a855f7', pipelineOrder: 10, pipelineStage: 'legal_review',
  },
  privilege: {
    id: 'privilege', name: 'Privilege Detection Agent', shortName: 'Privilege',
    description: 'Detects attorney-client privilege, attorney work product, and confidential legal memos.',
    iconName: 'Shield', color: '#ef4444', pipelineOrder: 11, pipelineStage: 'legal_review',
  },
  risk: {
    id: 'risk', name: 'Risk Assessment Agent', shortName: 'Risk Analysis',
    description: 'Assesses multi-dimensional legal, financial, and compliance risk severity levels.',
    iconName: 'AlertTriangle', color: '#f97316', pipelineOrder: 12, pipelineStage: 'legal_review',
  },
  pii: {
    id: 'pii', name: 'PII Redaction Agent', shortName: 'PII Guard',
    description: 'Detects and redacts sensitive PII (SSNs, credit cards, emails, phone numbers).',
    iconName: 'Lock', color: '#e11d48', pipelineOrder: 13, pipelineStage: 'legal_review',
  },
  review: {
    id: 'review', name: 'AI Review Agent', shortName: 'Reviewer',
    description: 'Synthesizes upstream agent findings into a consolidated legal review graph and map.',
    iconName: 'Scale', color: '#ec4899', pipelineOrder: 14, pipelineStage: 'legal_review',
  },
  verification: {
    id: 'verification', name: 'Citation Verification Agent', shortName: 'Verifier',
    description: 'Verifies citation authenticity, detects AI hallucinations, and audits evidentiary support.',
    iconName: 'BookCheck', color: '#22d3ee', pipelineOrder: 15, pipelineStage: 'legal_review',
  },
  clustering: {
    id: 'clustering', name: 'Document Clustering Agent', shortName: 'Clustering',
    description: 'Clusters documents by semantic similarity and topical cohesion across case matters.',
    iconName: 'Boxes', color: '#84cc16', pipelineOrder: 16, pipelineStage: 'retrieval',
  },
  report: {
    id: 'report', name: 'Report Generation Agent', shortName: 'Reporter',
    description: 'Generates comprehensive e-discovery review reports, privilege logs, and audit summaries.',
    iconName: 'FileBarChart', color: '#d946ef', pipelineOrder: 17, pipelineStage: 'final_report',
  },
  triage: {
    id: 'triage', name: 'Triage Orchestrator Agent', shortName: 'Triage Agent',
    description: 'Synthesizes multi-signal risk and privilege scores to assign priority tiers and escalation paths.',
    iconName: 'Compass', color: '#f43f5e', pipelineOrder: 18, pipelineStage: 'evidence_linking',
  },

  // ── Legacy Aliases ─────────────────────────────────────────────────────────
  relationship_extraction: {
    id: 'relationship_extraction', name: 'Relationship Extraction Agent', shortName: 'Relations',
    description: 'Maps relationships between extracted entities across documents.',
    iconName: 'GitFork', color: '#14b8a6', pipelineOrder: 8, pipelineStage: 'indexing',
  },
  knowledge_graph: {
    id: 'knowledge_graph', name: 'Knowledge Graph Agent', shortName: 'Graph',
    description: 'Builds and maintains the entity-relationship knowledge graph.',
    iconName: 'Share2', color: '#a855f7', pipelineOrder: 8, pipelineStage: 'graph_generation',
  },
  rag_retrieval: {
    id: 'rag_retrieval', name: 'RAG Retrieval Agent', shortName: 'Retrieval',
    description: 'Performs retrieval-augmented generation for contextual document analysis.',
    iconName: 'Database', color: '#3b82f6', pipelineOrder: 6, pipelineStage: 'retrieval',
  },
  legal_review: {
    id: 'legal_review', name: 'Legal Review Agent', shortName: 'Review',
    description: 'Conducts AI-powered legal analysis including privilege and risk assessment.',
    iconName: 'Scale', color: '#ec4899', pipelineOrder: 14, pipelineStage: 'legal_review',
  },
  citation_verification: {
    id: 'citation_verification', name: 'Citation Verification Agent', shortName: 'Citations',
    description: 'Verifies legal citations, case references, and statutory authority.',
    iconName: 'BookCheck', color: '#22d3ee', pipelineOrder: 15, pipelineStage: 'legal_review',
  },
  hallucination_detection: {
    id: 'hallucination_detection', name: 'Hallucination Detection Agent', shortName: 'Hallucination',
    description: 'Detects and flags potential AI hallucinations in generated content.',
    iconName: 'ShieldAlert', color: '#ef4444', pipelineOrder: 15, pipelineStage: 'legal_review',
  },
  evidence_linking: {
    id: 'evidence_linking', name: 'Evidence Linking Agent', shortName: 'Evidence',
    description: 'Links evidence across documents and cases to strengthen legal arguments.',
    iconName: 'Link2', color: '#f97316', pipelineOrder: 18, pipelineStage: 'evidence_linking',
  },
  similarity_search: {
    id: 'similarity_search', name: 'Similarity Search Agent', shortName: 'Similarity',
    description: 'Finds semantically similar documents and case precedents.',
    iconName: 'Sparkles', color: '#84cc16', pipelineOrder: 6, pipelineStage: 'retrieval',
  },
  report_generation: {
    id: 'report_generation', name: 'Report Generation Agent', shortName: 'Reports',
    description: 'Generates comprehensive review reports, privilege logs, and analysis summaries.',
    iconName: 'FileBarChart', color: '#d946ef', pipelineOrder: 17, pipelineStage: 'final_report',
  },
};

export const ALL_AGENT_IDS: CanonicalAgentId[] = [
  'ingestion',
  'ocr',
  'classification',
  'chunking',
  'embedding',
  'retrieval',
  'entity_extraction',
  'relationship',
  'timeline',
  'summarization',
  'privilege',
  'risk',
  'pii',
  'review',
  'verification',
  'clustering',
  'report',
  'triage',
];

// ── Pipeline Stages ──────────────────────────────────────────────────────────

export const PIPELINE_STAGES: PipelineStage[] = [
  { id: 'case_creation', label: 'Case Creation', order: 1, agentIds: [], status: 'idle' },
  { id: 'document_upload', label: 'Document Ingestion', order: 2, agentIds: ['ingestion'], status: 'idle' },
  { id: 'ocr', label: 'OCR & Extraction', order: 3, agentIds: ['ocr'], status: 'idle' },
  { id: 'indexing', label: 'Classification & Indexing', order: 4, agentIds: ['classification', 'chunking', 'embedding', 'entity_extraction'], status: 'idle' },
  { id: 'graph_generation', label: 'Knowledge Graph', order: 5, agentIds: ['relationship'], status: 'idle' },
  { id: 'timeline_generation', label: 'Timeline Generation', order: 6, agentIds: ['timeline'], status: 'idle' },
  { id: 'retrieval', label: 'Retrieval & Clustering', order: 7, agentIds: ['retrieval', 'clustering'], status: 'idle' },
  { id: 'legal_review', label: 'Legal Review & Analysis', order: 8, agentIds: ['summarization', 'privilege', 'risk', 'pii', 'review', 'verification'], status: 'idle' },
  { id: 'evidence_linking', label: 'Triage & Escalation', order: 9, agentIds: ['triage'], status: 'idle' },
  { id: 'final_report', label: 'Reporting', order: 10, agentIds: ['report'], status: 'idle' },
];

// ── Preview Widget Config ────────────────────────────────────────────────────

export const PREVIEW_WIDGET_CONFIG: Array<{
  type: string;
  title: string;
  route: string;
  iconName: string;
  color: string;
}> = [
  { type: 'knowledge_graph', title: 'Knowledge Graph', route: ROUTES.KNOWLEDGE_GRAPH, iconName: 'Share2', color: '#a855f7' },
  { type: 'timeline', title: 'Timeline', route: ROUTES.TIMELINE, iconName: 'CalendarClock', color: '#10b981' },
  { type: 'ai_review', title: 'AI Review', route: ROUTES.AI_REVIEW, iconName: 'Brain', color: '#ec4899' },
  { type: 'risk_analysis', title: 'Risk Analysis', route: ROUTES.ANALYTICS, iconName: 'ShieldAlert', color: '#ef4444' },
  { type: 'search_results', title: 'Semantic Search', route: ROUTES.SEMANTIC_SEARCH, iconName: 'Sparkles', color: '#84cc16' },
  { type: 'latest_reports', title: 'Latest Reports', route: ROUTES.REPORTS, iconName: 'FileBarChart', color: '#d946ef' },
  { type: 'linked_evidence', title: 'Linked Evidence', route: ROUTES.INVESTIGATION, iconName: 'Link2', color: '#f97316' },
  { type: 'active_investigations', title: 'Active Investigations', route: ROUTES.INVESTIGATION, iconName: 'Search', color: '#3b82f6' },
];

export const GRAPH_NODE_COLORS: Record<string, string> = {
  document: '#06b6d4',
  person: '#3b82f6',
  organization: '#8b5cf6',
  evidence: '#f97316',
  email: '#14b8a6',
  contract: '#ec4899',
  legal_issue: '#ef4444',
  event: '#f59e0b',
  location: '#10b981',
  case: '#6366f1',
};

export const GRAPH_EDGE_COLORS: Record<string, string> = {
  mentions: '#64748b',
  ownership: '#8b5cf6',
  similarity: '#84cc16',
  communication: '#14b8a6',
  citation: '#06b6d4',
  references: '#3b82f6',
  evidence_link: '#f97316',
  relationship: '#a855f7',
};

export const GRAPH_LAYOUTS: Array<{ mode: string; label: string }> = [
  { mode: 'force', label: 'Force Directed' },
  { mode: 'hierarchical', label: 'Hierarchical' },
  { mode: 'radial', label: 'Radial' },
  { mode: 'dagre', label: 'Dagre (Tree)' },
  { mode: 'grid', label: 'Grid' },
];


