import { create } from 'zustand';

export interface CollaborationComment {
  id: string;
  documentId: string;
  userId: string;
  userName: string;
  text: string;
  createdAt: string;
  mentions: string[];
}

export interface ReviewRequest {
  id: string;
  documentId: string;
  requesterId: string;
  reviewerId: string;
  status: 'pending' | 'accepted' | 'completed';
  createdAt: string;
}

export interface CaseAssignment {
  caseId: string;
  userId: string;
  role: 'owner' | 'reviewer' | 'viewer';
}

interface CollaborationState {
  // Data
  comments: CollaborationComment[];
  reviewRequests: ReviewRequest[];
  assignments: CaseAssignment[];
  unreadNotificationsCount: number;
  
  // Real-time Presence
  activeUsers: Record<string, 'online' | 'away' | 'offline'>;
  typingUsers: Record<string, boolean>; // documentId -> isTyping
  
  // Actions
  addComment: (comment: Omit<CollaborationComment, 'id' | 'createdAt'>) => void;
  createReviewRequest: (req: Omit<ReviewRequest, 'id' | 'createdAt' | 'status'>) => void;
  updateReviewRequestStatus: (id: string, status: ReviewRequest['status']) => void;
  assignCase: (assignment: CaseAssignment) => void;
  setTyping: (documentId: string, isTyping: boolean) => void;
  
  // WebSocket Event Handlers (Isolated for future real WS connection)
  _handleWSEvent: (event: any) => void;
}

export const useCollaborationStore = create<CollaborationState>((set) => ({
  comments: [],
  reviewRequests: [
    { id: 'req_1', documentId: 'doc_002', requesterId: 'usr_002', reviewerId: 'usr_001', status: 'pending', createdAt: new Date().toISOString() }
  ],
  assignments: [
    { caseId: 'case_001', userId: 'usr_001', role: 'owner' }
  ],
  unreadNotificationsCount: 3,
  
  activeUsers: {
    'usr_001': 'online',
    'usr_002': 'away',
    'usr_003': 'offline',
  },
  typingUsers: {},
  
  addComment: (comment) => set((state) => {
    const newComment = { ...comment, id: `com_${Math.random()}`, createdAt: new Date().toISOString() };
    
    // If mentioned, increment notification (mock logic)
    const mentionCount = comment.mentions.length;
    
    return {
      comments: [...state.comments, newComment],
      unreadNotificationsCount: state.unreadNotificationsCount + mentionCount
    };
  }),
  
  createReviewRequest: (req) => set((state) => ({
    reviewRequests: [
      ...state.reviewRequests,
      { ...req, id: `req_${Math.random()}`, status: 'pending', createdAt: new Date().toISOString() }
    ],
    unreadNotificationsCount: state.unreadNotificationsCount + 1
  })),
  
  updateReviewRequestStatus: (id, status) => set((state) => ({
    reviewRequests: state.reviewRequests.map(r => r.id === id ? { ...r, status } : r)
  })),
  
  assignCase: (assignment) => set((state) => ({
    assignments: [...state.assignments.filter(a => !(a.caseId === assignment.caseId && a.userId === assignment.userId)), assignment]
  })),
  
  setTyping: (documentId, isTyping) => set((state) => ({
    typingUsers: { ...state.typingUsers, [documentId]: isTyping }
  })),

  // Isolated WS Handler
  _handleWSEvent: (event: any) => set((state) => {
    switch (event.type) {
      case 'PRESENCE_UPDATE':
        return { activeUsers: { ...state.activeUsers, [event.userId]: event.status } };
      case 'TYPING_INDICATOR':
        return { typingUsers: { ...state.typingUsers, [event.documentId]: event.isTyping } };
      case 'NEW_NOTIFICATION':
        return { unreadNotificationsCount: state.unreadNotificationsCount + 1 };
      default:
        return state;
    }
  })
}));

// NOTE: Real-time collaboration presence is handled via WebSocket events
// from the backend. No client-side simulation needed.
