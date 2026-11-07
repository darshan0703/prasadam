/**
 * Navigation mappings for Prasadam Kiosk
 * Maps canonical backend screen names and section identifiers to React Router URLs.
 */

export const screenRoutes = {
  home: "/",
  welcome: "/",
  categories: "/Categories",
  category_selection: "/Categories",
  subcategories: "/Categories",
  menu_items: "/menu-items",
  product: "/product",
  product_details: "/product",
  cart: "/cart",
  checkout: "/cart",
  payment: "/cart",
  order_complete: "/order-complete",
};

/**
 * Resolves a backend screen name and optional payload into a concrete route string.
 */
export function getRoute(screen, payload = {}) {
  if (!screen) return null;

  if (screen === "previous") {
    return -1;
  }

  if (screen === "subcategories" && payload.category_id) {
    return `/Categories?group=${encodeURIComponent(payload.category_id)}`;
  }

  if (screen === "menu_items" && payload.section_id) {
    return `/menu-items?section=${encodeURIComponent(payload.section_id)}`;
  }

  return screenRoutes[screen] || null;
}
