/**
 * SkipLink — skip-to-content link for keyboard navigation.
 * Visually hidden until focused via Tab key.
 */

export function SkipLink() {
  return (
    <a
      href="#main-content"
      className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-[9999] focus:px-4 focus:py-2 focus:rounded-lg focus:bg-indigo-600 focus:text-white focus:text-sm focus:font-semibold focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:shadow-lg"
    >
      Skip to main content
    </a>
  );
}
