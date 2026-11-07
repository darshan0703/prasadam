import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useCart } from "./CartContext";
import { useUIAction } from "./UIActionContext";
import {
  startListening,
  stopListening,
  speak,
  stopSpeaking,
  prepareVoiceInput,
  setInterruptionHandler,
  stopVoiceSession,
  isSpeaking,
} from "../services/voice/voiceService";
import { sendCustomerMessage } from "../services/voice/conversationService";
import { handleKioskResponse } from "../services/responseHandler";
import { unlockAudio } from "../services/voice/ttsService";

const VoiceConversationContext = createContext(null);

export function VoiceConversationProvider({ children }) {
  const navigate = useNavigate();
  const location = useLocation();
  const locationRef = useRef(location);
  locationRef.current = location;

  const { syncCart } = useCart();
  const { executeUIAction } = useUIAction();

  const [voiceEnabled, setVoiceEnabled] = useState(false);
  const [voiceState, setVoiceState] = useState("idle"); // idle, listening, processing, speaking, error
  const [lastTranscript, setLastTranscript] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [pendingAudio, setPendingAudio] = useState(null);
  const [languagePreference, setLanguagePreference] = useState("AUTO"); // AUTO, kn, en

  const voiceEnabledRef = useRef(false);
  const processingRef = useRef(false);
  const languagePreferenceRef = useRef("AUTO");

  const updateLanguagePreference = useCallback((pref) => {
    languagePreferenceRef.current = pref;
    setLanguagePreference(pref);
    console.log("VOICE LANGUAGE PREFERENCE UPDATED:", pref);
  }, []);

  // ====================================================
  // LISTEN FOR CUSTOMER
  // ====================================================
  const listenForCustomer = useCallback(() => {
    if (!voiceEnabledRef.current || processingRef.current) {
      return;
    }

    console.log("STARTING CUSTOMER LISTENING LOOP");
    setVoiceState("listening");
    setErrorMessage("");

    startListening(
      async (transcript) => {
        if (!voiceEnabledRef.current || processingRef.current) {
          return;
        }

        processingRef.current = true;
        setVoiceState("processing");
        setLastTranscript(transcript);

        try {
          const sessionId =
            (typeof window !== "undefined" &&
              (sessionStorage.getItem("session_id") ||
                localStorage.getItem("session_id"))) ||
            "default-kiosk-session";

          console.log("SENDING CUSTOMER MESSAGE:", transcript, "LANG:", languagePreferenceRef.current);
          const data = await sendCustomerMessage(
            transcript,
            sessionId,
            locationRef.current?.pathname || "home",
            languagePreferenceRef.current
          );

          if (!voiceEnabledRef.current) {
            processingRef.current = false;
            setVoiceState("idle");
            return;
          }

          console.log("VOICE BACKEND RESPONSE:", data);

          // 1. Authoritative Cart Synchronization
          if (data?.data?.cart && Array.isArray(data.data.cart)) {
            syncCart(data.data);
          } else if (data?.cart && Array.isArray(data.cart)) {
            syncCart(data);
          }

          // 2. Execute Navigation and UI Actions
          handleKioskResponse(data, {
            navigate,
            location: locationRef.current,
            executeUIAction,
          });

          // 3. Spoken Audio Response with loop return
          if (data?.message) {
            setVoiceState("speaking");
            speak(
              data.message,
              () => {
                processingRef.current = false;
                setVoiceState("idle");
                if (voiceEnabledRef.current) {
                  listenForCustomer();
                }
              },
              {
                onAutoplayBlocked: (audioObj) => {
                  setPendingAudio(audioObj);
                  processingRef.current = false;
                  setVoiceState("idle");
                },
              }
            );
          } else {
            processingRef.current = false;
            setVoiceState("idle");
            if (voiceEnabledRef.current) {
              listenForCustomer();
            }
          }
        } catch (error) {
          console.error("VOICE PROCESSING ERROR:", error);
          processingRef.current = false;
          setVoiceState("error");
          setErrorMessage("Could not process voice request.");

          if (voiceEnabledRef.current) {
            setTimeout(listenForCustomer, 1500);
          }
        }
      },
      (error) => {
        console.warn("Microphone listener error:", error);
        setVoiceState("error");
        setErrorMessage(error?.message || "Microphone input unavailable.");
      }
    );
  }, [navigate, syncCart, executeUIAction]);

  // ====================================================
  // BARGE-IN / INTERRUPTION
  // ====================================================
  useEffect(() => {
    setInterruptionHandler(() => {
      if (!voiceEnabledRef.current) return;
      console.log("CUSTOMER TOOK THE TURN (INTERRUPTION)");
      processingRef.current = false;
      listenForCustomer();
    });

    return () => {
      setInterruptionHandler(null);
    };
  }, [listenForCustomer]);

  // ====================================================
  // START VOICE CONVERSATION
  // ====================================================
  const startVoiceConversation = useCallback(async () => {
    if (voiceEnabledRef.current) return;

    // Reset language mode to AUTO for fresh session
    languagePreferenceRef.current = "AUTO";
    setLanguagePreference("AUTO");

    unlockAudio();
    voiceEnabledRef.current = true;
    processingRef.current = false;
    setVoiceEnabled(true);
    setVoiceState("idle");
    setErrorMessage("");

    console.log("VOICE INTERFACE ENABLED");

    try {
      await prepareVoiceInput();

      if (!voiceEnabledRef.current) return;

      // Initial Greeting
      setVoiceState("speaking");
      speak(
        "Namaskara! Welcome to The Atom Prasadam. What would you like to enjoy today?",
        () => {
          setVoiceState("idle");
          if (voiceEnabledRef.current) {
            listenForCustomer();
          }
        },
        {
          onAutoplayBlocked: (audioObj) => {
            setPendingAudio(audioObj);
            setVoiceState("idle");
            listenForCustomer();
          },
        }
      );
    } catch (error) {
      console.warn("Could not start ambient voice input:", error);
      // Still enable voice interface so typed/modal remains active
      setVoiceState("error");
      setErrorMessage(error?.message || "Microphone access needed for voice.");
    }
  }, [listenForCustomer]);

  // ====================================================
  // STOP VOICE CONVERSATION
  // ====================================================
  const stopVoiceConversation = useCallback(() => {
    voiceEnabledRef.current = false;
    processingRef.current = false;
    stopSpeaking();
    stopVoiceSession();
    setVoiceEnabled(false);
    setVoiceState("idle");
    console.log("VOICE INTERFACE DISABLED");
  }, []);

  // ====================================================
  // DISPATCH TYPED / MODAL MESSAGE
  // ====================================================
  const dispatchMessage = useCallback(
    async (text) => {
      if (!text || !text.trim()) return;

      unlockAudio();
      processingRef.current = true;
      setVoiceState("processing");
      setLastTranscript(text.trim());

      try {
        const sessionId =
          (typeof window !== "undefined" &&
            (sessionStorage.getItem("session_id") ||
              localStorage.getItem("session_id"))) ||
          "default-kiosk-session";

        const data = await sendCustomerMessage(
          text.trim(),
          sessionId,
          locationRef.current?.pathname || "home",
          languagePreferenceRef.current
        );

        if (data?.data?.cart && Array.isArray(data.data.cart)) {
          syncCart(data.data);
        } else if (data?.cart && Array.isArray(data.cart)) {
          syncCart(data);
        }

        handleKioskResponse(data, {
          navigate,
          location: locationRef.current,
          executeUIAction,
        });

        if (data?.message) {
          setVoiceState("speaking");
          speak(
            data.message,
            () => {
              processingRef.current = false;
              setVoiceState("idle");
              if (voiceEnabledRef.current) {
                listenForCustomer();
              }
            },
            {
              onAutoplayBlocked: (audioObj) => {
                setPendingAudio(audioObj);
                processingRef.current = false;
                setVoiceState("idle");
              },
            }
          );
        } else {
          processingRef.current = false;
          setVoiceState("idle");
        }
      } catch (err) {
        console.error("Dispatch message error:", err);
        processingRef.current = false;
        setVoiceState("error");
        setErrorMessage("Could not connect to conversation service.");
      }
    },
    [navigate, syncCart, executeUIAction, listenForCustomer]
  );

  return (
    <VoiceConversationContext.Provider
      value={{
        voiceActive: voiceEnabled,
        voiceState,
        lastTranscript,
        errorMessage,
        pendingAudio,
        languagePreference,
        setLanguagePreference: updateLanguagePreference,
        startVoiceConversation,
        stopVoiceConversation,
        listenForCustomer,
        dispatchMessage,
      }}
    >
      {children}
    </VoiceConversationContext.Provider>
  );
}

const defaultVoiceContext = {
  voiceActive: false,
  voiceState: "idle",
  lastTranscript: "",
  errorMessage: "",
  pendingAudio: null,
  languagePreference: "AUTO",
  setLanguagePreference: () => {},
  startVoiceConversation: () => {},
  stopVoiceConversation: () => {},
  listenForCustomer: () => {},
  dispatchMessage: () => {},
};

export function useVoiceConversation() {
  const context = useContext(VoiceConversationContext);
  return context || defaultVoiceContext;
}
