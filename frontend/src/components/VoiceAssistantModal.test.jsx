import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { CartProvider } from "../context/CartContext";
import { UIActionProvider } from "../context/UIActionContext";
import { VoiceAssistantModal } from "./VoiceAssistantModal";
import * as convService from "../services/voice/conversationService";
import * as ttsService from "../services/voice/ttsService";

vi.mock("../services/voice/ttsService", () => ({
  speakText: vi.fn(),
  stopSpeaking: vi.fn(),
  isSpeaking: vi.fn(() => false),
  unlockAudio: vi.fn(),
}));

vi.mock("../services/voice/recorderService", () => ({
  startRecording: vi.fn(),
  stopRecording: vi.fn(),
  isRecording: vi.fn(() => false),
}));

describe("Prasadam VoiceAssistantModal Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderModal = (isOpen = true, onClose = vi.fn()) => {
    return render(
      <BrowserRouter>
        <CartProvider>
          <UIActionProvider>
            <VoiceAssistantModal isOpen={isOpen} onClose={onClose} />
          </UIActionProvider>
        </CartProvider>
      </BrowserRouter>
    );
  };

  it("does not render when isOpen is false", () => {
    renderModal(false);
    expect(screen.queryByLabelText(/Prasadam AI Voice Assistant/i)).toBeNull();
  });

  it("renders with header, mic button, input field, and suggestions when open", () => {
    renderModal(true);
    expect(screen.getByText(/Prasadam Voice AI/i)).toBeDefined();
    expect(screen.getByPlaceholderText(/What would you like to eat today/i)).toBeDefined();
    expect(screen.getByText(/Add Masala Dosa/i)).toBeDefined();
    expect(screen.getByText(/Filter Coffee/i)).toBeDefined();
  });

  it("calls onClose when the close button is clicked", () => {
    const handleClose = vi.fn();
    renderModal(true, handleClose);

    const closeBtn = screen.getByLabelText(/Close Assistant/i);
    fireEvent.click(closeBtn);
    expect(handleClose).toHaveBeenCalledTimes(1);
  });

  it("dispatches typed message and displays assistant response", async () => {
    vi.spyOn(convService, "sendCustomerMessage").mockResolvedValueOnce({
      message: "I have added Masala Dosa to your cart.",
      intent: "add_to_cart",
      screen: "menu_items",
      actions: [
        {
          type: "add_to_cart",
          payload: {
            id: "masala_dosa",
            name: "Masala Dosa",
            price: 60,
            quantity: 1,
          },
        },
      ],
      data: { cart_count: 1, cart_total: 60 },
    });

    renderModal(true);

    const input = screen.getByPlaceholderText(/What would you like to eat today/i);
    fireEvent.change(input, { target: { value: "add masala dosa" } });

    const submitBtn = screen.getByTitle(/Send Message/i);
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText(/I have added Masala Dosa to your cart/i)).toBeDefined();
      expect(screen.getByText(/Added to Tray Successfully/i)).toBeDefined();
    });
  });

  it("triggers suggestion chip on click and calls sendCustomerMessage", async () => {
    vi.spyOn(convService, "sendCustomerMessage").mockResolvedValueOnce({
      message: "All food served at The Atom Prasadam is 100% pure vegetarian.",
      intent: "dietary_query",
      screen: "categories",
      actions: [],
      data: {},
    });

    renderModal(true);

    const pureVegChip = screen.getByText(/Pure Veg Info/i);
    fireEvent.click(pureVegChip);

    await waitFor(() => {
      expect(convService.sendCustomerMessage).toHaveBeenCalledWith(
        "Is everything pure vegetarian?",
        expect.any(String)
      );
      expect(screen.getByText(/100% pure vegetarian/i)).toBeDefined();
    });
  });

  it("toggles audio mute button", () => {
    renderModal(true);

    const muteBtn = screen.getByTitle(/Mute Assistant Audio/i);
    expect(muteBtn).toBeDefined();

    fireEvent.click(muteBtn);
    expect(screen.getByTitle(/Unmute Assistant Audio/i)).toBeDefined();
  });

  it("displays clear error message and retry button when microphone access is denied", async () => {
    const recorderService = await import("../services/voice/recorderService");
    recorderService.startRecording.mockRejectedValueOnce(
      new Error("Microphone permission was denied. Please allow microphone access in your browser or macOS System Settings.")
    );

    renderModal(true);

    const micBtn = screen.getByTitle(/Tap to Speak/i);
    fireEvent.click(micBtn);

    await waitFor(() => {
      expect(screen.getByText(/Microphone permission was denied/i)).toBeDefined();
      expect(screen.getByText(/Try Speaking Again/i)).toBeDefined();
    });
  });
});
