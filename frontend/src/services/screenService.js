/**
 * Screen Synchronization Service for Prasadam Kiosk
 * Synchronizes the active screen, route, and section context with the backend.
 */

let screenSyncSeq = 0;
let latestAcceptedSeq = 0;
let lastKnownSessionId = null;
const inFlightRequests = new Map();

function checkSession(sessionId) {
  if (lastKnownSessionId !== null && sessionId !== lastKnownSessionId) {
    lastKnownSessionId = sessionId;
    screenSyncSeq = 0;
    latestAcceptedSeq = 0;
    inFlightRequests.clear();
  } else if (lastKnownSessionId === null) {
    lastKnownSessionId = sessionId;
  }
}

export function resetScreenSyncSeq() {
  screenSyncSeq = 0;
  latestAcceptedSeq = 0;
  inFlightRequests.clear();
}

export function syncScreen(screen, extra = {}) {
  const sessionId =
    (typeof window !== "undefined" &&
      (sessionStorage.getItem("session_id") || localStorage.getItem("session_id"))) ||
    "default";
  checkSession(sessionId);

  const seq = ++screenSyncSeq;
  const requestSessionId = sessionId;

  const syncPromise = (async () => {
    try {
      const response = await fetch("/screen", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          screen,
          seq,
          session_id: sessionId,
          client_timestamp: Date.now(),
          ...extra,
        }),
      });

      if (!response.ok) {
        throw new Error(`Screen sync failed: ${response.status}`);
      }

      const data = await response.json();
      if (data && data.success && !data.stale_ignored && requestSessionId === lastKnownSessionId) {
        latestAcceptedSeq = Math.max(latestAcceptedSeq, seq);
      }
      return data;
    } catch (error) {
      console.warn("Screen sync notice:", error.message);
      return null;
    } finally {
      inFlightRequests.delete(seq);
    }
  })();

  syncPromise.catch(() => {});
  syncPromise.seq = seq;
  inFlightRequests.set(seq, { sessionId: requestSessionId, promise: syncPromise });
  return syncPromise;
}
