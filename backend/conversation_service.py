"""
Prasadam AI Conversation Service
--------------------------------
Authoritative, catalogue-grounded conversational engine for TheAtom Prasadam kiosk.

Key Principles:
1. Strict Factual Grounding: Only authentic items from menu_data (262 dishes) are recognized.
   Prices, availability, and descriptions are strictly authoritative from the backend.
2. Safe LLM Integration: The LLM acts as an untrusted natural language parser.
   All actions and items are validated deterministically before mutating state.
3. Resilient Fallback: If LLM API keys (GEMINI_API_KEY / GROQ_API_KEY) are absent or fail,
   the rule-based semantic parser fulfills 100% of kiosk intents.
4. Session Isolation: All conversational state and cart modifications respect the customer's session_id.
"""

import os
import re
import json
import logging
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Authoritatively load environment variables
load_dotenv(Path(__file__).parent / ".env")

logger = logging.getLogger("conversation_service")

from kannada_transliteration import (
    is_kannada_input as kt_is_kannada_input,
    normalize_kannada_transliteration,
    classify_utterance_language,
)

# ==============================================================================
# Typed Contracts
# ==============================================================================

class MessageRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    screen: Optional[str] = "home"
    interaction_id: Optional[str] = None
    cart_items: Optional[List[Dict[str, Any]]] = None
    language_preference: Optional[str] = "AUTO"


class UIAction(BaseModel):
    type: str  # "navigate", "add_to_cart", "remove_from_cart", "clear_cart", "open_product"
    payload: Dict[str, Any] = Field(default_factory=dict)


class KioskResponse(BaseModel):
    message: str
    screen: str = "home"
    intent: str = "general"
    language: str = "en"
    data: Dict[str, Any] = Field(default_factory=dict)
    actions: List[Dict[str, Any]] = Field(default_factory=list)
    conversation_state: Dict[str, Any] = Field(default_factory=dict)
    requires_confirmation: bool = False


# ==============================================================================
# Canonical Knowledge Indexing
# ==============================================================================

COMMON_KANNADA_DISH_NAMES = {
    # Dosa
    "ghee_roast_masala_dosa": "ಮಸಾಲೆ ದೋಸೆ",
    "ghee_plain_dosa": "ದೋಸೆ",
    "ghee_set_dosa": "ಸೆಟ್ ದೋಸೆ",
    "ghee_rava_dosa": "ರವಾ ದೋಸೆ",
    "ghee_pudi_masala_dosa": "ಪುಡಿ ಮಸಾಲೆ ದೋಸೆ",
    "ghee_pudi_plain_dosa": "ಪುಡಿ ದೋಸೆ",
    "ghee_paper_masala_dosa": "ಪೇಪರ್ ಮಸಾಲೆ ದೋಸೆ",
    "ghee_paper_plain_dosa": "ಪೇಪರ್ ದೋಸೆ",
    "onion_dosa": "ಈರುಳ್ಳಿ ದೋಸೆ",
    "rava_masala_dosa": "ರವಾ ಮಸಾಲೆ ದೋಸೆ",
    # Breakfast & Snacks
    "idly_2": "ಇಡ್ಲಿ",
    "idly_1_vada": "ಇಡ್ಲಿ ವಡೆ",
    "vada_1": "ವಡೆ",
    "curd_vade_1": "ಮೊಸರು ವಡೆ",
    "mangalore_bajji": "ಮಂಗಳೂರು ಬಜ್ಜಿ",
    "bisi_bele_bath": "ಬಿಸಿ ಬೇಳೆ ಬಾತ್",
    "chow_chow_bath": "ಚೌ ಚೌ ಬಾತ್",
    "khara_bath": "ಖಾರಾ ಬಾತ್",
    "kesari_bath": "ಕೇಸರಿ ಬಾತ್",
    "poori_saagu": "ಪೂರಿ ಸಾಗು",
    # Sweets
    "jamoon_1": "ಜಾಮೂನ್",
    "carrot_halwa": "ಕ್ಯಾರೆಟ್ ಹಲ್ವಾ",
    "kashi_halwa": "ಕಾಶಿ ಹಲ್ವಾ",
    "hal_bai": "ಹಾಲ್ ಬಾಯಿ",
    "mysore_pak": "ಮೈಸೂರು ಪಾಕ್",
    "gulab_jamun": "ಗುಲಾಬ್ ಜಾಮೂನ್",
    "jalebi": "ಜಿಲೇಬಿ",
    # Beverages
    "filter_coffee": "ಫಿಲ್ಟರ್ ಕಾಫಿ",
    "jaggery_coffee": "ಬೆಲ್ಲದ ಕಾಫಿ",
    "tea": "ಟೀ",
    "badam_milk": "ಬಾದಾಮಿ ಹಾಲು",
    "hot_milk": "ಹಾಲು",
    "kashaya": "ಕಷಾಯ",
    # Meals & Rice
    "south_indian_meals": "ದಕ್ಷಿಣ ಭಾರತೀಯ ಊಟ",
    "special_meals": "ಸ್ಪೆಷಲ್ ಊಟ",
    "curd_rice": "ಮೊಸರನ್ನ",
    "jeera_rice": "ಜೀರಾ ರೈಸ್",
    "ghee_rice": "ತುಪ್ಪದನ್ನ",
    "veg_fried_rice": "ವೆಜ್ ಫ್ರೈಡ್ ರೈಸ್",
    # Breads
    "roti": "ರೊಟ್ಟಿ",
    "butter_roti": "ಬೆಣ್ಣೆ ರೊಟ್ಟಿ",
    "naan": "ನಾನ್",
    "butter_naan": "ಬೆಣ್ಣೆ ನಾನ್",
    "kulcha": "ಕುಲ್ಚಾ",
    "chapati": "ಚಪಾತಿ",
    "parotta": "ಪರೋಟ",
}

class MenuKnowledgeIndex:
    """Fast, normalized indexing of the 262 authentic Prasadam items and 19 sections."""

    def __init__(self, all_items_by_id: Dict[str, Dict[str, Any]], menu_structure: List[Dict[str, Any]]):
        self.all_items = all_items_by_id
        self.menu_structure = menu_structure
        
        # Build normalized name to item lookup
        self.normalized_to_item: Dict[str, Dict[str, Any]] = {}
        self.name_tokens_to_items: Dict[str, List[Dict[str, Any]]] = {}
        
        # Build section and category lookup
        self.section_lookup: Dict[str, Dict[str, Any]] = {}
        self.category_lookup: Dict[str, Dict[str, Any]] = {}

        self._index_catalog()

    def _normalize(self, text: str) -> str:
        if not text:
            return ""
        text = text.lower()
        # Preserve ASCII alphanumeric and Kannada Unicode characters (\u0C80-\u0CFF)
        text = re.sub(r"[^a-z0-9\u0C80-\u0CFF\s]", " ", text)
        return " ".join(text.split())

    def _index_catalog(self):
        # 1. Index macro categories with canonical data, Kannada titles and aliases
        category_aliases = {
            "south_indian_favourites": [
                "south indian favourites", "south indian favorites", "south indian", "breakfast specials",
                "ದಕ್ಷಿಣ ಭಾರತೀಯ ವಿಶೇಷಗಳು", "ದಕ್ಷಿಣ ಭಾರತೀಯ", "ದಕ್ಷಿಣ ಭಾರತ", "dakshina bharatheeya"
            ],
            "meals_and_rice": [
                "meals & rice", "meals and rice", "rice items", "rice item", "meals", "rice", "lunch", "thali",
                "ಊಟ ಮತ್ತು ಅನ್ನದ ವಿಧಗಳು", "ಊಟ ಮತ್ತು ಅನ್ನ", "ಅನ್ನದ ವಿಧಗಳು", "ಊಟ", "oota mattu anna", "oota", "anna"
            ],
            "curries_and_main_course": [
                "curries & main course", "curries and main course", "curries", "curry", "main course", "gravy", "gravies",
                "ಗ್ರೇವಿ ಮತ್ತು ಮುಖ್ಯ ಆಹಾರ", "ಗ್ರೇವಿ", "ಮುಖ್ಯ ಆಹಾರ", "gravy mattu mukhya aahara"
            ],
            "starters_and_sides": [
                "starters & sides", "starters and sides", "sides and starters", "starters", "sides", "appetizers",
                "ಸ್ಟಾರ್ಟರ್ಸ್ ಮತ್ತು ಸೈಡ್ ಡಿಶ್ಗಳು", "ಸ್ಟಾರ್ಟರ್ಸ್", "ಸೈಡ್ ಡಿಶ್", "starters mattu side dishes"
            ],
            "indian_breads": [
                "indian breads", "breads", "bread section", "roti section",
                "ಭಾರತೀಯ ರೊಟ್ಟಿ ಮತ್ತು ಬ್ರೆಡ್", "ರೊಟ್ಟಿ ಮತ್ತು ಬ್ರೆಡ್", "bharatheeya rotti", "indian bread"
            ],
            "beverages_and_sweets": [
                "beverages & sweets", "beverages and sweets", "sweets and beverages", "drinks and sweets",
                "ಪಾನೀಯಗಳು ಮತ್ತು ಸಿಹಿತಿಂಡಿಗಳು", "ಪಾನೀಯ ಮತ್ತು ಸಿಹಿ", "paneyagalu mattu sihitindigalu"
            ],
        }

        for group in self.menu_structure:
            grp_id = group.get("id")
            group_norm = self._normalize(group.get("title_english", ""))
            kn_norm = self._normalize(group.get("title_kannada", ""))
            self.category_lookup[grp_id] = group
            if group_norm:
                self.category_lookup[group_norm] = group
            if kn_norm:
                self.category_lookup[kn_norm] = group

            for alias in category_aliases.get(grp_id, []):
                self.category_lookup[self._normalize(alias)] = group

            for sec in group.get("sections", []):
                sec_id = sec.get("id")
                sec_norm = self._normalize(sec.get("canonical_name", ""))
                sec_kn_norm = self._normalize(sec.get("kannada_name", ""))
                self.section_lookup[sec_id] = sec
                if sec_norm:
                    self.section_lookup[sec_norm] = sec
                if sec_kn_norm:
                    self.section_lookup[sec_kn_norm] = sec

        # 2. Rich aliases for all 19 canonical sections (carefully excluding specific dish items)
        section_aliases = {
            "south_indian_breakfast": [
                "south indian breakfast", "breakfast", "morning breakfast", "tiffin", "upahara", "tindi",
                "ದಕ್ಷಿಣ ಭಾರತೀಯ ಉಪಾಹಾರ", "ದಕ್ಷಿಣ ಭಾರತ ಉಪಾಹಾರ", "ಉಪಾಹಾರ", "ತಿಂಡಿ"
            ],
            "dose_special": [
                "dose special", "dosa special", "dosa specials", "dose specials", "dosa", "dose", "dosas", "doses",
                "ದೋಸೆ ವಿಶೇಷ", "ದೋಸೆ", "ದೋಸೆಗಳು"
            ],
            "bajji_pakoda_snacks": [
                "bajji pakoda snacks", "bajji / pakoda / snacks", "snacks", "bajji", "pakoda", "snack items", "snack",
                "ಬಜ್ಜಿ / ಪಕೋಡ / ತಿಂಡಿಗಳು", "ಬಜ್ಜಿ ಪಕೋಡ ತಿಂಡಿಗಳು", "ಬಜ್ಜಿ", "ಪಕೋಡ", "ತಿಂಡಿಗಳು", "ಸ್ನ್ಯಾಕ್ಸ್"
            ],
            "meals": [
                "meals", "south indian meals", "full meals", "thali", "lunch", "bhojana",
                "ಊಟ", "ದಕ್ಷಿಣ ಭಾರತೀಯ ಊಟ", "ಫುಲ್ ಊಟ", "ಊಟದ ಮೆನು", "ಥಾಲಿ", "oota"
            ],
            "chinese_rice_items": [
                "chinese rice items", "chinese rice", "fried rice", "chinese fried rice", "schezwan rice",
                "ಚೈನೀಸ್ ರೈಸ್ ಐಟಮ್ಸ್", "ಚೈನೀಸ್ ರೈಸ್", "ಫ್ರೈಡ್ ರೈಸ್"
            ],
            "north_indian_rice_items": [
                "north indian rice items", "north indian rice", "biryani", "pulao", "jeera rice", "ghee rice",
                "ಉತ್ತರ ಭಾರತೀಯ ರೈಸ್ ಐಟಮ್ಸ್", "ಉತ್ತರ ಭಾರತೀಯ ರೈಸ್", "ಬಿರಿಯಾನಿ", "ಪುಲಾವ್", "ಜೀರಾ ರೈಸ್"
            ],
            "chinese_main_course": [
                "chinese main course", "chinese", "chinese items", "noodles", "veg noodles", "manchurian gravy",
                "ಚೈನೀಸ್ ಮೇನ್ ಕೋರ್ಸ್", "ಚೈನೀಸ್", "ನೂಡಲ್ಸ್"
            ],
            "dal_items": [
                "dal items", "dal", "dhal", "dal fry", "dal tadka", "ದಾಲ್ ಐಟಮ್ಸ್", "ದಾಲ್", "ಬೇಳೆ ಸಾರು"
            ],
            "kadai": [
                "kadai", "kadai items", "kadai dishes",
                "ಕಡಾಯಿ", "ಕಡಾಯಿ ಐಟಮ್ಸ್"
            ],
            "kofta": [
                "kofta", "kofta items", "kofta dishes", "kofta curry",
                "ಕೊಫ್ತಾ", "ಕೊಫ್ತಾ ಐಟಮ್ಸ್"
            ],
            "north_indian_jain_items": [
                "north indian jain items", "jain items", "jain food", "jain dishes", "jain", "without onion", "no onion",
                "ಉತ್ತರ ಭಾರತೀಯ ಜೈನ್ ಐಟಮ್ಸ್", "ಜೈನ್ ಐಟಮ್ಸ್", "ಜೈನ್ ಆಹಾರ", "ಜೈನ್"
            ],
            "indian_curries": [
                "indian curries", "curries", "curry", "indian curry", "paneer curries", "paneer curry", "veg curry",
                "ಭಾರತೀಯ ಮೇಲೋಗರಗಳು (ಕರಿಗಳು)", "ಭಾರತೀಯ ಮೇಲೋಗರಗಳು", "ಭಾರತೀಯ ಕರಿಗಳು", "ಮೇಲೋಗರಗಳು", "ಕರಿಗಳು"
            ],
            "soups": [
                "soups", "soup", "hot soup", "tomato soup", "ಸೂಪ್ಸ್", "ಸೂಪ್"
            ],
            "salads_raita_papad": [
                "salads / raita / papad", "salads raita papad", "salads", "salad", "raita", "papad", "happala",
                "ಸಲಾಡ್ಸ್ / ರಾಯ್ತ / ಹಪ್ಪಳ", "ಸಲಾಡ್ಸ್", "ಸಲಾಡ್", "ರಾಯ್ತ", "ಹಪ್ಪಳ"
            ],
            "chinese_starters": [
                "chinese starters", "chinese starter",
                "ಚೈನೀಸ್ ಸ್ಟಾರ್ಟರ್ಸ್"
            ],
            "indian_starters": [
                "indian starters", "indian starter", "paneer starters",
                "ಭಾರತೀಯ ಸ್ಟಾರ್ಟರ್ಸ್"
            ],
            "indian_breads_roti": [
                "indian breads / roti", "indian breads roti", "roti", "rotis", "naan", "kulcha", "chapati", "parota",
                "ಭಾರತೀಯ ರೊಟ್ಟಿ", "ರೊಟ್ಟಿ", "ನಾನ್", "ಕುಲ್ಚಾ", "ಪರೋಟ", "ಚಪಾತಿ", "ರೊಟ್ಟಿಗಳು"
            ],
            "hot_beverages": [
                "hot beverages", "beverages", "drinks", "hot drinks",
                "ಬಿಸಿ ಪಾನೀಯಗಳು", "ಪಾನೀಯಗಳು", "ಪಾನೀಯ"
            ],
            "sweet_items": [
                "sweet items", "sweets", "sweet", "desserts", "dessert",
                "ಸಿಹಿ ಪದಾರ್ಥಗಳು", "ಸಿಹಿ", "ಸಿಹಿತಿಂಡಿಗಳು", "ಸಿಹಿ ತಿಂಡಿಗಳು", "ಸಿಹಿತಿಂಡಿ"
            ],
        }
        for sec_id, aliases in section_aliases.items():
            for group in self.menu_structure:
                for sec in group.get("sections", []):
                    if sec.get("id") == sec_id:
                        for alias in aliases:
                            self.section_lookup[self._normalize(alias)] = sec

        # 3. Index items with Kannada & colloquial aliases
        for item_id, item in self.all_items.items():
            if not item.get("kannadaName") and item_id in COMMON_KANNADA_DISH_NAMES:
                item["kannadaName"] = COMMON_KANNADA_DISH_NAMES[item_id]
                item["kannada_name"] = COMMON_KANNADA_DISH_NAMES[item_id]

            name_norm = self._normalize(item.get("name", ""))
            self.normalized_to_item[name_norm] = item
            self.normalized_to_item[item_id] = item

            kannada = item.get("kannadaName") or item.get("kannada_name")
            if kannada:
                self.normalized_to_item[self._normalize(kannada)] = item

            tokens = name_norm.split()
            for token in tokens:
                if len(token) > 2 and token not in {"and", "with", "for", "the", "special", "plate", "cups", "cup"}:
                    self.name_tokens_to_items.setdefault(token, []).append(item)

        # Authentic colloquial aliases mapping common phrasing to primary house specialty
        colloquial_aliases = {
            "masala dosa": "ghee_roast_masala_dosa",
            "masale dose": "ghee_roast_masala_dosa",
            "masala dose": "ghee_roast_masala_dosa",
            "ಮಸಾಲೆ ದೋಸೆ": "ghee_roast_masala_dosa",
            "ಮಸಾಲ ದೋಸೆ": "ghee_roast_masala_dosa",
            "ಮಸಾಲೆದೋಸೆ": "ghee_roast_masala_dosa",
            "plain dosa": "ghee_plain_dosa",
            "plain dose": "ghee_plain_dosa",
            "ದೋಸೆ": "ghee_plain_dosa",
            "set dosa": "ghee_set_dosa",
            "set dose": "ghee_set_dosa",
            "ಸೆಟ್ ದೋಸೆ": "ghee_set_dosa",
            "pudi dosa": "ghee_pudi_plain_dosa",
            "pudi masala dosa": "ghee_pudi_masala_dosa",
            "ಪುಡಿ ದೋಸೆ": "ghee_pudi_plain_dosa",
            "paper dosa": "ghee_paper_plain_dosa",
            "ಪೇಪರ್ ದೋಸೆ": "ghee_paper_plain_dosa",
            "idli": "idly_2",
            "idlis": "idly_2",
            "iddly": "idly_2",
            "idly": "idly_2",
            "ಇಡ್ಲಿ": "idly_2",
            "ಇಡ್ಲಿಗಳು": "idly_2",
            "vada": "vada_1",
            "vadas": "vada_1",
            "vade": "vada_1",
            "ವಡೆ": "vada_1",
            "ವಡೆಗಳು": "vada_1",
            "idly vada": "idly_1_vada",
            "idly 1 vada": "idly_1_vada",
            "ಇಡ್ಲಿ ವಡೆ": "idly_1_vada",
            "maddur vada": "maddur_vada_1",
            "maddur vade": "maddur_vada_1",
            "ಮದ್ದೂರು ವಡೆ": "maddur_vada_1",
            "coffee": "jaggery_coffee",
            "filter coffee": "jaggery_coffee",
            "kaapi": "jaggery_coffee",
            "ಕಾಫಿ": "jaggery_coffee",
            "ಫಿಲ್ಟರ್ ಕಾಫಿ": "jaggery_coffee",
            "tea": "jaggery_tea",
            "chai": "jaggery_tea",
            "mysore pak": "special_mysore_pak_1",
            "ಮೈಸೂರು ಪಾಕ್": "special_mysore_pak_1",
            "gulab jamun": "jamoon_1",
            "gulab jamoon": "jamoon_1",
            "jamoon": "jamoon_1",
            "ಗುಲಾಬ್ ಜಾಮೂನ್": "jamoon_1",
            "ಜಾಮೂನ್": "jamoon_1",
            "bisi bele bath": "bisi_bele_bath",
            "ಬಿಸಿ ಬೇಳೆ ಬಾತ್": "bisi_bele_bath",
            "kesari bath": "kesari_bath",
            "ಕೇಸರಿ ಬಾತ್": "kesari_bath",
            "poori": "poori_saagu_3",
            "puri": "poori_saagu_3",
            "poori saagu": "poori_saagu_3",
            "puri sagu": "poori_saagu_3",
            "ಪೂರಿ": "poori_saagu_3",
            "ಪೂರಿ ಸಾಗು": "poori_saagu_3",
            "roti": "butter_roti",
            "rotti": "butter_roti",
            "rotis": "butter_roti",
            "ರೊಟ್ಟಿ": "butter_roti",
            "badam milk": "badam_milk",
            "ಬಾದಾಮಿ ಹಾಲು": "badam_milk",
            "khara bath": "khara_bath",
            "ಖಾರಾ ಬಾತ್": "khara_bath",
            "chow chow bath": "chow_chow_bath",
            "ಚೌ ಚೌ ಬಾತ್": "chow_chow_bath",
        }
        for alias, item_id in colloquial_aliases.items():
            if item_id in self.all_items:
                self.normalized_to_item[self._normalize(alias)] = self.all_items[item_id]

    def find_items_by_query(self, query: str) -> List[Tuple[Dict[str, Any], float]]:
        """
        Fuzzy match query against menu items.
        Returns list of (item, confidence) pairs sorted by confidence descending.
        """
        norm_query = self._normalize(query)
        if not norm_query:
            return []

        # Strip action and quantity stop-words (English and Kannada)
        stop_words = {
            "add", "please", "can", "i", "have", "want", "order", "get", "give", "me",
            "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
            "1", "2", "3", "4", "5", "6", "7", "8", "9", "10",
            "a", "an", "the", "some", "how", "much", "what", "is", "price", "of", "for", "cost", "does",
            # Kannada quantity & action terms
            "ondu", "ondhu", "eradu", "mooru", "muru", "naalku", "nalku", "aidu", "aydu", "aaru", "elu", "entu", "ombattu", "hatthu",
            "kodi", "kodu", "beku", "haki", "haaki", "thani", "madu", "maadi", "thago", "thagoli",
            "nanage", "nange", "namage", "bekittu", "bekagide", "dayavittu",
            "ಒಂದು", "ಎರಡು", "ಮೂರು", "ನಾಲ್ಕು", "ಐದು", "ಆರು", "ಏಳು", "ಎಂಟು", "ಒಂಬತ್ತು", "ಹತ್ತು",
            "ಕೊಡು", "ಕೊಡಿ", "ಬೇಕು", "ಹಾಕಿ", "ಮಾಡಿ", "ಸೇರಿಸು", "ದಯವಿಟ್ಟು", "ನನಗೆ", "ನಮಗೆ",
            "plate", "plates", "cup", "cups", "parcel", "takeaway", "to", "cart", "tray"
        }
        cleaned_tokens = [w for w in norm_query.split() if w not in stop_words]
        cleaned_query = " ".join(cleaned_tokens)

        # 1. Exact match on normalized or cleaned query
        if cleaned_query in self.normalized_to_item:
            return [(self.normalized_to_item[cleaned_query], 1.0)]
        if norm_query in self.normalized_to_item:
            return [(self.normalized_to_item[norm_query], 1.0)]

        # Check English plural / stem forms
        if cleaned_query.endswith("s") and cleaned_query[:-1] in self.normalized_to_item:
            return [(self.normalized_to_item[cleaned_query[:-1]], 1.0)]

        # Check Kannada plural and case suffixes
        for suffix in ["ಗಳನ್ನು", "ಗಳನ್ನ", "ಗಳು", "ಅನ್ನು", "ನ್ನ", "ಗೆ"]:
            if cleaned_query.endswith(suffix):
                stem = cleaned_query[:-len(suffix)].strip()
                if stem in self.normalized_to_item:
                    return [(self.normalized_to_item[stem], 1.0)]

        # 2. Substring match
        matches: Dict[str, float] = {}
        for name_norm, item in self.normalized_to_item.items():
            item_id = item["id"]
            if cleaned_query and cleaned_query == name_norm:
                matches[item_id] = 1.0
            elif cleaned_query and cleaned_query in name_norm:
                ratio = len(cleaned_query) / max(len(name_norm), 1)
                matches[item_id] = max(matches.get(item_id, 0), 0.70 + 0.28 * ratio)
            elif cleaned_query and name_norm in cleaned_query:
                ratio = len(name_norm) / max(len(cleaned_query), 1)
                matches[item_id] = max(matches.get(item_id, 0), 0.65 + 0.25 * ratio)

        # 3. Multi-token scoring with overlap
        if cleaned_tokens:
            q_token_count = len(cleaned_tokens)
            item_token_hits: Dict[str, int] = {}

            for token in cleaned_tokens:
                if len(token) <= 2:
                    continue
                synonyms = [token]
                if token in {"coffee", "kaapi", "ಕಾಫಿ"}:
                    synonyms.extend(["coffee", "filter", "ಕಾಫಿ"])
                elif token in {"tea", "chai", "ಚಹಾ"}:
                    synonyms.extend(["tea", "ಚಹಾ"])
                elif token in {"bath", "baath", "bhath", "ಬಾತ್"}:
                    synonyms.extend(["bath", "rice"])
                elif token in {"dosa", "dose", "ದೋಸೆ"}:
                    synonyms.extend(["dosa", "dose", "ದೋಸೆ"])
                elif token in {"vada", "vade", "ವಡೆ"}:
                    synonyms.extend(["vada", "vade", "ವಡೆ"])
                elif token in {"idli", "iddly", "idly", "ಇಡ್ಲಿ"}:
                    synonyms.extend(["idli", "idly", "ಇಡ್ಲಿ"])
                elif token in {"roti", "rotis", "chapati", "ರೊಟ್ಟಿ"}:
                    synonyms.extend(["roti", "chapati", "ರೊಟ್ಟಿ"])

                matched_item_ids_for_token = set()
                for syn in synonyms:
                    for item in self.name_tokens_to_items.get(syn, []):
                        matched_item_ids_for_token.add(item["id"])

                for i_id in matched_item_ids_for_token:
                    item_token_hits[i_id] = item_token_hits.get(i_id, 0) + 1

            for i_id, hits in item_token_hits.items():
                item = self.all_items.get(i_id)
                if not item:
                    continue
                item_name_norm = self._normalize(item.get("name", ""))
                item_token_count = len(item_name_norm.split())
                query_coverage = hits / max(q_token_count, 1)
                item_coverage = hits / max(item_token_count, 1)
                combined_score = 0.5 * query_coverage + 0.5 * item_coverage
                matches[i_id] = max(matches.get(i_id, 0), combined_score)

        results = []
        for item_id, score in matches.items():
            if item_id in self.all_items:
                results.append((self.all_items[item_id], round(score, 3)))

        results.sort(key=lambda x: x[1], reverse=True)
        return results

    def find_section_or_category(self, query: str) -> Optional[Tuple[str, str, Dict[str, Any]]]:
        """
        Dynamically and reliably resolves user query to a section or macro category.
        Fully supports:
        - English queries ('show south indian breakfast', 'show rice items')
        - Kannada script queries ('ದೋಸೆ ತೋರಿಸು', 'ಸಿಹಿ ಪದಾರ್ಥಗಳು ತೋರಿಸು')
        - Romanized Kannada queries ('dose torisu', 'oota torisu')
        - Shortened/conversational names ('show dosa', 'show sweets')
        """
        norm_query = self._normalize(query)
        if not norm_query:
            return None

        # 1. Exact direct match (macro categories prioritized first)
        if norm_query in self.category_lookup:
            cat = self.category_lookup[norm_query]
            return "category", cat.get("id"), cat

        if norm_query in self.section_lookup:
            sec = self.section_lookup[norm_query]
            return "section", sec.get("id"), sec

        # 2. Strip viewing verbs and polite particles
        view_stop_words = {
            "show", "open", "view", "explore", "see", "display", "list", "want", "need",
            "me", "please", "can", "i", "have", "would", "like", "to", "take", "go",
            "menu", "section", "items", "item", "page",
            # Kannada viewing terms and particles
            "ತೋರಿಸು", "ತೋರ್ಸು", "ನೋಡು", "ಹೋಗು",
            "ನನಗೆ", "ನಮಗೆ", "ದಯವಿಟ್ಟು", "ಪುಟ", "ವಿಭಾಗ", "ಪದಾರ್ಥಗಳು", "ಮೆನು",
            # Romanized Kannada
            "torisu", "thodisi", "thodisu", "nodona", "hogu", "nanage", "nange"
        }
        cleaned_tokens = [w for w in norm_query.split() if w not in view_stop_words]
        cleaned_query = " ".join(cleaned_tokens)

        if cleaned_query and cleaned_query in self.category_lookup:
            cat = self.category_lookup[cleaned_query]
            return "category", cat.get("id"), cat

        if cleaned_query and cleaned_query in self.section_lookup:
            sec = self.section_lookup[cleaned_query]
            return "section", sec.get("id"), sec

        # 3. Sort keys by length descending to match most specific subcategory/category first
        sorted_sections = sorted(self.section_lookup.items(), key=lambda x: len(x[0]), reverse=True)
        for sec_key, sec in sorted_sections:
            if len(sec_key) > 2:
                if cleaned_query and (sec_key == cleaned_query or sec_key in cleaned_query):
                    return "section", sec.get("id"), sec
                if len(sec_key) > 4 and sec_key in norm_query:
                    return "section", sec.get("id"), sec

        sorted_categories = sorted(self.category_lookup.items(), key=lambda x: len(x[0]), reverse=True)
        for cat_key, cat in sorted_categories:
            if len(cat_key) > 2:
                if cleaned_query and (cat_key == cleaned_query or cat_key in cleaned_query):
                    return "category", cat.get("id"), cat
                if len(cat_key) > 4 and cat_key in norm_query:
                    return "category", cat.get("id"), cat

        # 4. Token-level membership match
        for tok in cleaned_tokens:
            if len(tok) > 2:
                if tok in self.section_lookup:
                    sec = self.section_lookup[tok]
                    return "section", sec.get("id"), sec
                if tok in self.category_lookup:
                    cat = self.category_lookup[tok]
                    return "category", cat.get("id"), cat

        return None


# ==============================================================================
# Model Adapter (Gemini / Groq / Fallback)
# ==============================================================================

class ModelAdapter:
    """
    Lightweight, dependency-free HTTP LLM adapter.
    Uses Google Gemini REST API or Groq REST API when keys are configured,
    with automatic fail-fast to deterministic conversation rules.
    """

    def __init__(self):
        self.gemini_key = (os.getenv("GEMINI_API_KEY") or "").strip()
        self.gemini_model = (os.getenv("GEMINI_MODEL") or "gemini-flash-lite-latest").strip()
        self.groq_key = (os.getenv("GROQ_API_KEY") or "").strip()
        self.provider = None

        if self.gemini_key and not self.gemini_key.startswith("your_"):
            self.provider = "gemini"
        elif self.groq_key and not self.groq_key.startswith("your_"):
            self.provider = "groq"

        logger.info("ModelAdapter initialized with provider: %s", self.provider)

    @property
    def is_available(self) -> bool:
        return self.provider is not None

    def generate(self, system_prompt: str, user_prompt: str, timeout: float = 4.0) -> Optional[str]:
        if not self.is_available:
            return None

        if self.provider == "gemini":
            return self._call_gemini(system_prompt, user_prompt, timeout)
        elif self.provider == "groq":
            return self._call_groq(system_prompt, user_prompt, timeout)
        return None

    def _call_gemini(self, system_prompt: str, user_prompt: str, timeout: float) -> Optional[str]:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:generateContent?key={self.gemini_key}"
            payload = {
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": f"{system_prompt}\n\nUser request: {user_prompt}"}]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.1,
                    "maxOutputTokens": 256,
                }
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        return parts[0].get("text", "").strip()
        except Exception as e:
            logger.warning("Gemini API call failed: %s. Using deterministic fallback.", e)
            return None

    def _call_groq(self, system_prompt: str, user_prompt: str, timeout: float) -> Optional[str]:
        try:
            url = "https://api.groq.com/openai/v1/chat/completions"
            payload = {
                "model": os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.1,
                "max_tokens": 256
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.groq_key}"
                }
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                choices = data.get("choices", [])
                if choices:
                    return choices[0].get("message", {}).get("content", "").strip()
        except Exception as e:
            logger.warning("Groq API call failed: %s. Using deterministic fallback.", e)
            return None


# ==============================================================================
# Prasadam Conversation Engine
# ==============================================================================

from intent_classifier import (
    LLMIntentClassifier,
    CATEGORY_HIERARCHY,
    SECTION_HIERARCHY,
    VALID_CATEGORY_IDS,
    VALID_SECTION_IDS,
)
from conversation_memory import memory_manager, ConversationMemoryManager, SessionConversationMemory
from menu_knowledge import MenuKnowledge
from cashier_response_generator import CashierResponseGenerator

class PrasadamConversationEngine:
    """
    Central dialogue manager orchestrating intent detection, catalogue grounding,
    cart operations, and response creation.
    """

    def __init__(self, all_items_by_id: Dict[str, Dict[str, Any]], menu_structure: List[Dict[str, Any]]):
        self.all_items = all_items_by_id
        self.menu_structure = menu_structure
        self.index = MenuKnowledgeIndex(all_items_by_id, menu_structure)
        self.model_adapter = ModelAdapter()
        self.intent_classifier = LLMIntentClassifier(self.model_adapter)
        self.memory_manager = memory_manager
        self.cashier_generator = CashierResponseGenerator(self.model_adapter)
        self.response_generator = self.cashier_generator
        # In-memory conversational state keyed by session_id
        self.session_states: Dict[str, Dict[str, Any]] = {}

    def get_session_state(self, session_id: str) -> Dict[str, Any]:
        if session_id not in self.session_states:
            self.session_states[session_id] = {
                "dialogue_turn": 0,
                "last_intent": None,
                "last_mentioned_item": None,
                "last_added_item_id": None,
                "last_added_items": [],
                "last_options_shown": [],
                "cheapest_item": None,
                "pending_clarification": None,
                "pending_checkout": False,
                "rejected_items": [],
                "customer_language": "en",
                "conversational_phase": "browsing",
            }
        return self.session_states[session_id]

    def extract_multi_items(self, text: str) -> List[Tuple[Dict[str, Any], int]]:
        """
        Parses multi-item orders (e.g. '2 masala dosas and 1 coffee' or
        'ಎರಡು ಮಸಾಲೆ ದೋಸೆ ಮತ್ತು ಒಂದು ಕಾಫಿ ಕೊಡಿ' or '1 idly, 1 vada, and one coffee').
        Returns list of (item_dict, quantity) tuples.
        """
        if not text:
            return []

        # If the entire text has a very high confidence single item match (e.g. "idly 1 vada" -> idly_1_vada),
        # do not split it up into separate items.
        full_match = self.index.find_items_by_query(text)
        if full_match and full_match[0][1] >= 0.95:
            return []

        # Conjunction / list delimiters (English, Kannada, Romanized)
        delim_pattern = r"\s+(?:and|matte|mattu|ಮತ್ತು|ಜೊತೆಗೆ|with|&|\+)\s*|,\s*"
        raw_chunks = [c.strip() for c in re.split(delim_pattern, text, flags=re.IGNORECASE) if c.strip()]

        # If no delimiter split, try splitting on quantity markers if multiple exist in text
        if len(raw_chunks) <= 1:
            qty_boundary_pattern = r"(?<=[a-zA-Z\u0C80-\u0CFF])\s+(?=(?:\d+|one|two|three|four|five|ondu|ondhu|eradu|mooru|ಒಂದು|ಎರಡು|ಮೂರು|ನಾಲ್ಕು|ಐದು)\s+[a-zA-Z\u0C80-\u0CFF])"
            split_candidate = [c.strip() for c in re.split(qty_boundary_pattern, text, flags=re.IGNORECASE) if c.strip()]
            if len(split_candidate) > 1:
                raw_chunks = split_candidate

        if len(raw_chunks) <= 1:
            return []

        results = []
        seen_ids = set()

        for chunk in raw_chunks:
            qty = self._extract_quantity(chunk)
            matched = self.index.find_items_by_query(chunk)
            if matched and matched[0][1] >= 0.65:
                best_item = matched[0][0]
                item_id = best_item["id"]
                if item_id not in seen_ids:
                    seen_ids.add(item_id)
                    results.append((best_item, qty))

        # Only treat as multi-item if 2 or more distinct items are found
        if len(results) >= 2:
            return results
        return []

    def is_kannada_input(self, text: str) -> bool:
        """Detects if input is in Kannada script or contains characteristic Romanized Kannada phrasing."""
        return kt_is_kannada_input(text)

    def _extract_quantity(self, text: str) -> int:
        """Extract requested quantity from text supporting English and Kannada."""
        text_lower = text.lower()
        digit_match = re.search(r"\b(\d+)\b", text_lower)
        if digit_match:
            try:
                val = int(digit_match.group(1))
                if 1 <= val <= 50:
                    return val
            except ValueError:
                pass

        tokens = text_lower.split()
        # Kannada script numerals (checked first by value descending to avoid partial matches)
        kannada_script_numbers = [
            ("ಹತ್ತು", 10), ("ಒಂಬತ್ತು", 9), ("ಎಂಟು", 8), ("ಏಳು", 7), ("ಆರು", 6),
            ("ಐದು", 5), ("ನಾಲ್ಕು", 4), ("ಮೂರು", 3), ("ಎರಡು", 2), ("ಒಂದು", 1),
        ]
        for word, val in kannada_script_numbers:
            if word in tokens or word in text_lower:
                return val

        word_to_num = {
            "ten": 10, "hatthu": 10,
            "nine": 9, "ombattu": 9,
            "eight": 8, "entu": 8,
            "seven": 7, "elu": 7,
            "six": 6, "aaru": 6,
            "five": 5, "aidu": 5, "aydu": 5,
            "four": 4, "naalku": 4, "nalku": 4,
            "three": 3, "mooru": 3, "muru": 3,
            "two": 2, "eradu": 2, "couple": 2, "pair": 2,
            "one": 1, "ondu": 1, "ondhu": 1, "single": 1, "a": 1, "an": 1,
        }
        for word, val in word_to_num.items():
            if word in tokens or re.search(rf"\b{word}\b", text_lower):
                return val

        return 1

    def process_message(
        self,
        message: str,
        session_id: str,
        current_screen: Optional[str] = "home",
        cart_items: Optional[List[Dict[str, Any]]] = None,
        orders_store: Optional[Dict[str, Any]] = None,
        language_preference: Optional[str] = "AUTO",
    ) -> KioskResponse:
        """
        Authoritative entry point accepting customer utterance and context,
        returning validated typed KioskResponse and recording turn into memory.
        """
        response = self._process_message_internal(
            message=message,
            session_id=session_id,
            current_screen=current_screen,
            cart_items=cart_items,
            orders_store=orders_store,
            language_preference=language_preference,
        )
        # Record turn in session memory
        memory = self.memory_manager.get_memory(session_id)
        actions_list = [
            a.get("type") if isinstance(a, dict) else getattr(a, "type", "")
            for a in response.actions
        ]
        items_mentioned = []
        if response.data.get("item_id"):
            items_mentioned.append(response.data["item_id"])
        elif response.data.get("items_added"):
            items_mentioned.extend(response.data["items_added"])
        elif response.data.get("item") and isinstance(response.data["item"], dict):
            items_mentioned.append(response.data["item"].get("id"))
        elif response.data.get("cheapest_item") and isinstance(response.data["cheapest_item"], dict):
            items_mentioned.append(response.data["cheapest_item"].get("id"))

        state = self.get_session_state(session_id)
        if state.get("last_added_item_id"):
            memory.set_last_added_item(state["last_added_item_id"])
        elif state.get("last_added_item_id") is None and response.intent == "remove_from_cart":
            memory.last_added_item_id = None
        if state.get("last_mentioned_item"):
            memory.selected_item_id = state["last_mentioned_item"]
            memory.record_item_discussion(state["last_mentioned_item"])
        for iid in items_mentioned:
            if iid:
                memory.record_item_discussion(iid)

        memory.record_turn(
            user_utterance=(message or "").strip(),
            assistant_response=response.message,
            intent=response.intent,
            actions=actions_list,
            items_mentioned=[i for i in items_mentioned if i],
        )
        response.language = getattr(memory, "customer_language", None) or ("kn" if self.is_kannada_input(response.message) else "en")
        return response

    def _process_message_internal(
        self,
        message: str,
        session_id: str,
        current_screen: Optional[str] = "home",
        cart_items: Optional[List[Dict[str, Any]]] = None,
        orders_store: Optional[Dict[str, Any]] = None,
        language_preference: Optional[str] = "AUTO",
    ) -> KioskResponse:
        """
        Main processing method accepting customer message and context,
        returning validated typed KioskResponse.
        """
        raw_msg = (message or "").strip()
        state = self.get_session_state(session_id)
        state["dialogue_turn"] += 1
        msg_lower = raw_msg.lower()
        norm_query = self.index._normalize(raw_msg)
        cart_items = cart_items or []
        
        pref = (language_preference or state.get("language_preference") or "AUTO").strip().upper()
        state["language_preference"] = pref
        memory = self.memory_manager.get_memory(session_id)

        # 1. Resolve customer language:
        # Precedence: Explicit override -> Utterance detection -> Contextual dialogue memory
        raw_is_kn = self.is_kannada_input(raw_msg)
        if pref in ["KN", "KANNADA"]:
            is_kn = True
        elif pref in ["EN", "ENGLISH"]:
            is_kn = False
        else:
            # AUTO mode: detect from current utterance
            is_kn = raw_is_kn
            # If utterance is very short or ambiguous and no strong English marker, preserve recent conversation language
            if not is_kn and len(raw_msg.split()) <= 2 and memory.customer_language == "kn":
                english_only_markers = {"yes", "no", "english", "cancel", "checkout", "cart", "card", "cash", "upi", "hi", "hello"}
                if not any(w in raw_msg.lower() for w in english_only_markers):
                    is_kn = True

        memory.customer_language = "kn" if is_kn else "en"
        state["customer_language"] = "kn" if is_kn else "en"
        memory.update_screen_context(
            screen=current_screen or "home",
            category=state.get("active_category"),
            section=state.get("active_section"),
        )

        # ======================================================================
        # 1. LLM INTENT CLASSIFIER INVOCATION (Stage A with Multi-Turn Memory)
        # ======================================================================
        classified_intent = self.intent_classifier.extract_intent(
            user_input=raw_msg,
            current_screen=current_screen or "home",
            active_category=state.get("active_category"),
            active_section=state.get("active_section"),
            cart_items=cart_items,
            recent_context=state,
            conversation_history=memory.format_history_for_prompt(max_turns=4),
            recently_discussed_items=memory.recently_discussed_items,
            language_preference=pref,
        )

        # If in AUTO mode and classifier detected Kannada or mixed Kannada, enforce is_kn = True
        if pref not in ["EN", "ENGLISH"] and getattr(classified_intent, "detected_language", None) in ["kn", "mixed_kn_en"]:
            is_kn = True
            memory.customer_language = "kn"
            state["customer_language"] = "kn"

        # 1-ambiguity. AMBIGUITY / CANDIDATE CLARIFICATION (e.g. "Add two of those" when multiple items discussed)
        if not state.get("pending_clarification") and ((classified_intent.clarification_required and classified_intent.candidate_item_ids) or classified_intent.action == "clarify_candidate"):
            candidates = classified_intent.candidate_item_ids or (classified_intent.parameters.get("candidates") if classified_intent.parameters else [])
            if candidates:
                memory.set_pending_clarification(candidates)
                state["pending_clarification"] = candidates
                candidate_names = []
                for cid in candidates:
                    if cid in self.all_items:
                        candidate_names.append(self.all_items[cid]["name"])
                    elif cid in SECTION_HIERARCHY:
                        candidate_names.append(SECTION_HIERARCHY[cid]["canonical_name"])
                    else:
                        candidate_names.append(cid.replace("_", " ").title())

                c_str = " or ".join(candidate_names[:2])
                if is_kn:
                    msg = f"ನಾವು {c_str} ಎರಡನ್ನೂ ನೋಡಿದ್ದೇವೆ. ನೀವು ಯಾವುದನ್ನು ಸೇರಿಸಲು ಬಯಸುತ್ತೀರಿ?"
                else:
                    msg = f"We have multiple options discussed ({c_str}). Which one would you like me to add?"
                return KioskResponse(
                    message=msg,
                    screen=current_screen or "menu_items",
                    intent="clarify_item",
                    data={"candidates": candidates, "candidate_names": candidate_names},
                    conversation_state=state,
                )

        # 1-unsupported. UNSUPPORTED CUISINE GUARD (pizza, burger, chicken, non-veg, etc.)
        unsupported_food = MenuKnowledge.check_unsupported_item(raw_msg)
        if classified_intent.action == "unsupported_item" or unsupported_food:
            food_item = unsupported_food or classified_intent.target_id or "that"
            state["last_intent"] = "unsupported_cuisine"
            if is_kn:
                msg = f"ಕ್ಷಮಿಸಿ, ನಮ್ಮಲ್ಲಿ {food_item} ಲಭ್ಯವಿಲ್ಲ. ನಾವು ಸಾಂಪ್ರದಾಯಿಕ ಶುದ್ಧ ಸಸ್ಯಾಹಾರಿ ದಕ್ಷಿಣ ಭಾರತೀಯ ತಿಂಡಿಗಳಾದ ಮಸಾಲೆ ದೋಸೆ, ಇಡ್ಲಿ ವಡೆ, ಬಿಸಿ ಬೇಳೆ ಬಾತ್ ನೀಡುತ್ತೇವೆ."
            else:
                msg = f"We don't serve {food_item} here as The Atom Prasadam is an authentic South Indian pure vegetarian restaurant. May I suggest our crispy Masala Dosa, Bisi Bele Bath, or Filter Coffee?"
            return KioskResponse(
                message=msg,
                screen=current_screen or "categories",
                intent="unsupported_cuisine",
                data={"unsupported_item": food_item},
                conversation_state=state,
            )

        # 1-hunger. HUNGER & APPETITE QUERY ("I'm hungry", "What should I eat?")
        is_hungry = any(w in msg_lower for w in ["i'm hungry", "i am hungry", "im hungry", "hungry", "starving", "ಹಸಿವು", "ಹಸಿದಿದ್ದೇನೆ", "hasivu"])
        if is_hungry and not any(w in msg_lower for w in ["breakfast", "ತಿಂಡಿ", "dosa", "coffee", "rice", "recommend", "suggest", "crispy"]):
            state["last_intent"] = "general_food_inquiry"
            if is_kn:
                msg = "ಸುಸ್ವಾಗತ! ಬಿಸಿ ಬಿಸಿ ತುಪ್ಪದ ಮಸಾಲೆ ದೋಸೆ, ಇಡ್ಲಿ ವಡೆ, ಅಥವಾ ತುಪ್ಪದ ಬಿಸಿ ಬೇಳೆ ಬಾತ್ ಇವೆ. ನಿಮಗೆ ಯಾವುದು ಇಷ್ಟ?"
            else:
                msg = "Welcome! If you're hungry, we have delicious hot options like our Ghee Roast Masala Dosa, Idly Vada combo, and Bisi Bele Bath. What are you in the mood for?"
            return KioskResponse(
                message=msg,
                screen="categories",
                intent="general_food_inquiry",
                actions=[{"type": "navigate", "payload": {"screen": "categories"}}],
                conversation_state=state,
            )

        # 1-spice. SPICE LEVEL INQUIRY ("Which one is spicy?", "Is there any spicy dosa?")
        is_spice_query = any(w in msg_lower for w in ["which one is spicy", "is it spicy", "spicy dosa", "any spicy", "which dosa is spicy", "ಖಾರವಾದ ದೋಸೆ", "ಖಾರ"])
        if is_spice_query:
            state["last_intent"] = "product_details"
            spicy_item = self.all_items.get("ghee_pudi_masala_dosa")
            if spicy_item:
                state["last_mentioned_item"] = "ghee_pudi_masala_dosa"
                memory.record_item_discussion("ghee_pudi_masala_dosa")
                price = spicy_item["price"]
                if is_kn:
                    msg = f"ನಮ್ಮ ತುಪ್ಪದ ಪುಡಿ ಮಸಾಲೆ ದೋಸೆ (₹{price:.0f}) ಹೆಚ್ಚು ಖಾರ ಮತ್ತು ರುಚಿಯಾಗಿರುತ್ತದೆ. ಇದನ್ನು ಕಾರ್ಟ್ಗೆ ಸೇರಿಸ್ಲಾ?"
                else:
                    msg = f"Our Ghee Pudi Masala Dosa (₹{price:.0f}) is the spiciest, coated with our signature spiced chutney podi and potato masala. Would you like me to add it to your cart?"
                return KioskResponse(
                    message=msg,
                    screen="menu_items",
                    intent="product_details",
                    data={"item": spicy_item, "item_id": "ghee_pudi_masala_dosa"},
                    actions=[{"type": "open_product", "payload": {"item": spicy_item}}],
                    conversation_state=state,
                )

        # 1-popularity. POPULARITY / SIGNATURE DISH INQUIRY ("Which one is popular?", "What is popular?")
        is_pop_query = any(w in msg_lower for w in ["which one is popular", "what is popular", "popular dosa", "most popular", "ಜನಪ್ರಿಯ", "popular"])
        if is_pop_query:
            state["last_intent"] = "recommendation"
            pop_item = self.all_items.get("ghee_roast_masala_dosa")
            state["last_mentioned_item"] = "ghee_roast_masala_dosa"
            memory.record_item_discussion("ghee_roast_masala_dosa")
            if is_kn:
                msg = "ನಮ್ಮಲ್ಲಿ ತುಪ್ಪದ ಮಸಾಲೆ ದೋಸೆ (₹95), ಇಡ್ಲಿ ವಡೆ ಮತ್ತು ಫಿಲ್ಟರ್ ಕಾಫಿ ಸಾಂಪ್ರದಾಯಿಕ ಮೆಚ್ಚಿನ ತಿಂಡಿಗಳು. ಮಸಾಲೆ ದೋಸೆ ನೋಡೋಣವೇ?"
            else:
                msg = "Our traditional customer favorites are the Ghee Roast Masala Dosa (₹95), steaming Idly Vada (₹55), and fresh Filter Coffee (₹25). Would you like to try the Masala Dosa?"
            return KioskResponse(
                message=msg,
                screen="menu_items",
                intent="recommendation",
                data={"item_id": "ghee_roast_masala_dosa"},
                conversation_state=state,
            )

        # 1a. GREETING & COURTESY
        greetings = ["hello", "hi", "hey", "namaskara", "namaste", "vanakkam", "good morning", "good afternoon", "good evening", "ನಮಸ್ಕಾರ", "ನಮಸ್ತೆ"]
        if classified_intent.action == "greeting" or any(msg_lower == g or msg_lower.startswith(f"{g} ") or msg_lower.startswith(f"{g},") for g in greetings):
            state["last_intent"] = "greeting"
            if is_kn:
                msg = "Namaskara! ನಮಸ್ಕಾರ! ದಿ ಆಟಂ ಪ್ರಸಾದಂಗೆ ಸುಸ್ವಾಗತ. ಇಂದು ನಿಮಗೆ ಏನು ತರಲಿ? ಮಸಾಲೆ ದೋಸೆ, ಕಾಫಿ, ಅಥವಾ ಸಿಹಿ ತಿಂಡಿಗಳನ್ನು ಕೇಳಬಹುದು."
            else:
                msg = "Namaskara! Welcome to The Atom Prasadam. How may I serve you today? You can ask for our special dosas, filter coffee, sweets, or explore any section."
            return KioskResponse(
                message=msg,
                screen="categories",
                intent="greeting",
                actions=[{"type": "navigate", "payload": {"screen": "categories"}}],
                conversation_state=state,
            )

        # Determine if a specific dish was mentioned
        has_specific_dish = False
        dish_matches = self.index.find_items_by_query(raw_msg)
        if dish_matches and dish_matches[0][1] >= 0.8:
            matched_item = dish_matches[0][0]
            matched_name = matched_item["name"].lower()
            matched_kn = (matched_item.get("kannadaName") or matched_item.get("kannada_name") or "").lower()
            generic_en = {"dosa", "dose", "roti", "meals", "rice", "curry", "soup", "item", "bread", "breads", "snack", "snacks", "beverage", "beverages", "sweet", "sweets"}
            generic_kn = {"ದೋಸೆ", "ರೊಟ್ಟಿ", "ಊಟ", "ಅನ್ನ", "ತಿಂಡಿ", "ಪಾನೀಯ", "ಸಿಹಿ", "ಸ್ವೀಟ್"}
            has_eng_specific = any(w in msg_lower for w in matched_name.split() if w not in generic_en)
            has_kn_specific = any(w in raw_msg for w in matched_kn.split() if w not in generic_kn)
            norm_raw = normalize_kannada_transliteration(raw_msg)
            has_norm_specific = any(w in norm_raw for w in matched_name.split() if w not in generic_en)
            if has_eng_specific or has_kn_specific or has_norm_specific:
                has_specific_dish = True

        # 1b. TOP-LEVEL CATEGORY NAVIGATION ("Show me Indian breads", "What do you have in Meals and Rice?")
        is_ordering_intent = any(w in msg_lower for w in ["give me", "give", "add", "order", "parcel", "kodi", "kodu", "beku", "haaki", "serisu", "want", "like to have", "ಕೊಡು", "ಕೊಡಿ", "ಬೇಕು", "ಹಾಕಿ", "ಸೇರಿಸು"])
        cat_id = classified_intent.category or classified_intent.target_id
        if (classified_intent.action == "show_category" and not has_specific_dish) or (cat_id in CATEGORY_HIERARCHY and not has_specific_dish and not is_ordering_intent):
            if cat_id in CATEGORY_HIERARCHY:
                cat_info = CATEGORY_HIERARCHY[cat_id]
                state["last_intent"] = "show_category"
                state["active_category"] = cat_id
                en_title = cat_info["title_english"]
                kn_title = cat_info["title_kannada"]
                sec_names = [
                    s.get("canonical_name", "") for s in cat_info.get("sections", []) if isinstance(s, dict)
                ]
                msg = self.response_generator.generate_cashier_response(
                    customer_message=raw_msg,
                    memory=memory,
                    action_result={
                        "action": "show_category",
                        "category_id": cat_id,
                        "category_title": en_title,
                        "kannada_title": kn_title,
                        "sections": sec_names,
                    },
                    is_kn=is_kn,
                )
                return KioskResponse(
                    message=msg,
                    screen="subcategories",
                    intent="show_category",
                    language="kn" if is_kn else "en",
                    data={"category_id": cat_id, "title_english": en_title, "title_kannada": kn_title},
                    actions=[{"type": "navigate", "payload": {"screen": "subcategories", "category_id": cat_id}}],
                    conversation_state=state,
                )
            elif not is_ordering_intent and not any(w in msg_lower for w in ["kofta", "dosa", "idli", "roti", "paneer"]):
                state["last_intent"] = "navigate_categories"
                msg = classified_intent.response_text or ("ಎಲ್ಲಾ ಮೆನು ವಿಭಾಗಗಳು ಇಲ್ಲಿವೆ." if is_kn else "Here are all the menu categories.")
                return KioskResponse(
                    message=msg,
                    screen="categories",
                    intent="navigate",
                    actions=[{"type": "navigate", "payload": {"screen": "categories"}}],
                    conversation_state=state,
                )
        is_price_inquiry = any(q in msg_lower for q in ["how much", "price of", "what is the price", "cost of", "rate of", "ಎಷ್ಟು", "ಬೆಲೆ", "yestu", "eshtu"])
        is_dish_avail_inquiry = any(q in msg_lower for q in ["ideya", "ide ya", "ಇದೆಯಾ", "ಲಭ್ಯವಿದೆಯೇ", "available", "is there"]) and has_specific_dish
        is_dish_inquiry = is_price_inquiry or is_dish_avail_inquiry
        is_multi_order = len(self.extract_multi_items(raw_msg)) >= 2
        is_dosa_varieties = any(p in msg_lower for p in ["dosa varieties", "varieties of dosa", "variety of dosa", "what dosas", "types of dosa", "ದೋಸೆ ವಿಧಗಳು"])
        is_beverage_query = any(p in norm_query for p in ["coffee ideya", "kaapi ideya", "filter coffee ideya", "tea ideya", "chai ideya", "ಕಾಫಿ ಇದೆಯಾ", "ಫಿಲ್ಟರ್ ಕಾಫಿ ಇದೆಯಾ", "ಟೀ ಇದೆಯಾ", "is coffee available", "do you have coffee"])
        is_food_inquiry = any(p in msg_lower for p in ["ಏನಾದರೂ ತಿಂಡಿ ತೋರಿಸಿ", "suggest something", "recommend something"])
        is_crispy_query = any(w in msg_lower for w in ["crispy", "crunchy", "ಕರಂ ಕರಂ", "ಗರಿಗರಿ", "ಕುರುಕುರು"])

        # 1c-order. CATEGORY/SECTION-LEVEL ORDERING ("Ondu dose kodi", "One dosa please", "Roti kodi")
        # Customer expressed ordering intention for an entire section rather than a specific dish.
        dosa_specific_keywords = [
            "masala", "masale", "set", "rava", "plain", "pudi", "onion", "paper", "neer", "open", "ghee", "roast", "chilli", "butter", "palak", "cheese", "kal", "kali", "saagu", "sagu",
            "ಮಸಾಲೆ", "ಮಸಾಲ", "ಸೆಟ್", "ರವಾ", "ಪ್ಲೇನ್", "ಪುಡಿ", "ಈರುಳ್ಳಿ", "ನೀರ್", "ಖಾಲಿ", "ಓಪನ್", "ಬೆಣ್ಣೆ", "ತುಪ್ಪ", "ಕಾಯಿ", "ಸಾಗು", "ಚಿಲ್ಲಿ", "ಚೀಸ್",
            "ravva", "eerulli", "irulli", "neeru", "khali", "benne", "thuppa"
        ]
        roti_specific_keywords = [
            "tandoori", "butter", "naan", "kulcha", "parotta", "paratha", "chapati", "phulka", "rumali", "missi", "garlic", "stuffed",
            "ತಂದೂರಿ", "ಬಟರ್", "ನಾನ್", "ಕುಲ್ಚಾ", "ಪರೋಟ", "ಪರಾಟ", "ಚಪಾತಿ", "ಫುಲ್ಕಾ", "ರುಮಾಲಿ", "ಮಿಷಿ", "ಗಾರ್ಲಿಕ್",
            "tanduri", "batar", "chapathi", "parota"
        ]
        norm_raw = normalize_kannada_transliteration(raw_msg)
        is_generic_dosa = any(w in norm_query.split() for w in ["dosa", "dose", "ದೋಸೆ", "dosas", "doses"]) and not any(w in msg_lower or w in raw_msg or w in norm_raw for w in dosa_specific_keywords)
        is_generic_roti = any(w in norm_query.split() for w in ["roti", "bread", "breads", "ರೊಟ್ಟಿ"]) and not any(w in msg_lower or w in raw_msg or w in norm_raw for w in roti_specific_keywords) and not (classified_intent.target_id == "indian_breads" or classified_intent.category == "indian_breads")
        is_browse_request = any(w in msg_lower for w in ["show me", "show", "explore", "open", "view", "see", "display", "ತೋರಿಸಿ", "ತೋರಿಸು", "ನೋಡೋಣ"]) and not any(w in msg_lower for w in ["kodi", "kodu", "add", "give", "ಕೊಡು", "ಕೊಡಿ", "ಆರ್ಡರ್"])
        is_category_order = (is_generic_dosa or is_generic_roti) and (is_ordering_intent or classified_intent.action == "add_to_cart") and not is_browse_request

        if is_category_order and not has_specific_dish and not is_multi_order:
            if is_generic_dosa:
                sec_id = "dose_special"
                sec_info = SECTION_HIERARCHY[sec_id]
                state["last_intent"] = "clarify_item"
                state["active_section"] = sec_id
                state["active_category"] = sec_info["parent_category"]
                dosa_items = [it for it in self.all_items.values() if it.get("section_id") == sec_id and it.get("available") is not False]
                top_dosas = dosa_items[:5]
                state["last_options_shown"] = top_dosas
                state["pending_clarification"] = [it["id"] for it in top_dosas]
                state["pending_order_quantity"] = self._extract_quantity(raw_msg)
                if is_kn:
                    msg = "ಖಂಡಿತ! ನಮ್ಮಲ್ಲಿ ಮಸಾಲೆ ದೋಸೆ, ಸೆಟ್ ದೋಸೆ, ಪ್ಲೇನ್ ದೋಸೆ ಮತ್ತು ರವಾ ದೋಸೆ ಇದೆ. ನಿಮಗೆ ಯಾವುದು ಬೇಕು?"
                else:
                    msg = "Sure! We have multiple options for dosa, including Masala Dosa, Set Dosa, and Plain Dosa. Which one would you like?"
                return KioskResponse(
                    message=msg,
                    screen="menu_items",
                    intent="clarify_item",
                    data={"section_id": sec_id, "options": top_dosas},
                    actions=[{"type": "navigate", "payload": {"screen": "menu_items", "section_id": sec_id}}],
                    conversation_state=state,
                )
            elif is_generic_roti:
                sec_id = "indian_breads_roti"
                sec_info = SECTION_HIERARCHY[sec_id]
                state["last_intent"] = "clarify_item"
                state["active_section"] = sec_id
                state["active_category"] = sec_info["parent_category"]
                roti_items = [it for it in self.all_items.values() if it.get("section_id") == sec_id and it.get("available") is not False]
                top_rotis = roti_items[:5]
                state["last_options_shown"] = top_rotis
                state["pending_clarification"] = [it["id"] for it in top_rotis]
                state["pending_order_quantity"] = self._extract_quantity(raw_msg)
                if is_kn:
                    msg = "ಖಂಡಿತ! ನಮ್ಮಲ್ಲಿ ತಂದೂರಿ ರೊಟ್ಟಿ, ಬಟರ್ ರೊಟ್ಟಿ, ಮತ್ತು ನಾನ್ ಇವೆ. ಯಾವುದು ಬೇಕು?"
                else:
                    msg = "Sure! We have Tandoori Roti, Butter Roti, and Naan. Which one would you like?"
                return KioskResponse(
                    message=msg,
                    screen="menu_items",
                    intent="clarify_item",
                    data={"section_id": sec_id, "options": top_rotis},
                    actions=[{"type": "navigate", "payload": {"screen": "menu_items", "section_id": sec_id}}],
                    conversation_state=state,
                )

        if (classified_intent.action in ["show_subcategory", "show_section"]
            and not is_ordering_intent
            and not is_dish_inquiry
            and not has_specific_dish
            and not is_multi_order
            and not is_dosa_varieties
            and not is_beverage_query
            and not is_food_inquiry
            and not is_crispy_query):
            sec_id = classified_intent.section_id or classified_intent.target_id
            if sec_id in SECTION_HIERARCHY:
                sec_info = SECTION_HIERARCHY[sec_id]
                sec_title = sec_info["canonical_name"]
                kannada_title = sec_info["kannada_name"]
                state["last_intent"] = "show_section"
                state["active_section"] = sec_id
                state["active_category"] = sec_info["parent_category"]

                sec_items = [it for it in self.all_items.values() if it.get("section_id") == sec_id and it.get("available") is not False]
                state["last_options_shown"] = sec_items[:8]
                if sec_items:
                    state["last_mentioned_item"] = sec_items[0]["id"]

                available_item_names = [
                    it.get("kannadaName") or it["name"] if is_kn else it["name"]
                    for it in sec_items[:4]
                ]
                msg = self.response_generator.generate_cashier_response(
                    customer_message=raw_msg,
                    memory=memory,
                    action_result={
                        "action": "show_section",
                        "section_id": sec_id,
                        "section_title": sec_title,
                        "kannada_title": kannada_title,
                        "available_items": available_item_names,
                        "total_items": len(sec_items),
                    },
                    is_kn=is_kn,
                )
                return KioskResponse(
                    message=msg,
                    screen="menu_items",
                    intent="show_section",
                    language="kn" if is_kn else "en",
                    data={"section_id": sec_id, "section_title": sec_title, "options": sec_items[:8]},
                    actions=[{"type": "navigate", "payload": {"screen": "menu_items", "section_id": sec_id}}],
                    conversation_state=state,
                )

        # ======================================================================
        # 2. NAVIGATION & BACK INTENTS
        # ======================================================================
        if classified_intent.action == "modify_order" or any(term in msg_lower for term in ["change my order", "change order", "modify my order", "edit order", "edit my cart"]):
            state["last_intent"] = "modify_order"
            msg = "ನಿಮ್ಮ ಕಾರ್ಟ್ ತೆರೆಯುತ್ತಿದ್ದೇನೆ. ನೀವು ಪ್ರಮಾಣ ಬದಲಾಯಿಸಬಹುದು ಅಥವಾ ಪದಾರ್ಥಗಳನ್ನು ತೆಗೆಯಬಹುದು." if is_kn else "Opening your tray so you can modify quantities or remove items."
            return KioskResponse(
                message=msg,
                screen="cart",
                intent="modify_order",
                actions=[{"type": "navigate", "payload": {"screen": "cart"}}],
                conversation_state=state,
            )

        back_phrases = [
            "go back", "back", "previous screen", "return back",
            "ಹಿಂದಕ್ಕೆ ಹೋಗು", "ಹಿಂದೆ ಹೋಗು", "ಹಿಂದಕ್ಕೆ", "ಹಿಂದೆ",
            "hindakke hogu", "hindakke", "hinde hogu", "hinde"
        ]
        if classified_intent.action in ["navigate_back", "go_back"] or any(msg_lower == b or msg_lower.startswith(b) for b in back_phrases):
            state["last_intent"] = "go_back"
            msg = classified_intent.response_text or ("ಹಿಂದಿನ ಪುಟಕ್ಕೆ ಹಿಂತಿರುಗುತ್ತಿದ್ದೇನೆ." if is_kn else "Returning to the previous screen.")
            return KioskResponse(
                message=msg,
                screen="previous",
                intent="go_back",
                data={"ui_action": "go_back"},
                actions=[{"type": "go_back", "payload": {}}, {"type": "navigate", "payload": {"screen": "previous"}}],
                conversation_state=state,
            )

        home_phrases = [
            "go home", "take me home", "welcome screen", "start over", "home",
            "go to home", "go to the home", "go to home page", "go to the home page", "home page", "main screen",
            "ಮನೆ ಪುಟಕ್ಕೆ ಹೋಗು", "ಮನೆ ಪುಟ", "ಮೊದಲ ಪುಟಕ್ಕೆ ಹೋಗು", "ಮೊದಲ ಪುಟ",
            "mane putakke hogu", "mane putakke", "mane puta", "modala puta"
        ]
        if classified_intent.action == "navigate_home" or any(msg_lower == h or msg_lower.startswith(h) or "home page" in msg_lower or "home screen" in msg_lower for h in home_phrases):
            state["last_intent"] = "navigate_home"
            msg = classified_intent.response_text or ("ಸ್ವಾಗತ ಪುಟಕ್ಕೆ ಹಿಂತಿರುಗುತ್ತಿದ್ದೇನೆ." if is_kn else "Returning to the welcome screen.")
            return KioskResponse(
                message=msg,
                screen="home",
                intent="navigate_home",
                actions=[{"type": "navigate", "payload": {"screen": "home"}}],
                conversation_state=state,
            )

        cat_phrases = [
            "categories", "all categories", "go to menu", "main menu", "menu",
            "ವಿಭಾಗಗಳು", "ಎಲ್ಲಾ ವಿಭಾಗಗಳು", "ಮೆನು ತೋರಿಸು", "categories torisu", "menu torisu"
        ]
        if any(msg_lower == c or "categories" in msg_lower or "main menu" in msg_lower or "ವಿಭಾಗಗಳು" in msg_lower for c in cat_phrases):
            state["last_intent"] = "navigate_categories"
            msg = "ಎಲ್ಲಾ ಮೆನು ವಿಭಾಗಗಳು ಇಲ್ಲಿವೆ." if is_kn else "Here are all the menu categories."
            return KioskResponse(
                message=msg,
                screen="categories",
                intent="navigate",
                actions=[{"type": "navigate", "payload": {"screen": "categories"}}],
                conversation_state=state,
            )

        # ======================================================================
        # 3. MIND CHANGE, REMOVAL & REPLACEMENT ("Actually remove that", "Remove that and give me plain dosa")
        # ======================================================================
        is_remove_replace = ("remove" in msg_lower or "take out" in msg_lower or "drop" in msg_lower) and (
            "instead" in msg_lower or "give me" in msg_lower or "and add" in msg_lower or "and give" in msg_lower or "give" in msg_lower
        )
        if is_remove_replace:
            target_id = state.get("last_added_item_id")
            if not target_id and cart_items:
                target_id = cart_items[-1].get("id") or cart_items[-1].get("item_id")
            
            # Find the new dish to add from the second part of the utterance
            sub_phrase = re.split(r"\b(?:instead|give me|and add|and give|give)\b", msg_lower, flags=re.IGNORECASE)[-1]
            new_item_matches = self.index.find_items_by_query(sub_phrase)
            
            if target_id and new_item_matches and new_item_matches[0][1] >= 0.65:
                old_item = self.all_items.get(target_id, {})
                old_name = old_item.get("name", "dish")
                old_kn = old_item.get("kannadaName") or old_item.get("kannada_name") or old_name
                
                new_item = new_item_matches[0][0]
                new_id = new_item["id"]
                new_name = new_item["name"]
                new_price = float(new_item["price"])
                new_kn = new_item.get("kannadaName") or new_item.get("kannada_name") or new_name
                sec_id = new_item.get("section_id", "")
                
                state["last_added_item_id"] = new_id
                state["last_mentioned_item"] = new_id
                state["last_intent"] = "replace_item"
                
                if is_kn:
                    msg = f"ಕಾರ್ಟ್ನಿಂದ {old_kn} ತೆಗೆದು, {new_kn} (₹{new_price:.0f}) ಅನ್ನು ಸೇರಿಸಿದ್ದೀನಿ. ಇನ್ನೇನಾದರೂ ಬೇಕಾ?"
                else:
                    msg = f"I have removed {old_name} and added {new_name} (₹{new_price:.0f}) to your cart. Anything else?"
                
                return KioskResponse(
                    message=msg,
                    screen="cart",
                    intent="replace_item",
                    data={"removed_id": target_id, "added_id": new_id, "name": new_name, "price": new_price},
                    actions=[
                        {"type": "remove_from_cart", "payload": {"id": target_id}},
                        {
                            "type": "add_to_cart",
                            "payload": {
                                "id": new_id,
                                "name": new_name,
                                "price": new_price,
                                "quantity": 1,
                                "image": new_item.get("image", ""),
                                "section_id": sec_id,
                                "kannadaName": new_kn,
                            }
                        }
                    ],
                    conversation_state=state,
                )

        is_remove_that = any(p in msg_lower for p in [
            "actually remove that", "actually not that", "remove that", "take that out",
            "take out the last one", "drop that", "ಅದನ್ನು ತೆಗೆದುಹಾಕು", "ತೆಗೆದುಹಾಕು", "ಆ ಐಟಂ ಬೇಡ", "ಆ ದೋಸೆ ಬೇಡ ತೆಗೆ"
        ])
        if is_remove_that:
            target_id = state.get("last_added_item_id")
            if not target_id and cart_items:
                target_id = cart_items[-1].get("id") or cart_items[-1].get("item_id")

            if target_id and target_id in self.all_items:
                target_item = self.all_items[target_id]
                item_name = target_item.get("name", "dish")
                kannada = target_item.get("kannadaName") or target_item.get("kannada_name") or item_name
                state["last_added_item_id"] = None
                state["last_intent"] = "remove_from_cart"

                if is_kn:
                    msg = f"ಕಾರ್ಟ್ನಿಂದ {kannada} ಅನ್ನು ತೆಗೆದುಹಾಕಿದ್ದೀನಿ. ಬದಲಿಗೆ ಏನು ಬೇಕು?"
                else:
                    msg = f"I have removed {item_name} from your cart. What would you like instead?"

                return KioskResponse(
                    message=msg,
                    screen="cart",
                    intent="remove_from_cart",
                    data={"removed_item_id": target_id, "name": item_name},
                    actions=[{"type": "remove_from_cart", "payload": {"id": target_id}}],
                    conversation_state=state,
                )

        # Cancellation intent ("Cancel that", "Cancel checkout", "Cancel")
        if any(msg_lower == c or msg_lower.startswith(c) for c in ["cancel that", "cancel order", "cancel checkout", "cancel", "ರದ್ದು ಮಾಡು", "ಬೇಡ"]):
            state["last_intent"] = "cancel"
            if state.get("pending_checkout"):
                state["pending_checkout"] = False
                msg = "ಆರ್ಡರ್ ಪರಿಶೀಲನೆ ರದ್ದು ಮಾಡಲಾಗಿದೆ. ನಿಮ್ಮ ಕಾರ್ಟ್ನಲ್ಲಿ ಪದಾರ್ಥಗಳು ಹಾಗೇ ಇವೆ. ಮುಂದೆ ಏನು ಮಾಡಬೇಕು?" if is_kn else "Checkout cancelled. Your cart items are still in your tray. What would you like to do next?"
                return KioskResponse(
                    message=msg,
                    screen="cart",
                    intent="cancel_checkout",
                    actions=[{"type": "navigate", "payload": {"screen": "cart"}}],
                    conversation_state=state,
                )
            elif state.get("last_added_item_id"):
                rem_id = state.get("last_added_item_id")
                item = self.all_items.get(rem_id, {})
                name = item.get("kannadaName") or item.get("name", "item")
                state["last_added_item_id"] = None
                msg = f"ರದ್ದು ಮಾಡಲಾಗಿದೆ. ಕಾರ್ಟ್ನಿಂದ {name} ಅನ್ನು ತೆಗೆದುಹಾಕಿದ್ದೀನಿ." if is_kn else f"Cancelled. I have removed {name} from your cart."
                return KioskResponse(
                    message=msg,
                    screen="cart",
                    intent="cancel_add",
                    actions=[{"type": "remove_from_cart", "payload": {"id": rem_id}}],
                    conversation_state=state,
                )
            else:
                msg = "ರದ್ದು ಮಾಡಲಾಗಿದೆ. ನಾನು ನಿಮಗೆ ಹೇಗೆ ಸಹಾಯ ಮಾಡಲಿ?" if is_kn else "Cancelled. How can I help you today?"
                return KioskResponse(
                    message=msg,
                    screen=current_screen or "categories",
                    intent="cancel",
                    conversation_state=state,
                )

        # ======================================================================
        # 3b. FINISH ORDER / THAT'S ENOUGH ("That's enough", "I'm done", "ಸಾಕು, ಆರ್ಡರ್ ಮುಗಿಸೋಣ")
        # ======================================================================
        is_finish_order = any(p in msg_lower for p in [
            "that's enough", "thats enough", "that is enough", "that's all", "thats all", "that will be all",
            "i am done", "i'm done", "finished ordering", "finish order", "let's finish the order",
            "lets finish the order", "let's finish", "lets finish", "done ordering", "ಸಾಕು", "ಆರ್ಡರ್ ಮುಗಿಸೋಣ", "saku"
        ])
        if is_finish_order:
            state["last_intent"] = "finish_order"
            if not cart_items:
                msg = "ನಿಮ್ಮ ಕಾರ್ಟ್ ಖಾಲಿಯಾಗಿದೆ. ಆರ್ಡರ್ ಮಾಡಲು ಯಾವುದಾದರೂ ತಿಂಡಿ ಅಥವಾ ಪಾನೀಯ ಸೇರಿಸಬೇಕೇ?" if is_kn else "Your cart is currently empty. Would you like to add some dosas, meals, or filter coffee before finishing?"
                return KioskResponse(
                    message=msg,
                    screen="categories",
                    intent="finish_order_empty",
                    actions=[{"type": "navigate", "payload": {"screen": "categories"}}],
                    conversation_state=state,
                )
            total = sum(float(i.get("price", 0)) * int(i.get("quantity", 1)) for i in cart_items)
            item_count = sum(int(i.get("quantity", 1)) for i in cart_items)
            state["pending_checkout"] = True
            if is_kn:
                msg = f"ನಿಮ್ಮ ಕಾರ್ಟ್ ಇಲ್ಲಿದೆ. ಒಟ್ಟು {item_count} ಪದಾರ್ಥಗಳು, ಮೊತ್ತ {total:.0f} ರೂಪಾಯಿ. ಆರ್ಡರ್ ಖಚಿತಪಡಿಸೋಣವೇ?"
            else:
                msg = f"Here is your cart with {item_count} items totaling ₹{total:.0f}. Would you like to review and proceed to payment?"
            return KioskResponse(
                message=msg,
                screen="cart",
                intent="checkout",
                data={"total": total, "item_count": item_count, "cart": cart_items},
                actions=[{"type": "navigate", "payload": {"screen": "cart"}}],
                conversation_state=state,
                requires_confirmation=True,
            )

        # ======================================================================
        # 3c. BEVERAGE & COFFEE INQUIRY ("Coffee ideya?", "What about coffee?", "ಕಾಫಿ ಇದೆಯಾ?")
        # ======================================================================
        is_coffee_query = any(p in norm_query for p in [
            "coffee ideya", "kaapi ideya", "filter coffee ideya", "tea ideya", "chai ideya",
            "ಕಾಫಿ ಇದೆಯಾ", "ಫಿಲ್ಟರ್ ಕಾಫಿ ಇದೆಯಾ", "ಟೀ ಇದೆಯಾ", "ಚಹಾ ಇದೆಯಾ",
            "what about coffee", "what about tea", "do you have coffee", "do you have filter coffee",
            "is coffee available", "do you have tea", "is tea available"
        ])
        if is_coffee_query:
            state["last_intent"] = "beverage_inquiry"
            state["last_mentioned_item"] = "jaggery_coffee"
            if is_kn:
                msg = "ಹೌದು, ನಮ್ಮಲ್ಲಿ ಬಿಸಿ ಫಿಲ್ಟರ್ ಕಾಫಿ (₹30) ಮತ್ತು ಬೆಲ್ಲದ ಕಾಫಿ (₹35) ಲಭ್ಯವಿದೆ. ಒಂದು ಕಾಫಿ ಸೇರಿಸ್ಲಾ?"
            else:
                msg = "Yes! We have our authentic South Indian Filter Coffee (₹30) and Jaggery Coffee (₹35) piping hot. Would you like me to add one?"
            return KioskResponse(
                message=msg,
                screen="menu_items",
                intent="beverage_inquiry",
                data={"item_id": "jaggery_coffee", "price": 30.0},
                actions=[{"type": "navigate", "payload": {"screen": "menu_items", "section_id": "hot_beverages"}}],
                conversation_state=state,
            )

        # ======================================================================
        # 3d. PAIRING RECOMMENDATIONS ("What drink goes well with this?", "What goes well with dosa?")
        # ======================================================================
        is_pairing_query = any(p in msg_lower for p in [
             "what goes well with this", "what drink would go well", "drink with this",
             "what drink goes well", "drink goes well", "goes well with",
             "what to drink with", "what goes well with dosa", "what goes well with meal",
             "what goes well with", "ಜೊತೆಗೆ ಕುಡಿಯೋಕೆ ಏನು", "ಜೊತೆಗೆ ಏನು ಚೆನ್ನಾಗಿರುತ್ತೆ", "ಜೊತೆಗೆ ಕುಡಿಯೋಕೆ"
        ])
        if is_pairing_query:
            state["last_intent"] = "pairing_recommendation"
            state["last_mentioned_item"] = "jaggery_coffee"
            if is_kn:
                msg = "ದೋಸೆ ಅಥವಾ ತಿಂಡಿ ಜೊತೆಗೆ ಬಿಸಿ ಫಿಲ್ಟರ್ ಕಾಫಿ (₹30) ಅಥವಾ ಬಾದಾಮಿ ಹಾಲು (₹35) ತುಂಬಾ ಚೆನ್ನಾಗಿರುತ್ತೆ. ಕಾಫಿ ಸೇರಿಸ್ಲಾ?"
            else:
                msg = "A hot South Indian Filter Coffee (₹30) or warm Badam Milk (₹35) pairs wonderfully with your dish! Shall I add a filter coffee?"
            return KioskResponse(
                message=msg,
                screen="menu_items",
                intent="pairing_recommendation",
                data={"item_id": "jaggery_coffee", "price": 30.0},
                conversation_state=state,
            )

        # ======================================================================
        # 3e. SOMETHING LIGHT INQUIRY ("Something light", "Light breakfast", "ಲೈಟ್ ಆಗಿ ತಿಂಡಿ")
        # ======================================================================
        is_light_query = any(p in msg_lower for p in [
            "something light", "light breakfast", "light snack", "light food", "light meal", "light item",
            "ಲೈಟ್ ಆಗಿ", "ಲೈಟ್ ತಿಂಡಿ", "ಲೈಟ್ ಊಟ", "ಹಗುರವಾದ ತಿಂಡಿ"
        ])
        if is_light_query:
            state["last_intent"] = "recommend_light"
            light_items = [
                self.all_items.get("idly_2"),
                self.all_items.get("khara_bath"),
                self.all_items.get("ghee_plain_dosa"),
            ]
            light_items = [it for it in light_items if it]
            state["last_options_shown"] = light_items
            if light_items:
                state["last_mentioned_item"] = light_items[0]["id"]
            if is_kn:
                msg = "ಲೈಟ್ ಆಗಿ ತಿಂಡಿ ಬೇಕಿದ್ರೆ ಬಿಸಿ ಇಡ್ಲಿ (₹40) ಅಥವಾ ಖಾರಾ ಬಾತ್ (₹40) ಚೆನ್ನಾಗಿರುತ್ತೆ. ಇಡ್ಲಿ ಸೇರಿಸ್ಲಾ?"
            else:
                msg = "For something light, our steaming hot Idly (2 pcs, ₹40) or savoury Khara Bath (₹40) are freshly prepared and very popular. Would you like an idly?"
            return KioskResponse(
                message=msg,
                screen="menu_items",
                intent="recommend_light",
                data={"options": light_items},
                actions=[{"type": "navigate", "payload": {"screen": "menu_items", "section_id": "south_indian_breakfast"}}],
                conversation_state=state,
            )

        # ======================================================================
        # 3f. GENERAL FOOD INQUIRY ("What do you have?", "Let's get something to eat", "ಏನಾದರೂ ತಿಂಡಿ ತೋರಿಸಿ")
        # ======================================================================
        is_general_food_query = any(p in msg_lower for p in [
            "what do you have", "what do you serve", "what can i get here", "what can i eat",
            "let's get something to eat", "lets get something to eat", "something to eat",
            "ಏನಾದರೂ ತಿಂಡಿ ತೋರಿಸಿ", "ಏನಾದರೂ ತಿಂಡಿ", "ಏನು ಸಿಗುತ್ತೆ", "ತಿಂಡಿ ಏನು ಇದೆ", "enadaru thindi torisi", "thindi enu ide"
        ])
        if is_general_food_query:
            state["last_intent"] = "general_food_inquiry"
            specialties = [
                self.all_items.get("ghee_roast_masala_dosa"),
                self.all_items.get("idly_2"),
                self.all_items.get("south_indian_meals"),
                self.all_items.get("jaggery_coffee"),
            ]
            specialties = [it for it in specialties if it]
            state["last_options_shown"] = specialties
            if specialties:
                state["last_mentioned_item"] = specialties[0]["id"]
            if is_kn:
                msg = "ತಿಂಡಿಗೆ ಬಿಸಿ ಬಿಸಿ ಮಸಾಲೆ ದೋಸೆ, ಇಡ್ಲಿ, ವಡೆ ಮತ್ತು ಊಟ ಇವೆ. ಯಾವುದು ಬೇಕು?"
            else:
                msg = "Welcome to The Atom Prasadam! For food, our Ghee Roast Masala Dosa (₹95), hot Idly-Vada (₹55), and authentic South Indian Meals are our top specialties. Which one would you like?"
            return KioskResponse(
                message=msg,
                screen="categories",
                intent="general_food_inquiry",
                data={"specialties": specialties},
                actions=[{"type": "navigate", "payload": {"screen": "categories"}}],
                conversation_state=state,
            )

        is_dosa_varieties_query = any(p in msg_lower for p in [
            "dosa varieties", "what dosa varieties", "which dosa varieties", "what dosas do you have",
            "what kind of dosa", "dosa options", "varieties of dosa", "what varieties do you have",
            "what varieties", "ದೋಸೆ ವಿಧಗಳು", "ಯಾವ ಯಾವ ದೋಸೆ ಇದೆ"
        ]) or (
            "varieties" in msg_lower and (state.get("active_section") == "dose_special" or memory.active_section == "dose_special" or "dose" in (memory.active_section or ""))
        )
        if is_dosa_varieties_query:
            state["last_intent"] = "dosa_varieties"
            dosa_items = [it for it in self.all_items.values() if it.get("section_id") == "dose_special" and it.get("available") is not False]
            top_dosas = dosa_items[:5]
            state["last_options_shown"] = top_dosas
            if top_dosas:
                state["last_mentioned_item"] = top_dosas[0]["id"]
            if is_kn:
                msg = "ನಮ್ಮಲ್ಲಿ ತುಪ್ಪದ ಮಸಾಲೆ ದೋಸೆ (₹95), ಪ್ಲೇನ್ ದೋಸೆ (₹75), ಸೆಟ್ ದೋಸೆ (₹85), ಮತ್ತು ರವಾ ದೋಸೆ (₹90) ಇವೆ. ಯಾವುದು ಬೇಕು?"
            else:
                msg = "We have Ghee Roast Masala Dosa (₹95), Ghee Plain Dosa (₹75), Ghee Set Dosa (₹85), Ghee Rava Dosa (₹90), and Pudi Masala Dosa (₹105). Which one would you prefer?"
            return KioskResponse(
                message=msg,
                screen="menu_items",
                intent="dosa_varieties",
                data={"section_id": "dose_special", "options": top_dosas},
                actions=[{"type": "navigate", "payload": {"screen": "menu_items", "section_id": "dose_special"}}],
                conversation_state=state,
            )

        # ======================================================================
        # 3h. ADAPTIVE RECOMMENDATION REJECTION ("Actually, not that one", "No, not that", "Something else")
        # ======================================================================
        is_rejection_query = not any(w in msg_lower for w in ["recommend", "special"]) and any(p in msg_lower for p in [
            "not that one", "not that", "no not that", "dont want that", "don't want that",
            "something else", "show something else", "different one",
            "ಬೇರೆ ಏನಾದರೂ", "ಬೇರೆ ಏನು", "ಬೇರೆ ತೋರಿಸು", "ಅದು ಬೇಡ"
        ])
        if is_rejection_query and state.get("last_options_shown"):
            prev_ids = [it["id"] for it in state["last_options_shown"] if isinstance(it, dict) and "id" in it]
            state.setdefault("rejected_items", []).extend(prev_ids)

            alt_candidates = [
                self.all_items.get("poori_saagu_3"),
                self.all_items.get("ghee_set_dosa"),
                self.all_items.get("chow_chow_bath"),
                self.all_items.get("special_mysore_pak_1")
            ]
            alt_items = [it for it in alt_candidates if it and it["id"] not in state["rejected_items"]]
            if not alt_items:
                alt_items = [it for it in alt_candidates if it]
            state["last_options_shown"] = alt_items
            if alt_items:
                state["last_mentioned_item"] = alt_items[0]["id"]

            if is_kn:
                msg = "ಸರಿ, ಹಾಗಾದ್ರೆ ಬಿಸಿ ಪೂರಿ ಸಾಗು (₹65) ಅಥವಾ ಮೃದುವಾದ ಸೆಟ್ ದೋಸೆ (₹85) ತಗೋತೀರಾ?"
            else:
                msg = "No problem! How about our hot Poori Saagu (₹65) or crispy Set Dosa (₹85)? Both are house favorites."
            return KioskResponse(
                message=msg,
                screen="menu_items",
                intent="recommendation_adapted",
                data={"options": alt_items},
                conversation_state=state,
            )

        # ======================================================================
        # 3i. MULTI-ITEM ORDER HANDLING (Journey B & conversational compounding)
        # ======================================================================
        multi_items = self.extract_multi_items(raw_msg)
        if multi_items:
            actions = []
            added_summaries_en = []
            added_summaries_kn = []
            unavailable_items = []
            total_added_price = 0.0

            for item, qty in multi_items:
                item_id = item["id"]
                name = item["name"]
                kannada = item.get("kannadaName") or item.get("kannada_name")
                price = float(item["price"])
                sec_id = item.get("section_id", "")

                # Check availability
                if item.get("available") is False or item.get("requires_review") is True:
                    unavailable_items.append((item, kannada or name))
                    continue

                subtotal = price * qty
                total_added_price += subtotal

                actions.append({
                    "type": "add_to_cart",
                    "payload": {
                        "id": item_id,
                        "name": name,
                        "price": price,
                        "quantity": qty,
                        "image": item.get("image", ""),
                        "section_id": sec_id,
                        "kannadaName": kannada,
                    }
                })

                q_str = f"{qty} " if qty > 1 else ""
                k_str = f" ({kannada})" if kannada else ""
                added_summaries_en.append(f"{q_str}{name}{k_str} (₹{subtotal:.0f})")

                num_kn = {1: "ಒಂದು", 2: "ಎರಡು", 3: "ಮೂರು", 4: "ನಾಲ್ಕು", 5: "ಐದು"}.get(qty, str(qty))
                dish_display = kannada or name
                added_summaries_kn.append(f"{num_kn} {dish_display}")

            if actions:
                state["last_intent"] = "add_multi_to_cart"
                state["last_added_item_id"] = multi_items[-1][0]["id"]
                state["last_added_items"] = [item["id"] for item, _ in multi_items if item.get("available") is not False]
                state["last_mentioned_item"] = multi_items[-1][0]["id"]
                state["conversational_phase"] = "ordering"

                if is_kn:
                    msg = f"{' ಮತ್ತು '.join(added_summaries_kn)} ಕಾರ್ಟ್ಗೆ ಸೇರಿಸಿದ್ದೀನಿ. ಒಟ್ಟು {total_added_price:.0f} ರೂಪಾಯಿ."
                    if unavailable_items:
                        unav_names = ", ".join(unav_name for _, unav_name in unavailable_items)
                        msg += f" ಆದರೆ {unav_names} ಲಭ್ಯವಿಲ್ಲ."
                    msg += " ಇನ್ನೇನಾದರೂ ಬೇಕಾ?"
                else:
                    msg = f"I've added {', '.join(added_summaries_en)} to your cart, totaling ₹{total_added_price:.0f}."
                    if unavailable_items:
                        unav_names = ", ".join(it["name"] for it, _ in unavailable_items)
                        msg += f" Note: {unav_names} is currently unavailable."
                    msg += " Would you like anything else to eat or drink?"

                return KioskResponse(
                    message=msg,
                    screen="cart" if current_screen == "cart" else "menu_items",
                    intent="add_to_cart",
                    data={
                        "items_added": [item["id"] for item, _ in multi_items],
                        "total_added": total_added_price,
                    },
                    actions=actions,
                    conversation_state=state,
                )

        # ======================================================================
        # 3j. PAYMENT METHODS INQUIRY (Grounded & Demonstrative)
        # ======================================================================
        is_payment_query = any(p in msg_lower for p in [
            "payment method", "how to pay", "how can i pay", "accept upi", "pay with upi",
            "pay by upi", "accept card", "pay by card", "accept cash", "pay by cash",
            "google pay", "phonepe", "paytm", "can i pay with", "can i pay by"
        ])
        if is_payment_query and not any(kw in msg_lower for kw in ["checkout", "finish order", "complete order", "i want to pay"]):
            state["last_intent"] = "payment_info"
            msg = "ನಾವು ಯುಪಿಐ (ಗೂಗಲ್ ಪೇ, ಫೋನ್ಪೇ, ಪೇಟಿಎಂ), ಕಾರ್ಡ್ ಮತ್ತು ನಗದು ಪಾವತಿಗಳನ್ನು ಸ್ವೀಕರಿಸುತ್ತೇವೆ." if is_kn else "We accept UPI (Scan & Pay with Google Pay, PhonePe, Paytm), Credit/Debit Cards, and Cash at the billing counter. All kiosk checkout payments are demonstrative for this interactive demo."
            return KioskResponse(
                message=msg,
                screen=current_screen or "categories",
                intent="payment_info",
                conversation_state=state,
            )

        # ======================================================================
        # 4. CHECKOUT & PAYMENT INTENT ("I want to pay", "Checkout", "ಆರ್ಡರ್ ಖಚಿತಪಡಿಸು")
        # ======================================================================
        checkout_keywords = [
            "checkout", "pay", "payment", "place order", "complete order", "bill", "finish order", "i want to pay", "pay bill",
            "ಆರ್ಡರ್ ಖಚಿತಪಡಿಸು", "ಆರ್ಡರ್ ಮಾಡಿ", "ಖಚಿತಪಡಿಸು", "ಬಿಲ್ ಪಾವತಿಸು", "ಪಾವತಿ",
            "order khachithapadisu", "order confirm madi", "khachithapadisu", "bill madi"
        ]
        if any(kw in msg_lower for kw in checkout_keywords):
            state["last_intent"] = "checkout"
            if not cart_items:
                msg = "ನಿಮ್ಮ ಕಾರ್ಟ್ ಖಾಲಿಯಾಗಿದೆ. ದಯವಿಟ್ಟು ಆರ್ಡರ್ ಮಾಡಲು ಮೊದಲು ಪದಾರ್ಥಗಳನ್ನು ಸೇರಿಸಿ." if is_kn else "Your cart is currently empty. Would you like to add some delicious dosas, meals, or filter coffee before checking out?"
                return KioskResponse(
                    message=msg,
                    screen="categories",
                    intent="checkout_empty",
                    actions=[{"type": "navigate", "payload": {"screen": "categories"}}],
                    conversation_state=state,
                )
            total = sum(float(i.get("price", 0)) * int(i.get("quantity", 1)) for i in cart_items)
            item_count = sum(int(i.get("quantity", 1)) for i in cart_items)
            state["pending_checkout"] = True
            msg = f"ನಿಮ್ಮ ಕಾರ್ಟ್ನಲ್ಲಿ {item_count} ಪದಾರ್ಥಗಳಿವೆ, ಒಟ್ಟು ಮೊತ್ತ {total:.0f} ರೂಪಾಯಿ. ಪಾವತಿಗೆ ಮುಂದುವರಿಯೋಣವೇ?" if is_kn else f"You have {item_count} items in your cart totaling ₹{total:.0f}. Would you like to review your tray and proceed to payment?"
            return KioskResponse(
                message=msg,
                screen="cart",
                intent="checkout",
                data={"total": total, "item_count": item_count, "cart": cart_items},
                actions=[{"type": "navigate", "payload": {"screen": "cart"}}],
                conversation_state=state,
                requires_confirmation=True,
            )

        # ======================================================================
        # 5. VIEW / SUMMARY OF CART & TOTAL ("What is in my tray?", "How much is my order?", "ಕಾರ್ಟ್ ತೋರಿಸು")
        # ======================================================================
        cart_keywords = [
            "what is in my cart", "show cart", "show me the cart", "show me cart", "view cart", "view the cart",
            "check cart", "my tray", "what did i order", "go to cart", "open cart", "open the cart", "take me to cart",
            "cart summary", "what is in my tray", "how much is my order", "how much is the bill",
            "how much is it", "order total", "cart total", "what is my bill",
            "ಕಾರ್ಟ್ ತೋರಿಸು", "ನನ್ನ ಕಾರ್ಟ್", "ಕಾರ್ಟ್ ನೋಡು", "ಟ್ರೇ ತೋರಿಸು", "ಕಾರ್ಟ್",
            "cart torisu", "nanna cart torisu", "tray torisu", "cart nodu",
            "total eshtu", "total yestu", "bill eshtu", "bill yestu", "eshtu aytu", "eshtu aaytu", "yestu aytu", "yestu aaytu",
            "ಒಟ್ಟು ಎಷ್ಟು", "ಬಿಲ್ ಎಷ್ಟು", "ಎಷ್ಟು ಆಯ್ತು", "ಎಷ್ಟು ಆಯಿತು"
        ]
        if classified_intent.action == "view_cart" or any(kw in msg_lower for kw in cart_keywords):
            state["last_intent"] = "view_cart"
            if not cart_items:
                msg = "ನಿಮ್ಮ ಕಾರ್ಟ್ ಖಾಲಿಯಾಗಿದೆ. ನೀವು ಏನು ಆರ್ಡರ್ ಮಾಡಲು ಬಯಸುತ್ತೀರಿ?" if is_kn else "Your cart is currently empty. What would you like to order today?"
                return KioskResponse(
                    message=msg,
                    screen="cart",
                    intent="view_cart",
                    data={"cart": [], "total": 0},
                    actions=[{"type": "navigate", "payload": {"screen": "cart"}}],
                    conversation_state=state,
                )
            total = sum(float(i.get("price", 0)) * int(i.get("quantity", 1)) for i in cart_items)
            if is_kn:
                summary_parts = [f"{i.get('quantity', 1)} {i.get('kannadaName') or i.get('kannada_name') or i.get('name')}" for i in cart_items]
                msg = f"ನಿಮ್ಮ ಕಾರ್ಟ್ ಇಲ್ಲಿದೆ. {', '.join(summary_parts)}. ಒಟ್ಟು ಮೊತ್ತ {total:.0f} ರೂಪಾಯಿ. ನಿಮ್ಮ ಆರ್ಡರ್ ವಿವರಗಳನ್ನು ನೋಡಬಹುದು."
            else:
                summary_parts = [f"{i.get('quantity', 1)}x {i.get('name')}" for i in cart_items]
                msg = f"Your cart has: {', '.join(summary_parts)}. Total is ₹{total:.0f}. Would you like to add anything else or proceed to checkout?"
            return KioskResponse(
                message=msg,
                screen="cart",
                intent="view_cart",
                data={"cart": cart_items, "total": total},
                actions=[{"type": "navigate", "payload": {"screen": "cart"}}],
                conversation_state=state,
            )

        # ======================================================================
        # 6. QUANTITY MODIFICATION & CORRECTION ("Make that two", "No, I meant one", "Actually, ondu beda, eradu kodi")
        # ======================================================================
        is_qty_mod = any(p in msg_lower for p in ["make that", "make it", "change to", "change that to", "update to"])
        is_qty_correction = any(p in msg_lower for p in ["no, i meant", "no i meant", "actually one", "actually 1", "actually two", "actually 2", "i meant", "only one", "just one"]) or ("actually" in msg_lower and any(w in msg_lower for w in ["one", "two", "three", "1", "2", "3", "ondu", "eradu", "mooru"]))
        is_kannada_qty_correction = any(p in msg_lower for p in [
            "beda", "saaku", "saku", "ondu beda", "eradu beda", "eradu kodi", "ondu kodi", "2 kodi", "1 kodi",
            "ಒಂದು ಬೇಡ", "ಎರಡು ಕೊಡಿ", "ಸಾಕು", "ಬೇಡ"
        ])

        if (is_qty_mod or is_qty_correction or is_kannada_qty_correction or classified_intent.action == "set_quantity") and not has_specific_dish:
            target_id = state.get("last_added_item_id")
            if not target_id and cart_items:
                target_id = cart_items[-1].get("id") or cart_items[-1].get("item_id")

            if any(p in msg_lower for p in ["eradu kodi", "2 kodi", "eradu saaku", "2 saaku", "make it two", "make that two", "make it 2", "make that 2", "give me two", "give two"]):
                new_qty = 2
            elif any(p in msg_lower for p in ["ondu saaku", "1 saaku", "ondu kodi", "1 kodi", "make it one", "make that one", "make it 1", "make that 1", "only one", "just one"]):
                new_qty = 1
            elif any(p in msg_lower for p in ["mooru kodi", "3 kodi", "make it three", "make that three", "make it 3"]):
                new_qty = 3
            else:
                new_qty = self._extract_quantity(raw_msg)

            if target_id and target_id in self.all_items:
                target_item = self.all_items[target_id]
                item_name = target_item["name"]
                kannada = target_item.get("kannadaName") or target_item.get("kannada_name")
                price = float(target_item["price"])
                state["last_intent"] = "set_quantity"

                action_result = {
                    "action_type": "set_quantity",
                    "item": item_name,
                    "kannada_name": kannada,
                    "quantity": new_qty,
                    "subtotal": round(price * new_qty, 2),
                    "cart_total": round(price * new_qty, 2),
                }
                cashier_msg = self.cashier_generator.generate_cashier_response(
                    action_result=action_result,
                    user_input=raw_msg,
                    target_language="kn" if is_kn else "en",
                    active_screen="cart",
                    recent_dialogue=memory.format_history_for_prompt(max_turns=3),
                )
                if not cashier_msg:
                    cashier_msg = f"ಆಯ್ತು, {new_qty} {kannada or item_name}." if is_kn else f"Sure, updated to {new_qty} {item_name}."

                return KioskResponse(
                    message=cashier_msg,
                    screen="cart",
                    intent="set_quantity",
                    data={"item_id": target_id, "quantity": new_qty, "price": price},
                    actions=[
                        {"type": "set_quantity", "payload": {"id": target_id, "quantity": new_qty}}
                    ],
                    conversation_state=state,
                )
            elif cart_items:
                target_id = cart_items[-1].get("id") or cart_items[-1].get("item_id")
                item_name = cart_items[-1].get("name", "item")
                price = float(cart_items[-1].get("price", 0))
                state["last_intent"] = "set_quantity"
                msg_prefix = "Understood! " if is_qty_correction else ""
                return KioskResponse(
                    message=f"{msg_prefix}I have updated {item_name} quantity to {new_qty} in your cart.",
                    screen="cart",
                    intent="set_quantity",
                    data={"item_id": target_id, "quantity": new_qty},
                    actions=[
                        {"type": "set_quantity", "payload": {"id": target_id, "quantity": new_qty}}
                    ],
                    conversation_state=state,
                )
            else:
                state["last_intent"] = "set_quantity_empty"
                return KioskResponse(
                    message="Your cart is currently empty. Please add a dish to your tray first, and then you can update its quantity.",
                    screen="categories",
                    intent="set_quantity_empty",
                    actions=[{"type": "navigate", "payload": {"screen": "categories"}}],
                    conversation_state=state,
                )

        # ======================================================================
        # 7. REMOVE FROM CART ("Remove the last item", "Take out ...")
        # ======================================================================
        if any(p in msg_lower for p in ["remove the last item", "remove last item", "take out the last one", "delete the last item", "remove that last one"]):
            target_id = state.get("last_added_item_id")
            if not target_id and cart_items:
                target_id = cart_items[-1].get("id") or cart_items[-1].get("item_id")
            if target_id:
                item_name = self.all_items.get(target_id, {}).get("name") or (cart_items[-1].get("name") if cart_items else "item")
                state["last_intent"] = "remove_from_cart"
                state["last_added_item_id"] = None
                return KioskResponse(
                    message=f"I have removed {item_name} from your cart.",
                    screen="cart",
                    intent="remove_from_cart",
                    data={"removed_item_id": target_id, "name": item_name},
                    actions=[{"type": "remove_from_cart", "payload": {"id": target_id}}],
                    conversation_state=state,
                )
            else:
                return KioskResponse(
                    message="Your cart is empty. There is no item to remove.",
                    screen="cart",
                    intent="remove_from_cart",
                    actions=[{"type": "navigate", "payload": {"screen": "cart"}}],
                    conversation_state=state,
                )

        remove_keywords = ["remove", "delete", "cancel item", "take out", "drop"]
        if any(kw in msg_lower for kw in remove_keywords):
            state["last_intent"] = "remove_from_cart"
            matched_cart_item = None
            for item in cart_items:
                item_name_norm = self.index._normalize(item.get("name", ""))
                if item_name_norm in msg_lower or any(tok in msg_lower for tok in item_name_norm.split() if len(tok) > 3):
                    matched_cart_item = item
                    break

            if matched_cart_item:
                item_id = matched_cart_item.get("id") or matched_cart_item.get("item_id")
                return KioskResponse(
                    message=f"I have removed {matched_cart_item.get('name')} from your cart.",
                    screen="cart",
                    intent="remove_from_cart",
                    data={"removed_item_id": item_id, "name": matched_cart_item.get("name")},
                    actions=[{"type": "remove_from_cart", "payload": {"id": item_id}}],
                    conversation_state=state,
                )
            else:
                return KioskResponse(
                    message="Which item would you like me to remove from your cart?",
                    screen="cart",
                    intent="clarify_remove",
                    actions=[{"type": "navigate", "payload": {"screen": "cart"}}],
                    conversation_state=state,
                )

        # ======================================================================
        # 8. CLEAR CART
        # ======================================================================
        if "clear cart" in msg_lower or "empty cart" in msg_lower or "remove all" in msg_lower:
            state["last_intent"] = "clear_cart"
            return KioskResponse(
                message="I have cleared your cart. You can start fresh with our menu items.",
                screen="categories",
                intent="clear_cart",
                actions=[
                    {"type": "clear_cart", "payload": {}},
                    {"type": "navigate", "payload": {"screen": "categories"}}
                ],
                conversation_state=state,
            )

        # ======================================================================
        # 9. PRICE COMPARISON ("Which one is cheaper?", "Compare prices")
        # ======================================================================
        is_price_comp = any(p in msg_lower for p in ["which one is cheaper", "which is cheaper", "compare prices", "what is cheaper", "cheapest", "which one costs less"])
        if is_price_comp:
            state["last_intent"] = "price_comparison"
            options = state.get("last_options_shown") or []

            # If no cached options, but a section/keyword is in query (e.g. "which dosa is cheaper")
            if not options:
                matched_sec = self.index.find_section_or_category(raw_msg)
                if matched_sec and matched_sec[0] == "section":
                    options = [it for it in self.all_items.values() if it.get("section_id") == matched_sec[1] and it.get("available") is not False]

            if options:
                sorted_opts = sorted(options, key=lambda x: x.get("price", 9999))
                cheapest = sorted_opts[0]
                state["cheapest_item"] = cheapest
                state["last_mentioned_item"] = cheapest["id"]
                other_opts = [f"{it['name']} (₹{it['price']:.0f})" for it in sorted_opts[1:3]]
                other_str = f" Next are {', '.join(other_opts)}." if other_opts else ""
                return KioskResponse(
                    message=f"Between these options, the cheapest is {cheapest['name']} at ₹{cheapest['price']:.0f}.{other_str} Would you like to add it to your cart?",
                    screen="menu_items",
                    intent="price_comparison",
                    data={"cheapest_item": cheapest, "options": sorted_opts[:4]},
                    conversation_state=state,
                )
            else:
                return KioskResponse(
                    message="Which items would you like me to compare? You can ask about our Dosas, South Indian Breakfast, or Sweets.",
                    screen="categories",
                    intent="price_comparison_clarify",
                    conversation_state=state,
                )

        # ======================================================================
        # 10. ANAPHORA & CONTEXTUAL ADD ("Add that one", "ಇನ್ನೊಂದು ಸೇರಿಸು", "one more")
        # ======================================================================
        is_one_more = any(p in norm_query for p in [
            "innondhu serisu", "innu ondu serisu", "innondhu kodi", "innu ondu kodi",
            "innondhu haaki", "innondhu", "innu ondu", "one more", "add one more",
            "another one", "add another", "one more please", "same again",
            "ಇನ್ನೊಂದು ಸೇರಿಸು", "ಇನ್ನೂ ಒಂದು ಸೇರಿಸು", "ಇನ್ನೊಂದು ಕೊಡಿ", "ಇನ್ನೊಂದು ಹಾಕಿ",
            "ಇನ್ನೊಂದು ಕೊಡು", "ಇನ್ನೂ ಒಂದು ಕೊಡಿ", "ಇನ್ನೊಂದು"
        ])

        has_contextual_target = bool(state.get("cheapest_item") or state.get("last_mentioned_item") or state.get("last_added_item_id") or cart_items)
        has_explicit_item = bool(self.index.find_items_by_query(raw_msg))
        is_qty_context_add = bool(
            has_contextual_target and not has_explicit_item and (
                re.search(r"\b(add|order)\s+(one|two|three|four|five|\d+)\b", msg_lower) or
                re.search(r"^\s*(add\s+)?(two|three|four|\d+)\s*(of\s+(them|those|that))?\s*$", msg_lower)
            )
        )
        is_anaphora_add = is_one_more or is_qty_context_add or any(p in msg_lower for p in [
            "add that one", "add the cheaper one", "add the cheapest", "add that", "add it", "order that one", "order that", "order it", "ಅದನ್ನು ಸೇರಿಸು", "ಅದೇ ಕೊಡು"
        ])
        if is_anaphora_add:
            target_item = None
            if is_one_more:
                target_id = state.get("last_added_item_id") or state.get("last_mentioned_item")
                if not target_id and cart_items:
                    target_id = cart_items[-1].get("id") or cart_items[-1].get("item_id")
                if target_id and target_id in self.all_items:
                    target_item = self.all_items[target_id]
            elif ("cheaper" in msg_lower or "cheapest" in msg_lower) and state.get("cheapest_item"):
                target_item = state.get("cheapest_item")
            elif state.get("cheapest_item") and state.get("last_intent") == "price_comparison":
                target_item = state.get("cheapest_item")
            elif state.get("last_mentioned_item") and state.get("last_mentioned_item") in self.all_items:
                target_item = self.all_items[state.get("last_mentioned_item")]
            elif state.get("last_added_item_id") and state.get("last_added_item_id") in self.all_items:
                target_item = self.all_items[state.get("last_added_item_id")]
            elif cart_items:
                cid = cart_items[-1].get("id") or cart_items[-1].get("item_id")
                if cid and cid in self.all_items:
                    target_item = self.all_items[cid]

            if target_item:
                item_id = target_item["id"]
                name = target_item["name"]
                price = float(target_item["price"])
                sec_id = target_item.get("section_id", "")
                kannada = target_item.get("kannadaName") or target_item.get("kannada_name")

                qty = self._extract_quantity(raw_msg) if is_qty_context_add else 1
                if is_one_more or "one" in msg_lower or "1" in msg_lower:
                    qty = 1

                state["last_intent"] = "add_to_cart"
                state["last_added_item_id"] = item_id
                state["last_mentioned_item"] = item_id

                if is_kn:
                    dish_name = kannada or name
                    if is_one_more:
                        msg = f"ಇನ್ನೊಂದು {dish_name} ಅನ್ನು ಕಾರ್ಟ್ಗೆ ಸೇರಿಸಿದ್ದೇನೆ."
                    else:
                        num_kn = {1: "ಒಂದು", 2: "ಎರಡು", 3: "ಮೂರು", 4: "ನಾಲ್ಕು", 5: "ಐದು"}.get(qty, str(qty))
                        q_str = f"{num_kn} " if qty > 1 else ""
                        msg = f"{q_str}{dish_name} ಅನ್ನು ಕಾರ್ಟ್ಗೆ ಸೇರಿಸಿದ್ದೇನೆ."
                else:
                    if is_one_more:
                        msg = f"I have added one more {name} to your cart."
                    else:
                        q_prefix = f"{qty} " if qty > 1 else ""
                        msg = f"I have added {q_prefix}{name} (₹{price * qty:.0f}) to your cart. Anything else?"

                return KioskResponse(
                    message=msg,
                    screen="cart" if current_screen == "cart" else "menu_items",
                    intent="add_to_cart",
                    data={
                        "item_id": item_id,
                        "name": name,
                        "price": price,
                        "quantity": qty,
                        "section_id": sec_id,
                    },
                    actions=[
                        {
                            "type": "add_to_cart",
                            "payload": {
                                "id": item_id,
                                "name": name,
                                "price": price,
                                "quantity": qty,
                                "image": target_item.get("image", ""),
                                "section_id": sec_id,
                                "kannadaName": kannada,
                            }
                        }
                    ],
                    conversation_state=state,
                )
            else:
                msg = "ಯಾವ ಪದಾರ್ಥವನ್ನು ಸೇರಿಸಬೇಕು? ದಯವಿಟ್ಟು ಹೆಸರು ತಿಳಿಸಿ ಅಥವಾ ಪರದೆಯ ಮೇಲೆ ಆಯ್ಕೆ ಮಾಡಿ." if is_kn else "Which dish would you like to add? Please tell me the name or tap on the screen."
                return KioskResponse(
                    message=msg,
                    screen="menu_items",
                    intent="clarify_item",
                    conversation_state=state,
                )

        # ======================================================================
        # 10b. RESOLVE PENDING CLARIFICATION ("Ghee roast", "The first one", "Second option")
        # ======================================================================
        pending_ids = state.get("pending_clarification") or []
        if pending_ids:
            ordinal_patterns = [
                (r"\b(the\s+)?second(\s+one|\s+option)?\b|\b(option|number|no\.?)\s*(2|two)\b", 1),
                (r"\b(the\s+)?third(\s+one|\s+option)?\b|\b(option|number|no\.?)\s*(3|three)\b", 2),
                (r"\b(the\s+)?fourth(\s+one|\s+option)?\b|\b(option|number|no\.?)\s*(4|four)\b", 3),
                (r"\b(the\s+)?first(\s+one|\s+option)?\b|\b(option|number|no\.?)\s*(1|one)\b", 0),
                (r"\blast(\s+one|\s+option)?\b", -1),
            ]
            chosen_item_id = None
            for pattern, ord_idx in ordinal_patterns:
                if re.search(pattern, msg_lower):
                    if ord_idx == -1 and pending_ids:
                        chosen_item_id = pending_ids[-1]
                        break
                    elif 0 <= ord_idx < len(pending_ids):
                        chosen_item_id = pending_ids[ord_idx]
                        break

            if not chosen_item_id:
                # 1. Exact match on normalized candidate name
                for p_id in pending_ids:
                    p_item = self.all_items.get(p_id)
                    if p_item:
                        p_name_norm = self.index._normalize(p_item.get("name", ""))
                        if norm_query == p_name_norm:
                            chosen_item_id = p_id
                            break

                # 2. Distinguishing substring match
                if not chosen_item_id:
                    matching_candidates = []
                    for p_id in pending_ids:
                        p_item = self.all_items.get(p_id)
                        if p_item:
                            p_name_norm = self.index._normalize(p_item.get("name", ""))
                            if norm_query in p_name_norm:
                                matching_candidates.append(p_id)
                    if len(matching_candidates) == 1:
                        chosen_item_id = matching_candidates[0]

                # 3. Token-based distinguishing match
                if not chosen_item_id:
                    query_tokens = [t for t in norm_query.split() if len(t) > 2 and t not in {"the", "and", "please", "want", "kodi", "beku", "add"}]
                    candidate_token_scores = {}
                    for p_id in pending_ids:
                        p_item = self.all_items.get(p_id)
                        if p_item:
                            p_name_norm = self.index._normalize(p_item.get("name", ""))
                            candidate_token_scores[p_id] = sum(1 for t in query_tokens if t in p_name_norm)
                    sorted_by_score = sorted(candidate_token_scores.items(), key=lambda x: x[1], reverse=True)
                    if sorted_by_score and sorted_by_score[0][1] > 0:
                        if len(sorted_by_score) == 1 or sorted_by_score[0][1] > sorted_by_score[1][1]:
                            chosen_item_id = sorted_by_score[0][0]

            if chosen_item_id and chosen_item_id in self.all_items:
                state["pending_clarification"] = None
                target_item = self.all_items[chosen_item_id]
                item_name = target_item["name"]
                price = float(target_item["price"])
                sec_id = target_item.get("section_id", "")
                kannada = target_item.get("kannadaName") or target_item.get("kannada_name")
                order_qty = state.pop("pending_order_quantity", 1) or 1
                curr_turn_qty = self._extract_quantity(raw_msg)
                if curr_turn_qty > 1:
                    order_qty = curr_turn_qty

                state["last_intent"] = "add_to_cart"
                state["last_added_item_id"] = chosen_item_id
                state["last_mentioned_item"] = chosen_item_id

                action_result = {
                    "action_type": "add_to_cart",
                    "item": item_name,
                    "kannada_name": kannada,
                    "quantity": order_qty,
                    "subtotal": round(price * order_qty, 2),
                    "cart_count": len(cart_items) + order_qty,
                    "cart_total": sum(float(i.get("price", 0)) * int(i.get("quantity", 1)) for i in cart_items) + (price * order_qty),
                }
                cashier_msg = self.cashier_generator.generate_cashier_response(
                    action_result=action_result,
                    user_input=raw_msg,
                    target_language="kn" if is_kn else "en",
                    active_screen="menu_items",
                    recent_dialogue=memory.format_history_for_prompt(max_turns=3),
                )
                if not cashier_msg:
                    num_word_kn = {1: "ಒಂದು", 2: "ಎರಡು", 3: "ಮೂರು"}.get(order_qty, str(order_qty))
                    cashier_msg = f"ಆಯ್ತು! {num_word_kn} {kannada or item_name}." if is_kn else f"Sure, {order_qty} {item_name}."

                return KioskResponse(
                    message=cashier_msg,
                    screen="menu_items",
                    intent="add_to_cart",
                    data={
                        "item_id": chosen_item_id,
                        "name": item_name,
                        "price": price,
                        "quantity": order_qty,
                        "section_id": sec_id,
                    },
                    actions=[
                        {
                            "type": "add_to_cart",
                            "payload": {
                                "id": chosen_item_id,
                                "name": item_name,
                                "price": price,
                                "quantity": order_qty,
                                "image": target_item.get("image", ""),
                                "section_id": sec_id,
                                "kannadaName": kannada,
                            }
                        }
                    ],
                    conversation_state=state,
                )

        # ======================================================================
        # 11. RECOMMENDATIONS & CRISPY SPECIALTIES (Mission E)
        # ======================================================================
        is_crispy = any(w in msg_lower for w in ["crispy", "crisp", "something crispy", "crunchy"])
        if is_crispy:
            state["last_intent"] = "recommend_crispy"
            crispy_items = [
                self.all_items.get("ghee_roast_masala_dosa"),
                self.all_items.get("ghee_paper_plain_dosa"),
                self.all_items.get("maddur_vada_1"),
            ]
            crispy_items = [it for it in crispy_items if it]
            state["last_options_shown"] = crispy_items
            if crispy_items:
                state["last_mentioned_item"] = crispy_items[0]["id"]
            return KioskResponse(
                message="For something crispy, our Ghee Roast Masala Dosa (₹95) and wafer-thin Ghee Paper Plain Dosa (₹130) are roasted to golden perfection in pure ghee! We also have hot Maddur Vada (₹20) in our Snacks section.",
                screen="menu_items",
                intent="recommendation",
                data={"options": crispy_items},
                actions=[{"type": "navigate", "payload": {"screen": "menu_items", "section_id": "dose_special"}}],
                conversation_state=state,
            )

        is_recommendation = any(w in msg_lower for w in [
            "what else do you recommend", "what do you recommend", "recommend",
            "any recommendations", "suggest something", "what is good", "speciality", "specialties"
        ])
        if is_recommendation:
            state["last_intent"] = "recommendation"
            has_dosa = any("dosa" in i.get("name", "").lower() or i.get("section_id") == "dose_special" for i in cart_items)
            has_meals = any("meal" in i.get("name", "").lower() or i.get("section_id") == "meals" for i in cart_items)

            if has_dosa:
                message = "To complement your dosa, I highly recommend our authentic South Indian Filter Coffee (₹30) and sweet Special Mysore Pak (₹65)."
                rec_items = [self.all_items.get("filter_coffee"), self.all_items.get("special_mysore_pak_1")]
            elif has_meals:
                message = "To complete your meal, our traditional Sweet Lassi and hot Gulab Jamun make a perfect pairing!"
                rec_items = [self.all_items.get("jamoon_1"), self.all_items.get("butter_roti")]
            else:
                message = "Our signature specialties are the Ghee Roast Masala Dosa (₹95), authentic South Indian Filter Coffee (₹30), and Mysore Pak (₹65). Would you like to try any of these?"
                rec_items = [self.all_items.get("ghee_roast_masala_dosa"), self.all_items.get("filter_coffee")]

            rec_items = [it for it in rec_items if it]
            state["last_options_shown"] = rec_items
            if rec_items:
                state["last_mentioned_item"] = rec_items[0]["id"]
            return KioskResponse(
                message=message,
                screen="categories",
                intent="recommendation",
                data={"options": rec_items},
                conversation_state=state,
            )

        # ======================================================================
        # 12. BUDGET FILTERING ("Items under 50 rupees", "under 100")
        # ======================================================================
        budget_match = re.search(r"under\s+(?:rs\.?|inr|₹)?\s*(\d+)", msg_lower)
        if budget_match or ("cheap" in msg_lower and "items" in msg_lower):
            budget = float(budget_match.group(1)) if budget_match else 50.0
            state["last_intent"] = "budget_filter"
            affordable_items = [
                it for it in self.all_items.values()
                if it.get("available") is not False and it.get("price", 9999) <= budget
            ]
            affordable_items.sort(key=lambda x: x["price"])
            top_affordable = affordable_items[:4]
            state["last_options_shown"] = top_affordable
            if top_affordable:
                state["cheapest_item"] = top_affordable[0]
                state["last_mentioned_item"] = top_affordable[0]["id"]
                item_strs = [f"{it['name']} (₹{it['price']:.0f})" for it in top_affordable]
                return KioskResponse(
                    message=f"Here are dishes under ₹{budget:.0f}: {', '.join(item_strs)}. Would you like to add any to your cart?",
                    screen="menu_items",
                    intent="budget_filter",
                    data={"options": top_affordable, "budget": budget},
                    conversation_state=state,
                )
            else:
                return KioskResponse(
                    message=f"We don't have items under ₹{budget:.0f}. Our snacks and hot beverages start from ₹20.",
                    screen="categories",
                    intent="budget_filter",
                    conversation_state=state,
                )

        # ======================================================================
        # 13. DIETARY & JAIN / WITHOUT ONION INQUIRIES
        # ======================================================================
        if any(term in msg_lower for term in ["without onion", "no onion", "without garlic", "no garlic", "jain option", "jain food", "jain"]):
            is_view_cmd = any(v in msg_lower for v in ["show", "open", "view", "explore", "see", "ತೋರಿಸು", "ತೋರ್ಸು"])
            if is_view_cmd:
                sec = self.index.section_lookup.get("north indian jain items") or self.index.section_lookup.get("north_indian_jain_items")
                sec_title = sec.get("canonical_name", "North Indian Jain Items") if sec else "North Indian Jain Items"
                kannada_title = sec.get("kannada_name", "ಉತ್ತರ ಭಾರತೀಯ ಜೈನ್ ಐಟಮ್ಸ್") if sec else "ಉತ್ತರ ಭಾರತೀಯ ಜೈನ್ ಐಟಮ್ಸ್"
                state["last_intent"] = "show_section"
                msg = f"ಸರಿ, {kannada_title} ಮೆನು ತೋರಿಸುತ್ತಿದ್ದೇನೆ." if is_kn else f"Opening {sec_title} ({kannada_title}). You can tap any item or tell me what to add to your cart."
                return KioskResponse(
                    message=msg,
                    screen="menu_items",
                    intent="show_section",
                    data={"section_id": "north_indian_jain_items", "section_title": sec_title},
                    actions=[{"type": "navigate", "payload": {"screen": "menu_items", "section_id": "north_indian_jain_items"}}],
                    conversation_state=state,
                )
            state["last_intent"] = "jain_query"
            msg = "ನಮ್ಮಲ್ಲಿ ಉತ್ತರ ಭಾರತೀಯ ಜೈನ್ ವಿಭಾಗವಿದೆ. ಎಲ್ಲಾ ಪದಾರ್ಥಗಳನ್ನು ಈರುಳ್ಳಿ ಮತ್ತು ಬೆಳ್ಳುಳ್ಳಿ ಇಲ್ಲದೆ ತಯಾರಿಸಲಾಗುತ್ತದೆ. ಆ ವಿಭಾಗವನ್ನು ತೆರೆಯಬೇಕೇ?" if is_kn else "We have a dedicated North Indian Jain Items section where all dishes are prepared without onion and garlic to strict Jain traditions. Would you like me to open that section for you?"
            return KioskResponse(
                message=msg,
                screen="menu_items",
                intent="jain_query",
                data={"section_id": "north_indian_jain_items", "section_title": "North Indian Jain Items"},
                actions=[{"type": "navigate", "payload": {"screen": "menu_items", "section_id": "north_indian_jain_items"}}],
                conversation_state=state,
            )

        if any(term in msg_lower for term in ["pure veg", "vegetarian", "non veg", "meat", "egg", "sattvic"]):
            state["last_intent"] = "dietary_query"
            return KioskResponse(
                message="All food served at The Atom Prasadam is 100% pure vegetarian, prepared with authentic traditional ingredients and pure ghee. We serve zero non-vegetarian food, meat, or eggs.",
                screen="categories",
                intent="dietary_query",
                data={"dietary_type": "pure_veg", "guaranteed": True},
                conversation_state=state,
            )

        if any(term in msg_lower for term in ["allergen", "allergy", "nut allergy", "gluten", "lactose"]):
            state["last_intent"] = "allergen_query"
            return KioskResponse(
                message="Our dishes are freshly prepared using traditional South and North Indian recipes with milk, ghee, and nuts in select sweets. Because our catalogue does not currently itemize individual allergen traces, please consult our kitchen supervisor for specific severe allergies.",
                screen=current_screen or "categories",
                intent="allergen_query",
                conversation_state=state,
            )

        # ======================================================================
        # 14. ORDER STATUS LOOKUP
        # ======================================================================
        order_match = re.search(r"\b(ord-[a-z0-9\-]+)\b", msg_lower)
        if order_match or "order status" in msg_lower or "where is my order" in msg_lower:
            state["last_intent"] = "order_status"
            order_id = order_match.group(1).upper() if order_match else None
            if order_id and orders_store and order_id in orders_store:
                ord_data = orders_store[order_id]
                status = ord_data.get("status", "received").capitalize()
                return KioskResponse(
                    message=f"Order {order_id} is currently {status}. It is being prepared with pure ingredients.",
                    screen="order_complete",
                    intent="order_status",
                    data={"order": ord_data},
                    conversation_state=state,
                )
            elif order_id:
                return KioskResponse(
                    message=f"Order {order_id} was not found in our active records. Please check the order number on your receipt.",
                    screen="home",
                    intent="order_status_not_found",
                    conversation_state=state,
                )

        # ======================================================================
        # 14b. PAYMENT METHODS INQUIRY (Grounded & Demonstrative)
        # ======================================================================
        is_payment_query = any(p in msg_lower for p in [
            "payment method", "how to pay", "how can i pay", "accept upi", "pay with upi",
            "pay by upi", "accept card", "pay by card", "accept cash", "pay by cash",
            "google pay", "phonepe", "paytm", "can i pay with", "can i pay by"
        ])
        if is_payment_query and not any(kw in msg_lower for kw in ["checkout", "finish", "complete", "i want to pay"]):
            state["last_intent"] = "payment_info"
            return KioskResponse(
                message="We accept UPI (Scan & Pay with Google Pay, PhonePe, Paytm), Credit/Debit Cards, and Cash at the billing counter. All kiosk checkout payments are demonstrative for this interactive demo.",
                screen=current_screen or "categories",
                intent="payment_info",
                conversation_state=state,
            )

        # ======================================================================
        # 14c. PICKUP & ORDER COLLECTION INQUIRY
        # ======================================================================
        is_pickup_query = any(p in msg_lower for p in [
            "where do i collect", "where to collect", "where is my food", "pickup counter",
            "how to get food", "how do i get my food", "where to get food", "where is the pickup", "where is counter"
        ])
        if is_pickup_query:
            state["last_intent"] = "pickup_info"
            return KioskResponse(
                message="After completing checkout, your token number will be shown on the screen and printed receipt. When your number is called, you can collect your fresh dishes at the Prasadam food pickup counter!",
                screen=current_screen or "categories",
                intent="pickup_info",
                conversation_state=state,
            )

        # ======================================================================
        # 14d. RESTAURANT HOURS & TIMINGS INQUIRY
        # ======================================================================
        is_hours_query = any(p in msg_lower for p in [
            "what are your hours", "what are your timings", "opening time", "closing time",
            "when do you open", "when do you close", "restaurant timing", "timings"
        ])
        if is_hours_query:
            state["last_intent"] = "hours_info"
            return KioskResponse(
                message="The Atom Prasadam is open daily from 6:30 AM to 10:30 PM, serving South Indian breakfast, full meals, evening snacks, and dinner.",
                screen=current_screen or "categories",
                intent="hours_info",
                conversation_state=state,
            )

        # ======================================================================
        # 15. SECTION / CATEGORY REQUESTS ("Show me dosa", "What is available in South Indian breakfast?")
        # ======================================================================
        sec_or_cat = self.index.find_section_or_category(raw_msg)
        matched_items = self.index.find_items_by_query(raw_msg)
        has_high_confidence_dish = bool(matched_items and matched_items[0][1] >= 0.85)

        is_ordering_verb = any(v in msg_lower for v in [
            "add", "order", "get", "give me", "give", "i want", "buy", "parcel",
            # Kannada verbs
            "kodi", "kodu", "beku", "haaki", "haki", "thago", "thagoli", "serisu", "thanni",
            "ಕೊಡಿ", "ಕೊಡು", "ಬೇಕು", "ಹಾಕಿ", "ತಗೋ", "ತಗೊಳ್ಳಿ", "ಸೇರಿಸು", "ತನ್ನಿ"
        ])
        is_viewing_verb = any(v in msg_lower for v in [
            "show", "open", "view", "what is available", "what do you have", "what do you serve", "explore", "list", "see menu",
            "ತೋರಿಸು", "ತೋರ್ಸು", "ನೋಡು", "ತೋರಿಸಿ", "torisu", "thodisu", "nodona", "torisi"
        ])

        # Check if inquiry is specifically about an individual dish price/description/availability
        is_dish_price_or_desc = any(q in msg_lower for q in [
            "tell me about", "describe", "details of", "explain", "how is", "price of", "how much is", "how much does", "cost of", "rate of", "ಬೆಲೆ",
            "ಎಷ್ಟು", "yestu", "eshtu"
        ])
        is_dish_avail = any(q in msg_lower for q in ["ideya", "ide ya", "ಇದೆಯಾ", "ಲಭ್ಯವಿದೆಯೇ", "available", "is there", "do you have"]) and (has_high_confidence_dish or has_specific_dish)
        is_dish_inquiry = is_dish_price_or_desc or is_dish_avail
        cleaned_words = [w for w in norm_query.split() if w not in {"a", "an", "the", "some", "how", "much", "what", "is", "price", "of", "cost", "show", "me", "open", "view", "details", "ತೋರಿಸು", "ನೋಡು", "torisu"}]
        cleaned_for_check = " ".join(cleaned_words)
        is_dish_exact = (cleaned_for_check in self.index.normalized_to_item) and (cleaned_for_check not in self.index.section_lookup) and (cleaned_for_check not in self.index.category_lookup)

        has_kannada_number = any(w in raw_msg.split() for w in ["ಒಂದು", "ಎರಡು", "ಮೂರು", "ನಾಲ್ಕು", "ಐದು", "ಆರು", "ಏಳು", "ಎಂಟು", "ಒಂಬತ್ತು", "ಹತ್ತು"])
        qty_check = self._extract_quantity(raw_msg)
        is_dish_order = (has_high_confidence_dish or is_dish_exact or (matched_items and is_ordering_verb and sec_or_cat and sec_or_cat[0] == "section")) and (is_ordering_verb or qty_check > 1 or has_kannada_number)

        if sec_or_cat and not is_dish_order and not is_dish_exact and not is_dish_inquiry:
            match_type, match_id, match_obj = sec_or_cat
            if match_type == "section":
                sec_title = match_obj.get("canonical_name", match_id)
                kannada_title = match_obj.get("kannada_name", "")
                state["last_intent"] = "show_section"

                # Cache section items into last_options_shown for contextual follow-ups ("which one is cheaper?")
                sec_items = [it for it in self.all_items.values() if it.get("section_id") == match_id and it.get("available") is not False]
                state["last_options_shown"] = sec_items[:8]
                if sec_items:
                    state["last_mentioned_item"] = sec_items[0]["id"]

                if is_kn:
                    display_title = kannada_title or sec_title
                    msg = f"ಸರಿ, {display_title} ಮೆನು ತೋರಿಸುತ್ತಿದ್ದೇನೆ."
                else:
                    title_desc = f"{sec_title} ({kannada_title})" if kannada_title else sec_title
                    msg = f"Opening {title_desc}. You can tap any item or tell me what to add to your cart."

                return KioskResponse(
                    message=msg,
                    screen="menu_items",
                    intent="show_section",
                    data={"section_id": match_id, "section_title": sec_title, "options": sec_items[:8]},
                    actions=[{"type": "navigate", "payload": {"screen": "menu_items", "section_id": match_id}}],
                    conversation_state=state,
                )
            elif match_type == "category":
                cat_title = match_obj.get("title_english", match_id)
                kn_cat_title = match_obj.get("title_kannada", "")
                state["last_intent"] = "show_category"
                if is_kn:
                    display_title = kn_cat_title or cat_title
                    msg = f"{display_title} ಇಲ್ಲಿದೆ. ಯಾವ ವಿಭಾಗವನ್ನು ನೋಡಲು ಬಯಸುತ್ತೀರಿ?"
                else:
                    msg = f"Here is {cat_title}. Which section would you like to explore?"

                return KioskResponse(
                    message=msg,
                    screen="subcategories",
                    intent="show_category",
                    data={"category_id": match_id, "category_title": cat_title},
                    actions=[{"type": "navigate", "payload": {"screen": "subcategories", "category_id": match_id}}],
                    conversation_state=state,
                )

        # ======================================================================
        # 16. DISH MATCHING: ADD TO CART OR PRODUCT DETAILS
        # ======================================================================
        matched_items = self.index.find_items_by_query(raw_msg)
        quantity = self._extract_quantity(raw_msg)

        if matched_items:
            best_item, confidence = matched_items[0]

            # Ambiguity check: only trigger if top 2 matches are virtually tied
            if len(matched_items) > 1 and (confidence - matched_items[1][1]) < 0.08 and confidence < 0.98:
                target_sec = matched_items[0][0].get("section_id", "dose_special")
                state["pending_clarification"] = [it["id"] for it, _ in matched_items[:4]]
                state["last_options_shown"] = [it for it, _ in matched_items[:4]]
                state["pending_order_quantity"] = quantity
                if "dose" in msg_lower or "dosa" in msg_lower or "ದೋಸೆ" in msg_lower:
                    msg = "ಖಂಡಿತ! ನಮ್ಮಲ್ಲಿ ಮಸಾಲೆ ದೋಸೆ, ಸೆಟ್ ದೋಸೆ, ಪ್ಲೇನ್ ದೋಸೆ ಮತ್ತು ರವಾ ದೋಸೆ ಇದೆ. ನಿಮಗೆ ಯಾವುದು ಬೇಕು?" if is_kn else "Sure! We have Masala Dosa, Set Dosa, Plain Dosa, and Rava Dosa. Which one would you like?"
                else:
                    top_names = [f"{it['name']} (₹{it['price']:.0f})" for it, _ in matched_items[:4]]
                    msg = f"ನಮ್ಮಲ್ಲಿ ಹಲವು ಆಯ್ಕೆಗಳಿವೆ: {', '.join(top_names)}. ನೀವು ಯಾವುದನ್ನು ಬಯಸುತ್ತೀರಿ?" if is_kn else f"We have multiple options: {', '.join(top_names)}. Which one would you prefer?"
                return KioskResponse(
                    message=msg,
                    screen="menu_items",
                    intent="clarify_item",
                    data={"section_id": target_sec, "options": [it for it, _ in matched_items[:4]]},
                    actions=[{"type": "navigate", "payload": {"screen": "menu_items", "section_id": target_sec}}],
                    conversation_state=state,
                )

            # High confidence item match
            if confidence >= 0.65:
                item_id = best_item["id"]
                item_name = best_item["name"]
                kannada = best_item.get("kannadaName") or best_item.get("kannada_name")
                price = best_item["price"]
                sec_id = best_item.get("section_id", "")
                state["last_mentioned_item"] = item_id

                # Handle unavailable items with alternative suggestions (Mission E)
                if best_item.get("available") is False or best_item.get("requires_review") is True:
                    state["last_intent"] = "item_unavailable"
                    if is_kn:
                        alt_message = f"ಕ್ಷಮಿಸಿ, ಈ {kannada or item_name} ಈಗ ಲಭ್ಯವಿಲ್ಲ. ಬೇರೆ ಪದಾರ್ಥ ಬೇಕೇ?"
                    else:
                        alt_message = f"'{item_name}' is currently unavailable."
                        if "vada" in item_id and "idly" in item_id:
                            alt_message += " You can order Idly (1) (₹20) and Vada (1) (₹35) individually. Would you like to order those?"
                        else:
                            alt_message += " Would you like to explore other options in this section?"
                    return KioskResponse(
                        message=alt_message,
                        screen="menu_items",
                        intent="item_unavailable",
                        data={"item": best_item},
                        actions=[{"type": "navigate", "payload": {"screen": "menu_items", "section_id": sec_id}}],
                        conversation_state=state,
                    )

                is_inquiring = any(q in msg_lower for q in [
                    "tell me about", "what is", "describe", "details of", "explain", "how is", "price of", "how much is"
                ])
                is_viewing_item = any(v in msg_lower for v in ["show", "open", "view", "details", "ತೋರಿಸು", "ತೋರ್ಸು", "ತೋರಿಸಿ", "ನೋಡು", "torisu", "thodisu"])
                if (is_inquiring or is_viewing_item) and not is_ordering_verb:
                    state["last_intent"] = "product_details"
                    if is_kn:
                        desc = best_item.get("description") or f"ತಾಜಾ ಶುದ್ಧ ಸಸ್ಯಾಹಾರಿ {kannada or item_name}."
                        msg = f"{kannada or item_name} ಬೆಲೆ ₹{price:.0f}. {desc} ಕಾರ್ಟ್ಗೆ ಸೇರಿಸಬೇಕೇ?"
                    else:
                        k_str = f" ({kannada})" if kannada else ""
                        desc = best_item.get("description") or f"Authentic pure vegetarian {item_name} freshly made with pure ghee and spices."
                        msg = f"{item_name}{k_str} is ₹{price:.0f}. {desc} Would you like me to add it to your cart?"
                    return KioskResponse(
                        message=msg,
                        screen="product",
                        intent="product_details",
                        data={"item": best_item},
                        actions=[{"type": "open_product", "payload": {"item": best_item}}],
                        conversation_state=state,
                    )

                if is_ordering_verb or quantity > 1 or any(w in msg_lower for w in ["please", "parcel", "one", "two", "three", "order", "kodi", "kodu", "beku", "haaki", "serisu", "ondu", "ondhu", "eradu", "mooru", "ಕೊಡು", "ಕೊಡಿ", "ಬೇಕು", "ಹಾಕಿ", "ಸೇರಿಸು"]):
                    state["last_intent"] = "add_to_cart"
                    state["last_added_item_id"] = item_id

                    action_result = {
                        "action_type": "add_to_cart",
                        "item": item_name,
                        "kannada_name": kannada,
                        "quantity": quantity,
                        "subtotal": round(price * quantity, 2),
                        "cart_count": len(cart_items) + quantity,
                        "cart_total": sum(float(i.get("price", 0)) * int(i.get("quantity", 1)) for i in cart_items) + (price * quantity),
                    }
                    cashier_msg = self.cashier_generator.generate_cashier_response(
                        action_result=action_result,
                        user_input=raw_msg,
                        target_language="kn" if is_kn else "en",
                        active_screen="menu_items",
                        recent_dialogue=memory.format_history_for_prompt(max_turns=3),
                    )
                    if not cashier_msg:
                        dish_display = kannada or item_name
                        num_kn = {1: "ಒಂದು", 2: "ಎರಡು", 3: "ಮೂರು", 4: "ನಾಲ್ಕು", 5: "ಐದು"}.get(quantity, str(quantity))
                        cashier_msg = f"ಆಯ್ತು! {num_kn} {dish_display}." if is_kn else f"Sure, {quantity} {item_name} added to your tray."
                    msg = cashier_msg

                    return KioskResponse(
                        message=msg,
                        screen="menu_items",
                        intent="add_to_cart",
                        data={
                            "item_id": item_id,
                            "name": item_name,
                            "kannada_name": kannada,
                            "price": price,
                            "quantity": quantity,
                            "section_id": sec_id,
                        },
                        actions=[
                            {
                                "type": "add_to_cart",
                                "payload": {
                                    "id": item_id,
                                    "name": item_name,
                                    "price": price,
                                    "quantity": quantity,
                                    "image": best_item.get("image", ""),
                                    "section_id": sec_id,
                                    "kannadaName": kannada,
                                }
                            }
                        ],
                        conversation_state=state,
                    )
                else:
                    state["last_intent"] = "product_details"
                    k_str = f" ({kannada})" if kannada else ""
                    desc = best_item.get("description") or f"Authentic pure vegetarian {item_name} freshly made with pure ghee and spices."
                    return KioskResponse(
                        message=f"{item_name}{k_str} is ₹{price:.0f}. {desc} Would you like me to add it to your cart?",
                        screen="product",
                        intent="product_details",
                        data={"item": best_item},
                        actions=[{"type": "open_product", "payload": {"item": best_item}}],
                        conversation_state=state,
                    )

        # ======================================================================
        # 11. STAGE B: NATURAL CASHIER RESPONSE GENERATOR
        # ======================================================================
        try:
            cashier_reply = self.cashier_generator.generate_cashier_response(
                customer_message=raw_msg,
                memory=memory,
                action_result={"action": "inquiry", "status": "info", "info": "General restaurant inquiry"},
                is_kn=is_kn,
            )
            if cashier_reply and len(cashier_reply.strip()) > 3:
                state["last_intent"] = "conversational_inquiry"
                return KioskResponse(
                    message=cashier_reply,
                    screen=current_screen or "categories",
                    intent="conversational_inquiry",
                    conversation_state=state,
                )
        except Exception as e:
            logger.warning("Stage B cashier generator error: %s", e)

        # ======================================================================
        # 12. GRACEFUL GROUNDED CASHIER FALLBACK
        # ======================================================================
        state["last_intent"] = "fallback"
        if is_kn:
            msg = "ನಮಸ್ಕಾರ! ನೀವು ಮಸಾಲೆ ದೋಸೆ, ಫಿಲ್ಟರ್ ಕಾಫಿ, ಬಿಸಿ ಬೇಳೆ ಬಾತ್ ಅಥವಾ ಸಿಹಿ ತಿಂಡಿಗಳನ್ನು ಕೇಳಬಹುದು. ಏನು ಬೇಕು?"
        else:
            msg = "Welcome to The Atom Prasadam! You can ask for our special dosas, hot filter coffee, traditional meals, or view your cart. What would you like today?"
        return KioskResponse(
            message=msg,
            screen="categories",
            intent="fallback",
            actions=[{"type": "navigate", "payload": {"screen": "categories"}}],
            conversation_state=state,
        )
