import { useState, useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Check, Clock, Utensils, ArrowRight, ShieldCheck } from "lucide-react";
import CompactHeader from "../components/CompactHeader";
import { useVoiceConversation } from "../context/VoiceConversationProvider";
import { syncScreen } from "../services/screenService";
import "./OrderCompletePage.css";
import "./Categories.css";

/**
 * Dedicated Order Complete & Confirmation Page for Prasadam Kiosk (1080 x 1920)
 * 
 * Provides:
 * - Clear visual confirmation with gold seal emblem.
 * - Distinct, verified Order Number (e.g. #P-2048).
 * - Full itemized list of confirmed dishes and quantities.
 * - Verified total paid and payment method badge.
 * - Automatic session retirement and return to Welcome Screen after countdown.
 * - "Start New Order" touch button for instant kiosk reset.
 */
export function OrderCompletePage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { stopVoiceConversation } = useVoiceConversation();

  useEffect(() => {
    syncScreen("order_complete");
    stopVoiceConversation();
  }, [stopVoiceConversation]);

  const order = location.state?.order || null;
  const paymentMethod = location.state?.paymentMethod || order?.payment_method || "demo_upi";
  const orderNumber = order?.order_number || "#P-1001";
  const items = order?.items || [];
  const total = Number(order?.total) || 0;

  const [secondsRemaining, setSecondsRemaining] = useState(25);

  const getPaymentLabel = (method) => {
    switch (method) {
      case "demo_upi":
        return "UPI / QR Code (Demo)";
      case "demo_card":
        return "Credit / Debit Card (Demo)";
      case "demo_cash":
        return "Pay Cash at Counter (Demo)";
      default:
        return String(method).toUpperCase();
    }
  };

  const handleStartNewOrder = () => {
    // Retire completed session tokens
    if (typeof window !== "undefined") {
      sessionStorage.removeItem("session_id");
      sessionStorage.removeItem("prasadam_kiosk_cart");
      localStorage.removeItem("session_id");
    }
    navigate("/", { replace: true });
  };

  // Auto-redirect countdown
  useEffect(() => {
    // Retire old session markers upon reaching confirmation
    if (typeof window !== "undefined") {
      sessionStorage.removeItem("prasadam_kiosk_cart");
    }

    const interval = setInterval(() => {
      setSecondsRemaining((prev) => {
        if (prev <= 1) {
          clearInterval(interval);
          handleStartNewOrder();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="prasadam-order-complete-page">
      {/* Heritage Frame Corner Brackets */}
      <div className="heritage-border-corner top-left" />
      <div className="heritage-border-corner top-right" />
      <div className="heritage-border-corner bottom-left" />
      <div className="heritage-border-corner bottom-right" />

      {/* Top Branded Header */}
      <CompactHeader
        subtitle="ORDER CONFIRMED"
      />

      {/* Main Confirmation Content Area */}
      <main className="order-complete-stage">
        <div className="order-complete-card">
          {/* Heritage Seal Emblem */}
          <div className="heritage-seal-circle">
            <div className="seal-inner-ring">
              <Check size={56} className="seal-check-icon" />
            </div>
          </div>

          <div className="order-title-block">
            <h1 className="order-complete-title">Order Placed Successfully!</h1>
            <h2 className="order-complete-kannada" lang="kn">
              ನಿಮ್ಮ ಆದೇಶವನ್ನು ಯಶಸ್ವಿಯಾಗಿ ಸ್ವೀಕರಿಸಲಾಗಿದೆ
            </h2>
            <p className="order-complete-subtitle">
              Your order has been transmitted directly to our temple kitchen for fresh preparation.
            </p>
          </div>

          {/* Prominent Order Number Token Box */}
          <div className="order-token-banner" role="region" aria-label="Order Token Number">
            <div className="token-label-row">
              <span className="token-title">ORDER TOKEN NUMBER</span>
              <span className="token-kannada" lang="kn">ಆದೇಶ ಸಂಖ್ಯೆ</span>
            </div>
            <div className="token-number-value">{orderNumber}</div>
            <span className="token-instruction">
              Please present this token number at the Prasadam serving counter.
            </span>
          </div>

          {/* Itemized Order Receipt Card */}
          <div className="order-receipt-card">
            <div className="receipt-header">
              <div className="receipt-title-wrap">
                <Utensils size={20} className="receipt-icon" />
                <span className="receipt-title">Confirmed Dishes / ದೃಢೀಕರಿಸಿದ ಪದಾರ್ಥಗಳು</span>
              </div>
              <span className="receipt-badge">PAID</span>
            </div>

            <div className="receipt-items-list" role="list">
              {items.length === 0 ? (
                <div className="receipt-empty-note">
                  <span>Standard Prasadam Heritage Thali</span>
                </div>
              ) : (
                items.map((item, idx) => {
                  const qty = Number(item.quantity) || 1;
                  const price = Number(item.price) || 0;
                  const subtotal = price * qty;
                  return (
                    <div key={item._uniqueKey || item.id || idx} className="receipt-item-row" role="listitem">
                      <div className="receipt-item-meta">
                        <span className="receipt-item-qty">{qty} ×</span>
                        <span className="receipt-item-name">{item.name}</span>
                      </div>
                      <span className="receipt-item-subtotal">₹ {subtotal.toLocaleString("en-IN")}/-</span>
                    </div>
                  );
                })
              )}
            </div>

            <div className="receipt-footer">
              <div className="receipt-payment-row">
                <span className="receipt-label">Payment Method:</span>
                <span className="receipt-payment-val">{getPaymentLabel(paymentMethod)}</span>
              </div>
              <div className="receipt-total-row">
                <span className="receipt-total-label">TOTAL PAID / ಒಟ್ಟು ಪಾವತಿಸಿದ ಮೊತ್ತ:</span>
                <strong className="receipt-total-amount">₹ {total.toLocaleString("en-IN")}/-</strong>
              </div>
            </div>
          </div>

          {/* Kitchen Serving Assistance Note */}
          <div className="serving-assistance-note">
            <Clock size={20} className="clock-icon" />
            <span>
              Average kitchen preparation time is <strong>6 - 8 minutes</strong>. Listen for your order number at the counter.
            </span>
          </div>

          {/* Reset Countdown & Start New Order Action */}
          <div className="order-complete-actions">
            <button
              type="button"
              className="start-new-order-btn"
              onClick={handleStartNewOrder}
              aria-label="Start a new order"
            >
              <span>Start New Order / ಹೊಸ ಆದೇಶ</span>
              <ArrowRight size={24} />
            </button>
            <span className="countdown-text" aria-live="polite">
              Kiosk will return to Welcome Screen automatically in <strong>{secondsRemaining}s</strong>
            </span>
          </div>
        </div>
      </main>
    </div>
  );
}

export default OrderCompletePage;
