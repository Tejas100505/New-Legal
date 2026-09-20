import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface SavedSearch {
  id: string;
  name: string;
  query: string;
  filters: {
    cases: string[];
    documentTypes: string[];
  };
  createdAt: string;
}

interface SearchHistoryState {
  recentQueries: string[];
  savedSearches: SavedSearch[];
  addRecentQuery: (query: string) => void;
  clearRecentQueries: () => void;
  saveSearch: (search: Omit<SavedSearch, 'id' | 'createdAt'>) => void;
  removeSavedSearch: (id: string) => void;
}

export const useSearchHistory = create<SearchHistoryState>()(
  persist(
    (set) => ({
      recentQueries: [],
      savedSearches: [
        {
          id: '1',
          name: 'High Risk Contracts',
          query: 'indemnification OR liability AND risk',
          filters: { cases: ['SEC Investigation'], documentTypes: ['Word contracts'] },
          createdAt: new Date().toISOString(),
        }
      ],
      addRecentQuery: (query) => set((state) => {
        if (!query.trim()) return state;
        const filtered = state.recentQueries.filter(q => q.toLowerCase() !== query.toLowerCase());
        return { recentQueries: [query, ...filtered].slice(0, 10) };
      }),
      clearRecentQueries: () => set({ recentQueries: [] }),
      saveSearch: (search) => set((state) => ({
        savedSearches: [
          {
            ...search,
            id: Math.random().toString(36).substring(7),
            createdAt: new Date().toISOString(),
          },
          ...state.savedSearches
        ]
      })),
      removeSavedSearch: (id) => set((state) => ({
        savedSearches: state.savedSearches.filter(s => s.id !== id)
      }))
    }),
    {
      name: 'search-history-storage',
    }
  )
);
