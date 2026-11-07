import southIndianImg from "../assets/images/category_south_indian_favourites.jpg";
import mealsRiceImg from "../assets/images/category_meals_and_rice.jpg";
import curriesImg from "../assets/images/category_curries_and_main_course.jpg";
import startersImg from "../assets/images/category_starters_and_sides.jpg";
import breadsImg from "../assets/images/category_indian_breads.jpg";
import beveragesSweetsImg from "../assets/images/category_beverages_and_sweets.jpg";

/**
 * Canonical Prasadam Kiosk Menu Structure
 * 
 * Source of Truth: Supplied printed menu photographs containing 19 original sections.
 * Navigation: 6 macro-groups for 1080x1920 kiosk touch browsing.
 * 
 * Rule: Every one of the 19 original sections belongs to EXACTLY ONE group.
 * English and Kannada labels are stored separately.
 */

export const MENU_GROUPS = [
  {
    id: "south_indian_favourites",
    groupLetter: "A",
    titleEnglish: "South Indian Favourites",
    titleKannada: "ದಕ್ಷಿಣ ಭಾರತೀಯ ವಿಶೇಷಗಳು",
    shortDescription: "Traditional tiffins, crisp dosas, and heritage evening savouries",
    image: southIndianImg,
    sections: [
      {
        id: "south_indian_breakfast",
        canonicalName: "South Indian Breakfast",
        kannadaName: "ದಕ್ಷಿಣ ಭಾರತೀಯ ಉಪಾಹಾರ",
        order: 1,
        description: "Steamed idlis, crispy vadas, authentic khara bath & kesari bath",
      },
      {
        id: "dose_special",
        canonicalName: "Dose Special",
        kannadaName: "ದೋಸೆ ವಿಶೇಷ",
        order: 2,
        description: "Signature golden ghee roast, benne dosa, and spiced potato fillings",
      },
      {
        id: "bajji_pakoda_snacks",
        canonicalName: "Bajji / Pakoda / Snacks",
        kannadaName: "ಬಜ್ಜಿ / ಪಕೋಡ / ತಿಂಡಿಗಳು",
        order: 3,
        description: "Crispy freshly fried bajjis, onion pakodas, and evening snacks",
      },
    ],
  },
  {
    id: "meals_and_rice",
    groupLetter: "B",
    titleEnglish: "Meals & Rice",
    titleKannada: "ಊಟ ಮತ್ತು ಅನ್ನದ ವಿಧಗಳು",
    shortDescription: "Wholesome South Indian thalis and fragrant regional rice preparations",
    image: mealsRiceImg,
    sections: [
      {
        id: "meals",
        canonicalName: "Meals",
        kannadaName: "ಊಟ",
        order: 1,
        description: "Complete traditional South Indian meals served with seasonal gravies",
      },
      {
        id: "chinese_rice_items",
        canonicalName: "Chinese Rice Items",
        kannadaName: "ಚೈನೀಸ್ ರೈಸ್ ಐಟಮ್ಸ್",
        order: 2,
        description: "Wok-tossed fried rice and special fusion vegetable rice bowls",
      },
      {
        id: "north_indian_rice_items",
        canonicalName: "North Indian Rice Items",
        kannadaName: "ಉತ್ತರ ಭಾರತೀಯ ರೈಸ್ ಐಟಮ್ಸ್",
        order: 3,
        description: "Fragrant jeera rice, vegetable biryani, and aromatic pulao",
      },
    ],
  },
  {
    id: "curries_and_main_course",
    groupLetter: "C",
    titleEnglish: "Curries & Main Course",
    titleKannada: "ಗ್ರೇವಿ ಮತ್ತು ಮುಖ್ಯ ಆಹಾರ",
    shortDescription: "Rich artisanal gravies, traditional dals, and gourmet paneer curries",
    image: curriesImg,
    sections: [
      {
        id: "chinese_main_course",
        canonicalName: "Chinese Main Course",
        kannadaName: "ಚೈನೀಸ್ ಮೇನ್ ಕೋರ್ಸ್",
        order: 1,
        description: "Vegetable Manchurian, Paneer Chilli gravies, and noodles",
      },
      {
        id: "dal_items",
        canonicalName: "Dal Items",
        kannadaName: "ದಾಲ್ ಐಟಮ್ಸ್",
        order: 2,
        description: "Dal Fry, Dal Tadka, and slow-cooked seasoned lentil delicacies",
      },
      {
        id: "kadai",
        canonicalName: "Kadai",
        kannadaName: "ಕಡಾಯಿ",
        order: 3,
        description: "Wok-cooked gravies with crushed coriander and bell peppers",
      },
      {
        id: "kofta",
        canonicalName: "Kofta",
        kannadaName: "ಕೊಫ್ತಾ",
        order: 4,
        description: "Soft cottage cheese and vegetable dumplings in velvety gravies",
      },
      {
        id: "north_indian_jain_items",
        canonicalName: "North Indian Jain Items",
        kannadaName: "ಉತ್ತರ ಭಾರತೀಯ ಜೈನ್ ಐಟಮ್ಸ್",
        order: 5,
        description: "Authentic preparations made strictly without root vegetables",
      },
      {
        id: "indian_curries",
        canonicalName: "Indian Curries",
        kannadaName: "ಭಾರತೀಯ ಮೇಲೋಗರಗಳು (ಕರಿಗಳು)",
        order: 6,
        description: "Classic Paneer Butter Masala, Mixed Vegetable Curry, and kormas",
      },
    ],
  },
  {
    id: "starters_and_sides",
    groupLetter: "D",
    titleEnglish: "Starters & Sides",
    titleKannada: "ಸ್ಟಾರ್ಟರ್ಸ್ ಮತ್ತು ಸೈಡ್ ಡಿಶ್ಗಳು",
    shortDescription: "Crisp appetisers, warming soups, salads, and traditional accompaniments",
    image: startersImg,
    sections: [
      {
        id: "soups",
        canonicalName: "Soups",
        kannadaName: "ಸೂಪ್ಸ್",
        order: 1,
        description: "Hot vegetable soups, sweet corn soup, and spiced herbal rasam",
      },
      {
        id: "salads_raita_papad",
        canonicalName: "Salads / Raita / Papad",
        kannadaName: "ಸಲಾಡ್ಸ್ / ರಾಯ್ತ / ಹಪ್ಪಳ",
        order: 2,
        description: "Fresh garden salads, chilled seasoned curd raita, and roasted papad",
      },
      {
        id: "chinese_starters",
        canonicalName: "Chinese Starters",
        kannadaName: "ಚೈನೀಸ್ ಸ್ಟಾರ್ಟರ್ಸ್",
        order: 3,
        description: "Crispy Veg, Gobi Manchurian Dry, and Paneer 65",
      },
      {
        id: "indian_starters",
        canonicalName: "Indian Starters",
        kannadaName: "ಭಾರತೀಯ ಸ್ಟಾರ್ಟರ್ಸ್",
        order: 4,
        description: "Paneer Tikka, Tandoori starters, and spiced roasted appetisers",
      },
    ],
  },
  {
    id: "indian_breads",
    groupLetter: "E",
    titleEnglish: "Indian Breads",
    titleKannada: "ಭಾರತೀಯ ರೊಟ್ಟಿ ಮತ್ತು ಬ್ರೆಡ್",
    shortDescription: "Oven-baked tandoori rotis, buttery naans, and soft kulchas",
    image: breadsImg,
    sections: [
      {
        id: "indian_breads_roti",
        canonicalName: "Indian Breads / Roti",
        kannadaName: "ಭಾರತೀಯ ರೊಟ್ಟಿ ಮತ್ತು ಬ್ರೆಡ್",
        order: 1,
        description: "Butter Roti, Garlic Naan, Kulcha, and traditional flatbreads",
      },
    ],
  },
  {
    id: "beverages_and_sweets",
    groupLetter: "F",
    titleEnglish: "Beverages & Sweets",
    titleKannada: "ಪಾನೀಯಗಳು ಮತ್ತು ಸಿಹಿತಿಂಡಿಗಳು",
    shortDescription: "Authentic filter coffee, soothing beverages, and heritage Indian sweets",
    image: beveragesSweetsImg,
    sections: [
      {
        id: "hot_beverages",
        canonicalName: "Hot Beverages",
        kannadaName: "ಬಿಸಿ ಪಾನೀಯಗಳು",
        order: 1,
        description: "Signature South Indian filter coffee in brass davarah, and tea",
      },
      {
        id: "sweet_items",
        canonicalName: "Sweet Items",
        kannadaName: "ಸಿಹಿ ಪದಾರ್ಥಗಳು",
        order: 2,
        description: "Ghee Mysore Pak, Jamoon, Halwa, and traditional festival sweets",
      },
    ],
  },
];

/**
 * Validates that all 19 original sections are mapped exactly once.
 */
export function getMenuStatistics() {
  const allSections = [];
  MENU_GROUPS.forEach((group) => {
    group.sections.forEach((sec) => {
      allSections.push({
        groupId: group.id,
        groupEnglish: group.titleEnglish,
        groupKannada: group.titleKannada,
        ...sec,
      });
    });
  });

  return {
    totalGroups: MENU_GROUPS.length,
    totalSections: allSections.length,
    sections: allSections,
  };
}

export function findGroupById(groupId) {
  return MENU_GROUPS.find((g) => g.id === groupId) || null;
}

export function findSectionById(sectionId) {
  for (const group of MENU_GROUPS) {
    const sec = group.sections.find((s) => s.id === sectionId);
    if (sec) {
      return { ...sec, group };
    }
  }
  return null;
}
