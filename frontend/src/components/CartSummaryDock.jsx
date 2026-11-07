import { useNavigate, useLocation } from "react-router-dom";
import { ShoppingBag, ArrowRight } from "lucide-react";
import { useCart } from "../context/CartContext";
import "./CartSummaryDock.css";

export function CartSummaryDock({ onViewCart }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { cart, itemCount, total } = useCart();
  const count = Number(itemCount) || 0;
  const cartTotal = Number(total) || 0;
  const isEmpty = count === 0;

  const handleAction = () => {
    if (onViewCart) {
      onViewCart();
    } else {
      navigate("/cart", { state: { origin: `${location.pathname}${location.search}` } });
    }
  };

  return (
    <footer className="cart-summary-dock">
      <div className="cart-dock-card">
        {/* Left: Cart Info & Quantity Badge */}
        <div className="cart-dock-left">
          <div className="cart-icon-wrapper">
            <ShoppingBag size={30} className="cart-dock-icon" />
            {count > 0 && <span className="cart-qty-badge">{count}</span>}
          </div>

          <div className="cart-text-group">
            <div className="cart-title-row">
              <span className="cart-main-label">Your Order Summary</span>
              <span className="cart-kannada-label" lang="kn">ನಿಮ್ಮ ಆದೇಶ</span>
            </div>
            <span className="cart-status-hint">
              {isEmpty
                ? "Cart is empty • Select items from categories"
                : `${count} ${count === 1 ? "item" : "items"} added to your tray`}
            </span>
          </div>
        </div>

        {/* Center: Live Running Total */}
        <div className="cart-dock-center">
          <span className="total-label-text">TOTAL / ಒಟ್ಟು</span>
          <span className="total-amount-display">
            ₹ {cartTotal.toLocaleString("en-IN")}/-
          </span>
        </div>

        {/* Right: Review / View Cart Action */}
        <div className="cart-dock-right">
          <button
            type="button"
            className={`cart-action-btn ${isEmpty ? "disabled" : "active"}`}
            onClick={handleAction}
            disabled={isEmpty}
            aria-label="Review and pay"
          >
            <span>{isEmpty ? "TRAY EMPTY" : "VIEW CART"}</span>
            <ArrowRight size={24} className="btn-arrow" />
          </button>
        </div>
      </div>
    </footer>
  );
}

export default CartSummaryDock;
