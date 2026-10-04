import { useCaseWorkspace } from '../CaseWorkspaceContext';
import { DocumentsPage } from '@/features/documents/pages/DocumentsPage';

export function EvidenceTab() {
  const { caseId, caseData } = useCaseWorkspace();

  return <DocumentsPage caseId={caseId} caseName={caseData?.name} />;
}
