/**
 * useOptimisticUpdate — hook for optimistic UI updates.
 * Shows immediate state change before API confirms, with rollback on failure.
 */

import { useState, useCallback, useRef } from 'react';

interface UseOptimisticUpdateOptions<T> {
  onUpdate: (value: T) => Promise<T>;
  onRollback?: (previousValue: T) => void;
}

interface UseOptimisticUpdateReturn<T> {
  execute: (optimisticValue: T, previousValue: T) => Promise<void>;
  isPending: boolean;
  error: string | null;
  clearError: () => void;
}

export function useOptimisticUpdate<T>({
  onUpdate,
  onRollback,
}: UseOptimisticUpdateOptions<T>): UseOptimisticUpdateReturn<T> {
  const [isPending, setIsPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const previousRef = useRef<T | null>(null);

  const execute = useCallback(
    async (optimisticValue: T, previousValue: T) => {
      previousRef.current = previousValue;
      setIsPending(true);
      setError(null);

      try {
        await onUpdate(optimisticValue);
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Update failed';
        setError(message);
        // Rollback
        if (onRollback && previousRef.current !== null) {
          onRollback(previousRef.current);
        }
      } finally {
        setIsPending(false);
      }
    },
    [onUpdate, onRollback]
  );

  const clearError = useCallback(() => setError(null), []);

  return { execute, isPending, error, clearError };
}
