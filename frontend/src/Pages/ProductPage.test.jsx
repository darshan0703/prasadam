import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import ProductPage from "./ProductPage";
import { CartProvider } from "../context/CartContext";

const mockNavigate = vi.fn();

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

const mockItemWithAllFields = {
  id: "masala_dose",
  name: "Crispy Masala Dose",
  kannadaName: "ಗರಿಗರಿ ಮಸಾಲೆ ದೋಸೆ",
  price: 95,
  description: "Golden rice crepe smeared with red chutney and spiced potato palya",
  image: "/menu-items/masala_dose.jpg",
  is_veg: true,
  available: true,
  category: "Dose Special",
};

const mockItemMinimal = {
  id: "ghee_plain_dosa",
  name: "Ghee Plain Dosa",
  kannadaName: null,
  price: 70,
  description: null,
  image: null,
  is_veg: true,
  available: true,
  category: "Dose Special",
};

const mockUnavailableItem = {
  id: "coffee_tea",
  name: "Coffee / Tea",
  kannadaName: null,
  price: 15,
  description: null,
  image: "/menu-items/coffee_tea.jpg",
  is_veg: true,
  available: false,
  category: "Hot Beverages",
};

function renderProductPage({
  initialEntries = ["/product"],
  initialState = null,
} = {}) {
  return render(
    <MemoryRouter
      initialEntries={
        initialState
          ? [{ pathname: "/product", state: initialState }]
          : initialEntries
      }
    >
      <CartProvider>
        <Routes>
          <Route path="/product" element={<ProductPage />} />
        </Routes>
      </CartProvider>
    </MemoryRouter>
  );
}

describe("Prasadam Product Details Page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
    localStorage.clear();
  });

  it("renders verified product details including name, price, image, and veg indicator", async () => {
    renderProductPage({
      initialState: {
        item: mockItemWithAllFields,
        origin: "/menu-items?section=dose_special",
        sectionId: "dose_special",
      },
    });

    expect(screen.getByText("Crispy Masala Dose")).toBeTruthy();
    expect(screen.getByText("ಗರಿಗರಿ ಮಸಾಲೆ ದೋಸೆ")).toBeTruthy();
    expect(screen.getByText("95")).toBeTruthy();
    expect(screen.getByText("100% PURE VEG")).toBeTruthy();
    expect(
      screen.getByText(
        "Golden rice crepe smeared with red chutney and spiced potato palya"
      )
    ).toBeTruthy();

    const img = screen.getByAltText("Crispy Masala Dose");
    expect(img.getAttribute("src")).toBe("/menu-items/masala_dose.jpg");
  });

  it("safely handles missing optional fields (no Kannada name, no description, no image) without crashing", async () => {
    renderProductPage({
      initialState: {
        item: mockItemMinimal,
        origin: "/menu-items?section=dose_special",
        sectionId: "dose_special",
      },
    });

    expect(screen.getByText("Ghee Plain Dosa")).toBeTruthy();
    expect(screen.getByText("70")).toBeTruthy();
    // Kannada title should not be rendered
    expect(screen.queryByRole("heading", { level: 2, lang: "kn" })).toBeNull();
    // Description block heading should not be present
    expect(screen.queryByText("About This Item")).toBeNull();
  });

  it("loads product data via API when accessed directly with search query param", async () => {
    global.fetch = vi.fn().mockImplementation((url) => {
      if (url.includes("/menu/items/masala_dose")) {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              success: true,
              item: mockItemWithAllFields,
            }),
        });
      }
      return Promise.reject(new Error("Unknown URL"));
    });

    renderProductPage({
      initialEntries: ["/product?id=masala_dose&section=dose_special"],
    });

    await waitFor(() => {
      expect(screen.getByText("Crispy Masala Dose")).toBeTruthy();
      expect(screen.getByText("95")).toBeTruthy();
    });
  });

  it("enforces minimum quantity of 1 and prevents decrement below 1", async () => {
    renderProductPage({
      initialState: {
        item: mockItemWithAllFields,
        origin: "/menu-items?section=dose_special",
      },
    });

    const minusBtn = screen.getByRole("button", { name: /Decrease quantity/i });
    const quantityDisplay = screen.getByText("1");
    expect(quantityDisplay).toBeTruthy();
    expect(minusBtn.hasAttribute("disabled")).toBe(true);

    // Clicking disabled minus does not change quantity
    fireEvent.click(minusBtn);
    expect(screen.getByText("1")).toBeTruthy();
  });

  it("increments quantity and updates computed subtotal on Add to Cart button", async () => {
    renderProductPage({
      initialState: {
        item: mockItemWithAllFields,
        origin: "/menu-items?section=dose_special",
      },
    });

    // Initial total is 1 * 95 = 95
    expect(screen.getByText(/Add to Cart • ₹ 95\/-/i)).toBeTruthy();

    const plusBtn = screen.getByRole("button", { name: /Increase quantity/i });
    fireEvent.click(plusBtn);

    // Quantity becomes 2, total becomes 2 * 95 = 190
    await waitFor(() => {
      expect(screen.getByText("2")).toBeTruthy();
      expect(screen.getByText(/Add to Cart • ₹ 190\/-/i)).toBeTruthy();
    });

    // Increment again: quantity 3, total 3 * 95 = 285
    fireEvent.click(plusBtn);
    await waitFor(() => {
      expect(screen.getByText("3")).toBeTruthy();
      expect(screen.getByText(/Add to Cart • ₹ 285\/-/i)).toBeTruthy();
    });

    // Decrement once: quantity 2, total 190
    const minusBtn = screen.getByRole("button", { name: /Decrease quantity/i });
    fireEvent.click(minusBtn);
    await waitFor(() => {
      expect(screen.getByText("2")).toBeTruthy();
      expect(screen.getByText(/Add to Cart • ₹ 190\/-/i)).toBeTruthy();
    });
  });

  it("adds item with selected quantity to cart and navigates back to origin", async () => {
    global.fetch = vi.fn().mockImplementation((url, options) => {
      if (url === "/cart/add") {
        const body = JSON.parse(options.body);
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              success: true,
              cart: [
                {
                  id: body.item_id,
                  name: body.name,
                  price: body.price,
                  quantity: body.quantity,
                  subtotal: body.price * body.quantity,
                },
              ],
              itemCount: body.quantity,
              total: body.price * body.quantity,
            }),
        });
      }
      return Promise.reject(new Error("Unknown endpoint"));
    });

    renderProductPage({
      initialState: {
        item: mockItemWithAllFields,
        origin: "/menu-items?section=dose_special",
        sectionId: "dose_special",
      },
    });

    // Set quantity to 2
    const plusBtn = screen.getByRole("button", { name: /Increase quantity/i });
    fireEvent.click(plusBtn);

    // Tap Add to Cart
    const addBtn = screen.getByRole("button", {
      name: /Add 2 Crispy Masala Dose to cart/i,
    });
    fireEvent.click(addBtn);

    // Verify visual added confirmation
    await waitFor(() => {
      expect(screen.getByText("ADDED TO TRAY!")).toBeTruthy();
    });

    // Navigates back to originating route
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith("/menu-items?section=dose_special");
    });
  });

  it("displays clear error and does not navigate away when cart addition fails", async () => {
    global.fetch = vi.fn().mockImplementation((url) => {
      if (url === "/cart/add") {
        return Promise.resolve({
          ok: false,
          status: 400,
          json: () =>
            Promise.resolve({
              detail: "Kitchen is temporarily not accepting orders for this dish",
            }),
        });
      }
      return Promise.reject(new Error("Unknown endpoint"));
    });

    renderProductPage({
      initialState: {
        item: mockItemWithAllFields,
        origin: "/menu-items?section=dose_special",
      },
    });

    const addBtn = screen.getByRole("button", {
      name: /Add 1 Crispy Masala Dose to cart/i,
    });
    fireEvent.click(addBtn);

    // Error alert is displayed
    await waitFor(() => {
      expect(screen.getByText("Failed to Add Item")).toBeTruthy();
      expect(
        screen.getByText("Kitchen is temporarily not accepting orders for this dish")
      ).toBeTruthy();
    });

    // MUST NOT navigate away
    expect(mockNavigate).not.toHaveBeenCalled();
  });

  it("handles back button navigation returning directly to origin", async () => {
    renderProductPage({
      initialState: {
        item: mockItemWithAllFields,
        origin: "/Categories?group=south_indian_favourites&section=dose_special",
        sectionId: "dose_special",
      },
    });

    const backBtn = screen.getByRole("button", { name: /Back to Dose Special/i });
    fireEvent.click(backBtn);

    expect(mockNavigate).toHaveBeenCalledWith(
      "/Categories?group=south_indian_favourites&section=dose_special"
    );
  });

  it("disables Add to Cart button when dish is marked unavailable", async () => {
    renderProductPage({
      initialState: {
        item: mockUnavailableItem,
        origin: "/menu-items?section=hot_beverages",
      },
    });

    expect(screen.getByText("CURRENTLY SOLD OUT")).toBeTruthy();
    const addBtn = screen.getByRole("button", { name: /Add 1 Coffee \/ Tea to cart/i });
    expect(addBtn.hasAttribute("disabled")).toBe(true);
    expect(screen.getByText(/SOLD OUT • UNAVAILABLE/i)).toBeTruthy();
  });
});
