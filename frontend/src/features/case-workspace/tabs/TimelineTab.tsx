import { useCaseWorkspace } from '../CaseWorkspaceContext';
import { TimelinePage } from '@/features/timeline/pages/TimelinePage';

export function TimelineTab() {
  const { caseId } = useCaseWorkspace();

  return <TimelinePage caseId={caseId} />;
}
