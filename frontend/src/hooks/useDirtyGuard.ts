import { useEffect } from "react";
import { useBlocker } from "react-router-dom";

interface UseDirtyGuardOptions {
  when: boolean;
  // Optional override of the browser-native confirmation text. Most
  // modern browsers ignore the custom string and render their own;
  // we still set it because some older UAs honour it.
  message?: string;
}

// Blocks in-app navigation while `when` is true (React Router's
// `useBlocker`) and shows the browser-native "Leave site?" dialog on
// tab close / reload / external navigation (via `beforeunload`).
//
// PRD §6.4 trigger list:
//   - breadcrumb clicks        → useBlocker
//   - top-bar refresh          → user-initiated reload → beforeunload
//   - Cancel button            → caller wraps it in `window.confirm`
//   - browser back/forward     → useBlocker
//   - closing the tab          → beforeunload
export function useDirtyGuard({
  when,
  message = "You have unsaved changes. Leave anyway?",
}: UseDirtyGuardOptions): void {
  // In-app navigation guard. `useBlocker` returns a stable object so
  // it's safe in the dependency array; we no-op when not dirty.
  const blocker = useBlocker(({ currentLocation, nextLocation }) => {
    if (!when) return false;
    return currentLocation.pathname !== nextLocation.pathname;
  });

  useEffect(() => {
    if (blocker.state === "blocked") {
      const ok = window.confirm(message);
      if (ok) blocker.proceed();
      else blocker.reset();
    }
  }, [blocker, message]);

  // Browser-native dialog for tab close / reload / external nav.
  useEffect(() => {
    if (!when) return;
    function handler(e: BeforeUnloadEvent) {
      e.preventDefault();
      // Modern browsers ignore the return value but require the
      // returnValue to be set; we still set it for legacy UAs.
      e.returnValue = message;
      return message;
    }
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [when, message]);
}
