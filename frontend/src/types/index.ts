/**
 * Shared TypeScript types for the Agentic AI Legal Review platform.
 * Strict typing — no `any` types anywhere.
 */

// ── User & Auth ──────────────────────────────────────────────────────────────

export interface User {
  id: string;
  email: string;
  name: string;
  role: 'lawyer';
  avatar?: string;
  firm: string;
  barNumber: string;
  createdAt: string;
  lastLoginAt: string;
}

export interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface AuthResponse {
  user: User;
  token: string;
  expiresAt: string;
}

// ── Cases ────────────────────────────────────────────────────────────────────

export type CaseStatus = 'active' | 'pending' | 'review' | 'closed' | 'archived';
export type CasePriority = 'critical' | 'high' | 'medium' | 'low';
export type RiskLevel = 'critical' | 'high' | 'medium' | 'low' | 'none';

export interface LegalCase {
  id: string;
  name: string;
  caseNumber: string;
  description: string;
  status: CaseStatus;
  priority: CasePriority;
  riskLevel: RiskLevel;
  client: string;
  assignedTo: string;
  documentCount: number;
  evidenceCount: number;
  createdAt: string;
  updatedAt: string;
  dueDate: string;
  tags: string[];
}

// ── Documents ────────────────────────────────────────────────────────────────

export type DocumentType = 'pdf' | 'docx' | 'txt' | 'eml' | 'xlsx' | 'pptx' | 'jpg' | 'png';
export type DocumentStatus = 'uploaded' | 'processing' | 'ocr_complete' | 'analyzed' | 'reviewed' | 'flagged' | 'error' | 'quota_paused';
export type OCRConfidence = 'high' | 'medium' | 'low';

export type OverrideFieldType = 'privilege' | 'relevance' | 'confidentiality';
export const OverrideField = {
  PRIVILEGE: 'privilege' as const,
  RELEVANCE: 'relevance' as const,
  CONFIDENTIALITY: 'confidentiality' as const,
} as const;
export type OverrideField = typeof OverrideField[keyof typeof OverrideField];

export const OverrideAction = {
  CONFIRM: 'confirm' as const,
  OVERRIDE: 'override' as const,
} as const;
export type OverrideAction = typeof OverrideAction[keyof typeof OverrideAction];

export interface HumanOverrideRequest {
  field: OverrideField;
  action: OverrideAction;
  override_value: any;
  original_ai_value?: any;
  ai_confidence?: number | null;
  reason: string;
  new_status?: DocumentStatus;
}

export interface DocumentSummaryItem {
  summary_type: 'executive' | 'legal' | 'evidence' | 'clause';
  text: string;
  citations: string[];
  grounding_verified?: boolean;
}

export interface PrivilegeAnalysis {
  is_privileged: boolean;
  confidence: number;
  privilege_type?: string | null;
  reasoning: string;
  citations: string[];
  evidence_spans: string[];
  detection_method: string;
}

export interface HumanOverrideRecord {
  override_id: string;
  field: OverrideField;
  action: OverrideAction;
  override_value: any;
  original_ai_value?: any;
  ai_confidence?: number | null;
  reason: string;
  reviewer_id?: string;
  reviewer_email?: string;
  reviewed_at: string;
}

export interface LegalDocument {
  id: string;
  name: string;
  type: DocumentType;
  size: number;
  status: DocumentStatus;
  caseId: string;
  caseName: string;
  ocrAccuracy: number;
  ocrConfidence: OCRConfidence;
  pageCount: number;
  entityCount: number;
  uploadedBy: string;
  uploadedAt: string;
  processedAt: string | null;
  tags: string[];
  version: number;
  isPrivileged: boolean;
  riskLevel: RiskLevel;
  extractedEntities?: any[];
  extracted_text?: string | null;
  doc_metadata?: {
    document_type?: string;
    summaries?: DocumentSummaryItem[];
    privilege_analysis?: PrivilegeAnalysis | null;
    semantic_similarity_scores?: number[];
    lexical_similarity_scores?: number[];
    human_overrides?: HumanOverrideRecord[];
    review_status?: string;
    reviewed_by?: string;
    reviewed_at?: string;
    [key: string]: any;
  } | null;
}

export interface DocumentEntity {
  id: string;
  text: string;
  type: 'person' | 'organization' | 'date' | 'location' | 'monetary' | 'legal_term' | 'case_reference';
  confidence: number;
  startOffset: number;
  endOffset: number;
}

export interface DocumentVersion {
  id: string;
  version: number;
  uploadedBy: string;
  uploadedAt: string;
  size: number;
  changeNote: string;
}

export interface DocumentMetadata {
  author: string;
  createdDate: string;
  modifiedDate: string;
  language: string;
  encoding: string;
  wordCount: number;
  charCount: number;
  pageCount: number;
}

// ── Dashboard ────────────────────────────────────────────────────────────────

export interface MetricCardData {
  id: string;
  label: string;
  value: string | number;
  change: number;
  changeLabel: string;
  trend: 'up' | 'down' | 'neutral';
  icon: string;
  color: 'indigo' | 'violet' | 'cyan' | 'emerald' | 'amber' | 'rose' | 'blue' | 'orange' | 'teal';
}

export interface AIInsight {
  id: string;
  title: string;
  description: string;
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info';
  agentName: string;
  caseId: string;
  caseName: string;
  createdAt: string;
  isRead: boolean;
}

export interface RiskDistribution {
  level: RiskLevel;
  count: number;
  percentage: number;
}

export interface EvidenceSummary {
  type: string;
  count: number;
  trend: number;
}

// ── Timeline ─────────────────────────────────────────────────────────────────

export type TimelineEventCategory =
  | 'email' | 'contract' | 'hearing' | 'payment'
  | 'legal_event' | 'evidence' | 'incident'
  | 'ocr_timestamp' | 'ai_decision'
  | 'document' | 'case' | 'review' | 'ai_finding' | 'upload' | 'status_change';

export type TimelinePriority = 'critical' | 'high' | 'medium' | 'low';

export interface TimelineEvent {
  id: string;
  title: string;
  description: string;
  type: TimelineEventCategory;
  timestamp: string;
  endTimestamp?: string;
  caseId: string;
  caseName: string;
  userId: string;
  userName: string;
  entityNames?: string[];
  documentId?: string;
  documentName?: string;
  evidenceId?: string;
  priority?: TimelinePriority;
  lawyerName?: string;
  amount?: number;
  metadata: Record<string, string>;
}

export type TimelineZoomLevel = 'day' | 'week' | 'month' | 'year';

export interface TimelineFilters {
  caseId: string | null;
  dateRange: { start: string; end: string } | null;
  entityName: string | null;
  evidenceId: string | null;
  documentId: string | null;
  lawyerName: string | null;
  priority: TimelinePriority | null;
  categories: TimelineEventCategory[];
}

// ── Knowledge Graph ──────────────────────────────────────────────────────────

export type GraphNodeType =
  | 'document' | 'person' | 'organization' | 'evidence'
  | 'email' | 'contract' | 'legal_issue' | 'event' | 'location'
  | 'case';

export type GraphEdgeType =
  | 'mentions' | 'ownership' | 'similarity' | 'communication'
  | 'citation' | 'references' | 'evidence_link' | 'relationship';

export interface GraphNode {
  id: string;
  label: string;
  type: GraphNodeType;
  metadata: Record<string, string>;
  caseId?: string;
  dateAdded?: string;
  importance?: number;
  description?: string;
  evidenceIds?: string[];
  documentIds?: string[];
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  label: string;
  type: GraphEdgeType;
  weight: number;
  metadata?: Record<string, string>;
}

export type GraphLayoutMode = 'force' | 'hierarchical' | 'radial' | 'dagre' | 'grid';
export type GraphExportFormat = 'png' | 'svg' | 'pdf';

export interface GraphFilters {
  nodeTypes: GraphNodeType[];
  edgeTypes: GraphEdgeType[];
  minWeight: number;
  caseId: string | null;
  searchQuery: string;
  dateRange: { start: string; end: string } | null;
}

export interface GraphCluster {
  id: string;
  label: string;
  nodeIds: string[];
  color: string;
}

export interface ShortestPathResult {
  path: string[];
  edges: string[];
  totalWeight: number;
}

// ── Document Viewer ──────────────────────────────────────────────────────────

export type AnnotationType = 'highlight' | 'note' | 'flag' | 'redaction';
export type AnnotationColor = 'yellow' | 'green' | 'blue' | 'red' | 'purple';

export interface DocumentAnnotation {
  id: string;
  pageNumber: number;
  type: AnnotationType;
  color: AnnotationColor;
  text: string;
  note?: string;
  createdBy: string;
  createdAt: string;
  startOffset: number;
  endOffset: number;
}

export interface OCROverlay {
  pageNumber: number;
  text: string;
  confidence: number;
  boundingBox: { x: number; y: number; width: number; height: number };
}

export interface PrivilegeMarker {
  id: string;
  pageNumber: number;
  type: 'attorney_client' | 'work_product' | 'joint_defense';
  description: string;
  startOffset: number;
  endOffset: number;
}

export interface InlineCitation {
  id: string;
  text: string;
  caseReference: string;
  pageNumber: number;
  confidence: number;
  verified: boolean;
}

export interface EvidenceReference {
  id: string;
  evidenceId: string;
  evidenceName: string;
  type: string;
  relevanceScore: number;
  pageNumber: number;
}

export interface ReasoningStep {
  id: string;
  step: number;
  title: string;
  description: string;
  confidence: number;
  evidenceIds: string[];
  conclusion: string;
}

export interface DocumentSummary {
  overview: string;
  keyFindings: string[];
  entities: Array<{ name: string; type: string; count: number }>;
  riskFactors: string[];
  recommendations: string[];
  confidence: number;
}

export interface DocumentRiskAssessment {
  overallRisk: RiskLevel;
  score: number;
  factors: Array<{
    name: string;
    level: RiskLevel;
    description: string;
    pageReferences: number[];
  }>;
  flaggedSections: Array<{
    pageNumber: number;
    text: string;
    reason: string;
  }>;
}

export type ViewerTab = 'summary' | 'risk' | 'reasoning' | 'entities' | 'annotations' | 'search' | 'discussion';

export interface VersionDiff {
  type: 'addition' | 'deletion' | 'modification';
  pageNumber: number;
  oldText?: string;
  newText?: string;
  description: string;
}

// ── Notifications ────────────────────────────────────────────────────────────

export type NotificationType = 'info' | 'success' | 'warning' | 'error' | 'ai_insight';

export interface Notification {
  id: string;
  title: string;
  message: string;
  type: NotificationType;
  isRead: boolean;
  createdAt: string;
  actionUrl?: string;
}

// ── Activity Feed ────────────────────────────────────────────────────────────

export interface ActivityItem {
  id: string;
  action: string;
  description: string;
  user: string;
  timestamp: string;
  icon: string;
  category: 'document' | 'case' | 'ai' | 'system' | 'review';
}

// ── Reports ──────────────────────────────────────────────────────────────────

export type ReportType = 'privilege_log' | 'review_summary' | 'risk_assessment' | 'timeline_report' | 'entity_report' | 'analytics';
export type ReportStatus = 'generating' | 'completed' | 'failed';

export interface Report {
  id: string;
  name: string;
  type: ReportType;
  status: ReportStatus;
  caseId: string;
  caseName: string;
  generatedAt: string;
  size: number;
  pageCount: number;
}

// ── Search ───────────────────────────────────────────────────────────────────

export interface SearchResult {
  id: string;
  documentId: string;
  documentName: string;
  caseId: string;
  caseName: string;
  snippet: string;
  relevanceScore: number;
  matchType: 'semantic' | 'keyword' | 'entity';
  highlights: string[];
  pageNumber: number;
}

// ── Analytics ────────────────────────────────────────────────────────────────

export interface AnalyticsDataPoint {
  date: string;
  value: number;
  label: string;
}

export interface ChartData {
  name: string;
  value: number;
  color?: string;
}

// ── Settings ─────────────────────────────────────────────────────────────────

export type ThemeMode = 'dark' | 'light' | 'system';

export interface UserSettings {
  theme: ThemeMode;
  notifications: {
    email: boolean;
    push: boolean;
    aiInsights: boolean;
    caseUpdates: boolean;
  };
  display: {
    compactMode: boolean;
    showAnimations: boolean;
    sidebarCollapsed: boolean;
  };
}

// ── Upload ───────────────────────────────────────────────────────────────────

export type UploadStatus = 'pending' | 'uploading' | 'processing' | 'done' | 'error';

export interface UploadFile {
  file: File;
  id: string;
  status: UploadStatus;
  progress: number;
  error?: string;
  documentId?: string;
}

// ── Navigation ───────────────────────────────────────────────────────────────

export interface NavItem {
  label: string;
  path: string;
  icon: string;
  badge?: string;
  badgeColor?: string;
}

export interface BreadcrumbItem {
  label: string;
  path?: string;
}

// ── Command Palette ──────────────────────────────────────────────────────────

export interface CommandItem {
  id: string;
  label: string;
  description?: string;
  icon: string;
  action: () => void;
  category: 'navigation' | 'action' | 'search' | 'recent';
  shortcut?: string;
}

// ── AI Agents ────────────────────────────────────────────────────────────────

export type CanonicalAgentId =
  | 'ocr'
  | 'ingestion'
  | 'classification'
  | 'chunking'
  | 'embedding'
  | 'retrieval'
  | 'entity_extraction'
  | 'relationship'
  | 'timeline'
  | 'summarization'
  | 'privilege'
  | 'risk'
  | 'pii'
  | 'review'
  | 'verification'
  | 'clustering'
  | 'report'
  | 'triage';

export type AgentId =
  | CanonicalAgentId
  | 'relationship_extraction'
  | 'knowledge_graph'
  | 'rag_retrieval'
  | 'legal_review'
  | 'citation_verification'
  | 'hallucination_detection'
  | 'evidence_linking'
  | 'similarity_search'
  | 'report_generation';

export type AgentStatus = 'idle' | 'queued' | 'running' | 'completed' | 'failed' | 'retrying';

export interface AgentInfo {
  id: AgentId;
  name: string;
  shortName: string;
  description: string;
  iconName: string;
  color: string;
  pipelineOrder: number;
  pipelineStage: PipelineStageName;
}

export type PipelineStageName =
  | 'case_creation'
  | 'document_upload'
  | 'ocr'
  | 'indexing'
  | 'retrieval'
  | 'legal_review'
  | 'graph_generation'
  | 'timeline_generation'
  | 'evidence_linking'
  | 'final_report';

export interface PipelineStage {
  id: PipelineStageName;
  label: string;
  order: number;
  agentIds: AgentId[];
  status: AgentStatus;
}

export interface AgentLogEntry {
  id: string;
  timestamp: string;
  level: 'info' | 'warn' | 'error' | 'debug';
  message: string;
  metadata?: Record<string, string | number>;
}

export interface AgentState {
  agentId: AgentId;
  status: AgentStatus;
  progress: number;
  processingTimeMs: number;
  confidenceScore: number;
  tokenUsage: number;
  queuePosition: number;
  lastExecutionTime: string | null;
  logs: AgentLogEntry[];
  errors: string[];
  retryCount: number;
  startedAt: string | null;
  completedAt: string | null;
}

export interface PipelineState {
  caseId: string;
  currentStage: PipelineStageName;
  stages: PipelineStage[];
  overallProgress: number;
  startedAt: string;
  estimatedCompletionAt: string | null;
}

// ── Dashboard Analytics ──────────────────────────────────────────────────────

export interface DashboardAnalytics {
  ocrAccuracy: AnalyticsMetric;
  aiConfidence: AnalyticsMetric;
  documentsProcessed: AnalyticsMetric;
  agentRuntime: AnalyticsMetric;
  processingTime: AnalyticsMetric;
  evidenceCount: AnalyticsMetric;
  similarCases: AnalyticsMetric;
  retrievalQuality: AnalyticsMetric;
  hallucinationRate: AnalyticsMetric;
  storageUsage: AnalyticsMetric;
  apiUsage: AnalyticsMetric;
}

export interface AnalyticsMetric {
  value: number | null;
  unit: string;
  trend: number;
  trendDirection: 'up' | 'down' | 'neutral';
  sparkline: number[];
  threshold?: number;
  max?: number;
  label: string;
}

// ── Preview Widgets ──────────────────────────────────────────────────────────

export type PreviewWidgetType =
  | 'knowledge_graph'
  | 'timeline'
  | 'ai_review'
  | 'risk_analysis'
  | 'search_results'
  | 'latest_reports'
  | 'linked_evidence'
  | 'active_investigations';

export interface PreviewWidgetData {
  type: PreviewWidgetType;
  title: string;
  route: string;
  iconName: string;
  color: string;
  itemCount: number;
  lastUpdated: string;
  status: 'loading' | 'empty' | 'error' | 'success';
  errorMessage?: string;
}

// ── WebSocket ────────────────────────────────────────────────────────────────

export type WebSocketMessageType =
  | 'agent_update'
  | 'pipeline_progress'
  | 'analytics_update'
  | 'log_entry'
  | 'error'
  | 'heartbeat';

export type WebSocketConnectionState =
  | 'connecting'
  | 'connected'
  | 'disconnected'
  | 'reconnecting';

export interface WebSocketMessage<T = unknown> {
  type: WebSocketMessageType;
  payload: T;
  timestamp: string;
  caseId?: string;
}

export interface AgentUpdatePayload {
  agentId: AgentId;
  status: AgentStatus;
  progress: number;
  processingTimeMs: number;
  confidenceScore: number;
  tokenUsage: number;
  queuePosition: number;
  logEntry?: AgentLogEntry;
  error?: string;
}

export interface PipelineProgressPayload {
  caseId: string;
  currentStage: PipelineStageName;
  overallProgress: number;
  stages: Array<{ id: PipelineStageName; status: AgentStatus }>;
}

export interface AnalyticsUpdatePayload {
  metric: keyof DashboardAnalytics;
  value: number;
  trend: number;
}
