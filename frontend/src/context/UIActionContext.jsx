import { createContext, useContext, useCallback } from "react";

const UIActionContext = createContext(null);

export function UIActionProvider({ children }) {
  const executeUIAction = useCallback((action, value, extra) => {
    if (typeof window === "undefined") return;

    console.log("EXECUTING KIOSK UI ACTION:", action, value);

    window.dispatchEvent(
      new CustomEvent("kiosk-ui-action", {
        detail: {
          action,
          value,
          extra,
          ...(typeof extra === "object" ? extra : {}),
        },
      })
    );
  }, []);

  return (
    <UIActionContext.Provider value={{ executeUIAction }}>
      {children}
    </UIActionContext.Provider>
  );
}

const defaultUIActionContext = {
  executeUIAction: (action, value, extra) => {
    if (typeof window === "undefined") return;
    window.dispatchEvent(
      new CustomEvent("kiosk-ui-action", {
        detail: {
          action,
          value,
          extra,
          ...(typeof extra === "object" ? extra : {}),
        },
      })
    );
  },
};

export function useUIAction() {
  const context = useContext(UIActionContext);
  return context || defaultUIActionContext;
}
