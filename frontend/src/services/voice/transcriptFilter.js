/**
 * Transcript filtering utilities for speech recognition.
 * Prevents non-speech artifacts, hallucinations, and empty audio from polluting the dialogue loop.
 */

export function isNonSpeechTranscript(transcript) {
  const normalized = (transcript || "")
    .trim()
    .toLowerCase()
    .replace(/\s+/g, " ");

  if (!normalized) return true;

  // Bracketed audio descriptions: [applause], (music), etc.
  if (/^(\(|\[).*(\)|\])$/.test(normalized)) {
    return true;
  }

  // Hallucination keywords common in tiny whisper on silent audio
  const hallucinationPatterns = [
    "thank you for watching",
    "thanks for watching",
    "please subscribe",
    "subtitles by",
    "transcription by",
    "translated by",
    "[blank_audio]",
    "you",
  ];

  if (hallucinationPatterns.includes(normalized)) {
    return true;
  }

  const soundEventPattern =
    /^(?:a |an )?(?:bell|beep|beeping|alarm|siren|engine|car|horn|music|background noise|noise|indistinct chatter|chatter|laughter|laughing|coughing|cough|sneezing|breathing|applause|clapping|clicking|typing|door|phone|ringing|ringtone)(?: .*)?$/;

  return soundEventPattern.test(normalized);
}

export function isValidTranscript(transcript) {
  if (!transcript) return false;
  const normalized = transcript.trim();
  if (!normalized || normalized.length < 2) return false;
  if (normalized === "[BLANK_AUDIO]") return false;
  return !isNonSpeechTranscript(normalized);
}
