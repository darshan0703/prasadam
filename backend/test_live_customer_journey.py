"""
Live Full-Stack Customer Journey Verification Script.
Simulates a real customer browsing the kiosk via the Vite server (port 5173),
exercising all 10 customer journey steps against the live backend (port 8000).
"""

import os
import urllib.request
import json
import uuid

VITE_BASE = os.getenv("VITE_BASE", "http://localhost:5175")

def request_json(url, method="GET", data=None, headers=None):
    hdrs = {"Accept": "application/json"}
    if headers:
        hdrs.update(headers)
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        hdrs["Content-Type"] = "application/json"
    
    req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        try:
            return e.code, json.loads(err_body)
        except Exception:
            return e.code, {"raw": err_body}

def run_live_customer_journey():
    print("=== LIVE FULL-STACK CUSTOMER JOURNEY AUDIT ===")

    # Step 1: Kiosk Welcome / Home Screen
    print("\n[Step 1] Loading Kiosk Welcome / Home Screen HTML...")
    req = urllib.request.Request(f"{VITE_BASE}/")
    with urllib.request.urlopen(req) as resp:
        html = resp.read().decode("utf-8")
        assert resp.status == 200
        assert "<div id=\"root\"></div>" in html
        print("  -> Welcome page HTML loaded successfully (HTTP 200).")

    # Step 2: Start Customer Session
    print("\n[Step 2] Initializing fresh customer session via POST /session/start...")
    status, sess_data = request_json(f"{VITE_BASE}/session/start", method="POST")
    assert status == 200, f"Expected 200, got {status}"
    assert sess_data.get("success") is True
    session_id = sess_data["session_id"]
    print(f"  -> Session created: {session_id} ('{sess_data.get('message')}')")

    # Step 3: Browse Categories and Canonical Sections
    print("\n[Step 3] Fetching menu sections via GET /menu/sections...")
    status, sections_data = request_json(f"{VITE_BASE}/menu/sections")
    assert status == 200
    assert sections_data["total_groups"] == 6
    assert sections_data["total_sections"] == 19
    first_group = sections_data["groups"][0]
    print(f"  -> Found {sections_data['total_groups']} groups, 19 canonical sections.")
    print(f"  -> First Category: '{first_group['title_english']}' ({first_group['title_kannada']})")

    # Step 4: Browse Dishes in Selected Section ('dose_special')
    print("\n[Step 4] Fetching section dishes via GET /menu/sections/dose_special/items...")
    status, sec_items = request_json(f"{VITE_BASE}/menu/sections/dose_special/items")
    assert status == 200
    assert sec_items["item_count"] == 22
    assert sec_items["status"] == "active"
    dosa = next(i for i in sec_items["items"] if i["id"] == "ghee_plain_dosa")
    print(f"  -> Loaded 22 authentic dishes. Found: '{dosa['name']}' at ₹{dosa['price']}")

    # Step 5: Open Dedicated Product Details Page
    print("\n[Step 5] Fetching dish details via GET /menu/items/ghee_plain_dosa...")
    status, item_detail = request_json(f"{VITE_BASE}/menu/items/ghee_plain_dosa")
    assert status == 200
    item = item_detail["item"]
    assert item["name"] == "Ghee Plain Dosa"
    assert item["price"] == 70.0
    assert item["is_veg"] is True
    assert item["available"] is True
    print(f"  -> Verified product details: {item['name']}, Price: ₹{item['price']}, Veg: {item['is_veg']}")

    # Step 6: Add Dish with Selected Quantity to Cart
    print("\n[Step 6] Adding 2 units of Ghee Plain Dosa to Tray via POST /cart/add...")
    status, cart_res = request_json(
        f"{VITE_BASE}/cart/add",
        method="POST",
        data={
            "item_id": "ghee_plain_dosa",
            "quantity": 2,
            "session_id": session_id,
        }
    )
    assert status == 200
    assert cart_res["itemCount"] == 2
    assert cart_res["total"] == 140.0
    print(f"  -> Added to cart. Items in tray: {cart_res['itemCount']}, Total: ₹{cart_res['total']}")

    # Step 7: Modify Tray Quantities (Stepper + and -)
    print("\n[Step 7] Updating tray quantities via PATCH /cart/item...")
    # Increase to 3
    status, inc_res = request_json(
        f"{VITE_BASE}/cart/item",
        method="PATCH",
        data={
            "item_id": "ghee_plain_dosa",
            "action": "increase",
            "session_id": session_id,
        }
    )
    assert status == 200
    assert inc_res["itemCount"] == 3
    assert inc_res["total"] == 210.0
    print(f"  -> Increased quantity to 3: Subtotal ₹{inc_res['total']}")

    # Decrease back to 2
    status, dec_res = request_json(
        f"{VITE_BASE}/cart/item",
        method="PATCH",
        data={
            "item_id": "ghee_plain_dosa",
            "action": "decrease",
            "session_id": session_id,
        }
    )
    assert status == 200
    assert dec_res["itemCount"] == 2
    assert dec_res["total"] == 140.0
    print(f"  -> Decreased quantity back to 2: Subtotal ₹{dec_res['total']}")

    # Step 8: Session Persistence Across Page Navigation
    print("\n[Step 8] Verifying active session cart via GET /cart?session_id=...")
    status, check_cart = request_json(f"{VITE_BASE}/cart?session_id={session_id}")
    assert status == 200
    assert check_cart["itemCount"] == 2
    assert check_cart["total"] == 140.0
    print(f"  -> Cart persisted for session {session_id}: 2 items, ₹140.0")

    # Step 9: Complete Order Checkout via Demo UPI
    print("\n[Step 9] Completing order via POST /order/complete (demo_upi)...")
    idem_key = f"idem_kiosk_{uuid.uuid4()}"
    status, order_res = request_json(
        f"{VITE_BASE}/order/complete",
        method="POST",
        data={
            "session_id": session_id,
            "payment_method": "demo_upi",
            "customer_name": "Kiosk Devotee",
            "idempotency_key": idem_key,
        }
    )
    assert status == 200
    assert order_res["success"] is True
    order = order_res["order"]
    order_id = order["order_id"]
    order_number = order["order_number"]
    assert order_number.startswith("P-")
    assert order["total"] == 140.0
    assert order["payment_method"] == "demo_upi"
    assert order["payment_status"] == "demo_completed"
    assert order["status"] == "confirmed"
    print(f"  -> Order Confirmed! Token: #{order_number}, UUID: {order_id}")
    print(f"  -> Items: {len(order['items'])}, Total: ₹{order['total']}, Payment: {order['payment_method']} ({order['payment_status']})")

    # Step 10: Retrieve Order and Verify Cart is Cleared
    print("\n[Step 10] Retrieving confirmed order via GET /order/{order_number} and verifying cart is cleared...")
    status, fetch_ord = request_json(f"{VITE_BASE}/order/{order_number}")
    assert status == 200
    assert fetch_ord["order"]["order_id"] == order_id

    # Cart after checkout must be 0
    status, empty_cart = request_json(f"{VITE_BASE}/cart?session_id={session_id}")
    assert empty_cart["itemCount"] == 0
    print("  -> Order retrieved by token number. Cart authoritatively cleared.")

    # Step 11: Edge Cases & Integrity Verification
    print("\n[Step 11] Verifying edge cases (idempotency, unavailable item, empty cart, invalid item)...")
    # Duplicate submission with same idempotency key
    status, dup_res = request_json(
        f"{VITE_BASE}/order/complete",
        method="POST",
        data={
            "session_id": session_id,
            "payment_method": "demo_upi",
            "idempotency_key": idem_key,
        }
    )
    assert status == 200
    assert dup_res["order"]["order_id"] == order_id
    print("  -> [PASS] Idempotent order resubmission avoided duplicate order.")

    # Empty cart checkout rejected
    new_sess = f"empty_sess_{uuid.uuid4()}"
    status, empty_err = request_json(
        f"{VITE_BASE}/order/complete",
        method="POST",
        data={"session_id": new_sess, "payment_method": "demo_upi"}
    )
    assert status == 400
    assert "empty cart" in empty_err.get("detail", "").lower()
    print("  -> [PASS] Empty cart checkout rejected with HTTP 400.")

    # Uncatalogued item rejected
    status, uncat_err = request_json(
        f"{VITE_BASE}/cart/add",
        method="POST",
        data={"item_id": "non_existent_fake_dish", "quantity": 1, "session_id": new_sess}
    )
    assert status in [400, 404]
    print("  -> [PASS] Uncatalogued item ID rejected.")

    # Quarantined / unavailable item rejected
    status, unavail_err = request_json(
        f"{VITE_BASE}/cart/add",
        method="POST",
        data={"item_id": "coffee_tea", "quantity": 1, "session_id": new_sess}
    )
    assert status == 400
    assert "unavailable" in unavail_err.get("detail", "").lower()
    # Step 12: Live Voice & Conversational AI Assistant Verification
    print("\n[Step 12] Exercising Live AI Conversation & Voice Endpoints via Vite proxy...")
    
    # 12a: Greeting
    status, msg_resp = request_json(
        f"{VITE_BASE}/message",
        method="POST",
        data={"message": "Namaskara", "session_id": session_id}
    )
    assert status == 200
    assert msg_resp["intent"] == "greeting"
    print(f"  -> Voice/Text Greeting: '{msg_resp['message'][:50]}...'")

    # 12b: Add item to cart by voice
    voice_sess = f"voice_journey_sess_{uuid.uuid4()}"
    status, add_voice = request_json(
        f"{VITE_BASE}/message",
        method="POST",
        data={"message": "Add 2 Ghee Roast Masala Dosa", "session_id": voice_sess}
    )
    assert status == 200
    assert add_voice["intent"] == "add_to_cart"
    assert add_voice["data"]["cart_count"] == 2
    assert add_voice["data"]["cart_total"] == 190.0
    print(f"  -> Voice Add to Cart: '{add_voice['message']}' (Total: ₹{add_voice['data']['cart_total']})")

    # 12c: Cart summary by voice
    status, summary_voice = request_json(
        f"{VITE_BASE}/message",
        method="POST",
        data={"message": "What is in my cart?", "session_id": voice_sess}
    )
    assert status == 200
    assert summary_voice["intent"] == "view_cart"
    print(f"  -> Voice Cart Summary: '{summary_voice['message']}'")

    # 12d: Dietary / Pure Veg enquiry
    status, diet_voice = request_json(
        f"{VITE_BASE}/message",
        method="POST",
        data={"message": "Is this pure veg?", "session_id": voice_sess}
    )
    assert status == 200
    assert diet_voice["intent"] == "dietary_query"
    assert "pure vegetarian" in diet_voice["message"].lower()
    print(f"  -> Voice Dietary Query: '{diet_voice['message'][:60]}...'")

    # 12e: TTS audio generation
    print("  -> Testing TTS audio synthesis via POST /tts...")
    tts_req = urllib.request.Request(
        f"{VITE_BASE}/tts",
        data=json.dumps({"text": "Welcome to The Atom Prasadam"}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(tts_req) as tts_resp:
        assert tts_resp.status == 200
        assert tts_resp.headers.get("Content-Type") == "audio/wav"
        audio_content = tts_resp.read()
        assert len(audio_content) > 1000
        print(f"  -> Synthesized {len(audio_content)} bytes of 24kHz mono WAV audio.")

    print("\n=== ALL 12 LIVE CUSTOMER JOURNEY PHASES PASSED SUCCESSFULLY ===")

if __name__ == "__main__":
    run_live_customer_journey()
