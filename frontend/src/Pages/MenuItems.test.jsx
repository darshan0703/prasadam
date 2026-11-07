import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import MenuItems from "./MenuItems";
import SectionItemsView from "../components/SectionItemsView";
import { CartProvider, useCart } from "../context/CartContext";
import { findSectionById } from "../data/prasadamMenuStructure";

const mockNavigate = vi.fn();

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Sample verified test items adhering to real data schema
const mockVerifiedItems = [
  {
    id: "masala_dose",
    name: "Crispy Masala Dose",
    kannadaName: "ಗರಿಗರಿ ಮಸಾಲೆ ದೋಸೆ",
    price: 95,
    description: "Golden rice crepe smeared with red chutney and spiced potato palya",
    image: "/sections/section_dose_special.jpg",
    is_veg: true,
    available: true,
    category: "Signature",
  },
  {
    id: "benne_dose",
    name: "Davangere Benne Dose",
    kannadaName: "ದಾವಣಗೆರೆ ಬೆಣ್ಣೆ ದೋಸೆ",
    price: 110,
    description: "Fluffy aromatic dosa topped with fresh white churned butter",
    image: "/sections/section_dose_special.jpg",
    is_veg: true,
    available: true,
    category: "Special",
  },
  {
    id: "rava_dose",
    name: "Onion Rava Dose",
    kannadaName: "ಈರುಳ್ಳಿ ರವೆ ದೋಸೆ",
    price: 105,
    description: "Crisp semolina crepe laced with cracked peppercorns and green chillies",
    image: null, // Test missing image fallback
    is_veg: true,
    available: false, // Test unavailable state
    category: "Signature",
  },
];

function renderMenuItems(initialEntries = ["/menu-items?section=dose_special"]) {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <CartProvider>
        <Routes>
          <Route path="/menu-items" element={<MenuItems />} />
        </Routes>
      </CartProvider>
    </MemoryRouter>
  );
}

function renderSectionItemsDirect(section, mockItems = []) {
  global.fetch = vi.fn().mockImplementation((url) => {
    return Promise.resolve({
      ok: true,
      json: () =>
        Promise.resolve({
          success: true,
          section_id: section.id,
          item_count: mockItems.length,
          items: mockItems,
          status: mockItems.length > 0 ? "active" : "pending_restaurant_digitization",
        }),
    });
  });

  return render(
    <MemoryRouter>
      <CartProvider>
        <SectionItemsView section={section} />
      </CartProvider>
    </MemoryRouter>
  );
}

describe("Prasadam Menu Items Page (Compact Grid Design)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    sessionStorage.clear();
  });

  it("dynamically displays selected subcategory title and Kannada label", async () => {
    const doseSection = findSectionById("dose_special");
    renderSectionItemsDirect(doseSection, []);

    expect(screen.getByText("Dose Special")).toBeTruthy();
    expect(screen.getByText("ದೋಸೆ ವಿಶೇಷ")).toBeTruthy();
    expect(screen.getByText(/Signature golden ghee roast/i)).toBeTruthy();

    await waitFor(() => {
      expect(screen.getByText(/Verified Menu Items Pending Digitization/i)).toBeTruthy();
    });
  });

  it("renders verified items in 2-column compact grid with prices and landscape images", async () => {
    const doseSection = findSectionById("dose_special");
    renderSectionItemsDirect(doseSection, mockVerifiedItems);

    await waitFor(() => {
      expect(screen.getByText("Crispy Masala Dose")).toBeTruthy();
      expect(screen.getByText("ದಾವಣಗೆರೆ ಬೆಣ್ಣೆ ದೋಸೆ")).toBeTruthy();
      expect(screen.getByText("95")).toBeTruthy();
      expect(screen.getByText("110")).toBeTruthy();
    });

    // Check pure veg badge is present for verified items
    expect(screen.getAllByText("PURE VEG").length).toBeGreaterThanOrEqual(1);

    // Verify grid container exists
    const grid = screen.getByRole("grid", { name: /Dose Special Dishes/i });
    expect(grid).toBeTruthy();
  });

  it("handles touchscreen Add, increment, decrement and cart updates correctly", async () => {
    const doseSection = findSectionById("dose_special");
    renderSectionItemsDirect(doseSection, mockVerifiedItems);

    await waitFor(() => {
      expect(screen.getByText("Crispy Masala Dose")).toBeTruthy();
    });

    // Tap ADD on Crispy Masala Dose
    const addBtn = screen.getByRole("button", {
      name: /Add Crispy Masala Dose to order tray/i,
    });
    fireEvent.click(addBtn);

    // Stepper should now be visible with quantity 1
    await waitFor(() => {
      expect(screen.getByText("1")).toBeTruthy();
    });

    // Tap Plus (+) to increment quantity
    const plusBtn = screen.getByRole("button", {
      name: /Increase Crispy Masala Dose quantity/i,
    });
    fireEvent.click(plusBtn);

    await waitFor(() => {
      expect(screen.getByText("2")).toBeTruthy();
    });

    // Tap Minus (-) to decrement quantity
    const minusBtn = screen.getByRole("button", {
      name: /Decrease Crispy Masala Dose quantity/i,
    });
    fireEvent.click(minusBtn);

    await waitFor(() => {
      expect(screen.getByText("1")).toBeTruthy();
    });

    // Tap Minus again: quantity reaches 0, returning to ADD button
    fireEvent.click(minusBtn);

    await waitFor(() => {
      expect(
        screen.getByRole("button", {
          name: /Add Crispy Masala Dose to order tray/i,
        })
      ).toBeTruthy();
    });
  });

  it("disables adding unavailable dishes and renders SOLD OUT state", async () => {
    const doseSection = findSectionById("dose_special");
    renderSectionItemsDirect(doseSection, mockVerifiedItems);

    await waitFor(() => {
      expect(screen.getByText("Onion Rava Dose")).toBeTruthy();
    });

    // Verify SOLD OUT button is present and disabled
    const soldOutBtn = screen.getByRole("button", {
      name: /Onion Rava Dose is currently sold out/i,
    });
    expect(soldOutBtn).toBeTruthy();
    expect(soldOutBtn.hasAttribute("disabled")).toBe(true);
  });

  it("filters items using the compact filter strip when categories are present", async () => {
    const doseSection = findSectionById("dose_special");
    renderSectionItemsDirect(doseSection, mockVerifiedItems);

    await waitFor(() => {
      expect(screen.getByText("All Items (3)")).toBeTruthy();
      expect(screen.getByText("Signature (2)")).toBeTruthy();
      expect(screen.getByText("Special (1)")).toBeTruthy();
    });

    // Click "Special" filter pill
    const specialFilter = screen.getByRole("button", { name: /Special/i });
    fireEvent.click(specialFilter);

    // Only Davangere Benne Dose should be displayed
    expect(screen.getByText("Davangere Benne Dose")).toBeTruthy();
    expect(screen.queryByText("Crispy Masala Dose")).toBeNull();

    // Click "All Items" to restore full grid
    const allFilter = screen.getByRole("button", { name: /All Items/i });
    fireEvent.click(allFilter);

    expect(screen.getByText("Crispy Masala Dose")).toBeTruthy();
    expect(screen.getByText("Davangere Benne Dose")).toBeTruthy();
  });

  it("renders the persistent bottom cart bar with correct item count and total on MenuItems page", async () => {
    global.fetch = vi.fn().mockImplementation(() =>
      Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve({
            success: true,
            section_id: "dose_special",
            items: mockVerifiedItems,
          }),
      })
    );

    renderMenuItems();

    await waitFor(() => {
      expect(screen.getByText("Crispy Masala Dose")).toBeTruthy();
    });

    // Initially cart is empty
    expect(screen.getByText("TRAY EMPTY")).toBeTruthy();
    expect(screen.getByText("₹ 0/-")).toBeTruthy();

    // Add 1 Crispy Masala Dose (₹95)
    const addMasala = screen.getByRole("button", {
      name: /Add Crispy Masala Dose to order tray/i,
    });
    fireEvent.click(addMasala);

    // Bottom cart bar updates immediately
    await waitFor(() => {
      expect(screen.getByText("VIEW CART")).toBeTruthy();
      expect(screen.getByText("₹ 95/-")).toBeTruthy();
    });

    // Add 1 Benne Dose (₹110)
    const addBenne = screen.getByRole("button", {
      name: /Add Davangere Benne Dose to order tray/i,
    });
    fireEvent.click(addBenne);

    // Total should be 95 + 110 = 205
    await waitFor(() => {
      expect(screen.getByText("₹ 205/-")).toBeTruthy();
    });

    // Tapping "VIEW CART" opens the Order Tray drawer
    const viewCartBtn = screen.getByRole("button", { name: /Review and pay/i });
    fireEvent.click(viewCartBtn);

    expect(screen.getByRole("dialog", { name: /Your Order Tray/i })).toBeTruthy();
    expect(screen.getByText("ನಿಮ್ಮ ಆಹಾರ ತಟ್ಟೆ")).toBeTruthy();
  });

  it("tapping a menu item card opens the product details page with item and origin state", async () => {
    const doseSection = findSectionById("dose_special");
    renderSectionItemsDirect(doseSection, mockVerifiedItems);

    await waitFor(() => {
      expect(screen.getByText("Crispy Masala Dose")).toBeTruthy();
    });

    const card = screen.getByRole("button", { name: "Crispy Masala Dose" });
    fireEvent.click(card);

    expect(mockNavigate).toHaveBeenCalledWith(
      "/product?id=masala_dose",
      expect.objectContaining({
        state: expect.objectContaining({
          itemId: "masala_dose",
          sectionId: "dose_special",
        }),
      })
    );
  });
});

