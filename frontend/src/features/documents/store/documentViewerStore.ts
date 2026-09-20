import { create } from 'zustand';
import type { 
  DocumentAnnotation, ViewerTab
} from '@/types';

interface DocumentViewerState {
  currentTab: ViewerTab;
  showOcrOverlay: boolean;
  showEntityHighlights: boolean;
  showPrivilegeMarkers: boolean;
  isCompareMode: boolean;
  searchQuery: string;
  annotations: DocumentAnnotation[];
  selectedAnnotationId: string | null;

  // Actions
  setCurrentTab: (tab: ViewerTab) => void;
  toggleOcrOverlay: () => void;
  toggleEntityHighlights: () => void;
  togglePrivilegeMarkers: () => void;
  toggleCompareMode: () => void;
  setSearchQuery: (query: string) => void;
  addAnnotation: (ann: Omit<DocumentAnnotation, 'id' | 'createdAt' | 'createdBy'>) => void;
  deleteAnnotation: (id: string) => void;
  selectAnnotation: (id: string | null) => void;
}

export const useDocumentViewerStore = create<DocumentViewerState>((set) => ({
  currentTab: 'summary',
  showOcrOverlay: false,
  showEntityHighlights: true,
  showPrivilegeMarkers: true,
  isCompareMode: false,
  searchQuery: '',
  annotations: [],
  selectedAnnotationId: null,

  setCurrentTab: (currentTab) => set({ currentTab }),
  toggleOcrOverlay: () => set((state) => ({ showOcrOverlay: !state.showOcrOverlay })),
  toggleEntityHighlights: () => set((state) => ({ showEntityHighlights: !state.showEntityHighlights })),
  togglePrivilegeMarkers: () => set((state) => ({ showPrivilegeMarkers: !state.showPrivilegeMarkers })),
  toggleCompareMode: () => set((state) => ({ isCompareMode: !state.isCompareMode })),
  setSearchQuery: (searchQuery) => set({ searchQuery }),
  
  addAnnotation: (ann) => set((state) => {
    const newAnn: DocumentAnnotation = {
      ...ann,
      id: `ann_${Date.now()}`,
      createdAt: new Date().toISOString(),
      createdBy: 'Sarah Chen',
    };
    return { annotations: [...state.annotations, newAnn] };
  }),

  deleteAnnotation: (id) => set((state) => ({
    annotations: state.annotations.filter((a) => a.id !== id),
    selectedAnnotationId: state.selectedAnnotationId === id ? null : state.selectedAnnotationId,
  })),

  selectAnnotation: (id) => set({ selectedAnnotationId: id }),
}));
