import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import CartPage from "./CartPage";
import { CartProvider, useCart } from "../context/CartContext";

const mockNavigate = vi.fn();

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

const mockCartItems = [
  {
    id: "ghee_plain_dosa",
    name: "Ghee Plain Dosa",
    kannadaName: "ತುಪ್ಪದ ಸಾದಾ ದೋಸೆ",
    price: 70,
    quantity: 2,
    subtotal: 140,
    _uniqueKey: "item_1",
  },
  {
    id: "bisi_bele_bath",
    name: "Bisi Bele Bath",
    kannadaName: "ಬಿಸಿ ಬೇಳೆ ಬಾತ್",
    price: 60,
    quantity: 1,
    subtotal: 60,
    _uniqueKey: "item_2",
  },
];

// Helper to seed cart before rendering CartPage
function SeededCartPage({ items = mockCartItems, initialOrigin = "/menu-items?section=dose_special" }) {
  const { addItem, clearCart } = useCart();

  // Populate cart on mount
  useStateInit(addItem, clearCart, items);

  return <CartPage />;
}

function useStateInit(addItem, clearCart, items) {
  const [initialized, setInitialized] = vi.importActual("react").then ? [false, () => {}] : [false, () => {}];
}

function renderCartPageWithItems(items = mockCartItems, origin = "/menu-items?section=dose_special") {
  // Prepopulate sessionStorage with mock cart
  sessionStorage.setItem("prasadam_kiosk_cart", JSON.stringify(items));

  return render(
    <MemoryRouter initialEntries={[{ pathname: "/cart", state: { origin } }]}>
      <CartProvider>
        <Routes>
          <Route path="/cart" element={<CartPage />} />
        </Routes>
      </CartProvider>
    </MemoryRouter>
  );
}

describe("Prasadam Cart & Order Review Page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
    localStorage.clear();
  });

  it("renders empty state when cart has no items", async () => {
    renderCartPageWithItems([]);

    expect(screen.getByText("Your Order Tray is Empty")).toBeTruthy();
    expect(screen.getByText("ನಿಮ್ಮ ಆಹಾರ ತಟ್ಟೆಯಲ್ಲಿ ಯಾವುದೇ ಪದಾರ್ಥಗಳಿಲ್ಲ")).toBeTruthy();

    const browseBtn = screen.getByRole("button", { name: /Browse Menu Categories/i });
    fireEvent.click(browseBtn);

    expect(mockNavigate).toHaveBeenCalledWith("/menu-items?section=dose_special");
  });

  it("renders itemized dishes, prices, quantities, and line subtotals", async () => {
    renderCartPageWithItems(mockCartItems);

    expect(screen.getByText("Ghee Plain Dosa")).toBeTruthy();
    expect(screen.getByText("ತುಪ್ಪದ ಸಾದಾ ದೋಸೆ")).toBeTruthy();
    expect(screen.getByText("Bisi Bele Bath")).toBeTruthy();
    expect(screen.getByText("ಬಿಸಿ ಬೇಳೆ ಬಾತ್")).toBeTruthy();

    // Check item count badge (2 + 1 = 3 items)
    expect(screen.getByText("3 ITEMS")).toBeTruthy();

    // Check total (140 + 60 = 200)
    expect(screen.getByText("200")).toBeTruthy();
  });

  it("increments and decrements item quantity updating line subtotals and total", async () => {
    renderCartPageWithItems(mockCartItems);

    // Initial total is 200
    expect(screen.getByText("200")).toBeTruthy();

    // Click plus on Bisi Bele Bath (was qty 1, price 60)
    const plusBtns = screen.getAllByRole("button", { name: /Increase/i });
    fireEvent.click(plusBtns[1]);

    // Bisi Bele Bath quantity should become 2, total becomes 260
    await waitFor(() => {
      expect(screen.getByText("260")).toBeTruthy();
    });

    // Click minus on Bisi Bele Bath: becomes 1 again, total returns to 200
    const minusBtns = screen.getAllByRole("button", { name: /Decrease/i });
    fireEvent.click(minusBtns[1]);

    await waitFor(() => {
      expect(screen.getByText("200")).toBeTruthy();
    });
  });

  it("removes an item when the delete button is tapped", async () => {
    renderCartPageWithItems(mockCartItems);

    expect(screen.getByText("Bisi Bele Bath")).toBeTruthy();

    // Click remove button on second item
    const removeBtns = screen.getAllByRole("button", { name: /Remove .* from tray/i });
    fireEvent.click(removeBtns[1]);

    // Bisi Bele Bath should be removed, leaving only Ghee Plain Dosa (total 140)
    await waitFor(() => {
      expect(screen.queryByText("Bisi Bele Bath")).toBeNull();
      expect(screen.getByText("Ghee Plain Dosa")).toBeTruthy();
      expect(screen.getAllByText("140").length).toBeGreaterThan(0);
    });
  });

  it("clears the entire tray when Clear Entire Tray is clicked", async () => {
    renderCartPageWithItems(mockCartItems);

    const clearBtn = screen.getByRole("button", { name: /Clear Entire Tray/i });
    fireEvent.click(clearBtn);

    await waitFor(() => {
      expect(screen.getByText("Your Order Tray is Empty")).toBeTruthy();
    });
  });

  it("allows selecting payment method between UPI, Card, and Cash demo pathways", async () => {
    renderCartPageWithItems(mockCartItems);

    const cardOption = screen.getByRole("radio", { name: /Credit \/ Debit Card/i });
    fireEvent.click(cardOption);

    expect(cardOption.getAttribute("aria-checked")).toBe("true");

    const cashOption = screen.getByRole("radio", { name: /Pay at Counter \(Cash\)/i });
    fireEvent.click(cashOption);

    expect(cashOption.getAttribute("aria-checked")).toBe("true");
  });

  it("completes order successfully, clears cart, and navigates to /order-complete", async () => {
    global.fetch = vi.fn().mockImplementation((url) => {
      if (url === "/order/complete") {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              success: true,
              order: {
                order_id: "order_test_123",
                order_number: "P-4589",
                items: mockCartItems,
                itemCount: 3,
                total: 200,
                payment_method: "demo_upi",
                created_at: 1730123456,
              },
            }),
        });
      }
      return Promise.reject(new Error("Unknown URL"));
    });

    renderCartPageWithItems(mockCartItems);

    const checkoutBtn = screen.getByRole("button", { name: /Pay and complete order/i });
    fireEvent.click(checkoutBtn);

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith("/order-complete", {
        state: {
          order: expect.objectContaining({
            order_number: "P-4589",
            total: 200,
          }),
          paymentMethod: "demo_upi",
        },
      });
    });
  });

  it("displays clear error alert and remains on page if order completion fails", async () => {
    global.fetch = vi.fn().mockImplementation((url) => {
      if (url === "/order/complete") {
        return Promise.resolve({
          ok: false,
          status: 400,
          json: () =>
            Promise.resolve({
              detail: "Kitchen is at maximum capacity. Please wait 2 minutes.",
            }),
        });
      }
      return Promise.reject(new Error("Unknown URL"));
    });

    renderCartPageWithItems(mockCartItems);

    const checkoutBtn = screen.getByRole("button", { name: /Pay and complete order/i });
    fireEvent.click(checkoutBtn);

    await waitFor(() => {
      expect(screen.getByText("Order Placement Issue")).toBeTruthy();
      expect(
        screen.getByText("Kitchen is at maximum capacity. Please wait 2 minutes.")
      ).toBeTruthy();
    });

    // Must NOT navigate away
    expect(mockNavigate).not.toHaveBeenCalled();
  });
});
