export const MOCK_DOCUMENT_TYPES = [
  { name: 'Contracts', value: 4500, color: '#3b82f6' },
  { name: 'Emails', value: 12000, color: '#8b5cf6' },
  { name: 'Financials', value: 3200, color: '#10b981' },
  { name: 'Depositions', value: 850, color: '#f59e0b' },
  { name: 'Other', value: 1100, color: '#64748b' },
];

export const MOCK_RISK_DISTRIBUTION = [
  { name: 'Critical', value: 120, color: '#ef4444' },
  { name: 'High', value: 850, color: '#f97316' },
  { name: 'Medium', value: 2400, color: '#eab308' },
  { name: 'Low', value: 8500, color: '#22c55e' },
];

export const MOCK_PRIVILEGE_RATE = [
  { date: 'Jan', total: 4000, privileged: 800 },
  { date: 'Feb', total: 5200, privileged: 1100 },
  { date: 'Mar', total: 4800, privileged: 950 },
  { date: 'Apr', total: 6100, privileged: 1400 },
  { date: 'May', total: 5900, privileged: 1250 },
  { date: 'Jun', total: 7200, privileged: 1800 },
];

export const MOCK_AI_CONFIDENCE_TREND = [
  { date: 'Week 1', confidence: 82 },
  { date: 'Week 2', confidence: 85 },
  { date: 'Week 3', confidence: 88 },
  { date: 'Week 4', confidence: 91 },
  { date: 'Week 5', confidence: 94 },
  { date: 'Week 6', confidence: 96 },
];

export const MOCK_PROCESSING_TIME = [
  { time: '08:00', ms: 1400 },
  { time: '10:00', ms: 1250 },
  { time: '12:00', ms: 1600 },
  { time: '14:00', ms: 1800 },
  { time: '16:00', ms: 1300 },
  { time: '18:00', ms: 1100 },
];

export const MOCK_AGENT_RUNTIME = [
  { agent: 'Discovery', runtime: 1240 },
  { agent: 'Redaction', runtime: 850 },
  { agent: 'Summarization', runtime: 2100 },
  { agent: 'Risk Analysis', runtime: 1650 },
  { agent: 'OCR Extraction', runtime: 3200 },
];

export const MOCK_SIMILARITY_CLUSTERS = [
  { x: 10, y: 20, z: 200, name: 'IP Infringement' },
  { x: 40, y: 50, z: 400, name: 'Breach of Contract' },
  { x: 80, y: 30, z: 150, name: 'Employment Disputes' },
  { x: 30, y: 80, z: 300, name: 'Tax Fraud' },
  { x: 60, y: 60, z: 250, name: 'Merger Docs' },
];

export const MOCK_EVIDENCE_COUNT = [
  { name: 'Mon', count: 12 },
  { name: 'Tue', count: 28 },
  { name: 'Wed', count: 15 },
  { name: 'Thu', count: 42 },
  { name: 'Fri', count: 35 },
];

export const MOCK_REVIEW_PROGRESS = [
  { name: 'Completed', value: 68, color: '#10b981' },
  { name: 'In Progress', value: 20, color: '#3b82f6' },
  { name: 'Not Started', value: 12, color: '#64748b' },
];

export const MOCK_USER_ACTIVITY = [
  { day: 'Mon', active: 45 },
  { day: 'Tue', active: 52 },
  { day: 'Wed', active: 48 },
  { day: 'Thu', active: 61 },
  { day: 'Fri', active: 59 },
  { day: 'Sat', active: 12 },
  { day: 'Sun', active: 8 },
];

export const MOCK_TOKEN_USAGE = [
  { date: 'Jan', input: 4500000, output: 1200000 },
  { date: 'Feb', input: 5200000, output: 1500000 },
  { date: 'Mar', input: 4800000, output: 1300000 },
  { date: 'Apr', input: 6100000, output: 1800000 },
  { date: 'May', input: 7500000, output: 2200000 },
];

export const MOCK_HALLUCINATION_RATE = [
  { version: 'v1.0', rate: 4.2 },
  { version: 'v1.1', rate: 3.8 },
  { version: 'v1.2', rate: 2.5 },
  { version: 'v1.3', rate: 1.8 },
  { version: 'v1.4', rate: 0.9 },
  { version: 'v2.0', rate: 0.4 },
];

export const MOCK_RETRIEVAL_PRECISION = [
  { date: 'Week 1', precision: 75, recall: 68 },
  { date: 'Week 2', precision: 80, recall: 72 },
  { date: 'Week 3', precision: 85, recall: 79 },
  { date: 'Week 4', precision: 89, recall: 84 },
  { date: 'Week 5', precision: 92, recall: 88 },
  { date: 'Week 6', precision: 95, recall: 91 },
];

export const MOCK_OCR_ACCURACY = [
  { name: 'High Quality', value: 98, color: '#10b981' },
  { name: 'Scanned Text', value: 92, color: '#3b82f6' },
  { name: 'Handwritten', value: 78, color: '#f59e0b' },
  { name: 'Degraded', value: 65, color: '#ef4444' },
];
