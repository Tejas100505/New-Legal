import { useCaseWorkspace } from '../CaseWorkspaceContext';
import { ReportsPage } from '@/features/reports/pages/ReportsPage';

export function ReportTab() {
  const { caseId, caseData } = useCaseWorkspace();

  return <ReportsPage caseId={caseId} caseName={caseData?.name} />;
}
