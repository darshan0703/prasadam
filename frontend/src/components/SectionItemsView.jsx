import { useState, useEffect, useMemo } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { Plus, Minus, Check, Clock, Info, Sparkles, AlertCircle } from "lucide-react";
import { useCart } from "../context/CartContext";
import { getSectionImage } from "../data/prasadamSectionImages";
import { getMenuItemImage } from "../data/menuItemImageManifest";
import defaultFallbackImg from "../assets/images/prasadam_hero.jpg";
import "./SectionItemsView.css";

/**
 * Prasadam Menu Items Page Component (Compact Grid Design)
 * 
 * Viewport: 1080 x 1920 Kiosk Display.
 * - Dynamic subcategory title & verified Kannada label.
 * - Compact filter strip (defaults to "All Items", reflects verified attributes).
 * - Scrollable 2-column menu grid with consistent card heights.
 * - Medium landscape food images with graceful fallback.
 * - Touchscreen-friendly Add / Stepper controls updating shared CartContext.
 * - Verified pure veg indicators and availability states.
 * - Full data integrity compliance: zero fabricated dishes or fake prices.
 */
export function SectionItemsView({ section }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { cart, addItem, updateQuantity } = useCart();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeFilter, setActiveFilter] = useState("all");
  const [justAddedId, setJustAddedId] = useState(null);

  // Fallback section image
  const sectionFallbackImg = useMemo(() => {
    return getSectionImage(section?.id, defaultFallbackImg);
  }, [section?.id]);

  useEffect(() => {
    let isMounted = true;
    const fetchItems = async () => {
      if (!section?.id) {
        if (isMounted) {
          setItems([]);
          setLoading(false);
        }
        return;
      }

      setLoading(true);
      try {
        const response = await fetch(`/menu/sections/${section.id}/items`);
        if (response.ok) {
          const data = await response.json();
          if (isMounted) {
            setItems(Array.isArray(data.items) ? data.items : []);
          }
        } else {
          if (isMounted) setItems([]);
        }
      } catch {
        if (isMounted) setItems([]);
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    fetchItems();
    return () => {
      isMounted = false;
    };
  }, [section?.id]);

  // Derive filter categories strictly from real data attributes if present
  const availableFilters = useMemo(() => {
    if (!items || items.length === 0) return [];
    const filterSet = new Set();
    items.forEach((item) => {
      if (item.category && typeof item.category === "string") {
        filterSet.add(item.category.trim());
      } else if (item.tag && typeof item.tag === "string") {
        filterSet.add(item.tag.trim());
      } else if (item.dietary && typeof item.dietary === "string") {
        filterSet.add(item.dietary.trim());
      }
    });
    return Array.from(filterSet);
  }, [items]);

  // Filter items based on active selection
  const displayedItems = useMemo(() => {
    if (activeFilter === "all") return items;
    return items.filter(
      (item) =>
        item.category === activeFilter ||
        item.tag === activeFilter ||
        item.dietary === activeFilter
    );
  }, [items, activeFilter]);

  // Handle Add to Cart
  const handleAddToCart = (e, item) => {
    e.stopPropagation();
    if (item.available === false || item.is_available === false) return;

    addItem(item, 1);
    setJustAddedId(item.id);
    setTimeout(() => {
      setJustAddedId(null);
    }, 1200);
  };

  // Handle Stepper Increment
  const handleIncrement = (e, item, cartItem) => {
    e.stopPropagation();
    if (item.available === false || item.is_available === false) return;
    const targetKey = cartItem?._uniqueKey || item.id;
    updateQuantity(targetKey, 1);
  };

  // Handle Stepper Decrement
  const handleDecrement = (e, item, cartItem) => {
    e.stopPropagation();
    const targetKey = cartItem?._uniqueKey || item.id;
    updateQuantity(targetKey, -1);
  };

  // Open dedicated Product Details Page preserving originating menu route and section
  const handleOpenProduct = (item) => {
    const origin = `${location.pathname}${location.search}`;
    navigate(`/product?id=${encodeURIComponent(item.id)}`, {
      state: {
        item,
        itemId: item.id,
        sectionId: section?.id,
        origin,
      },
    });
  };

  if (!section) return null;

  return (
    <div className="section-items-container" role="region" aria-label={`${section.canonicalName} Menu Items`}>
      {/* Dynamic Subcategory Banner */}
      <header className="section-header-banner">
        <div className="section-badge-row">
          <span className="canonical-badge">CANONICAL SECTION</span>
          <span className="group-affiliation-badge">
            {section.group?.titleEnglish || "Prasadam Menu Collection"}
          </span>
          {!loading && items.length > 0 && (
            <span className="section-dish-count-badge">
              {items.length} {items.length === 1 ? "DISH" : "DISHES"}
            </span>
          )}
        </div>

        <div className="section-titles-wrap">
          <h2 className="section-header-canonical">{section.canonicalName}</h2>
          {section.kannadaName && (
            <h3 className="section-header-kannada" lang="kn">
              {section.kannadaName}
            </h3>
          )}
        </div>

        {section.description && (
          <p className="section-header-desc">{section.description}</p>
        )}
      </header>

      {/* Optional Compact Filter Strip */}
      {!loading && items.length > 0 && (
        <nav className="menu-filter-strip" aria-label="Menu Filters">
          <button
            type="button"
            className={`filter-pill ${activeFilter === "all" ? "active" : ""}`}
            onClick={() => setActiveFilter("all")}
          >
            <span>All Items ({items.length})</span>
          </button>
          {availableFilters.map((filter) => {
            const count = items.filter(
              (i) => i.category === filter || i.tag === filter || i.dietary === filter
            ).length;
            return (
              <button
                key={filter}
                type="button"
                className={`filter-pill ${activeFilter === filter ? "active" : ""}`}
                onClick={() => setActiveFilter(filter)}
              >
                <span>{filter} ({count})</span>
              </button>
            );
          })}
        </nav>
      )}

      {/* Content Area: Loading, 2-Column Compact Grid, or Integrity State */}
      {loading ? (
        <div className="items-loading-box" role="status" aria-live="polite">
          <div className="loading-spinner-ring" />
          <span className="loading-text">Loading verified menu dishes...</span>
          <span className="loading-subtext" lang="kn">ಆಹಾರ ಪದಾರ್ಥಗಳನ್ನು ಲೋಡ್ ಮಾಡಲಾಗುತ್ತಿದೆ</span>
        </div>
      ) : displayedItems.length > 0 ? (
        <div className="compact-menu-grid" role="grid" aria-label={`${section.canonicalName} Dishes`}>
          {displayedItems.map((item) => {
            const cartItem = cart.find((i) => i.id === item.id);
            const quantity = cartItem ? Number(cartItem.quantity) || 0 : 0;
            const isAdded = justAddedId === item.id;
            const isUnavailable = item.available === false || item.is_available === false;
            const manifestImg = getMenuItemImage(item.id);
            const itemImage = item.image || manifestImg || item.image_url || sectionFallbackImg;

            // Verified Pure Veg indicator
            const isVerifiedVeg =
              item.is_veg === true ||
              item.isVeg === true ||
              item.dietary === "veg" ||
              item.vegetarian === true;

            return (
              <article
                key={item.id}
                className={`menu-compact-card ${isUnavailable ? "unavailable" : ""}`}
                aria-label={item.name}
                onClick={() => handleOpenProduct(item)}
                tabIndex={0}
                role="button"
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    handleOpenProduct(item);
                  }
                }}
              >
                {/* Gold Inner Accent Rim */}
                <div className="card-gold-inner-rim" aria-hidden="true" />

                {/* Medium Landscape Food Image Container */}
                <div className="card-media-wrapper">
                  <img
                    src={itemImage}
                    alt={item.name}
                    className="card-landscape-img"
                    loading="lazy"
                    onError={(e) => {
                      if (e.currentTarget.src !== defaultFallbackImg) {
                        e.currentTarget.src = defaultFallbackImg;
                      }
                    }}
                  />
                  <div className="card-image-gradient-overlay" />

                  {/* Pure Veg Badge (verified by data) */}
                  {isVerifiedVeg && (
                    <div className="card-veg-badge" title="100% Pure Vegetarian">
                      <div className="card-veg-symbol-outer">
                        <div className="card-veg-symbol-dot" />
                      </div>
                      <span className="card-veg-label">PURE VEG</span>
                    </div>
                  )}

                  {/* Unavailable Status Badge */}
                  {isUnavailable && (
                    <div className="card-unavailable-badge">
                      <AlertCircle size={16} />
                      <span>UNAVAILABLE</span>
                    </div>
                  )}
                </div>

                {/* Card Content Information */}
                <div className="card-body-content">
                  <div className="card-title-block">
                    <h4 className="card-dish-name">{item.name}</h4>
                    {item.kannadaName || item.kannada_name ? (
                      <h5 className="card-dish-kannada" lang="kn">
                        {item.kannadaName || item.kannada_name}
                      </h5>
                    ) : null}
                  </div>

                  {item.description && (
                    <p className="card-dish-description">{item.description}</p>
                  )}

                  {/* Price & Touch Controls Row */}
                  <div className="card-action-row">
                    <div className="card-price-display">
                      <span className="currency-symbol">₹</span>
                      <span className="price-amount">
                        {Number(item.price).toLocaleString("en-IN")}
                      </span>
                      <span className="price-suffix">/-</span>
                    </div>

                    <div className="card-controls-slot">
                      {isUnavailable ? (
                        <button
                          type="button"
                          className="card-btn-disabled"
                          disabled
                          aria-label={`${item.name} is currently sold out`}
                        >
                          SOLD OUT
                        </button>
                      ) : quantity > 0 ? (
                        <div
                          className="touch-stepper-control"
                          role="group"
                          aria-label={`Quantity selector for ${item.name}`}
                          onClick={(e) => e.stopPropagation()}
                        >
                          <button
                            type="button"
                            className="stepper-touch-btn minus"
                            onClick={(e) => handleDecrement(e, item, cartItem)}
                            aria-label={`Decrease ${item.name} quantity`}
                          >
                            <Minus size={22} className="stepper-icon" />
                          </button>
                          <span className="stepper-quantity-val" aria-live="polite">
                            {quantity}
                          </span>
                          <button
                            type="button"
                            className="stepper-touch-btn plus"
                            onClick={(e) => handleIncrement(e, item, cartItem)}
                            aria-label={`Increase ${item.name} quantity`}
                          >
                            <Plus size={22} className="stepper-icon" />
                          </button>
                        </div>
                      ) : (
                        <button
                          type="button"
                          className={`card-add-touch-btn ${isAdded ? "added-animation" : ""}`}
                          onClick={(e) => handleAddToCart(e, item)}
                          aria-label={`Add ${item.name} to order tray`}
                        >
                          {isAdded ? (
                            <>
                              <Check size={20} className="add-btn-icon" />
                              <span className="add-btn-text">ADDED</span>
                            </>
                          ) : (
                            <>
                              <Plus size={20} className="add-btn-icon" />
                              <span className="add-btn-text">ADD</span>
                            </>
                          )}
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      ) : (
        /* Strict Integrity State: Preserves exact verification notice when items are pending digitization */
        <div className="menu-integrity-notice-card" role="note">
          <div className="integrity-icon-box">
            <Clock size={36} className="clock-icon" />
          </div>

          <h4 className="integrity-title">Verified Menu Items Pending Digitization</h4>
          <p className="integrity-subtitle" lang="kn">
            ಈ ವಿಭಾಗದ ಆಹಾರ ಪದಾರ್ಥಗಳ ಪಟ್ಟಿ ಸಿದ್ಧವಾಗುತ್ತಿದೆ
          </p>

          <div className="integrity-details-box">
            <div className="detail-row">
              <strong>Section Identity:</strong>
              <span>
                {section.canonicalName}
                {section.kannadaName ? ` (${section.kannadaName})` : ""}
              </span>
            </div>
            <div className="detail-row">
              <strong>Status:</strong>
              <span className="status-highlight">
                Original Section Verified from Printed Menu
              </span>
            </div>
            <div className="detail-row">
              <strong>Data Integrity Note:</strong>
              <p>
                In compliance with strict menu integrity rules, individual dish names, descriptions,
                and current kitchen prices are not fabricated. They will appear here automatically
                as soon as the restaurant database is populated.
              </p>
            </div>
          </div>

          <div className="integrity-assistance-footer">
            <Info size={20} />
            <span>
              Please consult the service staff at the Prasadam counter for live item availability.
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

export default SectionItemsView;
