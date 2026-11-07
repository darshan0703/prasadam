/**
 * Text-to-Speech (TTS) Service for Prasadam Kiosk
 * Handles backend WAV speech synthesis, HTML5 audio playback, and interruption controls.
 */

let currentAudio = null;
let currentAudioUrl = null;
let isSpeakingState = false;
let audioContext = null;
let isUnlocked = false;
let speechStartListeners = new Set();
let cooldownTimer = null;

export function registerSpeechStartListener(fn) {
  if (typeof fn === "function") {
    speechStartListeners.add(fn);
    return () => speechStartListeners.delete(fn);
  }
  return () => {};
}

function notifySpeechStart() {
  speechStartListeners.forEach((fn) => {
    try {
      fn();
    } catch (e) {
      console.warn("Error in speech start listener:", e);
    }
  });
}

/**
 * Unlocks audio playback within a direct user gesture (tap/click).
 * Essential for Chrome and Safari autoplay policies.
 */
export function unlockAudio() {
  if (typeof window === "undefined") return;

  try {
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (AudioCtx) {
      if (!audioContext) {
        audioContext = new AudioCtx();
      }
      if (audioContext.state === "suspended") {
        audioContext.resume();
      }
    }

    // Play a silent 1-sample WAV to prime HTML5 Audio element permissions
    const silentAudio = new Audio(
      "data:audio/wav;base64,UklGRigAAABXQVZFZm10IBIAAAABAAEARKwAAIhYAQACABAAAABkYXRhAgAAAAEA"
    );
    silentAudio.volume = 0.01;
    const playPromise = silentAudio.play();
    if (playPromise !== undefined) {
      playPromise
        .then(() => {
          isUnlocked = true;
        })
        .catch(() => {
          // Will be unlocked on subsequent user tap
        });
    }
  } catch (e) {
    console.warn("Audio unlock notice:", e);
  }
}

export function isSpeaking() {
  return isSpeakingState;
}

export function stopSpeaking() {
  if (cooldownTimer) {
    clearTimeout(cooldownTimer);
    cooldownTimer = null;
  }

  if (currentAudio) {
    currentAudio.onended = null;
    currentAudio.onerror = null;
    try {
      currentAudio.pause();
      currentAudio.currentTime = 0;
    } catch (e) {
      console.warn("Error pausing TTS audio:", e);
    }
    currentAudio = null;
  }

  if (currentAudioUrl) {
    try {
      URL.revokeObjectURL(currentAudioUrl);
    } catch (e) {
      // Ignore
    }
    currentAudioUrl = null;
  }

  if (typeof window !== "undefined" && window.speechSynthesis) {
    try {
      window.speechSynthesis.cancel();
    } catch (e) {
      // Ignore
    }
  }

  isSpeakingState = false;
}

export async function speakText(
  text,
  { onStart, onComplete, onError, onAutoplayBlocked } = {}
) {
  const clean = (text || "").trim();
  if (!clean) {
    onComplete?.();
    return;
  }

  // Interrupt any existing speech playback and notify listeners to pause microphone
  stopSpeaking();
  isSpeakingState = true;
  notifySpeechStart();

  const completeWithCooldown = (cb) => {
    // Keep isSpeakingState true during acoustic cooldown so microphone cannot capture room reverb / echo
    isSpeakingState = true;
    if (cooldownTimer) clearTimeout(cooldownTimer);
    cooldownTimer = setTimeout(() => {
      isSpeakingState = false;
      cb?.();
    }, 350);
  };

  try {
    const response = await fetch("/tts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: clean }),
    });

    if (!response.ok) {
      throw new Error(`TTS server responded with ${response.status}`);
    }

    const audioBlob = await response.blob();
    if (audioBlob.size === 0) {
      throw new Error("Received empty audio stream from TTS");
    }

    currentAudioUrl = URL.createObjectURL(audioBlob);
    const audio = new Audio();
    audio.preload = "auto";
    audio.src = currentAudioUrl;
    currentAudio = audio;

    audio.onplay = () => {
      onStart?.();
    };

    audio.onended = () => {
      if (currentAudio) {
        currentAudio = null;
      }
      completeWithCooldown(onComplete);
    };

    audio.onerror = (err) => {
      console.warn("TTS audio playback error, falling back to browser synthesis:", err);
      stopSpeaking();
      fallbackBrowserSpeech(clean, { onStart, onComplete, onError });
    };

    try {
      await audio.play();
    } catch (playErr) {
      console.warn("audio.play() was prevented by browser policy:", playErr);
      if (playErr.name === "NotAllowedError") {
        stopSpeaking();
        onAutoplayBlocked?.(audio);
        return;
      }
      // Attempt browser speech synthesis fallback
      fallbackBrowserSpeech(clean, { onStart, onComplete, onError });
    }
  } catch (err) {
    console.warn("Backend TTS failed, using browser speech fallback:", err);
    stopSpeaking();
    fallbackBrowserSpeech(clean, { onStart, onComplete, onError });
  }
}

function fallbackBrowserSpeech(text, { onStart, onComplete, onError } = {}) {
  if (typeof window === "undefined" || !window.speechSynthesis) {
    onError?.(new Error("Text-to-speech is not supported"));
    onComplete?.();
    return;
  }

  try {
    window.speechSynthesis.cancel();
    window.speechSynthesis.resume();

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.0;
    utterance.pitch = 1.0;

    const isKannada = /[\u0C80-\u0CFF]/.test(text);
    utterance.lang = isKannada ? "kn-IN" : "en-IN";

    // Pick best available voice (prefer kn-IN for Kannada, en-IN for English)
    const voices = window.speechSynthesis.getVoices();
    if (voices && voices.length > 0) {
      let preferredVoice = null;
      if (isKannada) {
        preferredVoice =
          voices.find((v) => v.lang === "kn-IN" || v.lang.startsWith("kn")) ||
          voices.find((v) => v.name.toLowerCase().includes("soumya") || v.name.toLowerCase().includes("kannada"));
      }
      if (!preferredVoice) {
        preferredVoice =
          voices.find((v) => v.lang === "en-IN") ||
          voices.find((v) => v.lang.startsWith("en") && (v.name.includes("Samantha") || v.name.includes("Karen") || v.name.includes("Natural") || v.name.includes("Google"))) ||
          voices.find((v) => v.lang.startsWith("en"));
      }
      if (preferredVoice) {
        utterance.voice = preferredVoice;
      }
    }

    utterance.onstart = () => {
      isSpeakingState = true;
      onStart?.();
    };

    utterance.onend = () => {
      isSpeakingState = false;
      onComplete?.();
    };

    utterance.onerror = (e) => {
      isSpeakingState = false;
      onError?.(e);
      onComplete?.();
    };

    window.speechSynthesis.speak(utterance);
  } catch (e) {
    isSpeakingState = false;
    onError?.(e);
    onComplete?.();
  }
}
