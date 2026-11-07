const BASE_URL = "";

/**
 * Initializes a new customer session on the Prasadam kiosk backend.
 * Reuses the existing /session/start API contract.
 */
export async function startSession() {
  if (typeof window !== "undefined") {
    localStorage.setItem("session_start_perf", String(performance.now()));
  }

  const response = await fetch(`${BASE_URL}/session/start`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    const errorText = await response.text().catch(() => "Unknown server error");
    throw new Error(`Failed to start session (${response.status}): ${errorText}`);
  }

  const data = await response.json();
  if (!data || !data.session_id) {
    throw new Error("Invalid session response received from server");
  }

  return data;
}
