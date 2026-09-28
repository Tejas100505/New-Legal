import { useCaseWorkspace } from '../CaseWorkspaceContext';
import { useCaseAsk } from '../hooks/useCaseAsk';
import { CaseQAPanel } from '../components/CaseQAPanel';

export function AskTab() {
  const { caseId, caseData } = useCaseWorkspace();
  const qa = useCaseAsk({ caseId });

  return (
    <div className="space-y-6" id="case-ask-tab">
      <CaseQAPanel
        caseId={caseId}
        caseName={caseData?.name}
        input={qa.input}
        setInput={qa.setInput}
        history={qa.history}
        submitQuestion={qa.submitQuestion}
        clearHistory={qa.clearHistory}
        isSubmitting={qa.isSubmitting}
        cooldownRemaining={qa.cooldownRemaining}
      />
    </div>
  );
}
