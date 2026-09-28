import { useCaseWorkspace } from '../CaseWorkspaceContext';
import { ReportsPage } from '@/features/reports/pages/ReportsPage';

export function ReportTab() {
  const { caseId } = useCaseWorkspace();

  return <ReportsPage caseId={caseId} />;
}
