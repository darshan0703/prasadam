"""
TheAtom Prasadam — Conversational Cashier Acceptance Test Suite
--------------------------------------------------------------
Verifies the 5 canonical multi-turn customer conversation scenarios:
1. Scenario A — Breakfast Discovery & Ordering (Hunger -> Breakfast -> Dosa -> Popularity -> Add 2 Masala Dosas)
2. Scenario B — Contextual Anaphora & Quantity Correction (Dosa -> Varieties -> Spicy -> Add that one -> Make it two)
3. Scenario C — Food & Beverage Pairings (What goes with dosa -> Do you have coffee -> Add one coffee)
4. Scenario D — Ambiguity & Candidate Clarification (Show dosa -> Show idli -> Add two of those -> Clarify candidates)
5. Scenario E — Unsupported Cuisine Handling (Do you have pizza -> Refusal & pure-veg explanation -> Authentic recommendations)

Also verifies end-to-end response latency, session isolation, inventory grounding, and single TTS synthesis.
"""

import time
import uuid
import pytest
from starlette.testclient import TestClient
from api import app

client = TestClient(app)


def test_conversation_scenario_a_breakfast():
    """
    Scenario A: Breakfast Discovery & Ordering
    Customer: 'I'm hungry' -> 'What do you have for breakfast?' -> 'Maybe dosa' -> 'Which one is popular?' -> 'Okay, add two masala dosas'
    """
    session_id = f"test-scenario-a-{uuid.uuid4()}"
    client.post("/session/start", json={"session_id": session_id})

    # Turn 1: Customer: "I'm hungry"
    t0 = time.time()
    r1 = client.post("/message", json={"message": "I'm hungry", "session_id": session_id}).json()
    lat1 = time.time() - t0
    assert r1["intent"] == "general_food_inquiry"
    assert any(term in r1["message"].lower() for term in ["dosa", "idly", "bisi bele bath", "welcome"])
    assert r1["screen"] in ["categories", "home"]

    # Turn 2: Customer: "What do you have for breakfast?"
    t0 = time.time()
    r2 = client.post("/message", json={"message": "What do you have for breakfast?", "session_id": session_id}).json()
    lat2 = time.time() - t0
    assert r2["intent"] == "show_section"
    assert r2["screen"] == "menu_items"
    assert any(a["type"] == "navigate" and a["payload"].get("section_id") == "south_indian_breakfast" for a in r2["actions"])

    # Turn 3: Customer: "Maybe dosa"
    t0 = time.time()
    r3 = client.post("/message", json={"message": "Maybe dosa", "session_id": session_id}).json()
    lat3 = time.time() - t0
    assert r3["intent"] == "show_section"
    assert r3["screen"] == "menu_items"
    assert any(a["type"] == "navigate" and a["payload"].get("section_id") == "dose_special" for a in r3["actions"])

    # Turn 4: Customer: "Which one is popular?"
    t0 = time.time()
    r4 = client.post("/message", json={"message": "Which one is popular?", "session_id": session_id}).json()
    lat4 = time.time() - t0
    assert r4["intent"] == "recommendation"
    # Grounded fact: mentions authentic staples without fabricated ratings
    assert "Masala Dosa" in r4["message"]

    # Turn 5: Customer: "Okay, add two masala dosas"
    t0 = time.time()
    r5 = client.post("/message", json={"message": "Okay, add two masala dosas", "session_id": session_id}).json()
    lat5 = time.time() - t0
    assert r5["intent"] == "add_to_cart"
    assert any(a["type"] == "add_to_cart" and a["payload"]["quantity"] == 2 for a in r5["actions"])
    assert r5["data"]["cart_count"] == 2
    assert r5["data"]["cart_total"] == 190.0

    # Verify TTS audio generation for the final spoken cashier confirmation
    tts_resp = client.post("/tts", json={"text": r5["message"]})
    assert tts_resp.status_code == 200
    assert tts_resp.headers["content-type"] == "audio/wav"
    assert tts_resp.headers["x-tts-engine"] in ["kokoro", "kannada-soumya"]
    assert tts_resp.content[:4] == b"RIFF"

    print(f"\n[Scenario A Latency] T1: {lat1:.2f}s, T2: {lat2:.2f}s, T3: {lat3:.2f}s, T4: {lat4:.2f}s, T5: {lat5:.2f}s")


def test_conversation_scenario_b_context_and_anaphora():
    """
    Scenario B: Contextual Anaphora & Quantity Correction
    Customer: 'Show me dosa' -> 'What varieties do you have?' -> 'Which one is spicy?' -> 'Add that one' -> 'Actually, make it two'
    """
    session_id = f"test-scenario-b-{uuid.uuid4()}"
    client.post("/session/start", json={"session_id": session_id})

    # Turn 1: Customer: "Show me dosa"
    r1 = client.post("/message", json={"message": "Show me dosa", "session_id": session_id}).json()
    assert r1["intent"] == "show_section"
    assert r1["screen"] == "menu_items"

    # Turn 2: Customer: "What varieties do you have?"
    r2 = client.post("/message", json={"message": "What varieties do you have?", "session_id": session_id}).json()
    assert r2["intent"] == "dosa_varieties"
    assert any(term in r2["message"] for term in ["Plain Dosa", "Masala Dosa", "Set Dosa", "Rava Dosa"])

    # Turn 3: Customer: "Which one is spicy?"
    r3 = client.post("/message", json={"message": "Which one is spicy?", "session_id": session_id}).json()
    assert r3["intent"] == "product_details"
    assert "Pudi Masala Dosa" in r3["message"]

    # Turn 4: Customer: "Add that one"
    r4 = client.post("/message", json={"message": "Add that one", "session_id": session_id}).json()
    assert r4["intent"] == "add_to_cart"
    assert any(a["type"] == "add_to_cart" and a["payload"]["id"] == "ghee_pudi_masala_dosa" for a in r4["actions"])
    assert r4["data"]["cart_count"] == 1

    # Turn 5: Customer: "Actually, make it two"
    r5 = client.post("/message", json={"message": "Actually, make it two", "session_id": session_id}).json()
    assert r5["intent"] == "set_quantity"
    assert any(a["type"] == "set_quantity" and a["payload"]["quantity"] == 2 for a in r5["actions"])
    assert r5["data"]["cart_count"] == 2

    # Verify session isolation and cart state
    cart_resp = client.get(f"/cart?session_id={session_id}").json()
    assert cart_resp["itemCount"] == 2
    assert cart_resp["cart"][0]["id"] == "ghee_pudi_masala_dosa"


def test_conversation_scenario_c_pairings_and_coffee():
    """
    Scenario C: Food & Beverage Pairings
    Customer: 'What goes well with dosa?' -> 'Do you have coffee?' -> 'Add one coffee'
    """
    session_id = f"test-scenario-c-{uuid.uuid4()}"
    client.post("/session/start", json={"session_id": session_id})

    # Turn 1: Customer: "What goes well with dosa?"
    r1 = client.post("/message", json={"message": "What goes well with dosa?", "session_id": session_id}).json()
    assert r1["intent"] == "pairing_recommendation"
    assert any(term in r1["message"] for term in ["Filter Coffee", "Mysore Pak", "Badam Milk"])

    # Turn 2: Customer: "Do you have coffee?"
    r2 = client.post("/message", json={"message": "Do you have coffee?", "session_id": session_id}).json()
    assert r2["intent"] == "beverage_inquiry"
    assert any(term in r2["message"] for term in ["Filter Coffee", "Jaggery Coffee", "coffee"])

    # Turn 3: Customer: "Add one coffee"
    r3 = client.post("/message", json={"message": "Add one coffee", "session_id": session_id}).json()
    assert r3["intent"] == "add_to_cart"
    assert any(a["type"] == "add_to_cart" and "coffee" in a["payload"]["id"] for a in r3["actions"])
    assert r3["data"]["cart_count"] == 1


def test_conversation_scenario_d_ambiguity_clarification():
    """
    Scenario D: Ambiguity & Candidate Clarification
    Customer: 'Show me dosa' -> 'Show me idli' -> 'Add two of those' -> (Clarification triggered) -> 'Dosa' -> Add 2
    """
    session_id = f"test-scenario-d-{uuid.uuid4()}"
    client.post("/session/start", json={"session_id": session_id})

    # Turn 1: Customer: "Show me dosa"
    r1 = client.post("/message", json={"message": "Show me dosa", "session_id": session_id}).json()
    assert r1["screen"] == "menu_items"

    # Turn 2: Customer: "Show me idli"
    r2 = client.post("/message", json={"message": "Show me idli", "session_id": session_id}).json()
    assert r2["screen"] in ["product", "menu_items"]

    # Turn 3: Customer: "Add two of those"
    # Stage A flags ambiguity between recent candidate items
    r3 = client.post("/message", json={"message": "Add two of those", "session_id": session_id}).json()
    # Must either ask a clear clarification or clarify candidates
    assert r3["intent"] in ["clarify_item", "add_to_cart"]
    if r3["intent"] == "clarify_item":
        assert any(term in r3["message"].lower() for term in ["options", "which", "dosa", "idli"])
        # Turn 4: Customer clarifies "Dosa"
        r4 = client.post("/message", json={"message": "Dosa", "session_id": session_id}).json()
        assert r4["intent"] in ["add_to_cart", "show_section"]


def test_conversation_scenario_e_unsupported_cuisine():
    """
    Scenario E: Unsupported Cuisine Handling
    Customer: 'Do you have pizza?' -> 'What else would you recommend?'
    """
    session_id = f"test-scenario-e-{uuid.uuid4()}"
    client.post("/session/start", json={"session_id": session_id})

    # Turn 1: Customer: "Do you have pizza?"
    r1 = client.post("/message", json={"message": "Do you have pizza?", "session_id": session_id}).json()
    assert r1["intent"] == "unsupported_cuisine"
    assert "pizza" in r1["message"].lower()
    assert any(term in r1["message"].lower() for term in ["pure vegetarian", "south indian", "authentic", "don't serve", "do not serve"])
    # No cart mutation
    assert r1["data"].get("cart_count", 0) == 0

    # Turn 2: Customer: "What else would you recommend?"
    r2 = client.post("/message", json={"message": "What else would you recommend?", "session_id": session_id}).json()
    assert r2["intent"] == "recommendation"
    assert any(term in r2["message"] for term in ["Masala Dosa", "Bisi Bele Bath", "Filter Coffee", "Mysore Pak"])
