/**
 * LiveRegion — ARIA live region component for screen reader announcements.
 * Renders two invisible regions (polite + assertive) that screen readers monitor.
 */

export function LiveRegion() {
  return (
    <>
      <div
        id="aria-live-polite"
        role="status"
        aria-live="polite"
        aria-atomic="true"
        className="sr-only"
      />
      <div
        id="aria-live-assertive"
        role="alert"
        aria-live="assertive"
        aria-atomic="true"
        className="sr-only"
      />
    </>
  );
}
