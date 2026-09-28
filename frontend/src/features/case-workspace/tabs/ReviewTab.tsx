import { useCaseWorkspace } from '../CaseWorkspaceContext';
import { AIReviewPage } from '@/features/ai-review/pages/AIReviewPage';

export function ReviewTab() {
  const { caseId } = useCaseWorkspace();

  return <AIReviewPage caseId={caseId} />;
}
