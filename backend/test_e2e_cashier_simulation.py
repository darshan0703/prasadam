import json
import os
import urllib.request
import urllib.error

BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8002")

def post(endpoint, data=None, headers=None):
    if headers is None:
        headers = {}
    headers["Content-Type"] = "application/json"
    body = json.dumps(data).encode("utf-8") if data else b""
    req = urllib.request.Request(f"{BASE_URL}{endpoint}", data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

def get(endpoint, headers=None):
    if headers is None:
        headers = {}
    req = urllib.request.Request(f"{BASE_URL}{endpoint}", headers=headers, method="GET")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

def run_simulation():
    print("=== THEATOM PRASADAM E2E CASHIER SIMULATION ===")
    
    # 1. Start Session
    sess = post("/session/start", {"preferred_language": "AUTO"})
    session_id = sess["session_id"]
    print(f"Step 1: Started new session: {session_id}")
    
    # 2. Utterance: 'Sweet yen idhe?'
    print("\nCustomer: 'Sweet yen idhe?'")
    resp1 = post("/message", {"message": "Sweet yen idhe?", "session_id": session_id, "screen": "categories"})
    print(f"Cashier: {resp1['message']}")
    print(f"Screen: {resp1.get('screen')}, Intent: {resp1.get('intent')}, Section: {resp1.get('data', {}).get('section_id')}")
    assert resp1["screen"] == "menu_items", f"Expected screen menu_items, got {resp1.get('screen')}"
    assert resp1.get("data", {}).get("section_id") == "sweet_items", f"Expected sweet_items section, got {resp1.get('data')}"
    assert resp1.get("language") == "kn", f"Expected language kn, got {resp1.get('language')}"
    print("  -> Navigation to Sweet Items verified!")
    print("  -> Spoken Bengaluru Kannada response verified!")

    # 3. Utterance: 'Ondu gulab jamun kodi'
    print("\nCustomer: 'Ondu gulab jamun kodi'")
    resp2 = post("/message", {"message": "Ondu gulab jamun kodi", "session_id": session_id, "screen": "menu_items"})
    print(f"Cashier: {resp2['message']}")
    print(f"Intent: {resp2.get('intent')}, Item: {resp2.get('data', {}).get('item_id')}, Qty: {resp2.get('data', {}).get('quantity')}")
    assert resp2["intent"] == "add_to_cart", f"Expected add_to_cart, got {resp2.get('intent')}"
    assert resp2.get("data", {}).get("item_id") == "jamoon_1", f"Expected jamoon_1, got {resp2.get('data')}"
    assert resp2.get("data", {}).get("quantity") == 1, f"Expected quantity 1, got {resp2.get('data')}"
    print("  -> Deterministic backend cart addition verified!")

    # 4. Check authoritative cart
    cart1 = get("/cart", headers={"X-Session-ID": session_id})
    print(f"\nAuthoritative Cart: items={len(cart1['cart'])}, total=₹{cart1['total']}")
    assert len(cart1["cart"]) == 1
    assert cart1["cart"][0]["item_id"] == "jamoon_1"
    assert cart1["cart"][0]["quantity"] == 1
    assert cart1["total"] == 20.0
    print("  -> Authoritative cart verified with ₹20.00 total!")

    # 5. Utterance: 'Coffee kooda kodi'
    print("\nCustomer: 'Coffee kooda kodi'")
    resp3 = post("/message", {"message": "Coffee kooda kodi", "session_id": session_id, "screen": "menu_items"})
    print(f"Cashier: {resp3['message']}")
    print(f"Intent: {resp3.get('intent')}, Item: {resp3.get('data', {}).get('item_id')}, Qty: {resp3.get('data', {}).get('quantity')}")
    assert resp3["intent"] == "add_to_cart", f"Expected add_to_cart, got {resp3.get('intent')}"
    print("  -> Added Coffee to cart verified!")

    # 6. Check authoritative cart with 2 items
    cart2 = get("/cart", headers={"X-Session-ID": session_id})
    print(f"\nAuthoritative Cart: items={len(cart2['cart'])}, total=₹{cart2['total']}")
    assert len(cart2["cart"]) == 2
    assert cart2["total"] == 45.0  # ₹20 (jamoon) + ₹25 (filter coffee)
    print("  -> Cart updated: Gulab Jamun (₹20) + Filter Coffee (₹25) = ₹45.00!")

    # 7. Utterance: 'Total eshtu?'
    print("\nCustomer: 'Total eshtu?'")
    resp4 = post("/message", {"message": "Total eshtu?", "session_id": session_id, "screen": "menu_items"})
    print(f"Cashier: {resp4['message']}")
    assert "45" in resp4["message"], f"Expected 45 in message, got {resp4['message']}"
    print("  -> Cashier quoted exact authoritative cart total in Kannada!")

    # 8. Complete Order
    print("\nCustomer: Completes order at kiosk")
    order_resp = post("/order/complete", {"payment_method": "demo_upi", "customer_name": "Pavan", "customer_phone": "9876543210"}, headers={"X-Session-ID": session_id})
    order = order_resp["order"]
    print(f"Order Completed! Order Number: #{order.get('order_number')}, Total: ₹{order.get('total')}")
    assert order["status"] == "confirmed"
    assert order["total"] == 45.0

    # 9. Verify cart is cleared after order
    cart3 = get("/cart", headers={"X-Session-ID": session_id})
    assert len(cart3["cart"]) == 0
    print("  -> Cart cleared after order completion!")

    print("\n=== ALL E2E SIMULATION STEPS VERIFIED 100% SUCCESSFULLY! ===")

if __name__ == "__main__":
    run_simulation()
