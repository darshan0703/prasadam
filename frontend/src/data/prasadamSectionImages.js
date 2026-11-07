/**
 * Central Mapping from Canonical Section IDs to Local Image Assets
 * 
 * Source of Truth: Canonical 19 Menu Sections from prasadamMenuStructure.js.
 * Separate from display names, Kannada labels, and prices.
 */

import sectionSouthIndianBreakfastImg from "../assets/images/sections/section_south_indian_breakfast.jpg";
import sectionDoseSpecialImg from "../assets/images/sections/section_dose_special.jpg";
import sectionBajjiPakodaSnacksImg from "../assets/images/sections/section_bajji_pakoda_snacks.jpg";

import sectionMealsImg from "../assets/images/sections/section_meals.jpg";
import sectionChineseRiceItemsImg from "../assets/images/sections/section_chinese_rice_items.jpg";
import sectionNorthIndianRiceItemsImg from "../assets/images/sections/section_north_indian_rice_items.jpg";

import sectionChineseMainCourseImg from "../assets/images/sections/section_chinese_main_course.jpg";
import sectionDalItemsImg from "../assets/images/sections/section_dal_items.jpg";
import sectionKadaiImg from "../assets/images/sections/section_kadai.jpg";
import sectionKoftaImg from "../assets/images/sections/section_kofta.jpg";
import sectionNorthIndianJainItemsImg from "../assets/images/sections/section_north_indian_jain_items.jpg";
import sectionIndianCurriesImg from "../assets/images/sections/section_indian_curries.jpg";

import sectionSoupsImg from "../assets/images/sections/section_soups.jpg";
import sectionSaladsRaitaPapadImg from "../assets/images/sections/section_salads_raita_papad.jpg";
import sectionChineseStartersImg from "../assets/images/sections/section_chinese_starters.jpg";
import sectionIndianStartersImg from "../assets/images/sections/section_indian_starters.jpg";

import sectionIndianBreadsRotiImg from "../assets/images/sections/section_indian_breads_roti.jpg";

import sectionHotBeveragesImg from "../assets/images/sections/section_hot_beverages.jpg";
import sectionSweetItemsImg from "../assets/images/sections/section_sweet_items.jpg";

// Default fallback image
import defaultFallbackImg from "../assets/images/prasadam_hero.jpg";

export const SECTION_IMAGES = {
  // South Indian Favourites
  south_indian_breakfast: sectionSouthIndianBreakfastImg,
  dose_special: sectionDoseSpecialImg,
  bajji_pakoda_snacks: sectionBajjiPakodaSnacksImg,

  // Meals & Rice
  meals: sectionMealsImg,
  chinese_rice_items: sectionChineseRiceItemsImg,
  north_indian_rice_items: sectionNorthIndianRiceItemsImg,

  // Curries & Main Course
  chinese_main_course: sectionChineseMainCourseImg,
  dal_items: sectionDalItemsImg,
  kadai: sectionKadaiImg,
  kofta: sectionKoftaImg,
  north_indian_jain_items: sectionNorthIndianJainItemsImg,
  indian_curries: sectionIndianCurriesImg,

  // Starters & Sides
  soups: sectionSoupsImg,
  salads_raita_papad: sectionSaladsRaitaPapadImg,
  chinese_starters: sectionChineseStartersImg,
  indian_starters: sectionIndianStartersImg,

  // Indian Breads
  indian_breads_roti: sectionIndianBreadsRotiImg,

  // Beverages & Sweets
  hot_beverages: sectionHotBeveragesImg,
  sweet_items: sectionSweetItemsImg,
};

/**
 * Returns the local image asset for a canonical section ID.
 * Gracefully falls back to groupImage or defaultFallbackImg.
 */
export function getSectionImage(sectionId, fallbackImage = null) {
  if (sectionId && SECTION_IMAGES[sectionId]) {
    return SECTION_IMAGES[sectionId];
  }
  return fallbackImage || defaultFallbackImg;
}

export default SECTION_IMAGES;
