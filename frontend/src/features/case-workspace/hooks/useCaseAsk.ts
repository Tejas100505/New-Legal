import { useState, useEffect, useCallback, useRef } from 'react';
import { useMutation } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import api from '@/lib/api';

export interface CitationItem {
  chunk_id: string;
  document_id: string;
  filename: string;
  section?: string;
  page?: number | null;
  excerpt: string;
}

export interface GroundingDiagnostics {
  gate_a_passed: boolean;
  gate_b_passed: boolean;
  failure_reason?: string | null;
  details?: Record<string, any> | null;
}

export interface QuestionResponse {
  status: 'grounded' | 'insufficient_evidence' | 'suppressed';
  answer?: string | null;
  citations: CitationItem[];
  retrieved_evidence: CitationItem[];
  grounding_diagnostics: GroundingDiagnostics;
  model_version: string;
  ai_generated: boolean;
  llm_calls: number;
}

export interface QAExchange {
  id: string;
  question: string;
  timestamp: string;
  response?: QuestionResponse;
  error?: {
    status?: number;
    message: string;
  };
}

const MAX_HISTORY_LENGTH = 10;
const RATE_LIMIT_LOCKOUT_SECONDS = 10;

interface UseCaseAskProps {
  caseId: string;
}

export function useCaseAsk({ caseId }: UseCaseAskProps) {
  const [input, setInput] = useState('');
  const [history, setHistory] = useState<QAExchange[]>([]);
  const [cooldownRemaining, setCooldownRemaining] = useState<number>(0);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Rate-limit countdown timer
  useEffect(() => {
    if (cooldownRemaining > 0) {
      timerRef.current = setTimeout(() => {
        setCooldownRemaining((prev) => Math.max(0, prev - 1));
      }, 1000);
    }
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [cooldownRemaining]);

  const addExchange = useCallback((exchange: QAExchange) => {
    setHistory((prev) => [exchange, ...prev].slice(0, MAX_HISTORY_LENGTH));
  }, []);

  const askMutation = useMutation({
    mutationFn: async (questionText: string) => {
      const res = await api.post<QuestionResponse>(
        `/cases/${caseId}/ask`,
        { question: questionText },
        { timeout: 120000, suppressErrorToast: true } as any
      );
      return res.data;
    },
    onSuccess: (data, questionText) => {
      addExchange({
        id: crypto.randomUUID(),
        question: questionText,
        timestamp: new Date().toISOString(),
        response: data,
      });
      if (data.status === 'grounded') {
        toast.success('Grounded answer verified.');
      } else if (data.status === 'insufficient_evidence') {
        toast('Insufficient case evidence to answer reliably.', { icon: 'ℹ️' });
      } else if (data.status === 'suppressed') {
        toast('Answer withheld to prevent ungrounded claims.', { icon: '⚠️' });
      }
    },
    onError: (err: any, questionText) => {
      const status = err?.status || err?.response?.status;
      let userMessage = err?.message || 'Failed to analyze question against case evidence.';

      if (status === 429) {
        setCooldownRemaining(RATE_LIMIT_LOCKOUT_SECONDS);
        userMessage = 'Rate limit reached (10 questions per minute). Cooldown active.';
        toast.error(userMessage);
      } else if (status === 503) {
        userMessage = 'AI generation service temporarily unavailable due to quota exhaustion. Please try again later.';
        toast.error(userMessage);
      } else if (status === 403) {
        userMessage = 'Access denied: You do not have permission to query this case.';
        toast.error(userMessage);
      } else if (status === 422) {
        userMessage = 'Question cannot be empty or exceed 1000 characters.';
        toast.error(userMessage);
      } else {
        toast.error(userMessage);
      }

      addExchange({
        id: crypto.randomUUID(),
        question: questionText,
        timestamp: new Date().toISOString(),
        error: {
          status,
          message: userMessage,
        },
      });
    },
  });

  const submitQuestion = useCallback(
    async (customQuestion?: string): Promise<boolean> => {
      const q = (customQuestion !== undefined ? customQuestion : input).trim();
      if (!q) {
        toast.error('Please enter a question before submitting.');
        return false;
      }
      if (q.length > 1000) {
        toast.error('Question exceeds maximum limit of 1000 characters.');
        return false;
      }
      if (cooldownRemaining > 0) {
        toast.error(`Please wait ${cooldownRemaining}s before asking another question.`);
        return false;
      }
      if (askMutation.isPending) {
        return false;
      }

      setInput('');
      await askMutation.mutateAsync(q).catch(() => {});
      return true;
    },
    [input, cooldownRemaining, askMutation]
  );

  const clearHistory = useCallback(() => {
    setHistory([]);
  }, []);

  return {
    input,
    setInput,
    history,
    submitQuestion,
    clearHistory,
    isSubmitting: askMutation.isPending,
    cooldownRemaining,
    lastError: askMutation.error,
  };
}
