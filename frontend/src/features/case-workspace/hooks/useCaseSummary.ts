import { useState, useEffect, useCallback, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import api from '@/lib/api';

export interface CaseSummaryMetrics {
  total_documents?: number;
  privileged_documents_count?: number;
  high_or_critical_risk_count?: number;
  flagged_documents_count?: number;
  timeline_span?: {
    total_events?: number;
    core_activity_start?: string;
    core_activity_end?: string;
    earliest_referenced_date?: string;
    latest_referenced_date?: string;
  };
}

export interface CaseSummarySections {
  executive?: string;
  legal?: string;
  notable_provisions_and_findings?: string;
  evidence?: string;
  key_people_and_relationships?: string;
}

export interface TopEntity {
  name: string;
  type: string;
  weighted_degree?: number;
  importance_score?: number;
  top_edges?: Array<{
    target: string;
    weight: number;
    relation: string;
    shared_docs: number;
  }>;
}

export interface KeyDate {
  date: string;
  title: string;
  confidence?: number;
  description?: string;
  source_doc_id?: string;
  source_document?: string;
}

export interface CaseSummaryJSON {
  case_id?: string;
  case_name?: string;
  generated_at?: string;
  metrics?: CaseSummaryMetrics;
  sections?: CaseSummarySections;
  top_entities?: TopEntity[];
  key_dates?: KeyDate[];
}

export interface CaseSummaryResponse {
  id: string;
  case_id: string;
  status: 'complete' | 'generating' | 'failed' | 'quota_paused' | string;
  source_doc_count: number;
  source_data_hash: string;
  model_version: string;
  generated_at: string | null;
  created_at: string | null;
  summary_json: CaseSummaryJSON | null;
  stale: boolean;
  generating: boolean;
  failed_last_generation?: boolean;
  last_generation_status?: 'failed' | 'quota_paused' | string;
}

const MAX_POLLS = 12; // 12 polls @ 5s = 60s
const RATE_LIMIT_COOLDOWN_SECONDS = 30;

export function useCaseSummary(caseId: string) {
  const queryClient = useQueryClient();
  const [pollCount, setPollCount] = useState<number>(0);
  const [isPollingTimedOut, setIsPollingTimedOut] = useState<boolean>(false);
  const [cooldownRemaining, setCooldownRemaining] = useState<number>(0);
  const [rateLimitError, setRateLimitError] = useState<string | null>(null);

  // Rate-limit countdown timer
  useEffect(() => {
    if (cooldownRemaining <= 0) return;
    const interval = setInterval(() => {
      setCooldownRemaining((prev) => {
        if (prev <= 1) {
          clearInterval(interval);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(interval);
  }, [cooldownRemaining]);

  const queryKey = ['case-summary', caseId];

  // TanStack Query for GET /cases/{case_id}/summary
  const {
    data: summary,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery<CaseSummaryResponse | null>({
    queryKey,
    queryFn: async () => {
      try {
        const res = await api.get(`/cases/${caseId}/summary`, {
          suppressErrorToast: true,
        } as any);
        return res.data;
      } catch (err: any) {
        if (err?.status === 404 || err?.response?.status === 404) {
          return null; // Clean empty state for no summary generated yet
        }
        throw err;
      }
    },
    enabled: Boolean(caseId),
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data?.generating && pollCount < MAX_POLLS && !isPollingTimedOut) {
        return 5000;
      }
      return false;
    },
    retry: (failureCount, err: any) => {
      if (err?.status === 404 || err?.response?.status === 404) return false;
      return failureCount < 2;
    },
  });

  // Track polling count and handle timeout
  const wasGeneratingRef = useRef(false);
  useEffect(() => {
    if (summary?.generating) {
      wasGeneratingRef.current = true;
      setPollCount((prev) => {
        const next = prev + 1;
        if (next >= MAX_POLLS) {
          setIsPollingTimedOut(true);
        }
        return next;
      });
    } else if (wasGeneratingRef.current && summary && !summary.generating) {
      // Finished generating
      wasGeneratingRef.current = false;
      setPollCount(0);
      setIsPollingTimedOut(false);
      toast.success('Case intelligence summary updated.');
    }
  }, [summary]);

  // Mutation for POST /cases/{case_id}/summary/generate
  const generateMutation = useMutation({
    mutationFn: async () => {
      setRateLimitError(null);
      const res = await api.post(`/cases/${caseId}/summary/generate`, null, {
        suppressErrorToast: true,
        timeout: 90000,
      } as any);
      return res.data;
    },
    onMutate: () => {
      setCooldownRemaining(RATE_LIMIT_COOLDOWN_SECONDS);
      setPollCount(0);
      setIsPollingTimedOut(false);
    },
    onSuccess: (newData) => {
      queryClient.setQueryData(queryKey, newData);
      queryClient.invalidateQueries({ queryKey });
    },
    onError: (err: any) => {
      const status = err?.status || err?.response?.status;
      if (status === 429) {
        const msg = 'Rate limit reached: Maximum 2 generation requests per minute. Please wait.';
        setRateLimitError(msg);
        toast.error(msg);
      } else if (status === 409) {
        toast('Summary generation is already in progress.', { icon: '⏳' });
        refetch();
      } else if (status === 503) {
        toast.error('AI API quota exhausted. Summary scheduled for resume when quota resets.');
        refetch();
      } else {
        toast.error(err?.message || 'Failed to initiate summary generation.');
      }
    },
  });

  const handleManualRefresh = useCallback(() => {
    setPollCount(0);
    setIsPollingTimedOut(false);
    refetch();
  }, [refetch]);

  const triggerGenerate = useCallback(() => {
    if (cooldownRemaining > 0 || generateMutation.isPending) return;
    generateMutation.mutate();
  }, [cooldownRemaining, generateMutation]);

  return {
    summary,
    isLoading,
    isError,
    error,
    isGenerating: Boolean(summary?.generating || generateMutation.isPending),
    isGeneratingMutation: generateMutation.isPending,
    isPollingTimedOut,
    cooldownRemaining,
    rateLimitError,
    generateSummary: triggerGenerate,
    manualRefresh: handleManualRefresh,
  };
}
