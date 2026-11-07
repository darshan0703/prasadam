import { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import CompactHeader from "../components/CompactHeader";
import SectionItemsView from "../components/SectionItemsView";
import CartSummaryDock from "../components/CartSummaryDock";
import { findSectionById, MENU_GROUPS } from "../data/prasadamMenuStructure";
import { useCart } from "../context/CartContext";
import { syncScreen } from "../services/screenService";
import "./Categories.css";

/**
 * Dedicated Menu Items Page
 * Supports direct routing to /menu-items?section=...
 * Reuses the approved Compact Grid design and shared Prasadam components.
 */
export function MenuItems() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { cart, total, clearCart } = useCart();
  const [showCartDrawer, setShowCartDrawer] = useState(false);

  const sectionId = searchParams.get("section") || "dose_special";
  const activeSection = findSectionById(sectionId) || MENU_GROUPS[0].sections[0];
  const activeGroup = activeSection?.group;

  useEffect(() => {
    syncScreen("menu_items", { section_id: sectionId });
  }, [sectionId]);

  const handleBackNavigation = () => {
    if (activeGroup?.id) {
      navigate(`/Categories?group=${activeGroup.id}`);
    } else {
      navigate("/Categories");
    }
  };

  useEffect(() => {
    const handleVoiceAction = (event) => {
      const { action } = event.detail || {};
      if (action === "go_back") {
        handleBackNavigation();
      }
    };
    window.addEventListener("kiosk-ui-action", handleVoiceAction);
    return () => window.removeEventListener("kiosk-ui-action", handleVoiceAction);
  }, [activeGroup]);

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
        backLabel={activeGroup ? `Back to ${activeGroup.titleEnglish}` : "Back to Categories"}
        subtitle={activeSection?.canonicalName || "MENU ITEMS"}
        onOpenCart={() => setShowCartDrawer(true)}
      />

      {/* Main Browsing Stage: 2-Column Compact Grid */}
      <main className="categories-stage-area">
        <SectionItemsView section={activeSection} />
      </main>

      {/* Persistent Bottom Cart Dock */}
      <CartSummaryDock onViewCart={() => setShowCartDrawer(true)} />

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
                      navigate("/cart", {
                        state: { origin: `/menu-items?section=${sectionId}` },
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

export default MenuItems;
