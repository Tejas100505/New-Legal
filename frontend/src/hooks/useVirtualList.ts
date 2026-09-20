/**
 * useVirtualList — lightweight virtualized list hook for rendering
 * large datasets (agent logs, activity feeds) efficiently.
 *
 * Uses IntersectionObserver to only render visible items.
 */

import { useState, useRef, useCallback, useEffect, useMemo } from 'react';

interface UseVirtualListOptions {
  itemCount: number;
  itemHeight: number;
  overscan?: number;
  containerHeight?: number;
}

interface VirtualItem {
  index: number;
  offsetTop: number;
}

interface UseVirtualListReturn {
  virtualItems: VirtualItem[];
  totalHeight: number;
  containerRef: React.RefObject<HTMLDivElement | null>;
  scrollToIndex: (index: number) => void;
  scrollToBottom: () => void;
}

export function useVirtualList({
  itemCount,
  itemHeight,
  overscan = 5,
  containerHeight: fixedHeight,
}: UseVirtualListOptions): UseVirtualListReturn {
  const containerRef = useRef<HTMLDivElement>(null);
  const [scrollTop, setScrollTop] = useState(0);
  const [containerHeight, setContainerHeight] = useState(fixedHeight || 400);

  // Observe container size
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    if (fixedHeight) {
      setContainerHeight(fixedHeight);
      return;
    }

    const observer = new ResizeObserver(([entry]) => {
      if (entry) {
        setContainerHeight(entry.contentRect.height);
      }
    });
    observer.observe(container);
    return () => observer.disconnect();
  }, [fixedHeight]);

  // Handle scroll
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const handleScroll = () => {
      setScrollTop(container.scrollTop);
    };
    container.addEventListener('scroll', handleScroll, { passive: true });
    return () => container.removeEventListener('scroll', handleScroll);
  }, []);

  const totalHeight = itemCount * itemHeight;

  const virtualItems = useMemo(() => {
    const startIndex = Math.max(0, Math.floor(scrollTop / itemHeight) - overscan);
    const endIndex = Math.min(
      itemCount - 1,
      Math.ceil((scrollTop + containerHeight) / itemHeight) + overscan
    );

    const items: VirtualItem[] = [];
    for (let i = startIndex; i <= endIndex; i++) {
      items.push({
        index: i,
        offsetTop: i * itemHeight,
      });
    }
    return items;
  }, [scrollTop, containerHeight, itemCount, itemHeight, overscan]);

  const scrollToIndex = useCallback(
    (index: number) => {
      const container = containerRef.current;
      if (!container) return;
      container.scrollTop = index * itemHeight;
    },
    [itemHeight]
  );

  const scrollToBottom = useCallback(() => {
    const container = containerRef.current;
    if (!container) return;
    container.scrollTop = totalHeight;
  }, [totalHeight]);

  return { virtualItems, totalHeight, containerRef, scrollToIndex, scrollToBottom };
}
