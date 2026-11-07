/**
 * Microphone Service for Prasadam Kiosk
 * Manages media stream lifecycle, microphone permissions, and clean track releases.
 */

let activeStream = null;

export async function requestMicrophone() {
  if (activeStream && activeStream.active) {
    return activeStream;
  }

  if (typeof navigator === "undefined" || !navigator.mediaDevices?.getUserMedia) {
    throw new Error("Microphone capture is not supported in this browser environment.");
  }

  try {
    activeStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    });
    return activeStream;
  } catch (error) {
    activeStream = null;
    if (error.name === "NotAllowedError" || error.name === "PermissionDeniedError") {
      throw new Error("Microphone permission was denied. Please allow microphone access in your browser or macOS System Settings.");
    }
    if (error.name === "NotFoundError" || error.name === "DevicesNotFoundError") {
      throw new Error("No microphone device was found on this computer.");
    }
    if (error.name === "NotReadableError" || error.name === "TrackStartError") {
      throw new Error("Microphone is currently in use by another application or blocked by OS permissions.");
    }
    if (error.name === "OverconstrainedError") {
      throw new Error("Microphone does not support the requested audio constraints.");
    }
    throw error;
  }
}

export function releaseMicrophone() {
  if (activeStream) {
    try {
      activeStream.getTracks().forEach((track) => track.stop());
    } catch (e) {
      console.warn("Error stopping microphone tracks:", e);
    }
    activeStream = null;
  }
}

export function isMicrophoneActive() {
  return activeStream !== null && activeStream.active;
}
