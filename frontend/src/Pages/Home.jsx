import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { AlertCircle, RefreshCw, Loader2, Sparkles } from "lucide-react";
import { useCart } from "../context/CartContext";
import { useVoiceConversation } from "../context/VoiceConversationProvider";
import { startSession } from "../services/api";
import { syncScreen } from "../services/screenService";
import heroFoodImage from "../assets/images/prasadam_hero.jpg";
import "./Home.css";

export function Home() {
  const navigate = useNavigate();
  const { clearCart } = useCart();
  const { startVoiceConversation, stopVoiceConversation } = useVoiceConversation();

  const [starting, setStarting] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);
  const [videoError, setVideoError] = useState(false);

  useEffect(() => {
    syncScreen("home");
  }, []);

  const handleStart = async () => {
    // Prevent repeated activations while startup is in progress
    if (starting) return;

    setStarting(true);
    setErrorMessage(null);

    try {
      // Step 1: Immediately cancel any existing voice session and stop active audio playback
      if (typeof stopVoiceConversation === "function") {
        stopVoiceConversation();
      }

      // Step 2: Clear client-side cart
      clearCart();

      // Step 5: Call backend session start endpoint
      const session = await startSession();

      // Step 6: Verify valid session identifier
      if (!session || !session.session_id) {
        throw new Error("Invalid session response received from kiosk server.");
      }

      // Step 7: Store session identifier in localStorage and sessionStorage
      localStorage.setItem("session_id", session.session_id);
      sessionStorage.setItem("session_id", session.session_id);

      // Step 8: Initialize Voice Conversation & Greeting on touch
      try {
        startVoiceConversation();
      } catch (voiceErr) {
        console.warn("Could not start ambient voice:", voiceErr);
      }

      // Step 9: Navigate to Categories
      navigate("/Categories");
    } catch (err) {
      // Step 9: If session creation fails, remain on welcome page and allow retry
      console.error("Session initialization failed:", err);
      setErrorMessage(
        err.message || "Unable to connect to kiosk server. Please touch to retry."
      );
      setStarting(false);
    }
  };

  return (
    <div className="prasadam-home">
      {/* Background ambient luxury lighting effects */}
      <div className="home-ambient-glow top" />
      <div className="home-ambient-glow bottom" />

      {/* Decorative Traditional Border Frame */}
      <div className="heritage-border-corner top-left" />
      <div className="heritage-border-corner top-right" />
      <div className="heritage-border-corner bottom-left" />
      <div className="heritage-border-corner bottom-right" />

      {/* Main Content Layout */}
      <div className="home-inner-container">
        
        {/* Header / Restaurant Identity */}
        <header className="restaurant-identity-section">
          {/* Subtle gold heritage insignia */}
          <div className="insignia-emblem">
            <span className="insignia-line left" />
            <div className="insignia-symbol">
              <Sparkles size={18} className="gold-sparkle" />
            </div>
            <span className="insignia-line right" />
          </div>

          {/* Authentic Kannada Typography */}
          <h2 className="restaurant-name-kannada" lang="kn">
            ಪ್ರಸಾದಂ
          </h2>

          {/* Prominent English Identity */}
          <h1 className="restaurant-name-english">
            PRASADAM
          </h1>

          {/* Restrained Hotel / Dining Description */}
          <div className="identity-subtitle-badge">
            <span className="gold-ornament-bullet">✦</span>
            <span className="subtitle-text">FINE DINING & TRADITIONAL HOSPITALITY</span>
            <span className="gold-ornament-bullet">✦</span>
          </div>
        </header>

        {/* Hero Section */}
        <section className="hero-showcase-section">
          <div className="hero-frame-outer">
            <div className="hero-frame-inner">
              {!videoError ? (
                <video
                  id="hero-ambience-video"
                  className="hero-ambience-video"
                  autoPlay
                  muted
                  loop
                  playsInline
                  preload="auto"
                  poster={heroFoodImage}
                  onError={() => setVideoError(true)}
                  aria-label="Prasadam Restaurant Ambience"
                >
                  <source src="/videos/restaurant_ambience.mp4" type="video/mp4" />
                  <img
                    src={heroFoodImage}
                    alt="Prasadam Culinary Presentation"
                    className="hero-food-image fallback"
                  />
                </video>
              ) : (
                <img
                  src={heroFoodImage}
                  alt="Prasadam Culinary Presentation"
                  className="hero-food-image"
                />
              )}
              <div className="hero-vignette-overlay" />
            </div>
            
            {/* Elegant Corner Filigree Accents */}
            <div className="frame-corner c-tl" />
            <div className="frame-corner c-tr" />
            <div className="frame-corner c-bl" />
            <div className="frame-corner c-br" />
          </div>
        </section>

        {/* Sensory Welcome Note */}
        <section className="welcome-invitation-section">
          <p className="invitation-kannada" lang="kn">
            ಶುದ್ಧ ಸಾಂಪ್ರದಾಯಿಕ ರುಚಿಗಳ ಸ್ವಾಗತ
          </p>
          <p className="invitation-english">
            Experience timeless heritage culinary traditions prepared with reverence
          </p>
        </section>

        {/* Footer / Touch-to-Start Control Area */}
        <footer className="home-start-footer">
          {/* Error alert state with retry prompt */}
          {errorMessage && (
            <div className="start-error-banner" role="alert">
              <AlertCircle size={24} className="error-icon" />
              <div className="error-details">
                <p className="error-text">{errorMessage}</p>
                <span className="error-hint">Touch button below to retry connection</span>
              </div>
            </div>
          )}

          {/* Start Control Button */}
          <button
            type="button"
            id="touch-to-start-btn"
            className={`touch-start-button ${starting ? "loading" : ""} ${errorMessage ? "retry-mode" : ""}`}
            onClick={handleStart}
            disabled={starting}
            aria-busy={starting}
            aria-label={starting ? "Starting session" : errorMessage ? "Retry touch to start" : "Touch to start"}
          >
            <div className="button-gold-rim" />
            
            <div className="button-content">
              {starting ? (
                <>
                  <Loader2 size={36} className="button-spinner" />
                  <span className="button-text">STARTING...</span>
                </>
              ) : errorMessage ? (
                <>
                  <RefreshCw size={36} className="button-refresh-icon" />
                  <span className="button-text">RETRY TOUCH TO START</span>
                </>
              ) : (
                <>
                  <span className="button-ornament">✧</span>
                  <span className="button-text">TOUCH TO START</span>
                  <span className="button-ornament">✧</span>
                </>
              )}
            </div>

            <div className="button-subtext">
              {starting ? "PREPARING YOUR EXPERIENCE" : "BEGIN YOUR DINING JOURNEY"}
            </div>
          </button>
        </footer>

      </div>
    </div>
  );
}

export default Home;
