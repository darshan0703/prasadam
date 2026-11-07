import React from "react";
import {
  ArrowLeft,
  ShoppingBag,
  ShieldCheck,
  Mic,
  Sparkles,
  Volume2,
  AlertCircle,
} from "lucide-react";
import { useCart } from "../context/CartContext";
import { useVoiceConversation } from "../context/VoiceConversationProvider";
import { unlockAudio } from "../services/voice/ttsService";
import "./CompactHeader.css";

export function CompactHeader({
  onBack,
  backLabel = "Back",
  subtitle = "TOUCH MENU BROWSING",
  onOpenCart,
}) {
  const { itemCount } = useCart();
  const count = Number(itemCount) || 0;

  // Connect global voice conversation context
  let voiceActive = false;
  let voiceState = "idle";
  let lastTranscript = "";
  let errorMessage = "";
  let languagePreference = "AUTO";
  let setLanguagePreference = () => {};
  let startVoiceConversation = () => {};
  let stopVoiceConversation = () => {};
  let listenForCustomer = () => {};

  try {
    const voiceContext = useVoiceConversation();
    if (voiceContext) {
      voiceActive = voiceContext.voiceActive;
      voiceState = voiceContext.voiceState;
      lastTranscript = voiceContext.lastTranscript;
      errorMessage = voiceContext.errorMessage;
      languagePreference = voiceContext.languagePreference || "AUTO";
      setLanguagePreference = voiceContext.setLanguagePreference;
      startVoiceConversation = voiceContext.startVoiceConversation;
      stopVoiceConversation = voiceContext.stopVoiceConversation;
      listenForCustomer = voiceContext.listenForCustomer;
    }
  } catch (e) {
    // Graceful fallback if outside provider
  }

  const sessionId =
    (typeof window !== "undefined" &&
      (sessionStorage.getItem("session_id") || localStorage.getItem("session_id"))) ||
    "";

  const shortSession = sessionId ? `${sessionId.slice(0, 8)}...` : "";

  const handleVoiceButtonClick = () => {
    unlockAudio();
    if (!voiceActive) {
      startVoiceConversation();
    } else if (voiceState === "speaking") {
      stopVoiceConversation();
    } else if (voiceState === "idle" || voiceState === "error") {
      listenForCustomer();
    }
  };

  return (
    <>
      <header className="compact-header-container">
        {/* Left: Gold-outlined circular back button */}
        <div className="header-left-col">
          {onBack ? (
            <button
              type="button"
              className="header-back-button-circle"
              onClick={onBack}
              aria-label={backLabel}
              title={backLabel}
            >
              <div className="back-inner-ring">
                <ArrowLeft size={28} className="back-icon" />
              </div>
              <span className="sr-only">{backLabel}</span>
            </button>
          ) : (
            <div className="header-placeholder" />
          )}
        </div>

        {/* Center: Refined, compact restaurant identity */}
        <div className="header-center-col">
          <div className="header-brand-line">
            <span className="brand-kannada" lang="kn">ಪ್ರಸಾದಂ</span>
            <span className="brand-divider">✦</span>
            <span className="brand-english">PRASADAM</span>
          </div>
          <div className="header-sub-tag">
            <span className="sub-tag-line" />
            <span className="sub-tag-text">{subtitle}</span>
            <span className="sub-tag-line" />
          </div>
        </div>

        {/* Right: Language Selector, Voice Cashier, Pure Veg & Cart */}
        <div className="header-right-col">
          {/* Compact 3-way Language Selector */}
          <div className="header-lang-selector" role="group" aria-label="Language Mode">
            <button
              type="button"
              className={`lang-pill-btn ${languagePreference === "AUTO" ? "active" : ""}`}
              onClick={() => setLanguagePreference("AUTO")}
              title="Automatic Language Detection / ಸ್ವಯಂಚಾಲಿತ ಭಾಷೆ"
            >
              AUTO
            </button>
            <button
              type="button"
              className={`lang-pill-btn ${languagePreference === "kn" ? "active" : ""}`}
              onClick={() => setLanguagePreference("kn")}
              title="Strict Kannada / ಕನ್ನಡ ಮಾತ್ರ"
            >
              ಕನ್ನಡ
            </button>
            <button
              type="button"
              className={`lang-pill-btn ${languagePreference === "en" ? "active" : ""}`}
              onClick={() => setLanguagePreference("en")}
              title="Strict English / English Only"
            >
              ENG
            </button>
          </div>

          {/* Voice AI Cashier Trigger Button */}
          <button
            type="button"
            className={`header-voice-ai-button ${voiceActive ? "voice-active" : ""} ${voiceState}`}
            onClick={handleVoiceButtonClick}
            title="Prasadam AI Voice Cashier / ಧ್ವನಿ ಸಹಾಯಕ"
            aria-label="Prasadam AI Voice Cashier"
          >
            <div className="voice-btn-mic-ring">
              {voiceState === "processing" ? (
                <div className="voice-header-spinner" />
              ) : voiceState === "speaking" ? (
                <Volume2 size={17} className="voice-btn-mic-icon speaking-icon" />
              ) : (
                <Mic size={17} className="voice-btn-mic-icon" />
              )}
            </div>
            <span className="voice-btn-text">
              {voiceState === "listening"
                ? "Listening..."
                : voiceState === "processing"
                ? "Thinking..."
                : voiceState === "speaking"
                ? "Speaking..."
                : "Voice Cashier"}
            </span>
          </button>

          <div className="pure-veg-badge" title="100% Pure Vegetarian Heritage Preparation">
            <div className="veg-symbol-outer">
              <div className="veg-symbol-dot" />
            </div>
            <span className="veg-text">PURE VEG</span>
          </div>

          {count > 0 && (
            <div
              className="header-cart-indicator"
              onClick={onOpenCart}
              role="button"
              tabIndex={0}
              title={`${count} items in cart`}
            >
              <ShoppingBag size={22} className="header-cart-icon" />
              <span className="header-cart-badge">{count}</span>
            </div>
          )}

          {shortSession && (
            <div className="session-pill" title={`Active Kiosk Session: ${sessionId}`}>
              <ShieldCheck size={15} className="session-check-icon" />
              <span className="session-text">{shortSession}</span>
            </div>
          )}
        </div>
      </header>

      {/* Non-invasive Compact Voice Status Floating Pill */}
      {voiceActive &&
        (voiceState === "listening" ||
          voiceState === "processing" ||
          voiceState === "speaking" ||
          voiceState === "error") && (
          <div className={`compact-voice-pill-bar ${voiceState}`} role="status">
            {voiceState === "listening" && (
              <div className="voice-pill-content">
                <span className="pill-pulse-dot" />
                <span className="pill-message-text">
                  {lastTranscript
                    ? `Hearing you: "${lastTranscript}"`
                    : "Cashier listening... Speak naturally (English or ಕನ್ನಡ)"}
                </span>
              </div>
            )}

            {voiceState === "processing" && (
              <div className="voice-pill-content">
                <div className="pill-spinner" />
                <span className="pill-message-text">Consulting Prasadam Menu...</span>
              </div>
            )}

            {voiceState === "speaking" && (
              <div className="voice-pill-content">
                <div className="pill-soundwaves">
                  <span className="wave-bar wb-1" />
                  <span className="wave-bar wb-2" />
                  <span className="wave-bar wb-3" />
                  <span className="wave-bar wb-4" />
                </div>
                <span className="pill-message-text">Cashier speaking...</span>
              </div>
            )}

            {voiceState === "error" && (
              <div className="voice-pill-content error">
                <AlertCircle size={16} className="pill-error-icon" />
                <span className="pill-message-text">
                  {errorMessage || "Microphone input needed. Tap to retry."}
                </span>
                <button
                  type="button"
                  className="pill-retry-btn"
                  onClick={listenForCustomer}
                >
                  Retry
                </button>
              </div>
            )}
          </div>
        )}
    </>
  );
}

export default CompactHeader;

