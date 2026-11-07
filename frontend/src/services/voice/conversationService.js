/**
 * Conversation API Client
 * Sends messages and audio to the unified backend conversation pipeline.
 */

export async function sendCustomerMessage(
  message,
  sessionId,
  screen = "home",
  languagePreference = "AUTO"
) {
  const sid =
    sessionId ||
    (typeof window !== "undefined" &&
      (sessionStorage.getItem("session_id") || localStorage.getItem("session_id"))) ||
    "default-kiosk-session";

  const response = await fetch("/message", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Session-ID": sid,
    },
    body: JSON.stringify({
      message,
      session_id: sid,
      screen,
      language_preference: languagePreference,
    }),
  });

  if (!response.ok) {
    throw new Error(`Conversation service error: HTTP ${response.status}`);
  }

  return response.json();
}

export async function sendAudioForTranscription(blob, mimeType = "audio/webm") {
  const formData = new FormData();
  let ext = "webm";
  if (mimeType.includes("mp4")) ext = "m4a";
  else if (mimeType.includes("ogg")) ext = "ogg";

  formData.append("file", blob, `audio.${ext}`);

  const response = await fetch("/stt", {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`STT request failed: HTTP ${response.status}`);
  }

  return response.json();
}
