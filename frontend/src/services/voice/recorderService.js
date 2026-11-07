/**
 * Audio Recorder & Speech Recognition Service
 * Handles audio recording with MediaRecorder and Web Speech API transcriptions.
 */

import { requestMicrophone, releaseMicrophone } from "./microphoneService";

let mediaRecorder = null;
let audioChunks = [];
let activeRecognition = null;

export function getSupportedMimeType() {
  if (typeof MediaRecorder === "undefined") {
    return "";
  }
  const types = [
    "audio/webm;codecs=opus",
    "audio/webm",
    "audio/mp4",
    "audio/ogg;codecs=opus",
  ];
  for (const t of types) {
    if (MediaRecorder.isTypeSupported(t)) {
      return t;
    }
  }
  return "";
}

/**
 * Starts recording audio using MediaRecorder.
 * Optionally runs Web Speech API in parallel for live streaming transcription preview.
 */
export async function startRecording({ onLiveTranscript = null, onError = null, lang = "kn-IN" } = {}) {
  const stream = await requestMicrophone();
  audioChunks = [];

  const mimeType = getSupportedMimeType();
  const options = mimeType ? { mimeType } : undefined;

  try {
    mediaRecorder = new MediaRecorder(stream, options);
  } catch (err) {
    console.warn("Failed to create MediaRecorder with options, using default:", err);
    mediaRecorder = new MediaRecorder(stream);
  }

  mediaRecorder.ondataavailable = (event) => {
    if (event.data && event.data.size > 0) {
      audioChunks.push(event.data);
    }
  };

  if (onError) {
    mediaRecorder.onerror = onError;
  }

  mediaRecorder.start(250); // Slice every 250ms for reliable chunking

  // Optional Web Speech API for instant live feedback
  const SpeechRecognition =
    typeof window !== "undefined" &&
    (window.SpeechRecognition || window.webkitSpeechRecognition);

  if (SpeechRecognition && onLiveTranscript) {
    try {
      activeRecognition = new SpeechRecognition();
      activeRecognition.continuous = true;
      activeRecognition.interimResults = true;
      activeRecognition.lang = lang || "kn-IN";

      activeRecognition.onresult = (event) => {
        let fullTranscript = "";
        for (let i = 0; i < event.results.length; i++) {
          fullTranscript += event.results[i][0].transcript;
        }
        if (fullTranscript.trim()) {
          onLiveTranscript(fullTranscript.trim());
        }
      };

      activeRecognition.onerror = (e) => {
        console.warn("Web Speech recognition warning:", e.error);
      };

      activeRecognition.onend = () => {
        // If recording is still active and recognition closed (e.g. Chrome 5s idle pause),
        // we can safely restart it if mediaRecorder is still recording.
        if (mediaRecorder && mediaRecorder.state === "recording") {
          try {
            activeRecognition.start();
          } catch (err) {
            // Can throw if already started
          }
        }
      };

      activeRecognition.start();
    } catch (e) {
      console.warn("Could not start Web Speech Recognition:", e);
      activeRecognition = null;
    }
  }
}

/**
 * Stops recording and returns the recorded audio Blob.
 */
export function stopRecording() {
  return new Promise((resolve) => {
    if (activeRecognition) {
      try {
        activeRecognition.onend = null;
        activeRecognition.stop();
      } catch (e) {
        // Ignore
      }
      activeRecognition = null;
    }

    if (!mediaRecorder || mediaRecorder.state === "inactive") {
      releaseMicrophone();
      resolve(null);
      return;
    }

    mediaRecorder.onstop = () => {
      const mimeType = mediaRecorder.mimeType || "audio/webm";
      const blob = new Blob(audioChunks, { type: mimeType });
      audioChunks = [];
      releaseMicrophone();
      resolve({ blob, mimeType });
    };

    try {
      if (mediaRecorder.state === "recording") {
        mediaRecorder.requestData();
      }
    } catch (e) {
      // Ignore
    }

    mediaRecorder.stop();
  });
}

export function isRecording() {
  return mediaRecorder !== null && mediaRecorder.state === "recording";
}
