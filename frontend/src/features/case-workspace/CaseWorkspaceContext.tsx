import { createContext, useContext } from 'react';
import type { LegalCase } from '@/types';

export interface CaseWorkspaceContextType {
  caseData: LegalCase | null;
  isLoading: boolean;
  error: string | null;
  caseId: string;
  refetchCase: () => Promise<void>;
}

export const CaseWorkspaceContext = createContext<CaseWorkspaceContextType | null>(null);

export function useCaseWorkspace(): CaseWorkspaceContextType {
  const context = useContext(CaseWorkspaceContext);
  if (!context) {
    throw new Error('useCaseWorkspace must be used within a CaseWorkspaceLayout');
  }
  return context;
}
