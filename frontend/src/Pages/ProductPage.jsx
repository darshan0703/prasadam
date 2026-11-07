import { useState, useEffect, useRef, useMemo } from "react";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { Plus, Minus, Check, AlertCircle, ShoppingBag, ArrowLeft } from "lucide-react";
import CompactHeader from "../components/CompactHeader";
import CartSummaryDock from "../components/CartSummaryDock";
import { useCart } from "../context/CartContext";
import { findSectionById, MENU_GROUPS } from "../data/prasadamMenuStructure";
import { getMenuItemImage } from "../data/menuItemImageManifest";
import { getSectionImage } from "../data/prasadamSectionImages";
import { syncScreen } from "../services/screenService";
import defaultFallbackImg from "../assets/images/prasadam_hero.jpg";
import "./ProductPage.css";
import "./Categories.css";

/**
 * Dedicated Product Details Page for Prasadam Kiosk (1080 x 1920)
 * 
 * Follows interaction patterns from the reference kiosk:
 * - Accepts stable item ID and originating route context.
 * - Displays verified dish imagery, name, Kannada title, price, and attributes.
 * - Quantity selector enforced with minimum quantity of 1.
 * - Authoritative backend transaction via /cart/add with optimistic fallback.
 * - Graceful error handling: fails safely without navigating away.
 * - Returns to the originating menu context on back or successful cart addition.
 */
export function ProductPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const { cart, total, clearCart, addToCart } = useCart();

  // Route and context extraction
  const itemIdFromUrl = searchParams.get("id");
  const sectionIdFromUrl = searchParams.get("section");
  const stateItem = location.state?.item || null;
  const targetItemId = stateItem?.id || itemIdFromUrl;

  const origin = useMemo(() => {
    const rawOrigin = location.state?.origin;
    if (rawOrigin && rawOrigin !== "/" && rawOrigin !== "/product") {
      return rawOrigin;
    }
    const sectionHint = location.state?.sectionId || sectionIdFromUrl;
    if (sectionHint) {
      return `/menu-items?section=${sectionHint}`;
    }
    return "/Categories";
  }, [location.state?.origin, location.state?.sectionId, sectionIdFromUrl]);

  // Product state
  const [product, setProduct] = useState(stateItem);
  const [loading, setLoading] = useState(!stateItem && Boolean(targetItemId));
  const [loadError, setLoadError] = useState(null);

  // Cart interaction state
  const [quantity, setQuantity] = useState(1);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [addError, setAddError] = useState(null);
  const [justAdded, setJustAdded] = useState(false);
  const [showCartDrawer, setShowCartDrawer] = useState(false);

  const isNavigatingRef = useRef(false);

  // Load product data if not provided via navigation state
  useEffect(() => {
    if (stateItem && stateItem.id === targetItemId) {
      setProduct(stateItem);
      setLoading(false);
      return;
    }

    if (!targetItemId) {
      setLoading(false);
      setLoadError("No menu item specified");
      return;
    }

    let isMounted = true;
    setLoading(true);
    setLoadError(null);

    const fetchProduct = async () => {
      try {
        // First try the direct item lookup
        const res = await fetch(`/menu/items/${encodeURIComponent(targetItemId)}`);
        if (res.ok) {
          const data = await res.json();
          if (isMounted && data.item) {
            setProduct(data.item);
            setLoading(false);
            return;
          }
        }

        // Fallback: search in section items if sectionId is known
        const sectionHint = location.state?.sectionId || sectionIdFromUrl;
        if (sectionHint) {
          const secRes = await fetch(`/menu/sections/${encodeURIComponent(sectionHint)}/items`);
          if (secRes.ok) {
            const secData = await secRes.json();
            const matched = Array.isArray(secData.items)
              ? secData.items.find((i) => i.id === targetItemId)
              : null;
            if (isMounted && matched) {
              setProduct(matched);
              setLoading(false);
              return;
            }
          }
        }

        if (isMounted) {
          setLoadError("Item not found in menu catalogue");
        }
      } catch (err) {
        if (isMounted) {
          setLoadError(err.message || "Failed to load product details");
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    fetchProduct();
    return () => {
      isMounted = false;
    };
  }, [targetItemId, stateItem, location.state?.sectionId, sectionIdFromUrl]);

  // Resolve section and imagery
  const sectionId = location.state?.sectionId || sectionIdFromUrl || product?.section_id;
  const activeSection = useMemo(() => {
    return sectionId ? findSectionById(sectionId) : null;
  }, [sectionId]);

  const fallbackSectionImg = useMemo(() => {
    return getSectionImage(sectionId, defaultFallbackImg);
  }, [sectionId]);

  const resolvedImage = useMemo(() => {
    if (!product) return defaultFallbackImg;
    const manifestImg = getMenuItemImage(product.id);
    return product.image || manifestImg || product.image_url || fallbackSectionImg;
  }, [product, fallbackSectionImg]);

  const isVerifiedVeg = useMemo(() => {
    if (!product) return false;
    return (
      product.is_veg === true ||
      product.isVeg === true ||
      product.dietary === "veg" ||
      product.vegetarian === true
    );
  }, [product]);

  const isUnavailable = useMemo(() => {
    if (!product) return false;
    return (
      product.available === false ||
      product.is_available === false ||
      product.requires_review === true
    );
  }, [product]);

  // Stepper handlers
  const handleDecrement = () => {
    setQuantity((prev) => Math.max(1, prev - 1));
  };

  const handleIncrement = () => {
    setQuantity((prev) => prev + 1);
  };

  // Back navigation preserving origin
  const handleGoBack = () => {
    if (isNavigatingRef.current) return;
    navigate(origin);
  };

  // Add to cart handler
  const handleAddToCart = async () => {
    if (!product || isUnavailable || isSubmitting || isNavigatingRef.current) {
      return;
    }

    setIsSubmitting(true);
    setAddError(null);

    try {
      const result = await addToCart(product, quantity);
      if (result && result.success) {
        setIsSubmitting(false);
        setJustAdded(true);
        isNavigatingRef.current = true;
        // Brief visual confirmation before returning to origin
        setTimeout(() => {
          navigate(origin);
        }, 350);
      } else {
        throw new Error("Unable to add item to tray. Please try again.");
      }
    } catch (err) {
      console.error("Add to cart failed:", err);
      setAddError(err.message || "Failed to add item to tray. Please try again.");
      setIsSubmitting(false);
      // Crucial: do NOT navigate away on failure
    }
  };

  // Sync active product screen with backend conversational engine
  useEffect(() => {
    syncScreen("product", { item_id: targetItemId });
  }, [targetItemId]);

  // Voice action listener for in-page actions
  useEffect(() => {
    const handleVoiceUIAction = (event) => {
      const { action, value } = event.detail || {};
      if (!action) return;

      if (action === "go_back") {
        handleGoBack();
      } else if (action === "add_to_cart") {
        handleAddToCart();
      } else if (action === "set_quantity") {
        const newQty = Number(value?.quantity ?? value);
        if (newQty && newQty > 0) {
          setQuantity(newQty);
        }
      } else if (action === "increase_quantity") {
        const delta = Number(value?.delta ?? value) || 1;
        setQuantity((prev) => prev + delta);
      } else if (action === "decrease_quantity") {
        const delta = Number(value?.delta ?? value) || 1;
        setQuantity((prev) => Math.max(1, prev - delta));
      } else if (action === "open_cart") {
        navigate("/cart", { state: { origin } });
      }
    };

    window.addEventListener("kiosk-ui-action", handleVoiceUIAction);
    return () => {
      window.removeEventListener("kiosk-ui-action", handleVoiceUIAction);
    };
  }, [origin, targetItemId, product, quantity]);

  // Total price calculation for this product
  const currentPrice = Number(product?.price) || 0;
  const computedSubtotal = currentPrice * quantity;

  return (
    <div className="prasadam-product-page">
      {/* Heritage Frame Corner Brackets */}
      <div className="heritage-border-corner top-left" />
      <div className="heritage-border-corner top-right" />
      <div className="heritage-border-corner bottom-left" />
      <div className="heritage-border-corner bottom-right" />

      {/* Top Branded Header */}
      <CompactHeader
        onBack={handleGoBack}
        backLabel={activeSection ? `Back to ${activeSection.canonicalName}` : "Back to Menu"}
        subtitle="DISH DETAILS"
        onOpenCart={() => setShowCartDrawer(true)}
      />

      {/* Main Kiosk Content Area */}
      <main className="product-page-stage">
        {loading ? (
          <div className="product-loading-box" role="status" aria-live="polite">
            <div className="loading-spinner-ring" />
            <span className="loading-text">Loading dish details...</span>
            <span className="loading-subtext" lang="kn">ಮಾಹಿತಿಯನ್ನು ಪಡೆಯಲಾಗುತ್ತಿದೆ</span>
          </div>
        ) : loadError || !product ? (
          <div className="product-error-box" role="alert">
            <div className="error-icon-circle">
              <AlertCircle size={44} />
            </div>
            <h2 className="error-heading">Dish Unavailable</h2>
            <p className="error-message">
              {loadError || "The requested item is not currently available in the menu catalogue."}
            </p>
            <button
              type="button"
              className="product-return-btn"
              onClick={handleGoBack}
            >
              <ArrowLeft size={20} />
              <span>Return to Browsing</span>
            </button>
          </div>
        ) : (
          <div className="product-details-container">
            {/* Upper Hero Media Showcase */}
            <div className="product-hero-showcase">
              <div className="product-image-frame">
                <img
                  src={resolvedImage}
                  alt={product.name}
                  className="product-hero-image"
                  onError={(e) => {
                    if (e.currentTarget.src !== defaultFallbackImg) {
                      e.currentTarget.src = defaultFallbackImg;
                    }
                  }}
                />
                <div className="product-image-vignette" />

                {/* Verified Pure Veg Badge */}
                {isVerifiedVeg && (
                  <div className="product-veg-pill" title="100% Pure Vegetarian Heritage Preparation">
                    <div className="veg-pill-outer">
                      <div className="veg-pill-dot" />
                    </div>
                    <span className="veg-pill-label">100% PURE VEG</span>
                  </div>
                )}

                {/* Unavailable / Sold Out Banner */}
                {isUnavailable && (
                  <div className="product-unavailable-banner">
                    <AlertCircle size={20} />
                    <span>CURRENTLY SOLD OUT</span>
                  </div>
                )}
              </div>
            </div>

            {/* Central Information Card */}
            <div className="product-info-card">
              <div className="product-header-block">
                <div className="product-meta-row">
                  {product.category && (
                    <span className="product-category-pill">
                      {product.category}
                    </span>
                  )}
                  {activeSection && activeSection.canonicalName !== product.category && (
                    <span className="product-section-pill">
                      {activeSection.canonicalName}
                    </span>
                  )}
                </div>

                <h1 className="product-primary-title">{product.name}</h1>

                {(product.kannadaName || product.kannada_name) && (
                  <h2 className="product-kannada-title" lang="kn">
                    {product.kannadaName || product.kannada_name}
                  </h2>
                )}
              </div>

              {/* Price Display */}
              <div className="product-price-section">
                <span className="price-tag-label">PRICE / ಬೆಲೆ</span>
                <div className="product-price-value-row">
                  <span className="currency-sign">₹</span>
                  <span className="price-number">
                    {currentPrice.toLocaleString("en-IN")}
                  </span>
                  <span className="price-suffix">/-</span>
                </div>
              </div>

              {/* Description (strictly optional, omitted when null) */}
              {product.description && (
                <div className="product-description-block">
                  <h3 className="section-label">About This Item</h3>
                  <p className="product-description-text">{product.description}</p>
                </div>
              )}

              {/* Heritage Tradition Notice */}
              <div className="heritage-note-card">
                <span className="heritage-icon">✦</span>
                <div className="heritage-note-text">
                  <strong>Authentic Prasadam Recipe:</strong> Prepared fresh with pure ingredients,
                  traditional South Indian roasting methods, and heritage spices.
                </div>
              </div>

              {/* Action Error Banner */}
              {addError && (
                <div className="product-action-error" role="alert">
                  <AlertCircle size={22} className="error-icon" />
                  <div className="error-text-content">
                    <strong>Failed to Add Item</strong>
                    <span>{addError}</span>
                  </div>
                  <button
                    type="button"
                    className="error-dismiss-btn"
                    onClick={() => setAddError(null)}
                  >
                    ✕
                  </button>
                </div>
              )}

              {/* Interactive Touch Controls Row */}
              <div className="product-action-controls">
                {/* Stepper with minimum quantity of 1 */}
                <div
                  className="product-quantity-selector"
                  role="group"
                  aria-label="Item quantity"
                >
                  <button
                    type="button"
                    className="quantity-btn minus"
                    onClick={handleDecrement}
                    disabled={quantity <= 1 || isSubmitting || isUnavailable}
                    aria-label="Decrease quantity"
                  >
                    <Minus size={28} />
                  </button>

                  <span className="quantity-display" aria-live="polite">
                    {quantity}
                  </span>

                  <button
                    type="button"
                    className="quantity-btn plus"
                    onClick={handleIncrement}
                    disabled={isSubmitting || isUnavailable}
                    aria-label="Increase quantity"
                  >
                    <Plus size={28} />
                  </button>
                </div>

                {/* Primary Add to Cart Button */}
                <button
                  type="button"
                  className={`product-add-cart-btn ${justAdded ? "success" : ""}`}
                  onClick={handleAddToCart}
                  disabled={isUnavailable || isSubmitting}
                  aria-label={`Add ${quantity} ${product.name} to cart for ₹ ${computedSubtotal}`}
                >
                  {isUnavailable ? (
                    <span>SOLD OUT • UNAVAILABLE</span>
                  ) : justAdded ? (
                    <span className="added-success-wrapper">
                      <Check size={28} />
                      <span>ADDED TO TRAY!</span>
                    </span>
                  ) : isSubmitting ? (
                    <span className="adding-spinner-wrapper">
                      <span className="btn-spinner" />
                      <span>ADDING TO TRAY...</span>
                    </span>
                  ) : (
                    <span>
                      Add to Cart • ₹ {computedSubtotal.toLocaleString("en-IN")}/-
                    </span>
                  )}
                </button>
              </div>
            </div>
          </div>
        )}
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
                      navigate("/cart", { state: { origin } });
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

export default ProductPage;
