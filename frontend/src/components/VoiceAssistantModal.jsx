import React, { useState, useEffect, useRef, useCallback } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import {
  Mic,
  MicOff,
  Volume2,
  VolumeX,
  Send,
  X,
  Sparkles,
  ShoppingBag,
  CheckCircle,
  AlertCircle,
  RotateCcw,
} from "lucide-react";
import { useCart } from "../context/CartContext";
import { useUIAction } from "../context/UIActionContext";
import { handleKioskResponse } from "../services/responseHandler";
import {
  startRecording,
  stopRecording,
  isRecording,
} from "../services/voice/recorderService";
import {
  speakText,
  stopSpeaking,
  isSpeaking,
  unlockAudio,
} from "../services/voice/ttsService";
import {
  sendCustomerMessage,
  sendAudioForTranscription,
} from "../services/voice/conversationService";
import "./VoiceAssistantModal.css";

export function VoiceAssistantModal({ isOpen, onClose }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { syncCart, clearCart, cart } = useCart();
  const { executeUIAction } = useUIAction();

  const [state, setState] = useState("idle"); // idle, listening, processing, speaking, error
  const [transcript, setTranscript] = useState("");
  const [lastResponse, setLastResponse] = useState(null);
  const [errorMessage, setErrorMessage] = useState("");
  const [isAudioMuted, setIsAudioMuted] = useState(false);
  const [pendingAudio, setPendingAudio] = useState(null);
  const [language, setLanguage] = useState("en-IN"); // "en-IN" or "kn-IN"

  const inputRef = useRef(null);
  const silenceTimerRef = useRef(null);
  const overallTimerRef = useRef(null);
  const latestTranscriptRef = useRef("");
  const wasOpenRef = useRef(false);
  const isDispatchingRef = useRef(false);

  // Suggested quick prompts dynamically adapted to active language
  const suggestions =
    language === "kn-IN"
      ? [
          { label: "ದೋಸೆ ತೋರಿಸು", text: "ದೋಸೆ ತೋರಿಸು" },
          { label: "2 ಮಸಾಲೆ ದೋಸೆ ಕೊಡು", text: "ಎರಡು ಮಸಾಲೆ ದೋಸೆ ಕೊಡು" },
          { label: "ಇನ್ನೊಂದು ಸೇರಿಸು", text: "ಇನ್ನೂ ಒಂದು ಸೇರಿಸು" },
          { label: "ಸಿಹಿ ಪದಾರ್ಥಗಳು", text: "ಸಿಹಿ ಪದಾರ್ಥಗಳು ತೋರಿಸು" },
          { label: "ಪಾನೀಯಗಳು", text: "ಪಾನೀಯಗಳು ತೋರಿಸು" },
          { label: "ಕಾರ್ಟ್ ತೋರಿಸು", text: "ಕಾರ್ಟ್ ತೋರಿಸು" },
          { label: "ಹಿಂದಕ್ಕೆ ಹೋಗು", text: "ಹಿಂದಕ್ಕೆ ಹೋಗು" },
          { label: "ಆರ್ಡರ್ ಖಚಿತಪಡಿಸು", text: "ಆರ್ಡರ್ ಖಚಿತಪಡಿಸು" },
        ]
      : [
          { label: "Add Masala Dosa", text: "Add 2 Ghee Roast Masala Dosa" },
          { label: "Filter Coffee", text: "I want a Filter Coffee" },
          { label: "Show Sweets", text: "Show sweets" },
          { label: "Pure Veg Info", text: "Is everything pure vegetarian?" },
          { label: "Check Tray", text: "What is in my cart?" },
          { label: "Checkout", text: "Proceed to checkout" },
          { label: "South Indian Breakfast", text: "Show me South Indian breakfast" },
          { label: "Indian Breads", text: "I want Indian breads" },
        ];

  const clearTimers = useCallback(() => {
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = null;
    }
    if (overallTimerRef.current) {
      clearTimeout(overallTimerRef.current);
      overallTimerRef.current = null;
    }
  }, []);

  // Stop recording and speech ONLY when an open modal closes or unmounts, not on initial closed mount
  useEffect(() => {
    if (!isOpen) {
      clearTimers();
      if (wasOpenRef.current) {
        if (isRecording()) {
          stopRecording();
        }
        stopSpeaking();
        wasOpenRef.current = false;
      }
      setState("idle");
      setTranscript("");
      setPendingAudio(null);
    } else {
      wasOpenRef.current = true;
      unlockAudio();
    }
  }, [isOpen, clearTimers]);

  useEffect(() => {
    return () => {
      clearTimers();
      if (wasOpenRef.current) {
        stopSpeaking();
      }
    };
  }, [clearTimers]);

  const handleStartListening = async () => {
    unlockAudio();
    clearTimers();
    setPendingAudio(null);

    try {
      stopSpeaking();
      setErrorMessage("");
      setTranscript("");
      latestTranscriptRef.current = "";
      setState("listening");

      await startRecording({
        lang: language,
        onLiveTranscript: (liveText) => {
          setTranscript(liveText);
          latestTranscriptRef.current = liveText;

          // Restart silence timer on each spoken fragment
          if (silenceTimerRef.current) {
            clearTimeout(silenceTimerRef.current);
          }
          if (liveText && liveText.trim().length > 0) {
            silenceTimerRef.current = setTimeout(() => {
              handleStopListeningAndSubmit();
            }, 2600);
          }
        },
        onError: (err) => {
          console.error("Recording error:", err);
          clearTimers();
          setState("error");
          setErrorMessage(err.message || "Microphone error. Please try again or type below.");
        },
      });

      // Max recording ceiling (12 seconds)
      overallTimerRef.current = setTimeout(() => {
        handleStopListeningAndSubmit();
      }, 12000);
    } catch (err) {
      console.error("Start listening error:", err);
      clearTimers();
      setState("error");
      setErrorMessage(
        err.message || "Could not access microphone. Please check permissions or type below."
      );
    }
  };

  const handleStopListeningAndSubmit = async () => {
    clearTimers();
    if (!isRecording()) {
      if (state === "listening") {
        setState("idle");
      }
      return;
    }

    setState("processing");
    try {
      const recording = await stopRecording();

      let finalMessage = (latestTranscriptRef.current || transcript).trim();

      // If we have an audio blob and transcript was not captured by Web Speech
      if (recording?.blob && !finalMessage) {
        try {
          const sttResult = await sendAudioForTranscription(
            recording.blob,
            recording.mimeType
          );
          if (sttResult.success && sttResult.text) {
            finalMessage = sttResult.text.trim();
            setTranscript(finalMessage);
            latestTranscriptRef.current = finalMessage;
          }
        } catch (sttErr) {
          console.warn("Backend STT transcription issue:", sttErr);
        }
      }

      if (!finalMessage) {
        setState("idle");
        setErrorMessage("We could not hear your speech clearly. Please tap to speak again or choose a suggestion below.");
        return;
      }

      await dispatchMessage(finalMessage);
    } catch (err) {
      console.error("Error processing voice input:", err);
      setState("error");
      setErrorMessage("Sorry, could not process voice request.");
    }
  };

  const dispatchMessage = async (text) => {
    if (!text || !text.trim() || isDispatchingRef.current) return;
    isDispatchingRef.current = true;

    unlockAudio();
    clearTimers();
    if (isRecording()) {
      try {
        await stopRecording();
      } catch (e) {
        // Ignore
      }
    }

    setState("processing");
    setErrorMessage("");
    setPendingAudio(null);

    try {
      const sessionId =
        (typeof window !== "undefined" &&
          (sessionStorage.getItem("session_id") ||
            localStorage.getItem("session_id"))) ||
        "default-kiosk-session";

      const data = await sendCustomerMessage(text, sessionId);
      setLastResponse(data);

      // Authoritatively sync cart if returned by conversation backend
      if (data.data?.cart && Array.isArray(data.data.cart)) {
        syncCart(data.data);
      } else if (data.cart && Array.isArray(data.cart)) {
        syncCart(data);
      }

      // Execute returned UI actions and deterministic navigation
      handleKioskResponse(data, {
        navigate,
        location,
        executeUIAction,
      });

      // Voice output
      if (!isAudioMuted && data.message) {
        setState("speaking");
        speakText(data.message, {
          onComplete: () => {
            setState("idle");
          },
          onError: () => {
            setState("idle");
          },
          onAutoplayBlocked: (audioObj) => {
            setPendingAudio(audioObj);
            setState("idle");
          },
        });
      } else {
        setState("idle");
      }
    } catch (err) {
      console.error("Failed to dispatch message:", err);
      setState("error");
      setErrorMessage("Could not connect to conversation service.");
    } finally {
      isDispatchingRef.current = false;
    }
  };

  const handlePlayPendingAudio = async () => {
    if (!pendingAudio) return;
    try {
      setState("speaking");
      await pendingAudio.play();
      pendingAudio.onended = () => {
        setPendingAudio(null);
        setState("idle");
      };
    } catch (err) {
      console.warn("Manual audio play error:", err);
      setPendingAudio(null);
      setState("idle");
    }
  };

  const handleManualSubmit = (e) => {
    e?.preventDefault();
    if (transcript.trim()) {
      unlockAudio();
      stopSpeaking();
      dispatchMessage(transcript.trim());
    }
  };

  const handleSuggestionClick = (text) => {
    unlockAudio();
    setTranscript(text);
    latestTranscriptRef.current = text;
    stopSpeaking();
    dispatchMessage(text);
  };

  if (!isOpen) return null;

  return (
    <div className="voice-modal-backdrop" onClick={onClose} role="dialog" aria-modal="true">
      <div
        className="voice-modal-card"
        onClick={(e) => e.stopPropagation()}
        aria-label="Prasadam AI Voice Assistant"
      >
        {/* Header Bar */}
        <div className="voice-modal-header">
          <div className="voice-modal-brand">
            <div className="voice-assistant-avatar">
              <Sparkles size={22} className="avatar-sparkle" />
            </div>
            <div>
              <h2 className="voice-modal-title">Prasadam Voice AI</h2>
              <span className="voice-modal-sub" lang="kn">
                ಧ್ವನಿ ಸಹಾಯಕ ✦ Voice Ordering & Menu Guide
              </span>
            </div>
          </div>

          <div className="voice-header-actions">
            <button
              type="button"
              className="voice-lang-toggle"
              onClick={() => {
                const nextLang = language === "kn-IN" ? "en-IN" : "kn-IN";
                setLanguage(nextLang);
              }}
              title={language === "kn-IN" ? "Switch to English speech" : "ಕನ್ನಡಕ್ಕೆ ಬದಲಾಯಿಸಿ"}
              aria-label="Toggle language between Kannada and English"
            >
              <span className="lang-toggle-text">{language === "kn-IN" ? "ಕನ್ನಡ" : "ENG"}</span>
            </button>
            <button
              type="button"
              className={`voice-mute-toggle ${isAudioMuted ? "muted" : ""}`}
              onClick={() => {
                if (!isAudioMuted) stopSpeaking();
                setIsAudioMuted(!isAudioMuted);
              }}
              title={isAudioMuted ? "Unmute Assistant Audio" : "Mute Assistant Audio"}
            >
              {isAudioMuted ? <VolumeX size={20} /> : <Volume2 size={20} />}
            </button>
            <button
              type="button"
              className="voice-close-button"
              onClick={onClose}
              aria-label="Close Assistant"
            >
              <X size={22} />
            </button>
          </div>
        </div>

        {/* Central Visual Interaction Area */}
        <div className="voice-visual-stage">
          {state === "listening" && (
            <div className="listening-visual">
              <div className="pulse-ring ring-1" />
              <div className="pulse-ring ring-2" />
              <div className="pulse-ring ring-3" />
              <button
                type="button"
                className="mic-orb listening"
                onClick={handleStopListeningAndSubmit}
                title="Tap when finished speaking"
                aria-label="Finish speaking and submit"
              >
                <Mic size={42} className="mic-active-icon" />
                <span className="mic-orb-hint">TAP TO FINISH</span>
              </button>

              {transcript ? (
                <div className="listening-transcript-preview">
                  <span className="live-pill">HEARING YOU</span>
                  <p className="listening-transcript-text">"{transcript}"</p>
                </div>
              ) : (
                <div className="listening-guidance">
                  <p className="state-caption">Listening to you... Speak clearly</p>
                  <span className="state-caption-kannada" lang="kn">
                    ದಯವಿಟ್ಟು ಮಾತನಾಡಿ...
                  </span>
                </div>
              )}

              <button
                type="button"
                className="tap-to-finish-btn"
                onClick={handleStopListeningAndSubmit}
              >
                Tap When Done Speaking
              </button>
            </div>
          )}

          {state === "processing" && (
            <div className="processing-visual">
              <div className="mandala-spinner" />
              <p className="state-caption">Consulting Prasadam Menu...</p>
              <span className="state-caption-kannada" lang="kn">
                ಪರಿಶೀಲಿಸಲಾಗುತ್ತಿದೆ...
              </span>
            </div>
          )}

          {state === "speaking" && (
            <div className="speaking-visual">
              <div className="waveform-container">
                <span className="wave-bar bar-1" />
                <span className="wave-bar bar-2" />
                <span className="wave-bar bar-3" />
                <span className="wave-bar bar-4" />
                <span className="wave-bar bar-5" />
              </div>
              <p className="state-caption">Prasadam Assistant speaking...</p>
              <button
                type="button"
                className="stop-speaking-btn"
                onClick={() => {
                  stopSpeaking();
                  setState("idle");
                }}
              >
                Stop Audio
              </button>
            </div>
          )}

          {state === "idle" && (
            <div className="idle-visual">
              <button
                type="button"
                className="mic-orb idle"
                onClick={handleStartListening}
                title="Tap to Speak"
                aria-label="Tap to speak"
              >
                <Mic size={40} className="mic-idle-icon" />
                <span className="mic-orb-hint">TAP TO SPEAK</span>
              </button>
              <p className="state-caption">Tap microphone to speak or type below</p>
              <span className="state-caption-kannada" lang="kn">
                ಮಾತನಾಡಲು ಮೈಕ್ರೊಫೋನ್ ಟ್ಯಾಪ್ ಮಾಡಿ
              </span>
            </div>
          )}

          {state === "error" && (
            <div className="error-visual">
              <AlertCircle size={40} className="error-icon" />
              <p className="error-text">{errorMessage}</p>
              <div className="error-action-row">
                <button
                  type="button"
                  className="retry-btn"
                  onClick={handleStartListening}
                >
                  <RotateCcw size={16} />
                  Try Speaking Again
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Assistant Response Card */}
        {lastResponse && (
          <div className="assistant-response-bubble">
            <div className="bubble-header">
              <Sparkles size={16} className="bubble-sparkle" />
              <span className="bubble-sender">Prasadam Kiosk Response</span>
            </div>
            <p className="bubble-message">{lastResponse.message}</p>
            {lastResponse.intent === "add_to_cart" && (
              <div className="response-action-badge">
                <CheckCircle size={15} />
                <span>Added to Tray Successfully</span>
              </div>
            )}
            {pendingAudio && (
              <button
                type="button"
                className="autoplay-unblock-pill"
                onClick={handlePlayPendingAudio}
              >
                <Volume2 size={16} />
                <span>Tap to Hear Audio Response</span>
              </button>
            )}
          </div>
        )}

        {/* Live Transcript / Touch Input Bar */}
        <form className="voice-input-bar" onSubmit={handleManualSubmit}>
          <input
            ref={inputRef}
            type="text"
            className="voice-text-field"
            value={transcript}
            onChange={(e) => {
              setTranscript(e.target.value);
              latestTranscriptRef.current = e.target.value;
            }}
            placeholder={
              language === "kn-IN"
                ? "ಮಾತನಾಡಿ ಅಥವಾ ಟೈಪ್ ಮಾಡಿ (ಉದಾ: ದೋಸೆ ತೋರಿಸು, 2 ಮಸಾಲೆ ದೋಸೆ ಕೊಡು)..."
                : "What would you like to eat today? (e.g. Masala Dosa)"
            }
          />
          <button
            type="submit"
            className="voice-send-btn"
            disabled={!transcript.trim()}
            title="Send Message"
          >
            <Send size={18} />
          </button>
        </form>

        {/* Suggestion Chips */}
        <div className="voice-suggestions-row">
          <span className="suggestions-label">Try Asking:</span>
          <div className="chips-scroll">
            {suggestions.map((s, idx) => (
              <button
                key={idx}
                type="button"
                className="suggestion-chip"
                onClick={() => handleSuggestionClick(s.text)}
              >
                {s.label}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export default VoiceAssistantModal;
