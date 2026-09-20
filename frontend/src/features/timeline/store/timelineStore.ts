import { create } from 'zustand';
import type { TimelineFilters, TimelineZoomLevel, TimelineEvent } from '@/types';
import api from '@/lib/api';

interface TimelineState {
  events: TimelineEvent[];
  source: 'live' | 'mock_fallback';
  selectedEventId: string | null;
  filters: TimelineFilters;
  zoomLevel: TimelineZoomLevel;
  visibleRange: { start: string; end: string } | null;

  // Actions
  fetchTimeline: (caseId?: string | null) => Promise<void>;
  setEvents: (events: TimelineEvent[]) => void;
  selectEvent: (eventId: string | null) => void;
  setFilters: (filters: Partial<TimelineFilters>) => void;
  resetFilters: () => void;
  setZoomLevel: (zoom: TimelineZoomLevel) => void;
  setVisibleRange: (start: string, end: string) => void;
}

const initialFilters: TimelineFilters = {
  caseId: null,
  dateRange: null,
  entityName: null,
  evidenceId: null,
  documentId: null,
  lawyerName: null,
  priority: null,
  categories: [
    'email', 'contract', 'hearing', 'payment', 'legal_event', 
    'evidence', 'incident', 'ocr_timestamp', 'ai_decision',
    'document', 'case', 'review', 'ai_finding', 'upload', 'status_change'
  ],
};

export const useTimelineStore = create<TimelineState>((set) => ({
  events: [],
  source: 'live',
  selectedEventId: null,
  filters: initialFilters,
  zoomLevel: 'month',
  visibleRange: null,

  fetchTimeline: async (caseId = null) => {
    try {
      const url = caseId ? `/timeline?caseId=${caseId}` : '/timeline';
      const response = await api.get(url);
      const raw = Array.isArray(response.data) ? response.data : (response.data?.events || []);
      // Filter out any mock fallbacks from the backend if they get returned and normalize event fields
      const liveEvents = raw
        .filter((e: any) => e.source !== 'mock_fallback')
        .map((e: any) => ({
          ...e,
          id: String(e.id),
          title: e.title || 'Investigation Event',
          timestamp: e.timestamp || e.date || new Date().toISOString(),
          type: e.type || (e.filename?.includes('email') || e.filename?.endsWith('.txt') ? 'email' : 'document'),
          priority: e.priority || e.importance || 'high',
          description: e.description || e.filename || '',
          documentId: e.document_id || e.documentId,
          documentName: e.filename || e.documentName || undefined,
          source: 'live' as const,
        }));
      set({
        events: liveEvents,
        source: 'live'
      });
    } catch (err) {
      console.error('Failed to fetch timeline from backend:', err);
      set({
        events: [],
        source: 'live'
      });
    }
  },

  setEvents: (events) => set({ events }),
  selectEvent: (eventId) => set({ selectedEventId: eventId }),
  setFilters: (newFilters) => set((state) => ({ filters: { ...state.filters, ...newFilters } })),
  resetFilters: () => set({ filters: initialFilters }),
  setZoomLevel: (zoomLevel) => set({ zoomLevel }),
  setVisibleRange: (start, end) => set({ visibleRange: { start, end } }),
}));
