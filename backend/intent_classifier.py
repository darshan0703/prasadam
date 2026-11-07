"""
Prasadam LLM Intent Classifier & Hierarchy Grounding Engine
Recreates Intelligent-agent's intent extraction architecture for TheAtom Prasadam.
Uses LLM-driven understanding with deterministic ontology grounding.
"""

import os
import re
import time
import json
import logging
import urllib.request
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from dotenv import load_dotenv

# Authoritatively load environment variables
load_dotenv(Path(__file__).parent / ".env")

from intent_schema import OrderIntent
from kannada_transliteration import is_kannada_input, normalize_kannada_transliteration

logger = logging.getLogger("prasadam.intent")

# ==============================================================================
# CANONICAL CATEGORY & SUBCATEGORY ONTOLOGY
# ==============================================================================

CATEGORY_HIERARCHY = {
    "south_indian_favourites": {
        "id": "south_indian_favourites",
        "title_english": "South Indian Favourites",
        "title_kannada": "ದಕ್ಷಿಣ ಭಾರತೀಯ ವಿಶೇಷಗಳು",
        "aliases": [
            "south indian favourites", "south indian favorites", "south indian",
            "ದಕ್ಷಿಣ ಭಾರತೀಯ ವಿಶೇಷಗಳು", "ದಕ್ಷಿಣ ಭಾರತೀಯ", "south indian thindi",
        ],
        "sections": ["south_indian_breakfast", "dose_special", "bajji_pakoda_snacks"]
    },
    "meals_and_rice": {
        "id": "meals_and_rice",
        "title_english": "Meals & Rice",
        "title_kannada": "ಊಟ ಮತ್ತು ಅನ್ನದ ವಿಧಗಳು",
        "aliases": [
            "meals and rice", "meals & rice", "rice items",
            "oota and rice", "oota rice", "oota and rice options", "oota and rice menu",
            "ಊಟ ಮತ್ತು ಅನ್ನದ ವಿಧಗಳು", "ಊಟ ಮತ್ತು ಅನ್ನ", "ಅನ್ನದ ವಿಧಗಳು", "meals and rice torisu",
        ],
        "sections": ["meals", "chinese_rice_items", "north_indian_rice_items"]
    },
    "curries_and_main_course": {
        "id": "curries_and_main_course",
        "title_english": "Curries & Main Course",
        "title_kannada": "ಗ್ರೇವಿ ಮತ್ತು ಮುಖ್ಯ ಆಹಾರ",
        "aliases": [
            "curries and main course", "curries & main course", "curries", "main course",
            "curry", "gravy", "ಗ್ರೇವಿ ಮತ್ತು ಮುಖ್ಯ ಆಹಾರ", "ಗ್ರೇವಿ", "ಮುಖ್ಯ ಆಹಾರ",
        ],
        "sections": ["chinese_main_course", "dal_items", "kadai", "kofta", "north_indian_jain_items", "indian_curries"]
    },
    "starters_and_sides": {
        "id": "starters_and_sides",
        "title_english": "Starters & Sides",
        "title_kannada": "ಸ್ಟಾರ್ಟರ್ಸ್ ಮತ್ತು ಸೈಡ್ ಡಿಶ್ಗಳು",
        "aliases": [
            "starters and sides", "starters & sides", "starters", "sides", "side dishes",
            "ಸ್ಟಾರ್ಟರ್ಸ್ ಮತ್ತು ಸೈಡ್ ಡಿಶ್ಗಳು", "ಸ್ಟಾರ್ಟರ್ಸ್", "ಸೈಡ್ ಡಿಶ್",
        ],
        "sections": ["soups", "salads_raita_papad", "chinese_starters", "indian_starters"]
    },
    "indian_breads": {
        "id": "indian_breads",
        "title_english": "Indian Breads",
        "title_kannada": "ಭಾರತೀಯ ರೊಟ್ಟಿ ಮತ್ತು ಬ್ರೆಡ್",
        "aliases": [
            "indian breads", "indian bread", "breads", "bread",
            "ಭಾರತೀಯ ರೊಟ್ಟಿ ಮತ್ತು ಬ್ರೆಡ್", "ಭಾರತೀಯ ಬ್ರೆಡ್", "ಬ್ರೆಡ್",
        ],
        "sections": ["indian_breads_roti"]
    },
    "beverages_and_sweets": {
        "id": "beverages_and_sweets",
        "title_english": "Beverages & Sweets",
        "title_kannada": "ಪಾನೀಯಗಳು ಮತ್ತು ಸಿಹಿತಿಂಡಿಗಳು",
        "aliases": [
            "beverages and sweets", "beverages & sweets", "drinks and sweets",
            "ಪಾನೀಯಗಳು ಮತ್ತು ಸಿಹಿತಿಂಡಿಗಳು", "ಪಾನೀಯ ಮತ್ತು ಸಿಹಿ",
        ],
        "sections": ["hot_beverages", "sweet_items"]
    }
}

SECTION_HIERARCHY = {
    "south_indian_breakfast": {
        "id": "south_indian_breakfast",
        "parent_category": "south_indian_favourites",
        "canonical_name": "South Indian Breakfast",
        "kannada_name": "ದಕ್ಷಿಣ ಭಾರತೀಯ ಉಪಾಹಾರ",
        "aliases": [
            "south indian breakfast", "breakfast", "morning breakfast", "tiffin",
            "ದಕ್ಷಿಣ ಭಾರತೀಯ ಉಪಾಹಾರ", "ಬೆಳಗಿನ ಉಪಾಹಾರ", "breakfast torisi", "breakfast torisu", "show breakfast", "show me breakfast"
        ]
    },
    "dose_special": {
        "id": "dose_special",
        "parent_category": "south_indian_favourites",
        "canonical_name": "Dose Special",
        "kannada_name": "ದೋಸೆ ವಿಶೇಷ",
        "aliases": [
            "dose special", "dosa special", "dosa section", "dosa menu", "show dosa", "show me dosa",
            "ದೋಸೆ ವಿಶೇಷ", "dose torisi", "dosa torisu", "dosa torisi"
        ]
    },
    "bajji_pakoda_snacks": {
        "id": "bajji_pakoda_snacks",
        "parent_category": "south_indian_favourites",
        "canonical_name": "Bajji / Pakoda / Snacks",
        "kannada_name": "ಬಜ್ಜಿ / ಪಕೋಡ / ತಿಂಡಿಗಳು",
        "aliases": [
            "bajji pakoda snacks", "bajji", "pakoda", "snacks", "vada", "buns",
            "ಬಜ್ಜಿ", "ಪಕೋಡ", "ತಿಂಡಿಗಳು", "ಬಜ್ಜಿ ಪಕೋಡ",
        ]
    },
    # Meals & Rice
    "meals": {
        "id": "meals",
        "parent_category": "meals_and_rice",
        "canonical_name": "Meals",
        "kannada_name": "ಊಟ",
        "aliases": [
            "meals", "south indian meals", "full meals", "thali", "lunch", "dinner",
            "ಊಟ", "ದಕ್ಷಿಣ ಭಾರತೀಯ ಊಟ", "ತಟ್ಟೆ ಊಟ",
        ]
    },
    "chinese_rice_items": {
        "id": "chinese_rice_items",
        "parent_category": "meals_and_rice",
        "canonical_name": "Chinese Rice Items",
        "kannada_name": "ಚೈನೀಸ್ ರೈಸ್ ಐಟಮ್ಸ್",
        "aliases": [
            "chinese rice items", "chinese rice", "fried rice", "schezwan rice",
            "ಚೈನೀಸ್ ರೈಸ್", "ಚೈನೀಸ್ ರೈಸ್ ಐಟಮ್ಸ್", "ಫ್ರೈಡ್ ರೈಸ್",
        ]
    },
    "north_indian_rice_items": {
        "id": "north_indian_rice_items",
        "parent_category": "meals_and_rice",
        "canonical_name": "North Indian Rice Items",
        "kannada_name": "ಉತ್ತರ ಭಾರತೀಯ ರೈಸ್ ಐಟಮ್ಸ್",
        "aliases": [
            "north indian rice items", "north indian rice", "jeera rice", "pulao", "biryani", "ghee rice",
            "ಉತ್ತರ ಭಾರತೀಯ ರೈಸ್ ಐಟಮ್ಸ್", "ಜೀರಾ ರೈಸ್", "ಪುಲಾವ್", "ಬಿರಿಯಾನಿ",
        ]
    },
    # Curries & Main Course
    "chinese_main_course": {
        "id": "chinese_main_course",
        "parent_category": "curries_and_main_course",
        "canonical_name": "Chinese Main Course",
        "kannada_name": "ಚೈನೀಸ್ ಮೇನ್ ಕೋರ್ಸ್",
        "aliases": ["chinese main course", "chinese gravy", "manchurian gravy", "ಚೈನೀಸ್ ಮೇನ್ ಕೋರ್ಸ್"]
    },
    "dal_items": {
        "id": "dal_items",
        "parent_category": "curries_and_main_course",
        "canonical_name": "Dal Items",
        "kannada_name": "ದಾಲ್ ಐಟಮ್ಸ್",
        "aliases": ["dal items", "dal", "daal", "dal fry", "dal tadka", "ದಾಲ್", "ದಾಲ್ ಐಟಮ್ಸ್"]
    },
    "kadai": {
        "id": "kadai",
        "parent_category": "curries_and_main_course",
        "canonical_name": "Kadai",
        "kannada_name": "ಕಡಾಯಿ",
        "aliases": ["kadai", "kadai gravy", "kadai paneer", "kadai veg", "ಕಡಾಯಿ"]
    },
    "kofta": {
        "id": "kofta",
        "parent_category": "curries_and_main_course",
        "canonical_name": "Kofta",
        "kannada_name": "ಕೊಫ್ತಾ",
        "aliases": ["kofta", "malai kofta", "veg kofta", "ಕೊಫ್ತಾ"]
    },
    "north_indian_jain_items": {
        "id": "north_indian_jain_items",
        "parent_category": "curries_and_main_course",
        "canonical_name": "North Indian Jain Items",
        "kannada_name": "ಉತ್ತರ ಭಾರತೀಯ ಜೈನ್ ಐಟಮ್ಸ್",
        "aliases": ["north indian jain items", "jain items", "jain food", "jain curry", "jain curries", "jain gravy", "jain", "ಜೈನ್", "ಉತ್ತರ ಭಾರತೀಯ ಜೈನ್ ಐಟಮ್ಸ್"]
    },
    "indian_curries": {
        "id": "indian_curries",
        "parent_category": "curries_and_main_course",
        "canonical_name": "Indian Curries",
        "kannada_name": "ಭಾರತೀಯ ಮೇಲೋಗರಗಳು (ಕರಿಗಳು)",
        "aliases": ["indian curries", "curry section", "curries section", "curries", "mixed veg curry", "paneer curries", "paneer curry", "paneer gravies", "paneer curries torisi", "ಭಾರತೀಯ ಮೇಲೋಗರಗಳು", "ಭಾರತೀಯ ಕರಿಗಳು", "ಕರಿಗಳು"]
    },
    # Starters & Sides
    "soups": {
        "id": "soups",
        "parent_category": "starters_and_sides",
        "canonical_name": "Soups",
        "kannada_name": "ಸೂಪ್ಸ್",
        "aliases": ["soups", "soup", "tomato soup", "hot and sour soup", "ಸೂಪ್ಸ್", "ಸೂಪ್"]
    },
    "salads_raita_papad": {
        "id": "salads_raita_papad",
        "parent_category": "starters_and_sides",
        "canonical_name": "Salads / Raita / Papad",
        "kannada_name": "ಸಲಾಡ್ಸ್ / ರಾಯ್ತ / ಹಪ್ಪಳ",
        "aliases": ["salads raita papad", "salad", "salads", "raita", "papad", "ಸಲಾಡ್ಸ್", "ರಾಯ್ತ", "ಹಪ್ಪಳ"]
    },
    "chinese_starters": {
        "id": "chinese_starters",
        "parent_category": "starters_and_sides",
        "canonical_name": "Chinese Starters",
        "kannada_name": "ಚೈನೀಸ್ ಸ್ಟಾರ್ಟರ್ಸ್",
        "aliases": ["chinese starters", "gobi manchurian", "paneer chilli", "spring roll", "ಚೈನೀಸ್ ಸ್ಟಾರ್ಟರ್ಸ್", "ಮಂಚೂರಿಯನ್"]
    },
    "indian_starters": {
        "id": "indian_starters",
        "parent_category": "starters_and_sides",
        "canonical_name": "Indian Starters",
        "kannada_name": "ಭಾರತೀಯ ಸ್ಟಾರ್ಟರ್ಸ್",
        "aliases": ["indian starters", "paneer tikka", "hara bhara kabab", "ಭಾರತೀಯ ಸ್ಟಾರ್ಟರ್ಸ್"]
    },
    # Indian Breads
    "indian_breads_roti": {
        "id": "indian_breads_roti",
        "parent_category": "indian_breads",
        "canonical_name": "Indian Breads / Roti",
        "kannada_name": "ಭಾರತೀಯ ರೊಟ್ಟಿ ಮತ್ತು ಬ್ರೆಡ್",
        "aliases": [
            "indian breads / roti", "indian breads and roti", "indian breads roti", "roti", "rotis", "naan", "kulcha", "parotta", "chapati", "tandoori roti", "butter naan",
            "ರೊಟ್ಟಿ", "ನಾನ್", "ಕುಲ್ಚಾ", "ಪರೋಟ", "ಚಪಾತಿ", "roti torisi", "naan torisi", "ಭಾರತೀಯ ರೊಟ್ಟಿ",
        ]
    },
    # Beverages & Sweets
    "hot_beverages": {
        "id": "hot_beverages",
        "parent_category": "beverages_and_sweets",
        "canonical_name": "Hot Beverages",
        "kannada_name": "ಬಿಸಿ ಪಾನೀಯಗಳು",
        "aliases": [
            "hot beverages", "hot drinks", "beverages", "coffee", "filter coffee", "tea", "badam milk", "hot milk",
            "ಬಿಸಿ ಪಾನೀಯಗಳು", "ಕಾಫಿ", "ಫಿಲ್ಟರ್ ಕಾಫಿ", "ಟೀ", "ಚಹಾ", "ಬಾದಾಮಿ ಹಾಲು",
        ]
    },
    "sweet_items": {
        "id": "sweet_items",
        "parent_category": "beverages_and_sweets",
        "canonical_name": "Sweet Items",
        "kannada_name": "ಸಿಹಿ ಪದಾರ್ಥಗಳು",
        "aliases": [
            "sweet items", "sweets section", "sweet section", "sweets", "sweet", "desserts", "dessert",
            "sweet dish", "sweet dishes", "something sweet", "after food", "after lunch", "after meals",
            "mysore pak", "holige", "gulab jamun", "jamoon", "carrot halwa", "kashi halwa", "hal bai", "jalebi", "kesari bath",
            "ಸಿಹಿ ಪದಾರ್ಥಗಳು", "ಸಿಹಿ", "ಸಿಹಿತಿಂಡಿ", "ಸಿಹಿತಿಂಡಿಗಳು", "ಮೈಸೂರು ಪಾಕ್", "ಹೋಳಿಗೆ", "ಜಾಮೂನ್", "ಗುಲಾಬ್ ಜಾಮೂನ್", "ಹಲ್ವಾ",
        ]
    }
}

VALID_CATEGORY_IDS = set(CATEGORY_HIERARCHY.keys())
VALID_SECTION_IDS = set(SECTION_HIERARCHY.keys())


# ==============================================================================
# INTENT PROMPT FOR THE LLM
# ==============================================================================

# ==============================================================================
# INTENT PROMPT FOR THE LLM
# ==============================================================================

SYSTEM_INTENT_PROMPT = """
You are the intelligent intent understanding system for TheAtom Prasadam kiosk in Bengaluru.
Your responsibility is to understand what the customer wants from their message, current kiosk screen, and conversation context.

AVAILABLE TOP-LEVEL CATEGORIES:
- south_indian_favourites: South Indian Favourites / ದಕ್ಷಿಣ ಭಾರತೀಯ ವಿಶೇಷಗಳು (contains breakfast, dose, snacks)
- meals_and_rice: Meals & Rice / ಊಟ ಮತ್ತು ಅನ್ನದ ವಿಧಗಳು (contains meals, chinese rice, north indian rice)
- curries_and_main_course: Curries & Main Course / ಗ್ರೇವಿ ಮತ್ತು ಮುಖ್ಯ ಆಹಾರ (contains curries, dal, kadai, kofta, jain, chinese main course)
- starters_and_sides: Starters & Sides / ಸ್ಟಾರ್ಟರ್ಸ್ ಮತ್ತು ಸೈಡ್ ಡಿಶ್ಗಳು (contains soups, salads, chinese starters, indian starters)
- indian_breads: Indian Breads / ಭಾರತೀಯ ರೊಟ್ಟಿ ಮತ್ತು ಬ್ರೆಡ್ (contains roti, naan, kulcha, chapati, parotta)
- beverages_and_sweets: Beverages & Sweets / ಪಾನೀಯಗಳು ಮತ್ತು ಸಿಹಿತಿಂಡಿಗಳು (contains hot beverages, filter coffee, sweets)

AVAILABLE SUBCATEGORIES (MENU SECTIONS):
- south_indian_breakfast: South Indian Breakfast / ದಕ್ಷಿಣ ಭಾರತೀಯ ಉಪಾಹಾರ (idly, vada, khara bath, poori)
- dose_special: Dose Special / ದೋಸೆ ವಿಶೇಷ (masala dosa, plain dosa, set dosa, rava dosa)
- bajji_pakoda_snacks: Bajji / Pakoda / Snacks (mangalore buns, curd vada, maddur vada)
- meals: Meals / ಊಟ (south indian meals, thali)
- chinese_rice_items: Chinese Rice Items (fried rice, schezwan rice)
- north_indian_rice_items: North Indian Rice Items (jeera rice, ghee rice, biryani)
- chinese_main_course: Chinese Main Course (manchurian gravy)
- dal_items: Dal Items (dal fry, dal tadka)
- kadai: Kadai (kadai paneer, kadai veg)
- kofta: Kofta (malai kofta, veg kofta)
- north_indian_jain_items: North Indian Jain Items (jain gravies)
- indian_curries: Indian Curries (paneer butter masala, veg curry)
- soups: Soups (tomato soup, sweet corn soup)
- salads_raita_papad: Salads / Raita / Papad
- chinese_starters: Chinese Starters (gobi manchurian, chilli paneer)
- indian_starters: Indian Starters (paneer tikka, kabab)
- indian_breads_roti: Indian Breads / Roti (roti, naan, kulcha, parotta)
- hot_beverages: Hot Beverages (filter coffee, jaggery coffee, tea, badam milk)
- sweet_items: Sweet Items (mysore pak, holige, gulab jamun, payasa)

INTENT ACTIONS:
- general_food_inquiry: Customer is hungry or asks what food exists ("I'm hungry", "What do you have?", "What is good here?", "Something light").
- show_category: Customer wants to view/browse a top-level category (e.g. "Show me Indian breads", "Meals and rice", "What categories do you have?"). TARGET_TYPE=category, TARGET_ID=<canonical category_id>.
- show_subcategory: Customer wants to view/browse a specific subcategory/section (e.g. "Show me roti", "Dosa menu", "Show breakfast", "Maybe dosa", "ದೋಸೆ ತೋರಿಸಿ", "ಕಾಫಿ ತೋರಿಸಿ"). TARGET_TYPE=subcategory, TARGET_ID=<canonical section_id>.
- dosa_varieties: Customer asks what dosas exist ("What dosa varieties are available?"). TARGET_TYPE=subcategory, TARGET_ID=dose_special.
- ask_about_menu: Customer asks an informational question about food ("What is dosa?", "Which one is spicy?", "Which one is popular?", "Which one is lighter?"). TARGET_TYPE=item or subcategory, TARGET_ID=<target>.
- show_product: Customer asks to view/inspect specific dish details ("Show me masala dosa", "How much is plain dosa?", "Tell me about poori saagu"). TARGET_TYPE=item, TARGET_ID=<item_id or query>.
- add_to_cart: Customer wants to add items to cart ("Add two masala dosas", "Give me 1 coffee", "I'll take two of those", "Add that one").
- set_quantity: Customer modifies quantity of a previously ordered or discussed item ("Actually, make that three", "Make it two", "No, I meant one"). QUANTITY=<integer>.
- remove_from_cart: Customer wants to remove an item ("Remove that", "Take out the last item", "No, not that one").
- replace_item: Customer wants to replace an item ("Remove that and give me plain dosa").
- navigate_back: Customer wants to go back ("Go back", "Previous screen", "ಹಿಂದಕ್ಕೆ ಹೋಗು").
- navigate_home: Customer wants to go home/restart ("Go home", "Main screen", "ಮನೆ ಪುಟ").
- view_cart: Customer wants to check tray/cart ("View cart", "Show me the cart", "What is in my cart?").
- checkout: Customer wants to finish order / pay ("Checkout", "Finish order", "That's enough", "ಸಾಕು ಆರ್ಡರ್ ಮುಗಿಸೋಣ").
- recommend_light: Customer wants something light ("Something light", "Light breakfast").
- pairing_recommendation: Customer asks what drink or sweet pairs with food ("What drink goes well with this?", "What goes well with dosa?").
- beverage_inquiry: Customer asks about coffee/tea availability ("Coffee ideya?", "Do you have filter coffee?").
- unsupported_item: Customer asks for non-menu or non-vegetarian food ("Do you have pizza?", "Burger", "Chicken"). ITEM_NAME=<dish name>.
- clarify: Customer request is ambiguous (e.g. "Add two of those" when multiple items were mentioned without a clear single referent).
- greeting: Customer greets ("Hello", "Namaskara").
- cancel: Customer cancels current operation.
- other: General question or conversation.

CONTEXT & ANAPHORA RULES:
1. Multi-turn reference:
   - If customer says "Add that one", "I'll take two of those", "Add two":
     Check RECENT CONVERSATION HISTORY and RECENTLY DISCUSSED DISHES.
     If a single dish was just discussed (e.g. Masala Dosa), resolve TARGET_ID to that dish (e.g. ghee_roast_masala_dosa), RESOLVED_FROM_CONTEXT=true.
     If MULTIPLE dishes were mentioned (e.g. Dosa AND Idli) and it is ambiguous which "those" refers to:
     ACTION=clarify, CLARIFICATION_REQUIRED=true, CANDIDATES=<cand1,cand2>.
2. Informational questions vs Action:
   - "What is dosa?" or "Which one is spicy?" is ask_about_menu (INTENT_TYPE=inquiry). Do NOT add to cart.
   - "Show me dosa" is show_subcategory (INTENT_TYPE=action).
3. Distinguish Category from Subcategory:
   - "Indian breads" -> show_category (TARGET_ID=indian_breads)
   - "Roti" -> show_subcategory (TARGET_ID=indian_breads_roti)
4. Unsupported items:
   - Items like pizza, burgers, non-vegetarian food are NOT on our pure vegetarian South Indian menu. Return ACTION=unsupported_item.
5. Detect customer language:
   - kn: Kannada script OR Romanized/Latin-script Kannada (e.g. "Ondu masala dosa kodi", "Nanage coffee beku", "Innondu add maadi", "Swalpa spicy kammi iroru beku", "Adanna beda", "Eradu beda ondu saaku", "Bere en ide?").
   - mixed_kn_en: Mixed Kannada-English syntax (e.g. "One coffee kooda kodi", "Dosa options ideya?", "Breakfast items torisi").
   - en: English utterances.

Return EXACTLY in this format:
ACTION=<action>
INTENT_TYPE=<action|inquiry|correction|clarification|chit_chat>
TARGET_TYPE=<category|subcategory|item|none>
TARGET_ID=<canonical ID or None>
ITEM_NAME=<item name or None>
QUANTITY=<integer or 1>
RESOLVED_FROM_CONTEXT=<true|false>
CLARIFICATION_REQUIRED=<true|false>
CANDIDATES=<candidate_id1,candidate_id2 or None>
LANGUAGE=<kn|mixed_kn_en|en>
RESPONSE_KN=<concise natural Kannada spoken response>
RESPONSE_EN=<concise natural English spoken response>
"""


# ==============================================================================
# LLM INTENT CLASSIFIER IMPLEMENTATION
# ==============================================================================

class LLMIntentClassifier:
    """
    LLM Intent Classifier backed by Gemini / Groq with deterministic ontology grounding.
    """

    def __init__(self, model_adapter=None):
        self.gemini_key = (os.getenv("GEMINI_API_KEY") or "").strip()
        self.gemini_model = (os.getenv("GEMINI_MODEL") or "gemini-flash-lite-latest").strip()
        self.groq_key = (os.getenv("GROQ_API_KEY") or "").strip()
        self.groq_model = (os.getenv("GROQ_MODEL") or "llama-3.1-8b-instant").strip()
        self._gemini_rate_limited_until = 0.0
        self._groq_failed_until = 0.0

    def is_kannada_text(self, text: str) -> bool:
        """Detects Kannada script or prominent romanized/Latin Kannada phrasing."""
        return is_kannada_input(text)

    def extract_intent(
        self,
        user_input: str,
        current_screen: str = "home",
        active_category: Optional[str] = None,
        active_section: Optional[str] = None,
        cart_items: Optional[List[Dict[str, Any]]] = None,
        recent_context: Optional[Dict[str, Any]] = None,
        conversation_history: Optional[str] = None,
        recently_discussed_items: Optional[List[str]] = None,
        language_preference: Optional[str] = None,
        **kwargs
    ) -> OrderIntent:
        """
        Classifies intent via LLM with session context, falling back deterministically
        to authoritative ontology rules. Respects explicit language preference override.
        """
        raw_msg = (user_input or "").strip()
        if not raw_msg:
            return OrderIntent(action="unknown", language="en")

        is_kn = self.is_kannada_text(raw_msg)
        # Strict language override takes precedence over auto-detection
        pref = (language_preference or "").strip().lower()
        if pref in ["kn", "kannada"]:
            is_kn = True
        elif pref in ["en", "english"]:
            is_kn = False

        lang = "kn" if is_kn else "en"

        # 1. Try LLM classification if Gemini or Groq is configured
        llm_intent = self._classify_with_llm(
            raw_msg,
            current_screen=current_screen,
            active_category=active_category,
            active_section=active_section,
            cart_items=cart_items or [],
            recent_context=recent_context or {},
            conversation_history=conversation_history,
            is_kn=is_kn
        )

        if llm_intent and llm_intent.action != "unknown":
            # Validate & ground target IDs
            grounded_intent = self._ground_and_validate(llm_intent, raw_msg, is_kn)
            if grounded_intent:
                return grounded_intent

        # 2. Deterministic ontology grounding fallback
        return self._classify_deterministic(raw_msg, current_screen, is_kn)

    def _classify_with_llm(
        self,
        user_input: str,
        current_screen: str,
        active_category: Optional[str],
        active_section: Optional[str],
        cart_items: List[Dict[str, Any]],
        recent_context: Dict[str, Any],
        conversation_history: Optional[str],
        is_kn: bool
    ) -> Optional[OrderIntent]:
        """Invokes LLM API to classify intent into key-value schema."""
        history_text = conversation_history or recent_context.get("formatted_history") or "No previous dialogue in this session."
        recent_dishes = recent_context.get("recently_discussed_items") or []
        last_item = recent_context.get("last_mentioned_item") or recent_context.get("last_added_item_id")

        dishes_line = f"RECENTLY DISCUSSED DISHES: {', '.join(recent_dishes)}" if recent_dishes else f"RECENTLY MENTIONED DISH: {last_item or 'None'}"

        context_block = f"""
RECENT CONVERSATION HISTORY:
{history_text}

CURRENT KIOSK SCREEN: {current_screen}
ACTIVE CATEGORY: {active_category or 'None'}
ACTIVE SECTION: {active_section or 'None'}
CURRENT CART ITEMS COUNT: {len(cart_items)}
{dishes_line}
CUSTOMER LANGUAGE DETECTED: {'kn' if is_kn else 'en'}
"""
        user_prompt = f"{context_block}\nCUSTOMER MESSAGE:\n{user_input}"

        raw_response = None
        now = time.time()
        # Try Gemini API if key is available and not rate limited
        if self.gemini_key and not self.gemini_key.startswith("your_") and now >= self._gemini_rate_limited_until:
            logger.info("Classifying intent with Gemini LLM model=%s for query='%s'", self.gemini_model, user_input)
            raw_response = self._call_gemini_api(user_prompt)

        # Fallback to Groq API if Gemini is not available or failed and Groq not disabled
        if not raw_response and self.groq_key and not self.groq_key.startswith("your_") and now >= self._groq_failed_until:
            logger.info("Falling back to Groq LLM model=%s for query='%s'", self.groq_model, user_input)
            raw_response = self._call_groq_api(user_prompt)

        if not raw_response:
            return None

        return self._parse_llm_response(raw_response, is_kn)

    def _call_gemini_api(self, user_prompt: str, timeout: Optional[float] = None) -> Optional[str]:
        if timeout is None:
            try:
                timeout = float(os.getenv("GEMINI_TIMEOUT", "3.0"))
            except ValueError:
                timeout = 3.0
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:generateContent?key={self.gemini_key}"
            payload = {
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": f"{SYSTEM_INTENT_PROMPT}\n\n{user_prompt}"}]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.0,
                    "maxOutputTokens": 250,
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
            if "429" in str(e):
                self._gemini_rate_limited_until = time.time() + 60.0
                logger.warning("Gemini 429 rate limit encountered. Backing off for 60s.")
            else:
                logger.warning("Gemini LLM Intent Classifier call failed: %s", e)
        return None

    def _call_groq_api(self, user_prompt: str, timeout: float = 3.0) -> Optional[str]:
        try:
            url = "https://api.groq.com/openai/v1/chat/completions"
            payload = {
                "model": self.groq_model,
                "messages": [
                    {"role": "system", "content": SYSTEM_INTENT_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.0,
                "max_tokens": 250
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
            if "403" in str(e) or "401" in str(e):
                self._groq_failed_until = time.time() + 300.0
                logger.warning("Groq authentication failure (401/403). Backing off for 300s.")
            else:
                logger.warning("Groq LLM Intent Classifier call failed: %s", e)
        return None

    def _parse_llm_response(self, raw_text: str, default_is_kn: bool) -> Optional[OrderIntent]:
        if not raw_text:
            return None

        fields = {
            "action": "unknown",
            "intent_type": "inquiry",
            "target_type": None,
            "target_id": None,
            "item_name": None,
            "quantity": 1,
            "resolved_from_context": "false",
            "clarification_required": "false",
            "candidates": None,
            "language": "kn" if default_is_kn else "en",
            "response_kn": None,
            "response_en": None,
        }

        for line in raw_text.splitlines():
            line = line.strip()
            if not line or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip().lower()
            v = v.strip()
            if v.lower() in ["none", "null", ""]:
                v = None
            if k in fields:
                fields[k] = v

        try:
            qty = int(fields.get("quantity") or 1)
        except (ValueError, TypeError):
            qty = 1

        action = (fields.get("action") or "unknown").strip().lower()
        target_id = fields.get("target_id")
        if target_id:
            target_id = target_id.strip().lower()

        raw_lang = (fields.get("language") or ("kn" if default_is_kn else "en")).lower()
        if "mixed" in raw_lang:
            detected_lang = "mixed_kn_en"
            lang = "kn"
        elif "kn" in raw_lang:
            detected_lang = "kn"
            lang = "kn"
        elif "en" in raw_lang:
            detected_lang = "en"
            lang = "en"
        else:
            detected_lang = "unknown"
            lang = "kn" if default_is_kn else "en"

        resp_text = fields.get("response_kn") if lang == "kn" else fields.get("response_en")
        if not resp_text:
            resp_text = fields.get("response_en") or fields.get("response_kn")

        is_clarify = str(fields.get("clarification_required") or "false").lower() in ["true", "1", "yes"]
        is_resolved = str(fields.get("resolved_from_context") or "false").lower() in ["true", "1", "yes"]
        cands_raw = fields.get("candidates") or ""
        cands = [c.strip() for c in cands_raw.split(",") if c.strip()] if cands_raw else []

        return OrderIntent(
            action=action,
            intent_type=fields.get("intent_type") or ("action" if action in ["add_to_cart", "remove_from_cart", "set_quantity", "checkout", "show_category", "show_subcategory"] else "inquiry"),
            target_type=fields.get("target_type"),
            target_id=target_id,
            category=target_id if fields.get("target_type") == "category" else None,
            section_id=target_id if fields.get("target_type") == "subcategory" else None,
            item_name=fields.get("item_name"),
            quantity=qty,
            language=lang,
            detected_language=detected_lang,
            clarification_required=is_clarify,
            candidate_item_ids=cands,
            resolved_from_context=is_resolved,
            response_text=resp_text,
            response_kn=fields.get("response_kn"),
            response_en=fields.get("response_en"),
            raw_response=raw_text
        )

    def _ground_and_validate(self, intent: OrderIntent, raw_msg: str, is_kn: bool) -> Optional[OrderIntent]:
        """
        Validates target IDs against authoritative category & section dictionaries.
        Prevents LLM hallucinations and rectifies category vs. subcategory distinctions.
        """
        target = intent.target_id

        # 1. Category validation
        if intent.action == "show_category":
            if target in VALID_CATEGORY_IDS:
                intent.target_type = "category"
                intent.category = target
                return intent
            # If LLM returned a section ID instead of category, rectify to show_subcategory
            if target in VALID_SECTION_IDS:
                intent.action = "show_subcategory"
                intent.target_type = "subcategory"
                intent.section_id = target
                return intent
            # Fallback category match from raw message
            inferred_cat = self._infer_category_from_text(raw_msg)
            if inferred_cat:
                intent.target_id = inferred_cat
                intent.target_type = "category"
                intent.category = inferred_cat
                return intent

        # 2. Subcategory validation
        if intent.action in ["show_subcategory", "show_section"]:
            if target in VALID_SECTION_IDS:
                intent.target_type = "subcategory"
                intent.section_id = target
                intent.action = "show_subcategory"
                return intent
            # If LLM returned a category ID, rectify to show_category
            if target in VALID_CATEGORY_IDS:
                intent.action = "show_category"
                intent.target_type = "category"
                intent.category = target
                return intent
            # Fallback section match from raw message
            inferred_sec = self._infer_section_from_text(raw_msg)
            if inferred_sec:
                intent.target_id = inferred_sec
                intent.target_type = "subcategory"
                intent.section_id = inferred_sec
                intent.action = "show_subcategory"
                return intent

        # If LLM gave valid action with no target required
        if intent.action in [
            "navigate_back", "go_back", "navigate_home", "view_cart", "checkout",
            "greeting", "cancel", "dosa_varieties", "recommend_light",
            "pairing_recommendation", "beverage_inquiry", "finish_order",
            "general_food_inquiry", "unsupported_item", "set_quantity",
            "ask_about_menu", "clarify", "recommendation"
        ]:
            return intent

        return intent

    def _classify_deterministic(self, raw_msg: str, current_screen: str, is_kn: bool) -> OrderIntent:
        """
        Authoritative ontology-grounded deterministic intent classifier.
        Used as primary offline engine and fallback.
        """
        msg_lower = raw_msg.lower().strip()
        lang = "kn" if is_kn else "en"

        # A. Navigation Home & Back
        if any(msg_lower == b or msg_lower.startswith(b) for b in [
            "go back", "back", "previous screen", "return back", "ಹಿಂದಕ್ಕೆ ಹೋಗು", "ಹಿಂದೆ ಹೋಗು", "ಹಿಂದಕ್ಕೆ", "ಹಿಂದೆ", "hindakke"
        ]):
            return OrderIntent(
                action="navigate_back",
                language=lang,
                response_text="ಹಿಂದಿನ ಪುಟಕ್ಕೆ ಹಿಂತಿರುಗುತ್ತಿದ್ದೇನೆ." if is_kn else "Going back to the previous screen."
            )

        if any(h in msg_lower for h in [
            "go home", "take me home", "welcome screen", "start over", "home page", "home screen",
            "ಮನೆ ಪುಟ", "ಮೊದಲ ಪುಟ", "mane puta"
        ]):
            return OrderIntent(
                action="navigate_home",
                language=lang,
                response_text="ಸ್ವಾಗತ ಪುಟಕ್ಕೆ ಹಿಂತಿರುಗುತ್ತಿದ್ದೇನೆ." if is_kn else "Returning to the welcome screen."
            )

        # B. View Cart & Checkout
        if any(c in msg_lower for c in [
            "what is in my cart", "show cart", "show me the cart", "show me cart", "view cart", "view the cart",
            "check cart", "my tray", "what did i order", "go to cart", "open cart", "ಕಾರ್ಟ್ ತೋರಿಸು", "ನನ್ನ ಕಾರ್ಟ್", "cart torisu",
            "total eshtu", "total yestu", "bill eshtu", "bill yestu", "eshtu aytu", "eshtu aaytu", "yestu aytu", "how much is the bill",
            "order total", "cart total", "what is my bill", "ಒಟ್ಟು ಎಷ್ಟು", "ಬಿಲ್ ಎಷ್ಟು", "ಎಷ್ಟು ಆಯ್ತು", "ಎಷ್ಟು ಆಯಿತು"
        ]):
            return OrderIntent(
                action="view_cart",
                language=lang,
                response_text="ನಿಮ್ಮ ಕಾರ್ಟ್ ವಿವರಗಳು ಇಲ್ಲಿವೆ." if is_kn else "Here is your cart."
            )

        if any(p in msg_lower for p in [
            "that's enough", "thats enough", "i am done", "i'm done", "finish order", "let's finish the order",
            "done ordering", "ಸಾಕು", "ಆರ್ಡರ್ ಮುಗಿಸೋಣ", "saku"
        ]):
            return OrderIntent(
                action="finish_order",
                language=lang,
                response_text="ನಿಮ್ಮ ಆರ್ಡರ್ ಇಲ್ಲಿದೆ. ಖಚಿತಪಡಿಸೋಣವೇ?" if is_kn else "Here is your order summary. Would you like to proceed to payment?"
            )

        # C. Specialized Inquiries
        # 1. Dosa varieties inquiry
        if any(p in msg_lower for p in [
            "dosa varieties", "varieties of dosa", "variety of dosa", "what dosas", "types of dosa",
            "ದೋಸೆ ವಿಧಗಳು", "ದೋಸೆಯ ವಿಧಗಳು", "ದೋಸೆಗಳು ಏನೇನಿದೆ"
        ]):
            return OrderIntent(
                action="dosa_varieties",
                language=lang,
                response_text="ನಮ್ಮಲ್ಲಿ ತುಪ್ಪದ ಮಸಾಲೆ ದೋಸೆ, ಪ್ಲೇನ್ ದೋಸೆ, ಈರುಳ್ಳಿ ದೋಸೆ ಮತ್ತು ರವೆ ದೋಸೆ ಲಭ್ಯವಿದೆ. ನಿಮಗೆ ಯಾವುದು ಬೇಕು?" if is_kn else "We have Ghee Roast Masala Dosa, Plain Dosa, Onion Dosa, and Rava Dosa. Which one would you prefer?"
            )

        # 2. Beverage inquiry
        if any(p in msg_lower for p in [
            "coffee ideya", "kaapi ideya", "filter coffee ideya", "tea ideya", "chai ideya",
            "ಕಾಫಿ ಇದೆಯಾ", "ಫಿಲ್ಟರ್ ಕಾಫಿ ಇದೆಯಾ", "ಟೀ ಇದೆಯಾ", "ಚಹಾ ಇದೆಯಾ",
            "is coffee available", "do you have coffee", "do you have filter coffee",
            "what about coffee", "is tea available", "do you have tea"
        ]):
            return OrderIntent(
                action="beverage_inquiry",
                target_id="jaggery_coffee",
                language=lang,
                response_text="ಹೌದು, ನಮ್ಮಲ್ಲಿ ಬಿಸಿ ಫಿಲ್ಟರ್ ಕಾಫಿ (₹30) ಮತ್ತು ಬೆಲ್ಲದ ಕಾಫಿ (₹35) ಲಭ್ಯವಿದೆ. ಒಂದು ಕಾಫಿ ಸೇರಿಸ್ಲಾ?" if is_kn else "Yes! We have our authentic South Indian Filter Coffee (₹30) and Jaggery Coffee (₹35) piping hot. Would you like me to add one?"
            )

        # 3. General food inquiry & hunger
        if any(p in msg_lower for p in [
            "hungry", "i'm hungry", "im hungry", "something light", "what is good here", "what do you have",
            "ಏನಾದರೂ ತಿಂಡಿ ತೋರಿಸಿ", "ತಿಂಡಿ ತೋರಿಸಿ", "suggest something", "recommend something", "what can i eat",
            "what food do you have", "what to eat", "ಯಾವುದು ಚೆನ್ನಾಗಿದೆ", "ಏನಾದರೂ ಊಟ ತೋರಿಸಿ"
        ]) and not any(w in msg_lower for w in ["breakfast", "dosa", "idli", "coffee", "roti", "meals", "sweet", "beverage", "ತಿಂಡಿ ವಿಭಾಗ"]):
            return OrderIntent(
                action="general_food_inquiry",
                intent_type="inquiry",
                language=lang,
                response_text="ನಮ್ಮ ಸ್ಪೆಷಲ್ ತುಪ್ಪದ ಮಸಾಲೆ ದೋಸೆ ಅಥವಾ ಬೆಳಗಿನ ತಿಂಡಿ ಇಡ್ಲಿ ವಡೆ ಟ್ರೈ ಮಾಡಿ. ಯಾವುದು ತರಲಿ?" if is_kn else "You could try our signature Ghee Roast Masala Dosa, crispy Vada, or hearty South Indian Meals. What are you in the mood for?"
            )

        # 3a. Unsupported cuisine check (pizza, burger, pasta, etc.)
        if any(p in msg_lower for p in ["pizza", "burger", "pasta", "sandwich", "french fries", "chicken", "mutton", "fish", "meat"]):
            item_match = next((p for p in ["pizza", "burger", "pasta", "sandwich", "chicken", "mutton", "fish", "meat"] if p in msg_lower), "that")
            return OrderIntent(
                action="unsupported_item",
                intent_type="inquiry",
                item_name=item_match,
                language=lang,
                response_text=f"We do not serve {item_match} here, but we have authentic South Indian specialties."
            )

        # 3b. Informational menu queries ("What is dosa?", "Which one is spicy?", "Which one is popular?")
        if any(p in msg_lower for p in ["which one is spicy", "which is spicy", "what is spicy", "which dosa is spicy"]):
            return OrderIntent(
                action="ask_about_menu",
                intent_type="inquiry",
                section_id="dose_special",
                target_id="ghee_pudi_masala_dosa",
                language=lang,
                response_text="Our Ghee Pudi Masala Dosa is prepared with flavorful traditional chutney powder."
            )

        if any(p in msg_lower for p in ["which one is popular", "which is popular", "popular dosa", "what do people order", "most popular"]):
            return OrderIntent(
                action="ask_about_menu",
                intent_type="inquiry",
                section_id="dose_special",
                target_id="ghee_roast_masala_dosa",
                language=lang,
                response_text="Our Ghee Roast Masala Dosa is a traditional favorite, roasted golden in pure ghee."
            )

        if any(p in msg_lower for p in ["what goes well with dosa", "pairing with dosa", "what drink goes well"]):
            return OrderIntent(
                action="pairing_recommendation",
                intent_type="inquiry",
                section_id="dose_special",
                target_id="filter_coffee",
                language=lang,
                response_text="Authentic South Indian Filter Coffee pairs wonderfully with any of our dosas."
            )

        # 4. Price & dish inquiry (e.g. "What is the price of masala dosa?")
        is_price_inquiry = any(q in msg_lower for q in [
            "price of", "how much is", "what is the price", "cost of", "rate of", "how much for",
            "ಎಷ್ಟು", "ಬೆಲೆ", "ರೇಟು", "ದರ"
        ])
        if is_price_inquiry:
            return OrderIntent(
                action="product_details",
                language=lang,
                response_text="ವಿವರಗಳು ಇಲ್ಲಿವೆ." if is_kn else "Here are the details."
            )

        # 5. Direct multi-item or quantity ordering
        has_qty = bool(re.search(r"\b(one|two|three|four|five|1|2|3|4|5|ondu|ondhu|eradu|yeradu|mooru|muru|naalku|nalku|aidu|ಒಂದು|ಎರಡು|ಮೂರು|ನಾಲ್ಕು|ಐದು)\b", msg_lower))
        has_order_words = any(w in msg_lower for w in ["give me", "give", "add", "order", "parcel", "kodi", "kodu", "beku", "haaki", "serisu", "want", "like to have", "plate", "cup", "ಕೊಡು", "ಕೊಡಿ", "ಬೇಕು", "ಹಾಕಿ", "ಸೇರಿಸು", "please"])
        has_dish = any(d in msg_lower for d in ["idli", "idly", "vada", "vade", "dosa", "dose", "coffee", "kaapi", "tea", "chai", "roti", "bath", "rice", "curry"])
        has_multiple_items = (" and " in msg_lower or " ಮತ್ತು " in msg_lower or "," in msg_lower) and has_qty

        if has_multiple_items or (has_qty and (has_order_words or has_dish)):
            return OrderIntent(
                action="add_to_cart",
                language=lang,
                response_text="ಆರ್ಡರ್ ಸೇರಿಸುತ್ತಿದ್ದೀನಿ." if is_kn else "Adding to your cart."
            )

        # D. Subcategories / Menu Sections / Categories Check
        norm_msg = normalize_kannada_transliteration(raw_msg)
        inferred_category, cat_alias = self._infer_category_from_text_with_alias(raw_msg)
        inferred_section, sec_alias = self._infer_section_from_text_with_alias(raw_msg)
        if not inferred_section and not inferred_category:
            inferred_category, cat_alias = self._infer_category_from_text_with_alias(norm_msg)
            inferred_section, sec_alias = self._infer_section_from_text_with_alias(norm_msg)

        # Specifically check for explicit top-level category meta queries:
        is_category_query = any(w in msg_lower for w in [
            "category", "categories", "all categories", "ವಿಭಾಗ", "ವಿಭಾಗಗಳು", "ವರ್ಗ"
        ])

        # If a category was matched and either:
        # 1. No section matched, OR
        # 2. An explicit category query keyword was used, OR
        # 3. The matched category alias is longer than or contains the section alias (e.g. "beverages and sweets" > "sweets")
        if inferred_category and (
            not inferred_section
            or is_category_query
            or (cat_alias and sec_alias and (len(cat_alias) > len(sec_alias) or sec_alias in cat_alias))
        ):
            cat_info = CATEGORY_HIERARCHY[inferred_category]
            title = cat_info["title_kannada"] if is_kn else cat_info["title_english"]
            resp = f"ಸರಿ, {title} ವಿಭಾಗವನ್ನು ನೋಡೋಣ." if is_kn else f"Opening {title}."
            return OrderIntent(
                action="show_category",
                target_type="category",
                target_id=inferred_category,
                category=inferred_category,
                language=lang,
                response_text=resp
            )

        if inferred_section:
            sec_info = SECTION_HIERARCHY[inferred_section]
            title = sec_info["kannada_name"] if is_kn else sec_info["canonical_name"]
            resp = f"ಸರಿ, {title} ನೋಡೋಣ." if is_kn else f"Opening {title}."
            return OrderIntent(
                action="show_subcategory",
                target_type="subcategory",
                target_id=inferred_section,
                section_id=inferred_section,
                language=lang,
                response_text=resp
            )

        if any(msg_lower == c or "all categories" in msg_lower or "main menu" in msg_lower for c in ["categories", "menu", "ವಿಭಾಗಗಳು", "ಮೆನು"]):
            return OrderIntent(
                action="show_category",
                target_type="none",
                language=lang,
                response_text="ಎಲ್ಲಾ ಮೆನು ವಿಭಾಗಗಳು ಇಲ್ಲಿವೆ." if is_kn else "Here are all the menu categories."
            )

        # E. Greetings
        if any(msg_lower == g or msg_lower.startswith(f"{g} ") for g in ["hello", "hi", "namaskara", "namaste", "ನಮಸ್ಕಾರ", "ನಮಸ್ತೆ"]):
            return OrderIntent(
                action="greeting",
                language=lang,
                response_text="ನಮಸ್ಕಾರ! ದಿ ಆಟಂ ಪ್ರಸಾದಂಗೆ ಸುಸ್ವಾಗತ. ನಿಮಗೆ ಏನು ಬೇಕು?" if is_kn else "Namaskara! Welcome to The Atom Prasadam. How may I serve you today?"
            )

        return OrderIntent(action="unknown", language=lang)

    def _matches_alias(self, text: str, alias: str) -> bool:
        """Matches alias against text with word boundaries for precision."""
        if not text or not alias:
            return False
        t = text.lower().strip()
        a = alias.lower().strip()
        if " " in a or "-" in a or "/" in a:
            return a in t
        pattern = rf"(?<![\w\u0C80-\u0CFF]){re.escape(a)}(?![\w\u0C80-\u0CFF])"
        return bool(re.search(pattern, t))

    def _infer_category_from_text_with_alias(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        """Matches customer text against canonical top-level category aliases, returning (cat_id, matched_alias)."""
        best_cat = None
        best_alias = ""
        for cat_id, info in CATEGORY_HIERARCHY.items():
            for alias in info["aliases"]:
                if self._matches_alias(text, alias):
                    if len(alias) > len(best_alias):
                        best_cat = cat_id
                        best_alias = alias
        return best_cat, (best_alias if best_cat else None)

    def _infer_section_from_text_with_alias(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        """Matches customer text against canonical subcategory / section aliases, returning (sec_id, matched_alias)."""
        best_sec = None
        best_alias = ""
        for sec_id, info in SECTION_HIERARCHY.items():
            for alias in info["aliases"]:
                if self._matches_alias(text, alias):
                    if len(alias) > len(best_alias):
                        best_sec = sec_id
                        best_alias = alias
        return best_sec, (best_alias if best_sec else None)

    def _infer_category_from_text(self, text: str) -> Optional[str]:
        """Matches customer text against canonical top-level category aliases."""
        cat, _ = self._infer_category_from_text_with_alias(text)
        return cat

    def _infer_section_from_text(self, text: str) -> Optional[str]:
        """Matches customer text against canonical subcategory / section aliases."""
        sec, _ = self._infer_section_from_text_with_alias(text)
        return sec
