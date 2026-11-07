"""
TheAtom Prasadam — Comprehensive Category & Section Semantic Understanding Test Matrix
--------------------------------------------------------------------------------------
Covers:
1. All 6 macro categories in 4 modalities:
   - Canonical English
   - Colloquial Latin-script Kannada (Bengaluru style)
   - Native Kannada script
   - Mixed Kannada-English code-switching
2. All 19 canonical menu sections in all modalities:
   - Canonical inquiries ("Show me breakfast", "Open sweet items")
   - Transliterated Kannada inquiries ("Breakfast alli en ide?", "Dosa yen yen ide?", "Sweet yen idhe?")
   - Native Kannada inquiries ("ದೋಸೆ ವಿಶೇಷ ತೋರಿಸು", "ಸಿಹಿ ತಿಂಡಿ ಏನೇನಿದೆ?")
   - Indirect semantic references ("dessert en ide?", "something sweet ideya?", "tea jothe en ide?")
3. Hard Negative Examples:
   - Specific item inquiry vs category inquiry ("Masala dosa ideya?" -> product_details)
   - Specific item order vs category inquiry ("Ondu gulab jamun kodi" -> add_to_cart)
   - Price inquiry ("Gulab jamun yestu?" -> product_details)
4. Response Naturalness & Contract Verification:
   - Verified that display action is 'navigate'
   - Verified that language is accurately set ('kn' or 'en')
   - Verified that cashier response is natural spoken conversational language, not robotic screen announcements.
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from conversation_service import PrasadamConversationEngine
from api import MENU_STRUCTURE, ALL_ITEMS_BY_ID
from intent_classifier import CATEGORY_HIERARCHY, SECTION_HIERARCHY


class TestCategoryUnderstanding(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = PrasadamConversationEngine(ALL_ITEMS_BY_ID, MENU_STRUCTURE)

    # =========================================================================
    # 1. Macro Category Navigation Across 4 Modalities
    # =========================================================================

    def test_all_6_macro_categories_multilingual(self):
        matrix = [
            # 1. South Indian Favourites
            ("Show South Indian Favourites", "south_indian_favourites", "en"),
            ("South Indian specials torisi", "south_indian_favourites", "kn"),
            ("ದಕ್ಷಿಣ ಭಾರತೀಯ ವಿಶೇಷಗಳು ತೋರಿಸು", "south_indian_favourites", "kn"),
            ("South Indian menu options heli", "south_indian_favourites", "kn"),

            # 2. Meals and Rice
            ("Show Meals and Rice", "meals_and_rice", "en"),
            ("Meals and rice menu torisi", "meals_and_rice", "kn"),
            ("ಊಟ ಮತ್ತು ಅನ್ನದ ವಿಧಗಳು ತೋರಿಸು", "meals_and_rice", "kn"),
            ("Oota and rice options en ide?", "meals_and_rice", "kn"),

            # 3. Curries and Main Course
            ("Show Curries and Main Course", "curries_and_main_course", "en"),
            ("Curries menu open maadi", "curries_and_main_course", "kn"),
            ("ಗ್ರೇವಿ ಮತ್ತು ಮುಖ್ಯ ಆಹಾರ ತೋರಿಸು", "curries_and_main_course", "kn"),
            ("Main course curries torisi", "curries_and_main_course", "kn"),

            # 4. Starters and Sides
            ("Show Starters and Sides", "starters_and_sides", "en"),
            ("Starters menu torisi", "starters_and_sides", "kn"),
            ("ಸ್ಟಾರ್ಟರ್ಸ್ ಮತ್ತು ಸೈಡ್ ಡಿಶ್ಗಳು ತೋರಿಸು", "starters_and_sides", "kn"),
            ("Starters en ide?", "starters_and_sides", "kn"),

            # 5. Indian Breads
            ("Show Indian Breads", "indian_breads", "en"),
            ("I want Indian Breads", "indian_breads", "en"),
            ("Indian breads torisi", "indian_breads", "kn"),
            ("ಭಾರತೀಯ ರೊಟ್ಟಿ ಮತ್ತು ಬ್ರೆಡ್ ತೋರಿಸು", "indian_breads", "kn"),

            # 6. Beverages and Sweets
            ("Show Beverages and Sweets", "beverages_and_sweets", "en"),
            ("Beverages and sweets torisi", "beverages_and_sweets", "kn"),
            ("ಪಾನೀಯಗಳು ಮತ್ತು ಸಿಹಿತಿಂಡಿಗಳು ತೋರಿಸು", "beverages_and_sweets", "kn"),
            ("Drinks and sweets torisi", "beverages_and_sweets", "kn"),
        ]

        for query, expected_cat_id, expected_lang in matrix:
            with self.subTest(query=query, cat=expected_cat_id, lang=expected_lang):
                res = self.engine.process_message(query, f"test_macro_{expected_cat_id}")
                self.assertEqual(res.intent, "show_category")
                self.assertEqual(res.screen, "subcategories")
                self.assertEqual(res.data.get("category_id"), expected_cat_id)
                self.assertEqual(res.language, expected_lang)
                self.assertTrue(len(res.actions) > 0)
                self.assertEqual(res.actions[0]["type"], "navigate")
                self.assertEqual(res.actions[0]["payload"].get("category_id"), expected_cat_id)
                # Verify no robotic announcements
                self.assertNotIn("Opening category", res.message)
                self.assertNotIn("Look at the screen", res.message)

    # =========================================================================
    # 2. Section Navigation Across All 19 Canonical Sections
    # =========================================================================

    def test_canonical_sections_multilingual(self):
        section_matrix = [
            # Group A: South Indian Favourites
            ("Breakfast alli en ide?", "south_indian_breakfast", "kn"),
            ("Morning tiffin torisi", "south_indian_breakfast", "kn"),
            ("Show me South Indian breakfast", "south_indian_breakfast", "en"),
            ("ದಕ್ಷಿಣ ಭಾರತೀಯ ಉಪಾಹಾರ ತೋರಿಸು", "south_indian_breakfast", "kn"),

            ("Dosa yen yen ide?", "dose_special", "kn"),
            ("Dosa section torisi", "dose_special", "kn"),
            ("Show me dosa specials", "dose_special", "en"),
            ("ದೋಸೆ ವಿಶೇಷ ತೋರಿಸು", "dose_special", "kn"),

            ("Bajji pakoda snacks torisi", "bajji_pakoda_snacks", "kn"),
            ("Show snacks menu", "bajji_pakoda_snacks", "en"),
            ("ಬಜ್ಜಿ ಪಕೋಡ ತಿಂಡಿಗಳು ತೋರಿಸು", "bajji_pakoda_snacks", "kn"),

            # Group B: Meals & Rice
            ("Oota en ide?", "meals", "kn"),
            ("South Indian meals torisi", "meals", "kn"),
            ("Show south indian meals", "meals", "en"),
            ("ಊಟದ ಮೆನು ತೋರಿಸು", "meals", "kn"),

            ("Chinese rice items torisi", "chinese_rice_items", "kn"),
            ("Fried rice en ide?", "chinese_rice_items", "kn"),
            ("Show Chinese rice items", "chinese_rice_items", "en"),
            ("ಚೈನೀಸ್ ರೈಸ್ ಐಟಮ್ಸ್ ತೋರಿಸು", "chinese_rice_items", "kn"),

            ("North Indian rice torisi", "north_indian_rice_items", "kn"),
            ("Jeera rice pulao en ide?", "north_indian_rice_items", "kn"),
            ("Show North Indian rice items", "north_indian_rice_items", "en"),
            ("ಉತ್ತರ ಭಾರತೀಯ ರೈಸ್ ಐಟಮ್ಸ್ ತೋರಿಸು", "north_indian_rice_items", "kn"),

            # Group C: Curries & Main Course
            ("Chinese main course torisi", "chinese_main_course", "kn"),
            ("Show Chinese main course", "chinese_main_course", "en"),
            ("ಚೈನೀಸ್ ಮೇನ್ ಕೋರ್ಸ್ ತೋರಿಸು", "chinese_main_course", "kn"),

            ("Dal items en ide?", "dal_items", "kn"),
            ("Show dal items", "dal_items", "en"),
            ("ದಾಲ್ ಐಟಮ್ಸ್ ತೋರಿಸು", "dal_items", "kn"),

            ("Kadai items torisi", "kadai", "kn"),
            ("Show kadai dishes", "kadai", "en"),
            ("ಕಡಾಯಿ ಐಟಮ್ಸ್ ತೋರಿಸು", "kadai", "kn"),

            ("Kofta menu torisi", "kofta", "kn"),
            ("Show kofta items", "kofta", "en"),
            ("ಕೊಫ್ತಾ ಐಟಮ್ಸ್ ತೋರಿಸು", "kofta", "kn"),

            ("North Indian jain items torisi", "north_indian_jain_items", "kn"),
            ("Show north indian jain items", "north_indian_jain_items", "en"),
            ("ಉತ್ತರ ಭಾರತೀಯ ಜೈನ್ ಐಟಮ್ಸ್ ತೋರಿಸು", "north_indian_jain_items", "kn"),

            ("Indian curries en ide?", "indian_curries", "kn"),
            ("Paneer curries torisi", "indian_curries", "kn"),
            ("Show indian curries", "indian_curries", "en"),
            ("ಭಾರತೀಯ ಮೇಲೋಗರಗಳು ತೋರಿಸು", "indian_curries", "kn"),

            # Group D: Starters & Sides
            ("Soups torisi", "soups", "kn"),
            ("Show soups menu", "soups", "en"),
            ("ಸೂಪ್ಸ್ ತೋರಿಸು", "soups", "kn"),

            ("Salads raita papad torisi", "salads_raita_papad", "kn"),
            ("Show salads raita papad", "salads_raita_papad", "en"),
            ("ಸಲಾಡ್ಸ್ ರಾಯ್ತ ಹಪ್ಪಳ ತೋರಿಸು", "salads_raita_papad", "kn"),

            ("Chinese starters en ide?", "chinese_starters", "kn"),
            ("Show Chinese starters", "chinese_starters", "en"),
            ("ಚೈನೀಸ್ ಸ್ಟಾರ್ಟರ್ಸ್ ತೋರಿಸು", "chinese_starters", "kn"),

            ("Indian starters torisi", "indian_starters", "kn"),
            ("Show Indian starters", "indian_starters", "en"),
            ("ಭಾರತೀಯ ಸ್ಟಾರ್ಟರ್ಸ್ ತೋರಿಸು", "indian_starters", "kn"),

            # Group E: Indian Breads
            ("Roti items en ide?", "indian_breads_roti", "kn"),
            ("Show roti items", "indian_breads_roti", "en"),
            ("ಭಾರತೀಯ ರೊಟ್ಟಿ ತೋರಿಸು", "indian_breads_roti", "kn"),

            # Group F: Beverages & Sweets
            ("Coffee tea en ide?", "hot_beverages", "kn"),
            ("Show hot beverages", "hot_beverages", "en"),
            ("ಬಿಸಿ ಪಾನೀಯಗಳು ತೋರಿಸು", "hot_beverages", "kn"),

            # Canonical sweet queries including "Sweet yen idhe?"
            ("Sweet yen idhe?", "sweet_items", "kn"),
            ("Sweet alli en ide?", "sweet_items", "kn"),
            ("Dessert en ide?", "sweet_items", "kn"),
            ("Something sweet ideya?", "sweet_items", "kn"),
            ("Show sweet items", "sweet_items", "en"),
            ("What sweets do you have?", "sweet_items", "en"),
            ("ಸಿಹಿ ಪದಾರ್ಥಗಳು ತೋರಿಸು", "sweet_items", "kn"),
            ("ಸಿಹಿ ತಿಂಡಿ ಏನೇನಿದೆ?", "sweet_items", "kn"),
        ]

        for query, expected_sec_id, expected_lang in section_matrix:
            with self.subTest(query=query, sec=expected_sec_id, lang=expected_lang):
                res = self.engine.process_message(query, f"test_sec_{expected_sec_id}")
                self.assertEqual(res.intent, "show_section")
                self.assertEqual(res.screen, "menu_items")
                self.assertEqual(res.data.get("section_id"), expected_sec_id)
                self.assertEqual(res.language, expected_lang)
                self.assertTrue(len(res.actions) > 0)
                self.assertEqual(res.actions[0]["type"], "navigate")
                self.assertEqual(res.actions[0]["payload"].get("section_id"), expected_sec_id)
                # Verify no robotic announcements
                self.assertNotIn("Opening section", res.message)
                self.assertNotIn("Look at the screen", res.message)

    # =========================================================================
    # 3. Hard Negatives: Disambiguating Category from Item Inquiries & Orders
    # =========================================================================

    def test_item_inquiry_not_category_navigation(self):
        """'Masala dosa ideya?' asks about a specific item, not the whole category."""
        res = self.engine.process_message("Masala dosa ideya?", "test_neg_item_inq")
        self.assertIn(res.intent, ["product_details", "item_availability"])
        self.assertIn(res.screen, ["menu_items", "product"])
        self.assertIn("95", res.message)

    def test_item_ordering_not_category_navigation(self):
        """'Ondu masala dosa kodi' expresses order intent, must add to cart."""
        res = self.engine.process_message("Ondu masala dosa kodi", "test_neg_order")
        self.assertEqual(res.intent, "add_to_cart")
        self.assertEqual(res.data.get("item_id"), "ghee_roast_masala_dosa")
        self.assertEqual(res.data.get("quantity"), 1)
        self.assertEqual(res.language, "kn")

    def test_sweet_item_ordering_not_category_navigation(self):
        """'Ondu gulab jamun kodi' orders a sweet, does not just open sweets section."""
        res = self.engine.process_message("Ondu gulab jamun kodi", "test_neg_sweet_order")
        self.assertEqual(res.intent, "add_to_cart")
        self.assertEqual(res.data.get("item_id"), "jamoon_1")
        self.assertEqual(res.data.get("quantity"), 1)
        self.assertEqual(res.language, "kn")

    def test_price_inquiry_not_category_navigation(self):
        """'Gulab jamun yestu?' asks for price, not category browsing."""
        res = self.engine.process_message("Gulab jamun yestu?", "test_neg_price")
        self.assertEqual(res.intent, "product_details")
        self.assertIn("20", res.message)
        self.assertEqual(res.language, "kn")


if __name__ == "__main__":
    unittest.main()
