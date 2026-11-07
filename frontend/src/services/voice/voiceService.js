/**
 * Central Voice Service for Prasadam Kiosk
 * Coordinates microphone input, silence/speech detection, STT transcription,
 * and interruption-safe TTS speech playback.
 */

import { requestMicrophone, releaseMicrophone, isMicrophoneActive } from "./microphoneService";
import { startRecording, stopRecording, isRecording } from "./recorderService";
import { speakText, stopSpeaking, isSpeaking, unlockAudio, registerSpeechStartListener } from "./ttsService";
import { sendAudioForTranscription } from "./conversationService";
import { isValidTranscript } from "./transcriptFilter";

let stopping = false;
let speechTriggered = false;
let transcriptCallback = null;
let interruptionHandler = null;
let silenceTimer = null;
let activeLiveTranscript = "";

// Authoritatively stop microphone listening whenever TTS speech synthesis begins
registerSpeechStartListener(() => {
  stopListening();
});

export function setInterruptionHandler(handler) {
  interruptionHandler = handler;
}

export async function prepareVoiceInput() {
  unlockAudio();
  try {
    await requestMicrophone();
  } catch (error) {
    console.error("Microphone preparation error:", error);
    throw error;
  }
}

export async function startListening(callback, onError) {
  if (isRecording() || isSpeaking()) {
    return;
  }

  if (callback) {
    transcriptCallback = callback;
  }

  stopping = false;
  speechTriggered = false;
  activeLiveTranscript = "";

  try {
    await requestMicrophone();

    if (stopping || isSpeaking()) {
      return;
    }

    await startRecording({
      onLiveTranscript: (liveText) => {
        if (stopping || isSpeaking()) return;
        activeLiveTranscript = liveText;

        // Restart silence timeout on new words
        if (silenceTimer) clearTimeout(silenceTimer);
        if (liveText && liveText.trim().length > 0) {
          speechTriggered = true;
          silenceTimer = setTimeout(() => {
            handleSpeechEnd();
          }, 2200);
        }
      },
      onError: (err) => {
        console.warn("Recorder error:", err);
        if (silenceTimer) clearTimeout(silenceTimer);
        if (!stopping) {
          onError?.(err);
          setTimeout(restartListening, 500);
        }
      },
    });

  } catch (error) {
    console.error("Voice listener start error:", error);
    onError?.(error);
    if (!stopping) {
      setTimeout(restartListening, 800);
    }
  }
}

async function handleSpeechEnd() {
  if (stopping || !isRecording() || isSpeaking()) return;
  if (silenceTimer) clearTimeout(silenceTimer);

  try {
    const recording = await stopRecording();
    let transcript = activeLiveTranscript.trim();

    // If live transcript was empty but we have an audio blob, transcribe via backend Whisper
    if (!transcript && recording?.blob) {
      try {
        const result = await sendAudioForTranscription(recording.blob, recording.mimeType);
        if (result?.success && result?.text) {
          transcript = result.text.trim();
        }
      } catch (err) {
        console.warn("Backend Whisper transcription error:", err);
      }
    }

    if (!isValidTranscript(transcript)) {
      console.log("Ignoring non-speech or invalid transcript:", transcript);
      if (!stopping && !isSpeaking()) {
        restartListening();
      }
      return;
    }

    console.log("Valid customer transcript received:", transcript);
    transcriptCallback?.(transcript);

  } catch (err) {
    console.error("Error processing customer recording:", err);
    if (!stopping && !isSpeaking()) {
      restartListening();
    }
  }
}

function restartListening() {
  if (stopping || isSpeaking() || isRecording()) return;
  speechTriggered = false;
  activeLiveTranscript = "";

  setTimeout(() => {
    if (!stopping && !isSpeaking() && !isRecording()) {
      startListening(transcriptCallback);
    }
  }, 400);
}

export function stopListening() {
  speechTriggered = false;
  if (silenceTimer) clearTimeout(silenceTimer);
  stopRecording();
}

export function speak(text, onComplete, options = {}) {
  stopListening();
  speechTriggered = false;

  speakText(text, {
    onStart: () => {
      // Audio started
    },
    onComplete: () => {
      if (onComplete) onComplete();
    },
    onError: () => {
      if (onComplete) onComplete();
    },
    onAutoplayBlocked: options.onAutoplayBlocked,
  });
}

export function stopVoiceSession() {
  stopping = true;
  speechTriggered = false;
  if (silenceTimer) clearTimeout(silenceTimer);
  stopListening();
  stopSpeaking();
  releaseMicrophone();
  transcriptCallback = null;
  interruptionHandler = null;
}

export { stopSpeaking, isSpeaking, isMicrophoneActive };
