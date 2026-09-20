/**
 * useCachedQuery — wrapper around React Query with intelligent caching,
 * background refresh, and stale-while-revalidate strategy.
 */

import { useQuery, type UseQueryOptions } from '@tanstack/react-query';

interface UseCachedQueryOptions<T> extends Omit<UseQueryOptions<T, Error, T, string[]>, 'queryKey' | 'queryFn'> {
  queryKey: string[];
  queryFn: () => Promise<T>;
  staleTime?: number;
  cacheTime?: number;
  refetchInterval?: number | false;
  refetchOnWindowFocus?: boolean;
  backgroundRefresh?: boolean;
}

export function useCachedQuery<T>({
  queryKey,
  queryFn,
  staleTime = 30000, // 30s stale time
  cacheTime = 5 * 60 * 1000, // 5 min cache
  refetchInterval = false,
  refetchOnWindowFocus = true,
  backgroundRefresh = true,
  ...rest
}: UseCachedQueryOptions<T>) {
  return useQuery<T, Error, T, string[]>({
    queryKey,
    queryFn,
    staleTime,
    gcTime: cacheTime,
    refetchInterval,
    refetchOnWindowFocus,
    refetchIntervalInBackground: backgroundRefresh,
    retry: 2,
    retryDelay: (attemptIndex) => Math.min(1000 * Math.pow(2, attemptIndex), 10000),
    ...rest,
  });
}

/**
 * Cache key factory for consistent cache key generation.
 */
export const cacheKeys = {
  agents: {
    all: () => ['agents'],
    status: (id: string) => ['agents', 'status', id],
    logs: (id: string) => ['agents', 'logs', id],
    pipeline: () => ['agents', 'pipeline'],
    analytics: () => ['agents', 'analytics'],
  },
  dashboard: {
    metrics: () => ['dashboard', 'metrics'],
    analytics: () => ['dashboard', 'analytics'],
    preview: (type: string) => ['dashboard', 'preview', type],
  },
} as const;
