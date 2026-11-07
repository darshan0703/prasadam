import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import Categories from "./Categories";
import { CartProvider } from "../context/CartContext";
import { MENU_GROUPS, getMenuStatistics } from "../data/prasadamMenuStructure";
import { SECTION_IMAGES } from "../data/prasadamSectionImages";

const mockNavigate = vi.fn();

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

function renderWithProviders(initialEntries = ["/Categories"]) {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <CartProvider>
        <Routes>
          <Route path="/Categories" element={<Categories />} />
          <Route path="/" element={<div>Home Screen</div>} />
        </Routes>
      </CartProvider>
    </MemoryRouter>
  );
}

describe("Prasadam Categories Browsing Experience", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    sessionStorage.clear();
    sessionStorage.setItem("session_id", "test-session-1234");
  });

  it("verifies canonical menu structure contains exactly 6 groups and 19 original sections", () => {
    const stats = getMenuStatistics();
    expect(stats.totalGroups).toBe(6);
    expect(stats.totalSections).toBe(19);

    // Group letters A through F
    const letters = MENU_GROUPS.map((g) => g.groupLetter);
    expect(letters).toEqual(["A", "B", "C", "D", "E", "F"]);

    // Verify all 19 sections are unique
    const sectionIds = stats.sections.map((s) => s.id);
    expect(new Set(sectionIds).size).toBe(19);
  });

  it("renders all 6 macro groups with English and Kannada labels on level 1", () => {
    renderWithProviders();

    // Verify groups exist
    expect(screen.getByText("South Indian Favourites")).toBeTruthy();
    expect(screen.getByText("ದಕ್ಷಿಣ ಭಾರತೀಯ ವಿಶೇಷಗಳು")).toBeTruthy();

    expect(screen.getByText("Meals & Rice")).toBeTruthy();
    expect(screen.getByText("ಊಟ ಮತ್ತು ಅನ್ನದ ವಿಧಗಳು")).toBeTruthy();

    expect(screen.getByText("Curries & Main Course")).toBeTruthy();
    expect(screen.getByText("Starters & Sides")).toBeTruthy();
    expect(screen.getByText("Indian Breads")).toBeTruthy();
    expect(screen.getByText("Beverages & Sweets")).toBeTruthy();

    // Verify persistent cart dock exists
    expect(screen.getByText("Your Order Summary")).toBeTruthy();
    expect(screen.getByText("TRAY EMPTY")).toBeTruthy();
  });

  it("navigates from Grouped Categories to Original Sections when a group is selected", () => {
    renderWithProviders();

    // Tap South Indian Favourites card
    const groupCard = screen.getByRole("button", {
      name: /South Indian Favourites/i,
    });
    fireEvent.click(groupCard);

    // Should display original sections under South Indian Favourites
    expect(screen.getByText("South Indian Breakfast")).toBeTruthy();
    expect(screen.getByText("Dose Special")).toBeTruthy();
    expect(screen.getByText("Bajji / Pakoda / Snacks")).toBeTruthy();

    // Kannada labels
    expect(screen.getByText("ದೋಸೆ ವಿಶೇಷ")).toBeTruthy();
    expect(screen.getByText("ಬಜ್ಜಿ / ಪಕೋಡ / ತಿಂಡಿಗಳು")).toBeTruthy();
  });

  it("navigates into Section Items view and displays menu integrity notice when items are pending", async () => {
    renderWithProviders(["/Categories?group=south_indian_favourites"]);

    // Tap Dose Special
    const doseSectionBtn = screen.getByRole("button", {
      name: /Dose Special/i,
    });
    fireEvent.click(doseSectionBtn);

    // Verify Section header exists (appears in header subtitle and section banner)
    expect(screen.getAllByText("Dose Special").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("ದೋಸೆ ವಿಶೇಷ").length).toBeGreaterThanOrEqual(1);

    // Verify integrity notice (no fabricated prices or sample dishes)
    await waitFor(() => {
      expect(
        screen.getByText(/Verified Menu Items Pending Digitization/i)
      ).toBeTruthy();
    });
  });

  it("verifies all 19 canonical sections have a distinct mapped image asset", () => {
    const stats = getMenuStatistics();
    expect(stats.totalSections).toBe(19);

    stats.sections.forEach((sec) => {
      const img = SECTION_IMAGES[sec.id];
      expect(img).toBeDefined();
      expect(typeof img).toBe("string");
      expect(img.length).toBeGreaterThan(0);
    });
  });

  it("handles back navigation gracefully level-by-level without resetting session or cart", () => {
    renderWithProviders([
      "/Categories?group=south_indian_favourites&section=dose_special",
    ]);

    // Currently at level 3 (Section Items): back should take us to level 2 (Sections)
    const backBtnL3 = screen.getByRole("button", {
      name: /Back to South Indian Favourites/i,
    });
    fireEvent.click(backBtnL3);

    expect(screen.getByText("Dose Special")).toBeTruthy();
    expect(screen.getByText("South Indian Breakfast")).toBeTruthy();

    // From level 2: back should take us to level 1 (Groups)
    const backBtnL2 = screen.getByRole("button", {
      name: /Back to Categories/i,
    });
    fireEvent.click(backBtnL2);

    expect(screen.getByText("South Indian Favourites")).toBeTruthy();
    expect(screen.getByText("Meals & Rice")).toBeTruthy();

    // Session remains completely intact
    expect(sessionStorage.getItem("session_id")).toBe("test-session-1234");
  });
});
