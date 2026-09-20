/**
 * Keyboard shortcut hook — registers global key listeners.
 */

import { useEffect } from 'react';

type KeyCombo = {
  key: string;
  ctrlOrMeta?: boolean;
  shift?: boolean;
  alt?: boolean;
};

export function useKeyboardShortcut(
  combo: KeyCombo,
  callback: () => void,
  enabled: boolean = true
) {
  useEffect(() => {
    if (!enabled) return;

    function handleKeyDown(event: KeyboardEvent) {
      const { key, ctrlOrMeta, shift, alt } = combo;

      const metaMatch = ctrlOrMeta
        ? (event.ctrlKey || event.metaKey)
        : true;
      const shiftMatch = shift ? event.shiftKey : !event.shiftKey;
      const altMatch = alt ? event.altKey : !event.altKey;

      if (
        event.key.toLowerCase() === key.toLowerCase() &&
        metaMatch &&
        shiftMatch &&
        altMatch
      ) {
        event.preventDefault();
        callback();
      }
    }

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [combo, callback, enabled]);
}
