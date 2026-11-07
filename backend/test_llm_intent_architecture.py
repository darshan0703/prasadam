"""
Comprehensive Test Suite for Rebuilt LLM Intent Classification & Navigation
Tests every top-level category, every subcategory, natural language variations,
parent vs child distinction, and context-aware responses.
"""

import pytest
from fastapi.testclient import TestClient
import uuid

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from api import app, MENU_STRUCTURE, VALID_SECTION_IDS
from intent_classifier import CATEGORY_HIERARCHY, SECTION_HIERARCHY

client = TestClient(app)

# All 6 Top-Level Categories
TOP_LEVEL_CATEGORIES = [
    ("south_indian_favourites", "South Indian Favourites", ["Show South Indian Favourites", "south indian", "ದಕ್ಷಿಣ ಭಾರತೀಯ ವಿಶೇಷಗಳು"]),
    ("meals_and_rice", "Meals & Rice", ["Show Meals & Rice", "meals and rice", "ಊಟ ಮತ್ತು ಅನ್ನದ ವಿಧಗಳು"]),
    ("curries_and_main_course", "Curries & Main Course", ["Show Curries and Main Course", "curries & main course", "ಗ್ರೇವಿ ಮತ್ತು ಮುಖ್ಯ ಆಹಾರ"]),
    ("starters_and_sides", "Starters & Sides", ["Show Starters and Sides", "starters and sides", "ಸ್ಟಾರ್ಟರ್ಸ್ ಮತ್ತು ಸೈಡ್ ಡಿಶ್ಗಳು"]),
    ("indian_breads", "Indian Breads", ["Show Indian Breads", "Indian breads", "ಭಾರತೀಯ ಬ್ರೆಡ್"]),
    ("beverages_and_sweets", "Beverages & Sweets", ["Show Beverages and Sweets", "beverages & sweets", "ಪಾನೀಯಗಳು ಮತ್ತು ಸಿಹಿತಿಂಡಿಗಳು"])
]

# All 19 Subcategories
SUBCATEGORIES = [
    ("south_indian_breakfast", ["South Indian Breakfast", "breakfast options torisu", "ಬೆಳಗಿನ ಉಪಾಹಾರ"]),
    ("dose_special", ["Dose Special", "I feel like eating dosa", "ದೋಸೆ ತೋರಿಸಿ", "dose torisi"]),
    ("bajji_pakoda_snacks", ["Bajji / Pakoda / Snacks", "snacks", "ಬಜ್ಜಿ ಪಕೋಡ"]),
    ("meals", ["Meals", "full meals", "ದಕ್ಷಿಣ ಭಾರತೀಯ ಊಟ"]),
    ("chinese_rice_items", ["Chinese Rice Items", "fried rice", "ಚೈನೀಸ್ ರೈಸ್"]),
    ("north_indian_rice_items", ["North Indian Rice Items", "jeera rice", "ಉತ್ತರ ಭಾರತೀಯ ರೈಸ್"]),
    ("chinese_main_course", ["Chinese Main Course", "manchurian gravy", "ಚೈನೀಸ್ ಮೇನ್ ಕೋರ್ಸ್"]),
    ("dal_items", ["Dal Items", "dal tadka", "ದಾಲ್"]),
    ("kadai", ["Kadai", "kadai gravy", "ಕಡಾಯಿ"]),
    ("kofta", ["Kofta", "malai kofta", "ಕೊಫ್ತಾ"]),
    ("north_indian_jain_items", ["North Indian Jain Items", "show jain section", "ಉತ್ತರ ಭಾರತೀಯ ಜೈನ್ ಐಟಮ್ಸ್"]),
    ("indian_curries", ["Indian Curries", "curry section", "ಭಾರತೀಯ ಕರಿಗಳು"]),
    ("soups", ["Soups", "tomato soup", "ಸೂಪ್"]),
    ("salads_raita_papad", ["Salads / Raita / Papad", "papad", "ಹಪ್ಪಳ"]),
    ("chinese_starters", ["Chinese Starters", "chinese starters torisu", "ಚೈನೀಸ್ ಸ್ಟಾರ್ಟರ್ಸ್"]),
    ("indian_starters", ["Indian Starters", "indian starters torisu", "ಭಾರತೀಯ ಸ್ಟಾರ್ಟರ್ಸ್"]),
    ("indian_breads_roti", ["Indian Breads / Roti", "roti", "ಭಾರತೀಯ ರೊಟ್ಟಿ"]),
    ("hot_beverages", ["Hot Beverages", "Show me beverages", "hot drinks", "ಬಿಸಿ ಪಾನೀಯಗಳು"]),
    ("sweet_items", ["Sweet Items", "Show me sweets", "sweets section", "ಸಿಹಿ ಪದಾರ್ಥಗಳು"])
]


def test_all_6_macro_categories_classification():
    """Verify all 6 macro categories navigate to subcategories screen with canonical category_id."""
    for cat_id, title, utterances in TOP_LEVEL_CATEGORIES:
        for utt in utterances:
            session_id = f"test-macro-{cat_id}-{uuid.uuid4()}"
            res = client.post("/message", json={"message": utt, "session_id": session_id}).json()
            assert res["intent"] == "show_category", f"Failed for '{utt}': expected show_category, got {res['intent']}"
            assert res["screen"] == "subcategories", f"Failed for '{utt}': expected subcategories screen, got {res['screen']}"
            assert res["data"]["category_id"] == cat_id, f"Failed for '{utt}': expected {cat_id}, got {res['data'].get('category_id')}"
            assert any(a["type"] == "navigate" and a["payload"].get("category_id") == cat_id for a in res["actions"])


def test_all_19_subcategories_classification():
    """Verify all 19 subcategories navigate to menu_items screen with canonical section_id."""
    for sec_id, utterances in SUBCATEGORIES:
        for utt in utterances:
            session_id = f"test-sec-{sec_id}-{uuid.uuid4()}"
            res = client.post("/message", json={"message": utt, "session_id": session_id}).json()
            assert res["intent"] in ["show_section", "show_subcategory"], f"Failed for '{utt}': expected show_section, got {res['intent']}"
            assert res["screen"] == "menu_items", f"Failed for '{utt}': expected menu_items screen, got {res['screen']}"
            assert res["data"]["section_id"] == sec_id, f"Failed for '{utt}': expected {sec_id}, got {res['data'].get('section_id')}"
            assert any(a["type"] == "navigate" and a["payload"].get("section_id") == sec_id for a in res["actions"])


def test_parent_vs_child_distinction():
    """Verify clear distinction between parent category and child subcategories."""
    # 1. Indian Breads (Category) vs Roti (Subcategory)
    r_cat = client.post("/message", json={"message": "Show me Indian breads", "session_id": str(uuid.uuid4())}).json()
    assert r_cat["intent"] == "show_category"
    assert r_cat["data"]["category_id"] == "indian_breads"
    assert r_cat["screen"] == "subcategories"

    r_sec = client.post("/message", json={"message": "Show me roti", "session_id": str(uuid.uuid4())}).json()
    assert r_sec["intent"] in ["show_section", "show_subcategory"]
    assert r_sec["data"]["section_id"] == "indian_breads_roti"
    assert r_sec["screen"] == "menu_items"

    # 2. Meals and Rice (Category) vs Chinese Rice Items (Subcategory)
    r_cat2 = client.post("/message", json={"message": "What do you have in Meals and Rice?", "session_id": str(uuid.uuid4())}).json()
    assert r_cat2["intent"] == "show_category"
    assert r_cat2["data"]["category_id"] == "meals_and_rice"

    r_sec2 = client.post("/message", json={"message": "Show me Chinese Rice Items", "session_id": str(uuid.uuid4())}).json()
    assert r_sec2["intent"] in ["show_section", "show_subcategory"]
    assert r_sec2["data"]["section_id"] == "chinese_rice_items"

    # 3. South Indian Favourites (Category) vs South Indian Breakfast (Subcategory)
    r_cat3 = client.post("/message", json={"message": "Show South Indian Favourites", "session_id": str(uuid.uuid4())}).json()
    assert r_cat3["intent"] == "show_category"
    assert r_cat3["data"]["category_id"] == "south_indian_favourites"

    r_sec3 = client.post("/message", json={"message": "What do you have in South Indian breakfast?", "session_id": str(uuid.uuid4())}).json()
    assert r_sec3["intent"] in ["show_section", "show_subcategory"]
    assert r_sec3["data"]["section_id"] == "south_indian_breakfast"


def test_natural_language_variations():
    """Verify assistant understands natural variations of dosa and breakfast requests."""
    variations = [
        ("I feel like eating dosa", "dose_special"),
        ("Do you have dosa?", "dose_special"),
        ("Let's see the breakfast options", "south_indian_breakfast"),
        ("ದೋಸೆ ತೋರಿಸಿ", "dose_special"),
        ("ದೋಸೆ ನೋಡೋಣ", "dose_special"),
        ("ಬೆಳಗಿನ ತಿಂಡಿ ನೋಡೋಣ", "south_indian_breakfast"),
        ("Dose torisi", "dose_special"),
        ("Breakfast options torisu", "south_indian_breakfast"),
    ]
    for phrase, expected_sec in variations:
        res = client.post("/message", json={"message": phrase, "session_id": str(uuid.uuid4())}).json()
        assert res["screen"] == "menu_items"
        assert res["data"]["section_id"] == expected_sec, f"Failed for '{phrase}': expected {expected_sec}, got {res['data'].get('section_id')}"


def test_conversational_navigation_and_back():
    """Verify contextual flow: navigate to category -> subcategory -> back -> home."""
    sid = f"flow-{uuid.uuid4()}"

    # 1. Ask for Indian Breads
    r1 = client.post("/message", json={"message": "Show me Indian breads", "session_id": sid}).json()
    assert r1["screen"] == "subcategories"
    assert r1["data"]["category_id"] == "indian_breads"

    # 2. Ask for Roti
    r2 = client.post("/message", json={"message": "Roti torisi", "session_id": sid}).json()
    assert r2["screen"] == "menu_items"
    assert r2["data"]["section_id"] == "indian_breads_roti"

    # 3. Go back
    r3 = client.post("/message", json={"message": "Go back", "session_id": sid}).json()
    assert r3["intent"] == "go_back"
    assert any(a["type"] == "go_back" for a in r3["actions"])

    # 4. Go home
    r4 = client.post("/message", json={"message": "Go home", "session_id": sid}).json()
    assert r4["screen"] == "home"
    assert r4["intent"] == "navigate_home"


def test_inquiry_vs_ordering_distinction():
    """Verify that asking price or inquiring is not confused with navigation or ordering."""
    # 1. Price inquiry
    r_price = client.post("/message", json={"message": "What is the price of masala dosa?", "session_id": str(uuid.uuid4())}).json()
    assert r_price["intent"] == "product_details"
    assert "95" in r_price["message"]

    # 2. Beverage availability inquiry
    r_bev = client.post("/message", json={"message": "ಕಾಫಿ ಇದೆಯಾ?", "session_id": str(uuid.uuid4())}).json()
    assert r_bev["intent"] == "beverage_inquiry"

    # 3. Direct ordering action
    r_order = client.post("/message", json={"message": "Two masala dosas and one coffee, please", "session_id": str(uuid.uuid4())}).json()
    assert r_order["intent"] == "add_to_cart"
    add_actions = [a for a in r_order["actions"] if a["type"] == "add_to_cart"]
    assert len(add_actions) == 2
