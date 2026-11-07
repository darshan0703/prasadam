"""
TheAtom Prasadam — Comprehensive Voice Navigation & Kannada Conversation Test Matrix
Tests:
A. Navigation Coverage: All 6 macro groups & all 19 canonical sections in English and Kannada
B. Cart & Contextual Actions: 1 item, multiple quantities, contextual 1 more, remove, show cart, unavailable item
C. Language & TTS Audio: Kannada Soumya WAV synthesis, English Kokoro synthesis, language normalization
D. Regression & Edge Cases: Ambiguity, back/home navigation
"""

import unittest
import io
import wave
import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from conversation_service import PrasadamConversationEngine
from menu_data import SECTION_ITEMS_DB
from api import MENU_STRUCTURE, ALL_ITEMS_BY_ID
from tts_service import kokoro_tts


class TestPrasadamNavigationAndKannada(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = PrasadamConversationEngine(ALL_ITEMS_BY_ID, MENU_STRUCTURE)

    # =========================================================================
    # Group A: Navigation Coverage - All 6 Categories & All 19 Subcategories
    # =========================================================================

    def test_all_6_macro_categories_english(self):
        categories_english = [
            ("Show South Indian Favourites", "south_indian_favourites"),
            ("Show Meals and Rice", "meals_and_rice"),
            ("Show Curries and Main Course", "curries_and_main_course"),
            ("Show Starters and Sides", "starters_and_sides"),
            ("I want Indian Breads", "indian_breads"),
            ("Show Beverages and Sweets", "beverages_and_sweets"),
        ]
        for query, expected_cat_id in categories_english:
            with self.subTest(query=query, expected=expected_cat_id):
                res = self.engine.process_message(query, "test_cat_en")
                self.assertEqual(res.intent, "show_category")
                self.assertEqual(res.screen, "subcategories")
                self.assertEqual(res.data.get("category_id"), expected_cat_id)
                self.assertTrue(len(res.actions) > 0)
                self.assertEqual(res.actions[0]["type"], "navigate")
                self.assertEqual(res.actions[0]["payload"]["category_id"], expected_cat_id)

    def test_all_6_macro_categories_kannada(self):
        categories_kannada = [
            ("ದಕ್ಷಿಣ ಭಾರತೀಯ ವಿಶೇಷಗಳು ತೋರಿಸು", "south_indian_favourites"),
            ("ಊಟ ಮತ್ತು ಅನ್ನದ ವಿಧಗಳು ತೋರಿಸು", "meals_and_rice"),
            ("ಗ್ರೇವಿ ಮತ್ತು ಮುಖ್ಯ ಆಹಾರ ತೋರಿಸು", "curries_and_main_course"),
            ("ಸ್ಟಾರ್ಟರ್ಸ್ ಮತ್ತು ಸೈಡ್ ಡಿಶ್ಗಳು ತೋರಿಸು", "starters_and_sides"),
            ("ಭಾರತೀಯ ರೊಟ್ಟಿ ಮತ್ತು ಬ್ರೆಡ್ ತೋರಿಸು", "indian_breads"),
            ("ಪಾನೀಯಗಳು ಮತ್ತು ಸಿಹಿತಿಂಡಿಗಳು ತೋರಿಸು", "beverages_and_sweets"),
        ]
        for query, expected_cat_id in categories_kannada:
            with self.subTest(query=query, expected=expected_cat_id):
                res = self.engine.process_message(query, "test_cat_kn")
                self.assertEqual(res.intent, "show_category")
                self.assertEqual(res.screen, "subcategories")
                self.assertEqual(res.data.get("category_id"), expected_cat_id)
                self.assertTrue(self.engine.is_kannada_input(res.message))

    def test_all_19_canonical_sections_english(self):
        sections_english = [
            # Group A
            ("Show me South Indian breakfast", "south_indian_breakfast"),
            ("Open dosa specials", "dose_special"),
            ("Show bajji pakoda snacks", "bajji_pakoda_snacks"),
            # Group B
            ("Show south indian meals", "meals"),
            ("Show Chinese rice items", "chinese_rice_items"),
            ("Show North Indian rice items", "north_indian_rice_items"),
            # Group C
            ("Show Chinese main course", "chinese_main_course"),
            ("Show dal items", "dal_items"),
            ("Show kadai dishes", "kadai"),
            ("Show kofta items", "kofta"),
            ("Show north indian jain items", "north_indian_jain_items"),
            ("Show indian curries", "indian_curries"),
            # Group D
            ("Show soups", "soups"),
            ("Show salads raita papad", "salads_raita_papad"),
            ("Show Chinese starters", "chinese_starters"),
            ("Show Indian starters", "indian_starters"),
            # Group E
            ("Show roti items", "indian_breads_roti"),
            # Group F
            ("Show hot beverages", "hot_beverages"),
            ("Show sweet items", "sweet_items"),
        ]
        for query, expected_sec_id in sections_english:
            with self.subTest(query=query, expected=expected_sec_id):
                res = self.engine.process_message(query, "test_sec_en")
                self.assertEqual(res.intent, "show_section")
                self.assertEqual(res.screen, "menu_items")
                self.assertEqual(res.data.get("section_id"), expected_sec_id)
                self.assertTrue(len(res.actions) > 0)
                self.assertEqual(res.actions[0]["type"], "navigate")
                self.assertEqual(res.actions[0]["payload"]["section_id"], expected_sec_id)

    def test_all_19_canonical_sections_kannada(self):
        sections_kannada = [
            # Group A
            ("ದಕ್ಷಿಣ ಭಾರತೀಯ ಉಪಾಹಾರ ತೋರಿಸು", "south_indian_breakfast"),
            ("ದೋಸೆ ವಿಶೇಷ ತೋರಿಸು", "dose_special"),
            ("ಬಜ್ಜಿ ಪಕೋಡ ತಿಂಡಿಗಳು ತೋರಿಸು", "bajji_pakoda_snacks"),
            # Group B
            ("ಊಟದ ಮೆನು ತೋರಿಸು", "meals"),
            ("ಚೈನೀಸ್ ರೈಸ್ ಐಟಮ್ಸ್ ತೋರಿಸು", "chinese_rice_items"),
            ("ಉತ್ತರ ಭಾರತೀಯ ರೈಸ್ ಐಟಮ್ಸ್ ತೋರಿಸು", "north_indian_rice_items"),
            # Group C
            ("ಚೈನೀಸ್ ಮೇನ್ ಕೋರ್ಸ್ ತೋರಿಸು", "chinese_main_course"),
            ("ದಾಲ್ ಐಟಮ್ಸ್ ತೋರಿಸು", "dal_items"),
            ("ಕಡಾಯಿ ಐಟಮ್ಸ್ ತೋರಿಸು", "kadai"),
            ("ಕೊಫ್ತಾ ಐಟಮ್ಸ್ ತೋರಿಸು", "kofta"),
            ("ಉತ್ತರ ಭಾರತೀಯ ಜೈನ್ ಐಟಮ್ಸ್ ತೋರಿಸು", "north_indian_jain_items"),
            ("ಭಾರತೀಯ ಮೇಲೋಗರಗಳು ತೋರಿಸು", "indian_curries"),
            # Group D
            ("ಸೂಪ್ಸ್ ತೋರಿಸು", "soups"),
            ("ಸಲಾಡ್ಸ್ ರಾಯ್ತ ಹಪ್ಪಳ ತೋರಿಸು", "salads_raita_papad"),
            ("ಚೈನೀಸ್ ಸ್ಟಾರ್ಟರ್ಸ್ ತೋರಿಸು", "chinese_starters"),
            ("ಭಾರತೀಯ ಸ್ಟಾರ್ಟರ್ಸ್ ತೋರಿಸು", "indian_starters"),
            # Group E
            ("ಭಾರತೀಯ ರೊಟ್ಟಿ ತೋರಿಸು", "indian_breads_roti"),
            # Group F
            ("ಬಿಸಿ ಪಾನೀಯಗಳು ತೋರಿಸು", "hot_beverages"),
            ("ಸಿಹಿ ಪದಾರ್ಥಗಳು ತೋರಿಸು", "sweet_items"),
        ]
        for query, expected_sec_id in sections_kannada:
            with self.subTest(query=query, expected=expected_sec_id):
                res = self.engine.process_message(query, "test_sec_kn")
                self.assertEqual(res.intent, "show_section")
                self.assertEqual(res.screen, "menu_items")
                self.assertEqual(res.data.get("section_id"), expected_sec_id)
                self.assertTrue(self.engine.is_kannada_input(res.message))

    def test_navigation_back_and_home(self):
        # Back
        for b_cmd in ["Go back", "Back", "ಹಿಂದಕ್ಕೆ ಹೋಗು", "Hindakke hogu"]:
            res = self.engine.process_message(b_cmd, "test_nav")
            self.assertEqual(res.intent, "go_back")
            self.assertEqual(res.screen, "previous")
            self.assertTrue(any(a["type"] == "go_back" for a in res.actions))

        # Home
        for h_cmd in ["Go to the home page", "Home", "ಮನೆ ಪುಟಕ್ಕೆ ಹೋಗು", "Mane putakke hogu"]:
            res = self.engine.process_message(h_cmd, "test_nav")
            self.assertEqual(res.intent, "navigate_home")
            self.assertEqual(res.screen, "home")

    # =========================================================================
    # Group B: Cart and Contextual Actions
    # =========================================================================

    def test_cart_single_item_and_quantity_kannada(self):
        # 1 item: ಮಸಾಲೆ ದೋಸೆ ಕೊಡು
        r1 = self.engine.process_message("ಮಸಾಲೆ ದೋಸೆ ಕೊಡು", "session_cart_test_1")
        self.assertEqual(r1.intent, "add_to_cart")
        self.assertEqual(r1.data.get("item_id"), "ghee_roast_masala_dosa")
        self.assertEqual(r1.data.get("quantity"), 1)
        self.assertIn("ಮಸಾಲೆ ದೋಸೆ", r1.message)

        # 2 items: ಎರಡು ಮಸಾಲೆ ದೋಸೆ ಕೊಡು
        r2 = self.engine.process_message("ಎರಡು ಮಸಾಲೆ ದೋಸೆ ಕೊಡು", "session_cart_test_2")
        self.assertEqual(r2.intent, "add_to_cart")
        self.assertEqual(r2.data.get("item_id"), "ghee_roast_masala_dosa")
        self.assertEqual(r2.data.get("quantity"), 2)
        self.assertIn("ಎರಡು ಮಸಾಲೆ ದೋಸೆಗಳನ್ನು", r2.message)

    def test_cart_contextual_add_one_more(self):
        session = "session_contextual_test"
        # Initial dish
        r1 = self.engine.process_message("ಎರಡು ಮಸಾಲೆ ದೋಸೆ ಕೊಡು", session)
        self.assertEqual(r1.intent, "add_to_cart")

        # Contextual add one more in Kannada
        r2 = self.engine.process_message("ಇನ್ನೊಂದು ಸೇರಿಸು", session)
        self.assertEqual(r2.intent, "add_to_cart")
        self.assertEqual(r2.data.get("item_id"), "ghee_roast_masala_dosa")
        self.assertEqual(r2.data.get("quantity"), 1)
        self.assertIn("ಇನ್ನೊಂದು ಮಸಾಲೆ ದೋಸೆ", r2.message)

        # Romanized contextual
        r3 = self.engine.process_message("Innu ondu serisu", session)
        self.assertEqual(r3.intent, "add_to_cart")
        self.assertEqual(r3.data.get("item_id"), "ghee_roast_masala_dosa")

    def test_cart_contextual_no_referent(self):
        # Empty fresh session with no prior dishes
        res = self.engine.process_message("ಇನ್ನೊಂದು ಸೇರಿಸು", "empty_session_test")
        self.assertIn("ಯಾವ ಪದಾರ್ಥವನ್ನು ಸೇರಿಸಬೇಕು", res.message)

    def test_view_cart_and_summary_kannada(self):
        cart_items = [
            {"id": "ghee_roast_masala_dosa", "name": "Ghee Roast Masala Dosa", "price": 95.0, "quantity": 2, "kannadaName": "ಮಸಾಲೆ ದೋಸೆ"},
            {"id": "filter_coffee", "name": "Filter Coffee", "price": 30.0, "quantity": 1, "kannadaName": "ಫಿಲ್ಟರ್ ಕಾಫಿ"}
        ]
        res = self.engine.process_message("ಕಾರ್ಟ್ ತೋರಿಸು", "view_cart_session", cart_items=cart_items)
        self.assertEqual(res.intent, "view_cart")
        self.assertEqual(res.screen, "cart")
        self.assertIn("220 ರೂಪಾಯಿ", res.message)
        self.assertIn("ನಿಮ್ಮ ಕಾರ್ಟ್ ಇಲ್ಲಿದೆ", res.message)

    def test_unavailable_item_rejection(self):
        # Mark an item unavailable temporarily
        orig_state = ALL_ITEMS_BY_ID["ghee_roast_masala_dosa"].get("available", True)
        ALL_ITEMS_BY_ID["ghee_roast_masala_dosa"]["available"] = False
        try:
            res = self.engine.process_message("ಮಸಾಲೆ ದೋಸೆ ಕೊಡು", "unavail_test")
            self.assertEqual(res.intent, "item_unavailable")
            self.assertIn("ಲಭ್ಯವಿಲ್ಲ", res.message)
        finally:
            ALL_ITEMS_BY_ID["ghee_roast_masala_dosa"]["available"] = orig_state

    # =========================================================================
    # Group C: Language Understanding & Dual-Language Audio (TTS)
    # =========================================================================

    def test_language_detection(self):
        self.assertTrue(self.engine.is_kannada_input("ದೋಸೆ ತೋರಿಸು"))
        self.assertTrue(self.engine.is_kannada_input("ಎರಡು ಮಸಾಲೆ ದೋಸೆ ಕೊಡು"))
        self.assertTrue(self.engine.is_kannada_input("Dose torisu"))
        self.assertTrue(self.engine.is_kannada_input("Eradu masala dose kodi"))
        self.assertTrue(self.engine.is_kannada_input("Hindakke hogu"))
        self.assertFalse(self.engine.is_kannada_input("Show me South Indian breakfast"))
        self.assertFalse(self.engine.is_kannada_input("Add two masala dosas to cart"))

    def test_real_kannada_tts_synthesis(self):
        kannada_text = "ಎರಡು ಮಸಾಲೆ ದೋಸೆಗಳನ್ನು ಕಾರ್ಟ್ಗೆ ಸೇರಿಸಿದ್ದೇನೆ."
        meta = kokoro_tts.synthesize_with_metadata(kannada_text)
        self.assertEqual(meta["engine"], "kannada-soumya")
        self.assertEqual(meta["lang"], "kn")
        self.assertEqual(meta["sample_rate"], 24000)

        audio_bytes = meta["audio_bytes"]
        self.assertGreater(len(audio_bytes), 10000, "Kannada audio must be non-empty valid WAV")

        with wave.open(io.BytesIO(audio_bytes), "rb") as wf:
            self.assertEqual(wf.getnchannels(), 1, "Must be mono audio")
            self.assertEqual(wf.getsampwidth(), 2, "Must be 16-bit PCM")
            self.assertEqual(wf.getframerate(), 24000, "Must be 24000 Hz")
            self.assertGreater(wf.getnframes(), 0)

    def test_real_english_tts_synthesis(self):
        english_text = "Opening South Indian Breakfast. You can tap any item to add to your tray."
        meta = kokoro_tts.synthesize_with_metadata(english_text)
        self.assertEqual(meta["engine"], "kokoro")
        self.assertEqual(meta["lang"], "en")
        self.assertEqual(meta["sample_rate"], 24000)

        audio_bytes = meta["audio_bytes"]
        self.assertGreater(len(audio_bytes), 10000, "English audio must be non-empty valid WAV")

        with wave.open(io.BytesIO(audio_bytes), "rb") as wf:
            self.assertEqual(wf.getnchannels(), 1)
            self.assertEqual(wf.getsampwidth(), 2)
            self.assertEqual(wf.getframerate(), 24000)


if __name__ == "__main__":
    unittest.main()
