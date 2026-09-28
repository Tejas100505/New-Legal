import { useCaseWorkspace } from '../CaseWorkspaceContext';
import { DocumentsPage } from '@/features/documents/pages/DocumentsPage';

export function EvidenceTab() {
  const { caseId } = useCaseWorkspace();

  return <DocumentsPage caseId={caseId} />;
}
