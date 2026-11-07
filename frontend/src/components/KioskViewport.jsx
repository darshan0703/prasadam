import { useState, useEffect } from "react";
import "./KioskViewport.css";

const CANVAS_WIDTH = 1080;
const CANVAS_HEIGHT = 1920;

/**
 * KioskViewport dynamically scales the 1080x1920 portrait canvas to fit
 * the actual device viewport while preserving exact 9:16 kiosk aspect ratio.
 * 
 * - Real 1080x1920 kiosk display: scale = 1.0 (fills 100% of display)
 * - Desktop/laptop browser preview: scales smoothly without distortion or scrollbars
 */
export function KioskViewport({ children }) {
  const [scale, setScale] = useState(1);

  useEffect(() => {
    const updateScale = () => {
      const windowWidth = window.innerWidth;
      const windowHeight = window.innerHeight;
      
      const scaleX = windowWidth / CANVAS_WIDTH;
      const scaleY = windowHeight / CANVAS_HEIGHT;
      const newScale = Math.min(scaleX, scaleY);
      
      setScale(newScale);
    };

    updateScale();
    window.addEventListener("resize", updateScale);
    return () => window.removeEventListener("resize", updateScale);
  }, []);

  return (
    <div className="kiosk-viewport-wrapper">
      <div
        className="kiosk-viewport-canvas"
        style={{
          width: `${CANVAS_WIDTH}px`,
          height: `${CANVAS_HEIGHT}px`,
          transform: `scale(${scale})`,
        }}
      >
        {children}
      </div>
    </div>
  );
}

export default KioskViewport;
