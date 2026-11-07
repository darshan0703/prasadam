import { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import CompactHeader from "../components/CompactHeader";
import GroupedCategoryGrid from "../components/GroupedCategoryGrid";
import OriginalSectionsView from "../components/OriginalSectionsView";
import SectionItemsView from "../components/SectionItemsView";
import CartSummaryDock from "../components/CartSummaryDock";
import {
  MENU_GROUPS,
  findGroupById,
  findSectionById,
} from "../data/prasadamMenuStructure";
import { useCart } from "../context/CartContext";
import { syncScreen } from "../services/screenService";
import "./Categories.css";

export function Categories() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { cart, total, clearCart } = useCart();

  const [activeGroupId, setActiveGroupId] = useState(
    searchParams.get("group") || null
  );
  const [activeSectionId, setActiveSectionId] = useState(
    searchParams.get("section") || null
  );

  const [showCartDrawer, setShowCartDrawer] = useState(false);

  // Synchronize state with URL parameters to support browser refresh/back button
  useEffect(() => {
    const groupParam = searchParams.get("group");
    const sectionParam = searchParams.get("section");
    setActiveGroupId(groupParam || null);
    setActiveSectionId(sectionParam || null);
  }, [searchParams]);

  // Synchronize active screen with backend conversational engine
  useEffect(() => {
    if (activeSectionId) {
      syncScreen("menu_items", { section_id: activeSectionId });
    } else if (activeGroupId) {
      syncScreen("subcategories", { category_id: activeGroupId });
    } else {
      syncScreen("categories");
    }
  }, [activeGroupId, activeSectionId]);

  // Resolve active objects from canonical data structure
  const activeGroup = activeGroupId ? findGroupById(activeGroupId) : null;
  const activeSection = activeSectionId ? findSectionById(activeSectionId) : null;

  // Level determination: 1 = Groups Grid, 2 = Original Sections, 3 = Section Items
  const currentLevel = activeSection ? 3 : activeGroup ? 2 : 1;

  // Handlers for forward touch navigation
  const handleSelectGroup = (group) => {
    setActiveGroupId(group.id);
    setActiveSectionId(null);
    setSearchParams({ group: group.id });
  };

  const handleSelectSection = (section) => {
    setActiveSectionId(section.id);
    setSearchParams({
      group: activeGroupId || section.group?.id,
      section: section.id,
    });
  };

  // Handler for hierarchical back navigation without resetting session or cart
  const handleBackNavigation = () => {
    if (currentLevel === 3) {
      // Step back from Section Items to Original Sections
      setActiveSectionId(null);
      if (activeGroupId) {
        setSearchParams({ group: activeGroupId });
      } else {
        setSearchParams({});
      }
    } else if (currentLevel === 2) {
      // Step back from Original Sections to Grouped Categories
      setActiveGroupId(null);
      setActiveSectionId(null);
      setSearchParams({});
    } else {
      // Step back to Welcome Screen (preserve session and cart in storage)
      navigate("/");
    }
  };

  // Listen for global voice UI actions
  useEffect(() => {
    const handleVoiceAction = (event) => {
      const { action } = event.detail || {};
      if (action === "go_back") {
        handleBackNavigation();
      }
    };
    window.addEventListener("kiosk-ui-action", handleVoiceAction);
    return () => window.removeEventListener("kiosk-ui-action", handleVoiceAction);
  }, [currentLevel, activeGroupId, activeSectionId]);

  const getBackLabel = () => {
    if (currentLevel === 3) {
      return activeGroup ? `Back to ${activeGroup.titleEnglish}` : "Back to Sections";
    }
    if (currentLevel === 2) {
      return "Back to Categories";
    }
    return "Home / Welcome";
  };

  const getSubtitle = () => {
    if (currentLevel === 3) {
      return activeSection?.canonicalName || "SECTION ITEMS";
    }
    if (currentLevel === 2) {
      return activeGroup?.titleEnglish || "ORIGINAL SECTIONS";
    }
    return "GROUPED CATEGORIES";
  };

  return (
    <div className="prasadam-categories-page">
      {/* Heritage Frame Corner Brackets */}
      <div className="heritage-border-corner top-left" />
      <div className="heritage-border-corner top-right" />
      <div className="heritage-border-corner bottom-left" />
      <div className="heritage-border-corner bottom-right" />

      {/* Compact Branded Header */}
      <CompactHeader
        onBack={handleBackNavigation}
        backLabel={getBackLabel()}
        subtitle={getSubtitle()}
        onOpenCart={() => setShowCartDrawer(true)}
      />

      {/* Main Browsing Stage */}
      <main className="categories-stage-area">
        {currentLevel === 1 && (
          <GroupedCategoryGrid onSelectGroup={handleSelectGroup} />
        )}

        {currentLevel === 2 && activeGroup && (
          <OriginalSectionsView
            group={activeGroup}
            onSelectSection={handleSelectSection}
          />
        )}

        {currentLevel === 3 && activeSection && (
          <SectionItemsView section={activeSection} />
        )}
      </main>

      {/* Persistent Bottom Cart Dock */}
      <CartSummaryDock
        onViewCart={() => setShowCartDrawer(true)}
      />

      {/* Cart Review Drawer / Modal */}
      {showCartDrawer && (
        <div className="cart-drawer-overlay" onClick={() => setShowCartDrawer(false)}>
          <div
            className="cart-drawer-content"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-label="Your Order Tray"
          >
            <div className="drawer-header">
              <div className="drawer-title-group">
                <h3 className="drawer-title">Your Order Tray</h3>
                <span className="drawer-kannada" lang="kn">ನಿಮ್ಮ ಆಹಾರ ತಟ್ಟೆ</span>
              </div>
              <button
                type="button"
                className="drawer-close-btn"
                onClick={() => setShowCartDrawer(false)}
              >
                ✕ Close
              </button>
            </div>

            <div className="drawer-items-list">
              {cart.length === 0 ? (
                <div className="drawer-empty-state">
                  <p>Your cart is empty.</p>
                  <span>Select items from any menu section to build your order.</span>
                </div>
              ) : (
                cart.map((item) => (
                  <div key={item._uniqueKey || item.id} className="drawer-item-row">
                    <div className="drawer-item-info">
                      <span className="drawer-item-name">{item.name}</span>
                      <span className="drawer-item-price">
                        ₹ {item.price} × {item.quantity}
                      </span>
                    </div>
                    <span className="drawer-item-subtotal">
                      ₹ {(Number(item.price) || 0) * (Number(item.quantity) || 1)}
                    </span>
                  </div>
                ))
              )}
            </div>

            <div className="drawer-footer">
              <div className="drawer-total-row">
                <span>Total Amount / ಒಟ್ಟು:</span>
                <strong>₹ {total.toLocaleString("en-IN")}/-</strong>
              </div>
              <div className="drawer-action-buttons">
                <button
                  type="button"
                  className="drawer-clear-btn"
                  onClick={clearCart}
                  disabled={cart.length === 0}
                >
                  Clear Cart
                </button>
                <button
                  type="button"
                  className="drawer-continue-btn"
                  onClick={() => setShowCartDrawer(false)}
                >
                  Continue Browsing
                </button>
                {cart.length > 0 && (
                  <button
                    type="button"
                    className="drawer-checkout-btn"
                    onClick={() => {
                      setShowCartDrawer(false);
                      const currentOrigin = activeSectionId
                        ? `/Categories?group=${activeGroupId}&section=${activeSectionId}`
                        : activeGroupId
                        ? `/Categories?group=${activeGroupId}`
                        : "/Categories";
                      navigate("/cart", {
                        state: { origin: currentOrigin },
                      });
                    }}
                  >
                    <span>Review & Pay</span>
                    <span>→</span>
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Categories;
