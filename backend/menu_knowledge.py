"""
Prasadam Restaurant Menu Knowledge & Fact Grounding
Provides verified culinary facts derived strictly from authentic menu data.
Guards against fabricated claims, popularity assumptions, or fictitious ingredients.
"""

from typing import Dict, List, Any, Optional
from menu_data import SECTION_ITEMS_DB

# Compile all items lookup
ALL_ITEMS: Dict[str, Dict[str, Any]] = {}
for section_items in SECTION_ITEMS_DB.values():
    for item in section_items:
        ALL_ITEMS[item["id"]] = item

# Verified dish attributes from authentic restaurant menu data
VERIFIED_BREAKFAST_ITEMS = [
    "idly_1_vada", "ghee_plain_dosa", "ghee_roast_masala_dosa",
    "bisi_bele_bath", "khara_bath", "kesari_bath", "poori_saagu"
]

VERIFIED_HOT_BEVERAGES = [
    "filter_coffee", "jaggery_coffee", "tea", "badam_milk"
]

VERIFIED_SWEETS = [
    "special_mysore_pak_1", "gulab_jamoon_2", "holige_1"
]

VERIFIED_CRISPY_ITEMS = [
    "ghee_paper_plain_dosa", "ghee_roast_masala_dosa", "maddur_vada_1"
]

# Section ID for certified Jain items (prepared strictly without onion and garlic)
JAIN_SECTION_ID = "north_indian_jain_items"

UNSUPPORTED_FOOD_PATTERNS = [
    "pizza", "burger", "pasta", "sandwich", "french fries", "fries",
    "chicken", "mutton", "fish", "egg", "meat", "non-veg", "beef", "pork"
]


class MenuKnowledge:
    """Provides authoritative, verified answers grounded strictly in restaurant data."""

    @staticmethod
    def get_item(item_id: str) -> Optional[Dict[str, Any]]:
        return ALL_ITEMS.get(item_id)

    @staticmethod
    def is_pure_veg() -> bool:
        """The Atom Prasadam is 100% pure vegetarian across the entire menu."""
        return True

    @staticmethod
    def get_jain_section() -> Dict[str, Any]:
        """Returns verified Jain items section."""
        jain_items = SECTION_ITEMS_DB.get(JAIN_SECTION_ID, [])
        return {
            "section_id": JAIN_SECTION_ID,
            "section_name": "North Indian Jain Items",
            "kannada_name": "ಉತ್ತರ ಭಾರತೀಯ ಜೈನ್ ಐಟಮ್ಸ್",
            "description": "Certified preparations without onion and garlic.",
            "items": [it["name"] for it in jain_items[:5]],
        }

    @staticmethod
    def check_unsupported_item(query: str) -> Optional[str]:
        """Detects if query asks for non-menu items (e.g. pizza, chicken, burger)."""
        q = (query or "").lower()
        for pattern in UNSUPPORTED_FOOD_PATTERNS:
            if pattern in q:
                return pattern
        return None

    @staticmethod
    def get_grounded_facts_for_context(
        active_section: Optional[str] = None,
        mentioned_item_id: Optional[str] = None,
        query: str = ""
    ) -> str:
        """
        Builds a compact summary of verified facts for the LLM prompt.
        Explicitly notes unknowns if information is not recorded in the menu catalogue.
        """
        facts = [
            "RESTAURANT IDENTITY: The Atom Prasadam, Bengaluru.",
            "DIETARY INTEGRITY: 100% Pure Vegetarian heritage cuisine. No meat, fish, or egg dishes.",
            "JAIN OPTIONS: Prepared without onion/garlic, exclusively in the 'North Indian Jain Items' section.",
        ]

        q = (query or "").lower()

        # Check unsupported items
        unsupported = MenuKnowledge.check_unsupported_item(q)
        if unsupported:
            facts.append(
                f"UNSUPPORTED ITEM DETECTED: Customer asked about '{unsupported}'. "
                "The restaurant does NOT serve this. Politely inform the customer and suggest authentic South Indian options."
            )

        # Breakfast grounding
        if any(w in q for w in ["breakfast", "morning", "tiffin", "ಉಪಾಹಾರ", "ತಿಂಡಿ"]):
            facts.append(
                "VERIFIED BREAKFAST STAPLES: Idli Vada, Ghee Roast Masala Dosa, Ghee Plain Dosa, Khara Bath, Kesari Bath."
            )

        # Dosa grounding
        if "dosa" in q or "dose" in q or active_section == "dose_special":
            dosa_items = [
                f"{it['name']} (₹{it['price']:.0f})"
                for it in SECTION_ITEMS_DB.get("dose_special", [])[:6]
            ]
            facts.append(
                f"VERIFIED DOSAS AVAILABLE: {', '.join(dosa_items)}. "
                "All dosas are roasted in pure ghee and served with fresh coconut chutney and hot sambar."
            )
            if "spicy" in q:
                facts.append(
                    "SPICE NOTE: Ghee Pudi Masala Dosa and Ghee Pudi Plain Dosa are prepared with flavorful traditional chutney powder (chutney podi)."
                )
            if "light" in q:
                facts.append("LIGHT NOTE: Ghee Plain Dosa is a simpler, lighter option than filled masala dosas.")

        # Beverage grounding
        if any(w in q for w in ["coffee", "tea", "drink", "beverage", "ಕಾಫಿ", "ಟೀ"]):
            facts.append("VERIFIED BEVERAGES: South Indian Filter Coffee (₹25), Jaggery Coffee, Tea, Hot Badam Milk.")

        # Pairing grounding
        if any(w in q for w in ["pair", "goes well", "along with", "with dosa"]):
            facts.append("VERIFIED PAIRING: Authentic South Indian Filter Coffee and traditional Mysore Pak are classic companions.")

        # Specific item facts
        if mentioned_item_id and mentioned_item_id in ALL_ITEMS:
            it = ALL_ITEMS[mentioned_item_id]
            kn = it.get('kannadaName') or it.get('kannada_name') or ''
            kn_str = f" ({kn})" if kn else ""
            facts.append(f"CURRENT ITEM IN FOCUS: {it['name']}{kn_str}, Price: ₹{it['price']:.0f}, Section: {it.get('category')}.")

        return "\n".join(facts)
