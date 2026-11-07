import { useState, useRef, useMemo, useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Plus, Minus, Trash2, ArrowLeft, Check, AlertCircle, ShoppingBag, CreditCard, QrCode, Banknote } from "lucide-react";
import CompactHeader from "../components/CompactHeader";
import { useCart } from "../context/CartContext";
import { syncScreen } from "../services/screenService";
import { getMenuItemImage } from "../data/menuItemImageManifest";
import defaultFallbackImg from "../assets/images/prasadam_hero.jpg";
import "./CartPage.css";
import "./Categories.css";

/**
 * Dedicated Cart & Order Review Page for Prasadam Kiosk (1080 x 1920)
 * 
 * Provides:
 * - Line-by-line review of selected dishes, unit prices, quantities, and line subtotals.
 * - Interactive touchscreen stepper and item deletion.
 * - Authoritative total calculation without fabricated fees.
 * - Payment method selection (UPI, Card, Cash demo pathways).
 * - Authoritative order placement via /order/complete with duplicate-tap guards.
 * - Navigation to /order-complete with receipt state.
 */
export function CartPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { cart, itemCount, total, updateItem, removeItem, clearCart, completeOrder } = useCart();

  const rawOrigin = location.state?.origin;
  const origin = useMemo(() => {
    if (rawOrigin && rawOrigin !== "/" && rawOrigin !== "/cart") {
      return rawOrigin;
    }
    return "/Categories";
  }, [rawOrigin]);

  const [selectedPayment, setSelectedPayment] = useState("demo_upi");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [orderError, setOrderError] = useState(null);
  const isNavigatingRef = useRef(false);

  const isEmpty = !cart || cart.length === 0;

  const handleBack = () => {
    if (isNavigatingRef.current) return;
    navigate(origin);
  };

  const handlePaymentSelect = (method) => {
    setSelectedPayment(method);
  };

  const handleCompleteOrder = async () => {
    if (isEmpty || isSubmitting || isNavigatingRef.current) return;

    setIsSubmitting(true);
    setOrderError(null);

    try {
      const result = await completeOrder(selectedPayment, "Kiosk Guest");
      if (result && result.success && result.order) {
        isNavigatingRef.current = true;
        navigate("/order-complete", {
          state: {
            order: result.order,
            paymentMethod: selectedPayment,
          },
        });
      } else {
        throw new Error("Unable to place order. Please try again.");
      }
    } catch (err) {
      console.error("Order placement failed:", err);
      setOrderError(err.message || "Failed to complete order. Please check with counter staff.");
      setIsSubmitting(false);
    }
  };

  useEffect(() => {
    syncScreen("cart");
  }, []);

  useEffect(() => {
    const handleVoiceAction = (event) => {
      const { action, value } = event.detail || {};
      if (!action) return;

      if (action === "go_back") {
        handleBack();
      } else if (action === "checkout") {
        const paymentSection = document.querySelector(".payment-methods-card");
        paymentSection?.scrollIntoView({ behavior: "smooth" });
      } else if (action === "select_payment" || action === "payment_method") {
        const method = String(value || "").toLowerCase();
        if (method.includes("upi")) setSelectedPayment("demo_upi");
        else if (method.includes("card")) setSelectedPayment("demo_card");
        else if (method.includes("cash")) setSelectedPayment("demo_cash");
      } else if (action === "confirm_order") {
        handleCompleteOrder();
      } else if (action === "clear_cart") {
        clearCart();
      }
    };

    window.addEventListener("kiosk-ui-action", handleVoiceAction);
    return () => window.removeEventListener("kiosk-ui-action", handleVoiceAction);
  }, [origin, isEmpty, isSubmitting, selectedPayment]);

  return (
    <div className="prasadam-cart-page">
      {/* Heritage Frame Corner Brackets */}
      <div className="heritage-border-corner top-left" />
      <div className="heritage-border-corner top-right" />
      <div className="heritage-border-corner bottom-left" />
      <div className="heritage-border-corner bottom-right" />

      {/* Top Branded Header */}
      <CompactHeader
        onBack={handleBack}
        backLabel="Back to Menu"
        subtitle="ORDER REVIEW & CHECKOUT"
      />

      {/* Main Kiosk Review Stage */}
      <main className="cart-page-stage">
        {isEmpty ? (
          <div className="cart-empty-state-card" role="status">
            <div className="empty-cart-icon-circle">
              <ShoppingBag size={54} />
            </div>
            <h2 className="empty-cart-title">Your Order Tray is Empty</h2>
            <p className="empty-cart-kannada" lang="kn">
              ನಿಮ್ಮ ಆಹಾರ ತಟ್ಟೆಯಲ್ಲಿ ಯಾವುದೇ ಪದಾರ್ಥಗಳಿಲ್ಲ
            </p>
            <p className="empty-cart-subtext">
              Select your favourite temple-style dosas, authentic meals, or hot filter coffee to build your order.
            </p>
            <button
              type="button"
              className="cart-browse-menu-btn"
              onClick={handleBack}
            >
              <ArrowLeft size={22} />
              <span>Browse Menu Categories</span>
            </button>
          </div>
        ) : (
          <div className="cart-layout-container">
            {/* Left/Main Column: Itemized Tray List */}
            <section className="cart-items-section" aria-label="Review selected items">
              <div className="cart-section-header">
                <div className="cart-section-title-wrap">
                  <h2 className="cart-section-title">Your Order Tray</h2>
                  <span className="cart-section-kannada" lang="kn">ನಿಮ್ಮ ಆಹಾರ ತಟ್ಟೆ</span>
                </div>
                <span className="cart-item-count-badge">
                  {itemCount} {itemCount === 1 ? "ITEM" : "ITEMS"}
                </span>
              </div>

              <div className="cart-items-list" role="list">
                {cart.map((item, index) => {
                  const key = item._uniqueKey || item.id || `cart_item_${index}`;
                  const itemImg = item.image || getMenuItemImage(item.id) || defaultFallbackImg;
                  const itemQty = Number(item.quantity) || 1;
                  const unitPrice = Number(item.price) || 0;
                  const lineSubtotal = unitPrice * itemQty;

                  return (
                    <article key={key} className="cart-item-card" role="listitem">
                      {/* Dish Thumbnail */}
                      <div className="cart-item-thumb-wrapper">
                        <img
                          src={itemImg}
                          alt={item.name}
                          className="cart-item-thumb"
                          onError={(e) => {
                            if (e.currentTarget.src !== defaultFallbackImg) {
                              e.currentTarget.src = defaultFallbackImg;
                            }
                          }}
                        />
                      </div>

                      {/* Info Block */}
                      <div className="cart-item-info-block">
                        <h3 className="cart-item-name">{item.name}</h3>
                        {(item.kannadaName || item.kannada_name) && (
                          <h4 className="cart-item-kannada" lang="kn">
                            {item.kannadaName || item.kannada_name}
                          </h4>
                        )}
                        <span className="cart-item-unit-price">
                          ₹ {unitPrice.toLocaleString("en-IN")}/- per portion
                        </span>
                      </div>

                      {/* Stepper Controls */}
                      <div
                        className="cart-stepper-control"
                        role="group"
                        aria-label={`Quantity selector for ${item.name}`}
                      >
                        <button
                          type="button"
                          className="cart-stepper-btn minus"
                          onClick={() => updateItem(key, "decrease")}
                          aria-label={`Decrease ${item.name} quantity`}
                          disabled={isSubmitting}
                        >
                          <Minus size={22} />
                        </button>
                        <span className="cart-stepper-value" aria-live="polite">
                          {itemQty}
                        </span>
                        <button
                          type="button"
                          className="cart-stepper-btn plus"
                          onClick={() => updateItem(key, "increase")}
                          aria-label={`Increase ${item.name} quantity`}
                          disabled={isSubmitting}
                        >
                          <Plus size={22} />
                        </button>
                      </div>

                      {/* Line Subtotal */}
                      <div className="cart-item-subtotal-block">
                        <span className="cart-subtotal-currency">₹</span>
                        <span className="cart-subtotal-amount">
                          {lineSubtotal.toLocaleString("en-IN")}
                        </span>
                        <span className="cart-subtotal-suffix">/-</span>
                      </div>

                      {/* Remove Button */}
                      <button
                        type="button"
                        className="cart-item-remove-btn"
                        onClick={() => removeItem(key)}
                        aria-label={`Remove ${item.name} from tray`}
                        disabled={isSubmitting}
                        title="Remove dish"
                      >
                        <Trash2 size={22} />
                      </button>
                    </article>
                  );
                })}
              </div>

              {/* Tray Clear & Continue Row */}
              <div className="cart-secondary-actions">
                <button
                  type="button"
                  className="cart-clear-tray-btn"
                  onClick={clearCart}
                  disabled={isSubmitting}
                >
                  Clear Entire Tray
                </button>
                <button
                  type="button"
                  className="cart-add-more-btn"
                  onClick={handleBack}
                  disabled={isSubmitting}
                >
                  + Add More Dishes
                </button>
              </div>
            </section>

            {/* Bottom Summary & Payment Section */}
            <section className="cart-checkout-section" aria-label="Order summary and payment">
              {/* Order Bill Summary */}
              <div className="cart-bill-card">
                <div className="bill-title-row">
                  <span className="bill-title">Order Bill Summary / ಒಟ್ಟು ಮೊತ್ತ</span>
                  <span className="bill-items-count">{itemCount} items</span>
                </div>

                <div className="bill-total-row">
                  <div className="bill-total-labels">
                    <span className="bill-total-main">TOTAL PAYABLE</span>
                    <span className="bill-total-kannada" lang="kn">ಪಾವತಿಸಬೇಕಾದ ಮೊತ್ತ</span>
                  </div>
                  <div className="bill-total-display">
                    <span className="bill-currency">₹</span>
                    <span className="bill-amount">{total.toLocaleString("en-IN")}</span>
                    <span className="bill-suffix">/-</span>
                  </div>
                </div>

                <div className="bill-guarantee-note">
                  <span>✦ Authentic Pure Vegetarian • Fresh Kitchen Preparation • Inclusive of All Taxes</span>
                </div>
              </div>

              {/* Payment Method Selector */}
              <div className="cart-payment-card">
                <div className="payment-heading-wrap">
                  <h3 className="payment-heading">Choose Payment Method</h3>
                  <span className="payment-kannada" lang="kn">ಪಾವತಿ ವಿಧಾನವನ್ನು ಆಯ್ಕೆಮಾಡಿ</span>
                </div>

                <div className="payment-options-grid" role="radiogroup" aria-label="Payment Method">
                  {/* UPI Option */}
                  <button
                    type="button"
                    role="radio"
                    aria-checked={selectedPayment === "demo_upi"}
                    className={`payment-option-tile ${selectedPayment === "demo_upi" ? "selected" : ""}`}
                    onClick={() => handlePaymentSelect("demo_upi")}
                  >
                    <div className="payment-tile-icon-box">
                      <QrCode size={30} />
                    </div>
                    <div className="payment-tile-text">
                      <strong className="payment-tile-name">UPI / QR Code</strong>
                      <span className="payment-tile-desc">GPay, PhonePe, Paytm, BHIM</span>
                    </div>
                    <span className="demo-badge">DEMO</span>
                    {selectedPayment === "demo_upi" && (
                      <div className="payment-selected-check">
                        <Check size={18} />
                      </div>
                    )}
                  </button>

                  {/* Card Option */}
                  <button
                    type="button"
                    role="radio"
                    aria-checked={selectedPayment === "demo_card"}
                    className={`payment-option-tile ${selectedPayment === "demo_card" ? "selected" : ""}`}
                    onClick={() => handlePaymentSelect("demo_card")}
                  >
                    <div className="payment-tile-icon-box">
                      <CreditCard size={30} />
                    </div>
                    <div className="payment-tile-text">
                      <strong className="payment-tile-name">Credit / Debit Card</strong>
                      <span className="payment-tile-desc">Tap or Insert Card at Terminal</span>
                    </div>
                    <span className="demo-badge">DEMO</span>
                    {selectedPayment === "demo_card" && (
                      <div className="payment-selected-check">
                        <Check size={18} />
                      </div>
                    )}
                  </button>

                  {/* Cash Option */}
                  <button
                    type="button"
                    role="radio"
                    aria-checked={selectedPayment === "demo_cash"}
                    className={`payment-option-tile ${selectedPayment === "demo_cash" ? "selected" : ""}`}
                    onClick={() => handlePaymentSelect("demo_cash")}
                  >
                    <div className="payment-tile-icon-box">
                      <Banknote size={30} />
                    </div>
                    <div className="payment-tile-text">
                      <strong className="payment-tile-name">Pay at Counter (Cash)</strong>
                      <span className="payment-tile-desc">Receive token & pay cash at counter</span>
                    </div>
                    <span className="demo-badge">DEMO</span>
                    {selectedPayment === "demo_cash" && (
                      <div className="payment-selected-check">
                        <Check size={18} />
                      </div>
                    )}
                  </button>
                </div>
              </div>

              {/* Order Error Alert */}
              {orderError && (
                <div className="cart-order-error-banner" role="alert">
                  <AlertCircle size={24} className="error-icon" />
                  <div className="error-msg-content">
                    <strong>Order Placement Issue</strong>
                    <span>{orderError}</span>
                  </div>
                  <button
                    type="button"
                    className="error-dismiss-btn"
                    onClick={() => setOrderError(null)}
                  >
                    ✕
                  </button>
                </div>
              )}

              {/* Primary Place Order CTA */}
              <button
                type="button"
                className="cart-checkout-cta-btn"
                onClick={handleCompleteOrder}
                disabled={isEmpty || isSubmitting}
                aria-label={`Pay and complete order for ₹ ${total}`}
              >
                {isSubmitting ? (
                  <span className="checkout-submitting-wrapper">
                    <span className="btn-spinner" />
                    <span>TRANSACTING ORDER...</span>
                  </span>
                ) : (
                  <span className="checkout-cta-content">
                    <span>Pay & Complete Order • ₹ {total.toLocaleString("en-IN")}/-</span>
                  </span>
                )}
              </button>
            </section>
          </div>
        )}
      </main>
    </div>
  );
}

export default CartPage;
