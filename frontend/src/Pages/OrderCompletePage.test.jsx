import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import OrderCompletePage from "./OrderCompletePage";

const mockNavigate = vi.fn();

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

const mockOrder = {
  order_id: "order_test_999",
  order_number: "#P-2048",
  items: [
    {
      id: "masala_dosa",
      name: "Crispy Masala Dosa",
      kannadaName: "ಗರಿಗರಿ ಮಸಾಲೆ ದೋಸೆ",
      price: 85,
      quantity: 2,
    },
    {
      id: "filter_coffee",
      name: "Degree Filter Coffee",
      kannadaName: "ಡಿಗ್ರಿ ಫಿಲ್ಟರ್ ಕಾಫಿ",
      price: 35,
      quantity: 1,
    },
  ],
  itemCount: 3,
  total: 205,
  payment_method: "demo_upi",
};

function renderOrderCompletePage(order = mockOrder, paymentMethod = "demo_upi") {
  return render(
    <MemoryRouter initialEntries={[{ pathname: "/order-complete", state: { order, paymentMethod } }]}>
      <Routes>
        <Route path="/order-complete" element={<OrderCompletePage />} />
      </Routes>
    </MemoryRouter>
  );
}

describe("Prasadam Order Complete & Confirmation Page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
    localStorage.clear();
  });

  it("renders verified order token number prominently", () => {
    renderOrderCompletePage();

    expect(screen.getByText("#P-2048")).toBeTruthy();
    expect(screen.getByText("ORDER TOKEN NUMBER")).toBeTruthy();
    expect(screen.getByText("ಆದೇಶ ಸಂಖ್ಯೆ")).toBeTruthy();
    expect(screen.getByText(/Order Placed Successfully!/i)).toBeTruthy();
  });

  it("renders itemized list of confirmed dishes, quantities, and line amounts", () => {
    renderOrderCompletePage();

    expect(screen.getByText("Crispy Masala Dosa")).toBeTruthy();
    expect(screen.getByText("2 ×")).toBeTruthy();
    expect(screen.getByText("₹ 170/-")).toBeTruthy();

    expect(screen.getByText("Degree Filter Coffee")).toBeTruthy();
    expect(screen.getByText("1 ×")).toBeTruthy();
    expect(screen.getByText("₹ 35/-")).toBeTruthy();
  });

  it("displays verified total paid amount and payment method badge", () => {
    renderOrderCompletePage();

    expect(screen.getByText("₹ 205/-")).toBeTruthy();
    expect(screen.getByText("UPI / QR Code (Demo)")).toBeTruthy();
  });

  it("provides manual 'Start New Order' button that clears kiosk tokens and navigates to '/'", () => {
    sessionStorage.setItem("session_id", "sess_active_123");
    sessionStorage.setItem("prasadam_kiosk_cart", "[{}]");

    renderOrderCompletePage();

    const newOrderBtn = screen.getByRole("button", { name: /Start a new order/i });
    fireEvent.click(newOrderBtn);

    expect(sessionStorage.getItem("session_id")).toBeNull();
    expect(sessionStorage.getItem("prasadam_kiosk_cart")).toBeNull();
    expect(mockNavigate).toHaveBeenCalledWith("/", { replace: true });
  });

  it("auto-navigates to '/' after countdown timer expires", () => {
    vi.useFakeTimers();

    renderOrderCompletePage();

    expect(screen.getByText(/25s/i)).toBeTruthy();

    // Fast-forward 25 seconds
    act(() => {
      vi.advanceTimersByTime(25000);
    });

    expect(mockNavigate).toHaveBeenCalledWith("/", { replace: true });

    vi.useRealTimers();
  });
});
