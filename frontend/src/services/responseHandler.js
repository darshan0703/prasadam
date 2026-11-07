import { getRoute } from "../utils/navigation";

/**
 * Handles conversational assistant responses and executes deterministic UI actions & navigations.
 */
export function handleKioskResponse(
  data,
  { navigate, location, executeUIAction } = {}
) {
  if (!data) return;

  console.log("HANDLING KIOSK RESPONSE:", data);

  // 1. Process explicit UI action in data.data
  if (data.data?.ui_action && executeUIAction) {
    const uiAct = data.data.ui_action;

    if (uiAct === "go_back") {
      const currentPath = location?.pathname || "";
      const origin = location?.state?.origin;
      if (origin && origin !== currentPath) {
        navigate?.(origin);
      } else {
        navigate?.(-1);
      }
      executeUIAction("go_back", data.data?.value, data.data);
      return;
    }

    if (uiAct === "open_cart" || uiAct === "checkout") {
      navigate?.("/cart", { state: { origin: location?.pathname } });
      executeUIAction("open_cart", data.data?.value, data.data);
      return;
    }

    executeUIAction(uiAct, data.data?.value, data.data);
  }

  // 2. Process actions list from backend
  if (data.actions && Array.isArray(data.actions)) {
    for (const action of data.actions) {
      const type = action.type;
      const payload = action.payload || {};

      if (type === "go_back") {
        const currentPath = location?.pathname || "";
        const origin = location?.state?.origin;
        if (origin && origin !== currentPath) {
          navigate?.(origin);
        } else {
          navigate?.(-1);
        }
        executeUIAction?.("go_back", payload);
      } else if (type === "open_product" && payload.item) {
        navigate?.("/product", {
          state: {
            item: payload.item,
            origin: location?.pathname || "/Categories",
          },
        });
        executeUIAction?.("open_product", payload.item, payload);
      } else if (type === "navigate" && payload.screen) {
        const dest = getRoute(payload.screen, payload);
        if (dest === -1) {
          navigate?.(-1);
        } else if (dest) {
          navigate?.(dest);
        }
      } else if (executeUIAction) {
        // Dispatch in-page cart/ui mutations
        executeUIAction(type, payload);
      }
    }
    return;
  }

  // 3. Navigate based on data.screen if specified
  if (data.screen) {
    if (data.screen === "previous") {
      const currentPath = location?.pathname || "";
      const origin = location?.state?.origin;
      if (origin && origin !== currentPath) {
        navigate?.(origin);
      } else {
        navigate?.(-1);
      }
      return;
    }

    if (data.screen === "product" && data.data?.item) {
      navigate?.("/product", {
        state: {
          item: data.data.item,
          origin: location?.pathname || "/Categories",
        },
      });
      return;
    }

    const route = getRoute(data.screen, data.data || {});
    if (route) {
      if (route === -1) {
        navigate?.(-1);
      } else {
        navigate?.(route);
      }
    }
  }
}
