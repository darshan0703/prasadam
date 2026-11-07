import { describe, it, expect, vi } from "vitest";
import { getRoute } from "../utils/navigation";
import { handleKioskResponse } from "./responseHandler";
import { isValidTranscript, isNonSpeechTranscript } from "./voice/transcriptFilter";

describe("Prasadam Voice & Navigation Integration", () => {
  describe("Navigation Route Resolution (navigation.js)", () => {
    it("maps section menu items to /menu-items?section=...", () => {
      expect(getRoute("menu_items", { section_id: "dose_special" })).toBe(
        "/menu-items?section=dose_special"
      );
      expect(
        getRoute("menu_items", { section_id: "south_indian_breakfast" })
      ).toBe("/menu-items?section=south_indian_breakfast");
    });

    it("maps subcategories with category_id to /Categories?group=...", () => {
      expect(
        getRoute("subcategories", { category_id: "south_indian" })
      ).toBe("/Categories?group=south_indian");
    });

    it("maps previous screen to -1 (history back)", () => {
      expect(getRoute("previous")).toBe(-1);
    });

    it("maps standard screens correctly", () => {
      expect(getRoute("home")).toBe("/");
      expect(getRoute("categories")).toBe("/Categories");
      expect(getRoute("product")).toBe("/product");
      expect(getRoute("cart")).toBe("/cart");
      expect(getRoute("order_complete")).toBe("/order-complete");
    });

    it("returns null for unknown screens rather than falling back to /Categories", () => {
      expect(getRoute("unknown_screen")).toBeNull();
      expect(getRoute("non_existent")).toBeNull();
      expect(getRoute(null)).toBeNull();
    });
  });

  describe("Kiosk Response Handler (responseHandler.js)", () => {
    it("navigates to menu section when response contains navigate action", () => {
      const navigate = vi.fn();
      const executeUIAction = vi.fn();

      const response = {
        message: "Opening Dose Special",
        screen: "menu_items",
        intent: "show_section",
        actions: [
          {
            type: "navigate",
            payload: { screen: "menu_items", section_id: "dose_special" },
          },
        ],
      };

      handleKioskResponse(response, { navigate, executeUIAction });

      expect(navigate).toHaveBeenCalledWith("/menu-items?section=dose_special");
    });

    it("handles 'go_back' action and navigates to previous screen", () => {
      const navigate = vi.fn();
      const executeUIAction = vi.fn();

      const response = {
        message: "Returning to previous screen.",
        screen: "previous",
        intent: "go_back",
        actions: [
          { type: "go_back", payload: {} },
          { type: "navigate", payload: { screen: "previous" } },
        ],
      };

      handleKioskResponse(response, {
        navigate,
        location: { pathname: "/menu-items", state: { origin: "/Categories" } },
        executeUIAction,
      });

      expect(navigate).toHaveBeenCalledWith("/Categories");
      expect(executeUIAction).toHaveBeenCalledWith("go_back", {});
    });

    it("handles 'open_product' action with item details", () => {
      const navigate = vi.fn();
      const executeUIAction = vi.fn();

      const item = {
        id: "ghee_roast_masala_dosa",
        name: "Ghee Roast Masala Dosa",
        price: 95.0,
      };

      const response = {
        message: "Ghee Roast Masala Dosa is ₹95.",
        screen: "product",
        intent: "product_details",
        actions: [
          {
            type: "open_product",
            payload: { item },
          },
        ],
      };

      handleKioskResponse(response, {
        navigate,
        location: { pathname: "/menu-items" },
        executeUIAction,
      });

      expect(navigate).toHaveBeenCalledWith("/product", {
        state: {
          item,
          origin: "/menu-items",
        },
      });
      expect(executeUIAction).toHaveBeenCalledWith("open_product", item, { item });
    });

    it("dispatches cart mutations to executeUIAction", () => {
      const navigate = vi.fn();
      const executeUIAction = vi.fn();

      const payload = {
        id: "ghee_roast_masala_dosa",
        name: "Ghee Roast Masala Dosa",
        quantity: 2,
        price: 95.0,
      };

      const response = {
        message: "I have added 2 Ghee Roast Masala Dosa to your cart.",
        screen: "menu_items",
        intent: "add_to_cart",
        actions: [{ type: "add_to_cart", payload }],
      };

      handleKioskResponse(response, { navigate, executeUIAction });

      expect(executeUIAction).toHaveBeenCalledWith("add_to_cart", payload);
    });

    it("safely handles null, empty, or unknown responses without throwing", () => {
      const navigate = vi.fn();
      const executeUIAction = vi.fn();

      expect(() => handleKioskResponse(null, { navigate, executeUIAction })).not.toThrow();
      expect(() => handleKioskResponse({}, { navigate, executeUIAction })).not.toThrow();
      expect(() =>
        handleKioskResponse({ screen: "unknown_mystery_page" }, { navigate, executeUIAction })
      ).not.toThrow();
      expect(navigate).not.toHaveBeenCalled();
    });
  });

  describe("Transcript Filtering (transcriptFilter.js)", () => {
    it("discards non-speech noise, bracketed artifacts, and blank audio", () => {
      expect(isValidTranscript("")).toBe(false);
      expect(isValidTranscript(" ")).toBe(false);
      expect(isValidTranscript("[applause]")).toBe(false);
      expect(isValidTranscript("(music)")).toBe(false);
      expect(isValidTranscript("[BLANK_AUDIO]")).toBe(false);
      expect(isValidTranscript("thank you for watching")).toBe(false);
      expect(isValidTranscript("please subscribe")).toBe(false);
      expect(isValidTranscript("a bell")).toBe(false);
      expect(isNonSpeechTranscript("coughing")).toBe(true);
    });

    it("accepts valid conversational utterances", () => {
      expect(isValidTranscript("Show me dosa")).toBe(true);
      expect(isValidTranscript("Show South Indian breakfast")).toBe(true);
      expect(isValidTranscript("Go back")).toBe(true);
      expect(isValidTranscript("Show me masala dosa")).toBe(true);
      expect(isValidTranscript("How much is ghee plain dosa?")).toBe(true);
      expect(isValidTranscript("Add two masala dosas")).toBe(true);
      expect(isValidTranscript("Remove the last item")).toBe(true);
      expect(isValidTranscript("What is in my cart?")).toBe(true);
      expect(isValidTranscript("Proceed to checkout")).toBe(true);
      expect(isValidTranscript("Which one is cheaper?")).toBe(true);
      expect(isValidTranscript("Add two")).toBe(true);
    });
  });
});
