import { useCaseWorkspace } from '../CaseWorkspaceContext';
import { KnowledgeGraphPage } from '@/features/knowledge-graph/pages/KnowledgeGraphPage';

export function RelationshipsTab() {
  const { caseId } = useCaseWorkspace();

  return <KnowledgeGraphPage caseId={caseId} />;
}
