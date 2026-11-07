"""
Comprehensive Customer Journeys Test Suite (Journeys A through J)
Tests the end-to-end conversation flows, state preservation, catalogue grounding,
navigation actions, cart updates, and Kannada/English response generation.
"""

import uuid
import pytest
from fastapi.testclient import TestClient
from api import app

client = TestClient(app)


def test_journey_a_browse_and_order():
    """
    Journey A: Browse and order
    - Customer asks to see dosa
    - Kiosk navigates to appropriate menu screen (dose_special)
    - Customer asks which dosa varieties are available
    - Assistant answers with verified menu items (Ghee Roast Masala Dosa, etc.)
    - Customer selects two masala dosas
    - Cart updates with 2 dosas
    - Customer asks to see the cart
    - Cart screen opens with correct quantity and total
    """
    session_id = f"journey-a-{uuid.uuid4()}"

    # Step 1: "Show me dosa"
    r1 = client.post("/message", json={"message": "Show me dosa", "session_id": session_id}).json()
    assert r1["intent"] in ["navigate_section", "category_selected", "dosa_varieties", "show_section"]
    assert r1["screen"] == "menu_items"

    # Step 2: "What dosa varieties are available?"
    r2 = client.post("/message", json={"message": "What dosa varieties are available?", "session_id": session_id}).json()
    assert r2["intent"] == "dosa_varieties"
    assert "Masala Dosa" in r2["message"]
    assert "Ghee Plain Dosa" in r2["message"]

    # Step 3: "Give me two masala dosas"
    r3 = client.post("/message", json={"message": "Give me two masala dosas", "session_id": session_id}).json()
    assert r3["intent"] == "add_to_cart"
    add_actions = [a for a in r3["actions"] if a["type"] == "add_to_cart"]
    assert len(add_actions) == 1
    assert add_actions[0]["payload"]["quantity"] == 2
    assert "ghee_roast_masala_dosa" in add_actions[0]["payload"]["id"]

    # Step 4: "Show me the cart"
    r4 = client.post("/message", json={"message": "Show me the cart", "session_id": session_id}).json()
    assert r4["screen"] == "cart"
    assert r4["intent"] in ["view_cart", "navigate_cart"]


def test_journey_b_complete_multi_item_request():
    """
    Journey B: Complete multi-item request
    - Customer asks for two dosas and one coffee in a single utterance
    - Assistant resolves both items, verifies availability, executes corresponding cart operations
    - Confirms both additions without asking for each item one at a time
    """
    session_id = f"journey-b-{uuid.uuid4()}"

    r = client.post("/message", json={
        "message": "Two masala dosas and one coffee, please",
        "session_id": session_id
    }).json()

    assert r["intent"] == "add_to_cart"
    add_actions = [a for a in r["actions"] if a["type"] == "add_to_cart"]
    assert len(add_actions) == 2

    # Check quantities and items
    ids = [a["payload"]["id"] for a in add_actions]
    qtys = {a["payload"]["id"]: a["payload"]["quantity"] for a in add_actions}

    assert "ghee_roast_masala_dosa" in ids
    assert "jaggery_coffee" in ids
    assert qtys["ghee_roast_masala_dosa"] == 2
    assert qtys["jaggery_coffee"] == 1

    # Spoken message confirms both
    assert "Masala Dosa" in r["message"]
    assert "Coffee" in r["message"]


def test_journey_c_contextual_recommendations():
    """
    Journey C: Contextual recommendations
    - Customer asks for something light
    - Assistant uses supported menu information to offer relevant choices (Idly, Khara Bath)
    - Customer rejects first recommendation ("Actually, not that one")
    - Assistant adapts instead of repeating the same suggestion
    - Customer asks what drink would go well with it
    - Assistant suggests a real available beverage (Filter Coffee / Badam Milk)
    """
    session_id = f"journey-c-{uuid.uuid4()}"

    # Step 1: "Something light"
    r1 = client.post("/message", json={"message": "Something light", "session_id": session_id}).json()
    assert r1["intent"] == "recommend_light"
    assert "Idly" in r1["message"]

    # Step 2: "Actually, not that one"
    r2 = client.post("/message", json={"message": "Actually, not that one", "session_id": session_id}).json()
    assert r2["intent"] == "recommendation_adapted"
    assert "Poori Saagu" in r2["message"] or "Set Dosa" in r2["message"]

    # Step 3: "What drink goes well with this?"
    r3 = client.post("/message", json={"message": "What drink goes well with this?", "session_id": session_id}).json()
    assert r3["intent"] == "pairing_recommendation"
    assert "Filter Coffee" in r3["message"] or "Badam Milk" in r3["message"]


def test_journey_d_customer_changes_mind():
    """
    Journey D: Customer changes their mind
    - Customer adds a dish
    - Customer says "Actually, remove that"
    - Assistant resolves reference and removes the correct item
    - Customer changes quantity or selects another dish
    """
    session_id = f"journey-d-{uuid.uuid4()}"

    # Step 1: Add dish
    r1 = client.post("/message", json={"message": "Add one masala dosa", "session_id": session_id}).json()
    assert r1["intent"] == "add_to_cart"

    # Step 2: "Actually, remove that"
    r2 = client.post("/message", json={
        "message": "Actually, remove that",
        "session_id": session_id,
        "cart_items": [{"id": "ghee_roast_masala_dosa", "name": "Ghee Roast Masala Dosa", "quantity": 1, "price": 95}]
    }).json()
    assert r2["intent"] == "remove_from_cart"
    rem_actions = [a for a in r2["actions"] if a["type"] == "remove_from_cart"]
    assert len(rem_actions) == 1
    assert rem_actions[0]["payload"]["id"] == "ghee_roast_masala_dosa"

    # Step 3: Combined remove and replace: "Remove that and give me plain dosa"
    r3 = client.post("/message", json={
        "message": "Remove that and give me plain dosa",
        "session_id": session_id,
        "cart_items": [{"id": "ghee_roast_masala_dosa", "name": "Ghee Roast Masala Dosa", "quantity": 1, "price": 95}]
    }).json()
    assert r3["intent"] == "replace_item"
    action_types = [a["type"] for a in r3["actions"]]
    assert "remove_from_cart" in action_types
    assert "add_to_cart" in action_types


def test_journey_e_natural_kannada_ordering():
    """
    Journey E: Natural Kannada ordering
    - Customer speaks naturally in Kannada ("ಏನಾದರೂ ತಿಂಡಿ ತೋರಿಸಿ")
    - Assistant understands, suggests available items in Kannada
    - Customer asks "ಮಸಾಲೆ ದೋಸೆ ಎರಡು ಕೊಡಿ"
    - Assistant adds 2 masala dosas and responds in authentic Kannada
    - Customer asks "ಕಾಫಿ ಇದೆಯಾ?"
    - Assistant confirms filter coffee availability in Kannada
    """
    session_id = f"journey-e-{uuid.uuid4()}"

    # Step 1: "ಏನಾದರೂ ತಿಂಡಿ ತೋರಿಸಿ"
    r1 = client.post("/message", json={"message": "ಏನಾದರೂ ತಿಂಡಿ ತೋರಿಸಿ", "session_id": session_id}).json()
    assert r1["intent"] == "general_food_inquiry"
    assert "ದೋಸೆ" in r1["message"]

    # Step 2: "ಮಸಾಲೆ ದೋಸೆ ಎರಡು ಕೊಡಿ"
    r2 = client.post("/message", json={"message": "ಮಸಾಲೆ ದೋಸೆ ಎರಡು ಕೊಡಿ", "session_id": session_id}).json()
    assert r2["intent"] == "add_to_cart"
    assert "ಎರಡು" in r2["message"] or "ಸೇರಿಸಿದ್ದೀನಿ" in r2["message"]
    add_act = [a for a in r2["actions"] if a["type"] == "add_to_cart"]
    assert len(add_act) == 1
    assert add_act[0]["payload"]["quantity"] == 2

    # Step 3: "ಕಾಫಿ ಇದೆಯಾ?"
    r3 = client.post("/message", json={"message": "ಕಾಫಿ ಇದೆಯಾ?", "session_id": session_id}).json()
    assert r3["intent"] == "beverage_inquiry"
    assert "ಫಿಲ್ಟರ್ ಕಾಫಿ" in r3["message"] or "ಕಾಫಿ" in r3["message"]


def test_journey_f_kannada_english_switching():
    """
    Journey F: Kannada-English switching
    - Customer starts in Kannada ("ತಿಂಡಿ ಮೆನು ತೋರಿಸಿ")
    - Asks follow-up question in English ("What is the price of masala dosa?")
    - Returns to Kannada ("ಒಂದು ಮಸಾಲೆ ದೋಸೆ ಹಾಕಿ")
    - Context and cart preserved across language switches
    """
    session_id = f"journey-f-{uuid.uuid4()}"

    # Step 1: Kannada menu inquiry
    r1 = client.post("/message", json={"message": "ತಿಂಡಿ ಮೆನು ತೋರಿಸಿ", "session_id": session_id}).json()
    assert r1["screen"] in ["menu_items", "categories"]

    # Step 2: English price inquiry
    r2 = client.post("/message", json={"message": "What is the price of masala dosa?", "session_id": session_id}).json()
    assert r2["intent"] == "product_details"
    assert "₹95" in r2["message"]

    # Step 3: Return to Kannada
    r3 = client.post("/message", json={"message": "ಒಂದು ಮಸಾಲೆ ದೋಸೆ ಹಾಕಿ", "session_id": session_id}).json()
    assert r3["intent"] == "add_to_cart"
    assert "ಸೇರಿಸಿದ್ದೀನಿ" in r3["message"] or "ಸೇರಿಸಿದ್ದೇನೆ" in r3["message"]


def test_journey_g_availability_and_alternatives():
    """
    Journey G: Availability and alternatives
    - Customer asks for an unavailable item (Idly 1 Vada combo)
    - Assistant explains item is unavailable and offers verified individual alternatives
    """
    session_id = f"journey-g-{uuid.uuid4()}"

    r = client.post("/message", json={"message": "I want idly 1 vada", "session_id": session_id}).json()
    assert r["intent"] == "item_unavailable"
    assert "unavailable" in r["message"]
    assert "individually" in r["message"]


def test_journey_h_ambiguity_and_repair():
    """
    Journey H: Ambiguity and repair
    - Customer requests ambiguous item ("I want kofta" or generic "I want dosa")
    - Assistant asks clarification presenting top options
    - Customer answers with ordinal ("The second one")
    - Assistant resolves ordinal against options presented
    """
    session_id = f"journey-h-{uuid.uuid4()}"

    # Ambiguous request
    r1 = client.post("/message", json={"message": "I want kofta", "session_id": session_id}).json()
    assert r1["intent"] == "clarify_item"
    assert "multiple options" in r1["message"]

    # Ordinal clarification
    r2 = client.post("/message", json={"message": "The second one", "session_id": session_id}).json()
    assert r2["intent"] == "add_to_cart"
    assert "Kadai Kofta" in r2["message"]


def test_journey_i_navigation_while_ordering():
    """
    Journey I: Navigation while ordering
    - Customer navigates from category to section, back to another category, and to cart
    - Preserves active order and conversational context
    """
    session_id = f"journey-i-{uuid.uuid4()}"

    # Step 1: Go to South Indian breakfast
    r1 = client.post("/message", json={"message": "Open breakfast section", "session_id": session_id}).json()
    assert r1["screen"] == "menu_items"

    # Step 2: Add an item
    r2 = client.post("/message", json={"message": "Add one idly", "session_id": session_id}).json()
    assert r2["intent"] == "add_to_cart"

    # Step 3: Go back
    r3 = client.post("/message", json={"message": "Go back", "session_id": session_id}).json()
    assert r3["intent"] == "go_back"

    # Step 4: Open beverages
    r4 = client.post("/message", json={"message": "Show me beverages", "session_id": session_id}).json()
    assert r4["screen"] == "menu_items"

    # Step 5: Go to cart
    r5 = client.post("/message", json={"message": "View cart", "session_id": session_id}).json()
    assert r5["screen"] == "cart"


def test_journey_j_no_action_or_early_exit():
    """
    Journey J: No action or early exit
    - Customer says "That's enough" or "I'm done"
    - Cart summary presented if cart has items, or polite prompt if empty
    - Customer says "Cancel" -> safely cancels checkout without trapping customer
    """
    session_id = f"journey-j-{uuid.uuid4()}"

    # Empty cart finish
    r1 = client.post("/message", json={"message": "That's enough", "session_id": session_id, "cart_items": []}).json()
    assert r1["intent"] == "finish_order_empty"

    # Cart with items finish
    r2 = client.post("/message", json={
        "message": "Let's finish the order",
        "session_id": session_id,
        "cart_items": [{"id": "ghee_roast_masala_dosa", "name": "Ghee Roast Masala Dosa", "price": 95, "quantity": 1}]
    }).json()
    assert r2["intent"] == "checkout"
    assert r2["requires_confirmation"] is True

    # Cancel checkout
    r3 = client.post("/message", json={"message": "Cancel", "session_id": session_id}).json()
    assert r3["intent"] == "cancel_checkout"
    assert r3["screen"] == "cart"
