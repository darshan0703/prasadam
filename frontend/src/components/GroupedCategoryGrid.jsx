import { MENU_GROUPS } from "../data/prasadamMenuStructure";
import defaultFallbackImg from "../assets/images/prasadam_hero.jpg";
import "./GroupedCategoryGrid.css";

export function GroupedCategoryGrid({ onSelectGroup }) {
  return (
    <div className="grouped-category-container">
      {/* Category Selection Prompt */}
      <div className="category-browse-intro">
        <div className="browse-flourish-top">
          <span className="flourish-diamond">❖</span>
        </div>
        <h2 className="browse-title-main">Select Category Group</h2>
        <p className="browse-title-kannada" lang="kn">
          ಆಹಾರ ವಿಭಾಗವನ್ನು ಆಯ್ಕೆಮಾಡಿ
        </p>
        <div className="browse-ornamental-divider">
          <span className="divider-line" />
          <span className="divider-motif">✦</span>
          <span className="divider-line" />
        </div>
      </div>

      {/* 2-Column x 3-Row Grid of Circular Food Medallions */}
      <div className="category-medallion-grid" role="grid">
        {MENU_GROUPS.map((group) => {
          const sectionCount = group.sections.length;

          return (
            <button
              key={group.id}
              type="button"
              className="category-medallion-tile"
              onClick={() => onSelectGroup(group)}
              aria-label={`${group.titleEnglish} (${group.titleKannada})`}
            >
              {/* Circular Food Medallion Frame */}
              <div className="medallion-frame-outer">
                <div className="medallion-frame-secondary">
                  <div className="medallion-frame-inner">
                    <img
                      src={group.image || defaultFallbackImg}
                      alt={group.titleEnglish}
                      className="medallion-img"
                      loading="eager"
                      onError={(e) => {
                        if (e.currentTarget.src !== defaultFallbackImg) {
                          e.currentTarget.src = defaultFallbackImg;
                        }
                      }}
                    />
                  </div>
                </div>
              </div>

              {/* Centered Bilingual Labels & Ornamental Flourish */}
              <div className="medallion-details">
                <h3 className="medallion-title-english">{group.titleEnglish}</h3>
                <h4 className="medallion-title-kannada" lang="kn">
                  {group.titleKannada}
                </h4>

                <div className="medallion-ornament-line">
                  <span className="line-half" />
                  <span className="ornament-glyph">✦</span>
                  <span className="line-half" />
                </div>

                <span className="medallion-count-pill">
                  {sectionCount} {sectionCount === 1 ? "Section" : "Sections"}
                </span>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

export default GroupedCategoryGrid;

