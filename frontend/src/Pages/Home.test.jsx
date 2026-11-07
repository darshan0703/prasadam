import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Home from "./Home";
import * as api from "../services/api";

const mockNavigate = vi.fn();

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

const mockClearCart = vi.fn();
vi.mock("../context/CartContext", () => ({
  useCart: () => ({
    clearCart: mockClearCart,
  }),
}));

describe("Prasadam Home Welcome Screen", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    sessionStorage.clear();
  });

  it("renders restaurant identity PRASADAM and Kannada name without errors", () => {
    render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>
    );

    expect(screen.getByText("PRASADAM")).toBeTruthy();
    expect(screen.getByText("ಪ್ರಸಾದಂ")).toBeTruthy();
    expect(screen.getByText("TOUCH TO START")).toBeTruthy();
  });

  it("clears cart, calls startSession, stores session_id, and navigates to /Categories on touch", async () => {
    const fakeSessionId = "test-session-uuid-1234";
    vi.spyOn(api, "startSession").mockResolvedValueOnce({
      success: true,
      session_id: fakeSessionId,
      message: "Welcome to Prasadam",
    });

    render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>
    );

    const startButton = screen.getByRole("button", { name: /touch to start/i });
    fireEvent.click(startButton);

    // Verify cart clearing was invoked
    expect(mockClearCart).toHaveBeenCalledTimes(1);

    // Verify loading state appears
    expect(screen.getByText("STARTING...")).toBeTruthy();

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith("/Categories");
    });

    // Verify session storage
    expect(localStorage.getItem("session_id")).toBe(fakeSessionId);
    expect(sessionStorage.getItem("session_id")).toBe(fakeSessionId);
  });

  it("prevents repeated activation while startup is in progress", async () => {
    let resolveSession;
    const sessionPromise = new Promise((resolve) => {
      resolveSession = resolve;
    });

    vi.spyOn(api, "startSession").mockReturnValue(sessionPromise);

    render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>
    );

    const startButton = screen.getByRole("button", { name: /touch to start/i });
    
    // First click
    fireEvent.click(startButton);
    expect(api.startSession).toHaveBeenCalledTimes(1);

    // Repeated clicks while in progress
    fireEvent.click(startButton);
    fireEvent.click(startButton);
    expect(api.startSession).toHaveBeenCalledTimes(1);

    // Resolve promise
    resolveSession({
      success: true,
      session_id: "uuid-single-call",
    });

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith("/Categories");
    });
  });

  it("displays clear error and stays on welcome page if session creation fails, allowing retry", async () => {
    vi.spyOn(api, "startSession").mockRejectedValueOnce(
      new Error("Server offline")
    );

    render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>
    );

    const startButton = screen.getByRole("button", { name: /touch to start/i });
    fireEvent.click(startButton);

    // Wait for failure state
    await waitFor(() => {
      expect(screen.getByText("Server offline")).toBeTruthy();
    });

    // Confirm navigation was NOT triggered
    expect(mockNavigate).not.toHaveBeenCalled();

    // Verify retry is possible
    vi.spyOn(api, "startSession").mockResolvedValueOnce({
      success: true,
      session_id: "retry-session-ok",
    });

    const retryButton = screen.getByRole("button", { name: /retry/i });
    fireEvent.click(retryButton);

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith("/Categories");
    });
    expect(localStorage.getItem("session_id")).toBe("retry-session-ok");
  });

  it("renders restaurant ambience video with correct kiosk autoplay attributes and poster", () => {
    const { container } = render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>
    );

    const videoEl = container.querySelector("video#hero-ambience-video");
    expect(videoEl).toBeTruthy();
    expect(videoEl.getAttribute("autoplay")).toBeDefined();
    expect(videoEl.muted).toBe(true);
    expect(videoEl.getAttribute("loop")).toBeDefined();
    expect(videoEl.getAttribute("playsinline")).toBeDefined();
    expect(videoEl.getAttribute("preload")).toBe("auto");
    expect(videoEl.getAttribute("poster")).toBeTruthy();

    const sourceEl = videoEl.querySelector("source");
    expect(sourceEl).toBeTruthy();
    expect(sourceEl.getAttribute("src")).toBe("/videos/restaurant_ambience.mp4");
    expect(sourceEl.getAttribute("type")).toBe("video/mp4");
  });

  it("gracefully falls back to static hero image if video encounters an error", async () => {
    const { container } = render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>
    );

    const videoEl = container.querySelector("video#hero-ambience-video");
    expect(videoEl).toBeTruthy();

    // Trigger video error
    fireEvent.error(videoEl);

    await waitFor(() => {
      expect(container.querySelector("video#hero-ambience-video")).toBeNull();
      const fallbackImg = container.querySelector(".hero-food-image");
      expect(fallbackImg).toBeTruthy();
      expect(fallbackImg.getAttribute("src")).toBeTruthy();
    });
  });
});
