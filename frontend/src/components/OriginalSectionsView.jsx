import { ArrowRight } from "lucide-react";
import { getSectionImage } from "../data/prasadamSectionImages";
import "./OriginalSectionsView.css";

export function OriginalSectionsView({ group, onSelectSection }) {
  if (!group) return null;

  return (
    <div className="original-sections-container">
      {/* Active Group Banner - Traditional Elegance */}
      <div className="group-active-banner">
        <div className="banner-ornament-top">
          <span className="banner-glyph">❖</span>
        </div>
        <h2 className="banner-title-english">{group.titleEnglish}</h2>
        <h3 className="banner-title-kannada" lang="kn">{group.titleKannada}</h3>
        <div className="banner-divider">
          <span className="banner-divider-line" />
          <span className="banner-badge-text">
            {group.sections.length} {group.sections.length === 1 ? "SECTION" : "SECTIONS"} • EDITORIAL MOSAIC
          </span>
          <span className="banner-divider-line" />
        </div>
      </div>

      {/* Single-Column Sequence of Large Alternating Mosaic Tiles (Design 4) */}
      <div className="mosaic-tiles-sequence" role="list">
        {group.sections.map((section, idx) => {
          const sectionImg = getSectionImage(section.id, group.image);
          const isReversed = idx % 2 === 1;

          return (
            <button
              key={section.id}
              type="button"
              className={`mosaic-section-tile ${isReversed ? "reversed" : ""}`}
              onClick={() => onSelectSection(section)}
              aria-label={`${section.canonicalName} (${section.kannadaName})`}
            >
              {/* Large Food Photograph Panel */}
              <div className="mosaic-image-box">
                <img
                  src={sectionImg}
                  alt={section.canonicalName}
                  className="mosaic-food-img"
                  loading="lazy"
                  onError={(e) => {
                    if (group.image && e.currentTarget.src !== group.image) {
                      e.currentTarget.src = group.image;
                    }
                  }}
                />
                <div className="mosaic-img-inner-border" />
              </div>

              {/* Cream Information Panel with Ornamental Corner Accents */}
              <div className="mosaic-info-panel">
                <span className="mosaic-corner top-left" aria-hidden="true" />
                <span className="mosaic-corner top-right" aria-hidden="true" />
                <span className="mosaic-corner bottom-left" aria-hidden="true" />
                <span className="mosaic-corner bottom-right" aria-hidden="true" />

                <div className="mosaic-panel-header">
                  <span className="mosaic-section-order">
                    SECTION 0{section.order || idx + 1}
                  </span>
                  <span className="mosaic-flourish-dot">✦</span>
                </div>

                <div className="mosaic-titles-group">
                  <h4 className="mosaic-title-english">{section.canonicalName}</h4>
                  {section.kannadaName && (
                    <h5 className="mosaic-title-kannada" lang="kn">{section.kannadaName}</h5>
                  )}
                </div>

                {section.description && (
                  <p className="mosaic-description">{section.description}</p>
                )}

                <div className="mosaic-panel-footer">
                  <span className="mosaic-explore-hint">EXPLORE DISHES</span>
                  <div className="mosaic-nav-arrow" aria-hidden="true">
                    <ArrowRight size={22} className="nav-arrow-icon" />
                  </div>
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

export default OriginalSectionsView;


