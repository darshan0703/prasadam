import uuid
from fastapi.testclient import TestClient
from api import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"
    assert "service" in data

def test_start_session_contract():
    response = client.post("/session/start")
    assert response.status_code == 200
    data = response.json()
    assert data.get("success") is True
    assert "session_id" in data
    parsed_uuid = uuid.UUID(data["session_id"])
    assert str(parsed_uuid) == data["session_id"]
    assert "Welcome to Prasadam" in data.get("message", "")

def test_menu_sections_endpoint():
    response = client.get("/menu/sections")
    assert response.status_code == 200
    data = response.json()
    assert data.get("success") is True
    assert data.get("total_groups") == 6
    assert data.get("total_sections") == 19
    
    # Verify all 6 group letters A through F
    groups = data.get("groups", [])
    letters = [g["group_letter"] for g in groups]
    assert letters == ["A", "B", "C", "D", "E", "F"]

    # Verify every section has canonical_name and kannada_name
    section_ids = []
    for g in groups:
        for s in g["sections"]:
            assert "canonical_name" in s
            assert "kannada_name" in s
            section_ids.append(s["id"])
    
    assert len(section_ids) == 19
    assert len(set(section_ids)) == 19  # No duplicates

def test_section_items_integrity():
    # 1. Populated dose_special section (22 dishes)
    resp_dose = client.get("/menu/sections/dose_special/items")
    assert resp_dose.status_code == 200
    data_dose = resp_dose.json()
    assert data_dose.get("success") is True
    assert data_dose.get("section_id") == "dose_special"
    assert data_dose.get("item_count") == 22
    assert data_dose.get("status") == "active"
    dosa_names = [i["name"] for i in data_dose["items"]]
    assert "Ghee Pudi Plain Dosa" in dosa_names
    pudi_dosa = next(i for i in data_dose["items"] if i["name"] == "Ghee Pudi Plain Dosa")
    assert pudi_dosa["price"] == 85.0
    assert pudi_dosa["available"] is True

    # 2. Populated south_indian_breakfast section (17 dishes)
    resp_bfast = client.get("/menu/sections/south_indian_breakfast/items")
    assert resp_bfast.status_code == 200
    data_bfast = resp_bfast.json()
    assert data_bfast.get("success") is True
    assert data_bfast.get("section_id") == "south_indian_breakfast"
    assert data_bfast.get("item_count") == 17
    assert data_bfast.get("status") == "active"
    bfast_names = [i["name"] for i in data_bfast["items"]]
    assert "Bisi Bele Bath" in bfast_names
    assert "Chow-chow Bath" in bfast_names
    bisi_bele = next(i for i in data_bfast["items"] if i["name"] == "Bisi Bele Bath")
    assert bisi_bele["price"] == 60.0
    chow_chow = next(i for i in data_bfast["items"] if i["name"] == "Chow-chow Bath")
    assert chow_chow["price"] == 80.0

    # 3. Populated meals section (9 dishes)
    resp_meals = client.get("/menu/sections/meals/items")
    assert resp_meals.status_code == 200
    data_meals = resp_meals.json()
    assert data_meals.get("success") is True
    assert data_meals.get("section_id") == "meals"
    assert data_meals.get("item_count") == 9
    assert data_meals.get("status") == "active"
    assert any(i["name"] == "South Meals" and i["price"] == 100.0 for i in data_meals["items"])

    # 4. Comprehensive verification across all 19 canonical sections
    resp_sections = client.get("/menu/sections")
    all_sections = [s["id"] for g in resp_sections.json()["groups"] for s in g["sections"]]
    assert len(all_sections) == 19
    total_catalogue_dishes = 0
    for sec_id in all_sections:
        r = client.get(f"/menu/sections/{sec_id}/items")
        assert r.status_code == 200
        sec_data = r.json()
        assert sec_data["status"] == "active"
        assert sec_data["item_count"] > 0
        total_catalogue_dishes += sec_data["item_count"]
        # Ensure all items have valid prices and image paths
        for item in sec_data["items"]:
            assert item["price"] > 0
            assert item["image"].startswith("/menu-items/")
    assert total_catalogue_dishes == 262

def test_menu_review_queue():
    response = client.get("/menu/review-queue")
    assert response.status_code == 200
    data = response.json()
    assert data.get("success") is True
    assert data.get("total_review_items") == 6
    assert data.get("sections_requiring_review") == 4
    queue = data.get("review_queue", {})
    assert "hot_beverages" in queue
    assert "south_indian_breakfast" in queue
    assert "north_indian_jain_items" in queue
    assert "indian_curries" in queue
    
    # Verify Coffee / Tea review quarantine
    hot_bev = queue["hot_beverages"]
    assert any(item["name"] == "Coffee / Tea" and item["requires_review"] is True for item in hot_bev)

    # Verify quarantined items are unavailable for checkout
    bfast_items = client.get("/menu/sections/south_indian_breakfast/items").json()["items"]
    idly_vada_1 = next(i for i in bfast_items if i["name"] == "Idly (1) Vada")
    assert idly_vada_1["available"] is False
    assert idly_vada_1["requires_review"] is True

    bev_items = client.get("/menu/sections/hot_beverages/items").json()["items"]
    coffee_tea = next(i for i in bev_items if i["name"] == "Coffee / Tea")
    assert coffee_tea["available"] is False
    assert coffee_tea["requires_review"] is True

def test_menu_item_endpoint():
    # Valid item lookup by stable ID
    resp = client.get("/menu/items/ghee_plain_dosa")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("success") is True
    item = data.get("item")
    assert item["id"] == "ghee_plain_dosa"
    assert item["name"] == "Ghee Plain Dosa"
    assert item["price"] == 70.0
    assert item["section_id"] == "dose_special"

    # Nonexistent item returns 404
    resp_404 = client.get("/menu/items/non_existent_item_xyz")
    assert resp_404.status_code == 404

def test_cart_endpoints():
    test_session = f"test_session_{uuid.uuid4()}"

    # Initially empty
    response = client.get(f"/cart?session_id={test_session}")
    assert response.status_code == 200
    data = response.json()
    assert data.get("cart") == []
    assert data.get("itemCount") == 0
    assert data.get("total") == 0

    # Add item to cart
    add_resp = client.post(
        "/cart/add",
        json={
            "item_id": "ghee_plain_dosa",
            "name": "Ghee Plain Dosa",
            "price": 70.0,
            "quantity": 1,
            "session_id": test_session,
        },
    )
    assert add_resp.status_code == 200
    add_data = add_resp.json()
    assert add_data.get("success") is True
    assert add_data.get("itemCount") == 1
    assert add_data.get("total") == 70.0
    assert len(add_data.get("cart")) == 1

    # Add 2 more of the same item
    add_resp2 = client.post(
        "/cart/add",
        json={
            "item_id": "ghee_plain_dosa",
            "name": "Ghee Plain Dosa",
            "price": 70.0,
            "quantity": 2,
            "session_id": test_session,
        },
    )
    assert add_resp2.status_code == 200
    add_data2 = add_resp2.json()
    assert add_data2.get("itemCount") == 3
    assert add_data2.get("total") == 210.0
    assert len(add_data2.get("cart")) == 1
    assert add_data2["cart"][0]["quantity"] == 3
    assert add_data2["cart"][0]["subtotal"] == 210.0

    # Quantity <= 0 rejected
    bad_qty = client.post(
        "/cart/add",
        json={
            "item_id": "ghee_plain_dosa",
            "name": "Ghee Plain Dosa",
            "price": 70.0,
            "quantity": 0,
            "session_id": test_session,
        },
    )
    assert bad_qty.status_code == 400

    # Unavailable / review quarantined item rejected
    unavail = client.post(
        "/cart/add",
        json={
            "item_id": "coffee_tea",
            "name": "Coffee / Tea",
            "price": 15.0,
            "quantity": 1,
            "session_id": test_session,
        },
    )
    assert unavail.status_code == 400

    # Clear cart
    clear_resp = client.post(f"/cart/clear?session_id={test_session}")
    assert clear_resp.status_code == 200
    assert clear_resp.json().get("success") is True

    # Verify empty after clear
    after_clear = client.get(f"/cart?session_id={test_session}")
    assert after_clear.json().get("itemCount") == 0

def test_cart_item_patch_endpoint():
    test_session = f"test_session_{uuid.uuid4()}"

    # Add item
    client.post(
        "/cart/add",
        json={
            "item_id": "ghee_plain_dosa",
            "name": "Ghee Plain Dosa",
            "price": 70.0,
            "quantity": 2,
            "session_id": test_session,
        },
    )

    # Increase quantity
    inc_resp = client.patch(
        "/cart/item",
        json={
            "item_id": "ghee_plain_dosa",
            "action": "increase",
            "session_id": test_session,
        },
    )
    assert inc_resp.status_code == 200
    assert inc_resp.json()["itemCount"] == 3
    assert inc_resp.json()["total"] == 210.0

    # Decrease quantity
    dec_resp = client.patch(
        "/cart/item",
        json={
            "item_id": "ghee_plain_dosa",
            "action": "decrease",
            "session_id": test_session,
        },
    )
    assert dec_resp.status_code == 200
    assert dec_resp.json()["itemCount"] == 2
    assert dec_resp.json()["total"] == 140.0

    # Remove item
    rem_resp = client.patch(
        "/cart/item",
        json={
            "item_id": "ghee_plain_dosa",
            "action": "remove",
            "session_id": test_session,
        },
    )
    assert rem_resp.status_code == 200
    assert rem_resp.json()["itemCount"] == 0
    assert len(rem_resp.json()["cart"]) == 0

def test_order_complete_endpoint():
    test_session = f"test_session_{uuid.uuid4()}"

    # Empty cart order completion rejected
    bad_order = client.post(
        "/order/complete",
        json={
            "session_id": test_session,
            "payment_method": "demo_upi",
        },
    )
    assert bad_order.status_code == 400

    # Add 2 items
    client.post(
        "/cart/add",
        json={
            "item_id": "ghee_plain_dosa",
            "name": "Ghee Plain Dosa",
            "price": 70.0,
            "quantity": 2,
            "session_id": test_session,
        },
    )
    client.post(
        "/cart/add",
        json={
            "item_id": "bisi_bele_bath",
            "name": "Bisi Bele Bath",
            "price": 60.0,
            "quantity": 1,
            "session_id": test_session,
        },
    )

    # Complete order
    complete_resp = client.post(
        "/order/complete",
        json={
            "session_id": test_session,
            "payment_method": "demo_upi",
            "customer_name": "Devotee Kiosk",
        },
    )
    assert complete_resp.status_code == 200
    comp_data = complete_resp.json()
    assert comp_data["success"] is True
    order = comp_data["order"]
    assert order["order_number"].startswith("P-")
    assert order["itemCount"] == 3
    assert order["total"] == 200.0
    assert len(order["items"]) == 2
    assert order["payment_method"] == "demo_upi"

    # Verify session cart cleared authoritatively
    cart_after = client.get(f"/cart?session_id={test_session}").json()
    assert cart_after["itemCount"] == 0
    assert cart_after["cart"] == []

    # Verify retrieval
    get_order_resp = client.get(f"/order/{order['order_id']}")
    assert get_order_resp.status_code == 200
    assert get_order_resp.json()["order"]["order_number"] == order["order_number"]


def test_menu_invalid_section_id_returns_404():
    resp = client.get("/menu/sections/non_existent_section_id_xyz/items")
    assert resp.status_code == 404
    assert "not found" in resp.json().get("detail", "").lower()


def test_menu_item_optional_fields_and_aliases():
    # Mangalore Buns (2) has description=None and kannadaName=None
    resp = client.get("/menu/items/mangalore_buns_2")
    assert resp.status_code == 200
    item = resp.json()["item"]
    assert item["id"] == "mangalore_buns_2"
    assert item["name"] == "Mangalore Bun's (2)"
    assert item["price"] == 60.0
    assert item["description"] is None
    # Both kannadaName and kannada_name should be present
    assert "kannadaName" in item
    assert "kannada_name" in item
    # Dietary type
    assert item["is_veg"] is True
    assert item["dietary_type"] == "pure_veg"
    assert item["section_id"] == "bajji_pakoda_snacks"


def test_cart_rejects_uncatalogued_item_id():
    test_session = f"test_session_{uuid.uuid4()}"
    resp = client.post(
        "/cart/add",
        json={
            "item_id": "fake_uncatalogued_dish_123",
            "name": "Fabricated Dish",
            "price": 50.0,
            "quantity": 1,
            "session_id": test_session,
        },
    )
    # Must reject uncatalogued items
    assert resp.status_code in [400, 404]
    # Cart must remain empty
    cart_resp = client.get(f"/cart?session_id={test_session}")
    assert cart_resp.json()["itemCount"] == 0


def test_cart_ignores_client_supplied_price():
    test_session = f"test_session_{uuid.uuid4()}"
    # Ghee Plain Dosa authentic price is 70.0
    # Attempt to spoof price to 1.0
    resp = client.post(
        "/cart/add",
        json={
            "item_id": "ghee_plain_dosa",
            "name": "Ghee Plain Dosa",
            "price": 1.0,  # Client attempting to tamper price
            "quantity": 2,
            "session_id": test_session,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    item = data["cart"][0]
    assert item["price"] == 70.0  # Must be backend authoritative price
    assert item["subtotal"] == 140.0
    assert data["total"] == 140.0


def test_cart_rejects_invalid_quantities():
    test_session = f"test_session_{uuid.uuid4()}"

    # Negative quantity
    resp_neg = client.post(
        "/cart/add",
        json={"item_id": "ghee_plain_dosa", "quantity": -5, "session_id": test_session},
    )
    assert resp_neg.status_code == 400

    # Excessive quantity > 99
    resp_excess = client.post(
        "/cart/add",
        json={"item_id": "ghee_plain_dosa", "quantity": 105, "session_id": test_session},
    )
    assert resp_excess.status_code == 400


def test_cart_patch_set_quantity_and_invalid_actions():
    test_session = f"test_session_{uuid.uuid4()}"

    client.post(
        "/cart/add",
        json={"item_id": "ghee_plain_dosa", "quantity": 1, "session_id": test_session},
    )

    # set_quantity to 5
    resp_set = client.patch(
        "/cart/item",
        json={
            "item_id": "ghee_plain_dosa",
            "action": "set_quantity",
            "quantity": 5,
            "session_id": test_session,
        },
    )
    assert resp_set.status_code == 200
    assert resp_set.json()["itemCount"] == 5
    assert resp_set.json()["total"] == 350.0

    # set_quantity to 0 removes the item
    resp_zero = client.patch(
        "/cart/item",
        json={
            "item_id": "ghee_plain_dosa",
            "action": "set_quantity",
            "quantity": 0,
            "session_id": test_session,
        },
    )
    assert resp_zero.status_code == 200
    assert resp_zero.json()["itemCount"] == 0
    assert len(resp_zero.json()["cart"]) == 0

    # Unsupported action returns 400
    resp_bad = client.patch(
        "/cart/item",
        json={
            "item_id": "ghee_plain_dosa",
            "action": "invalid_magic_action",
            "session_id": test_session,
        },
    )
    assert resp_bad.status_code in [400, 404]


def test_cart_session_isolation():
    session_a = f"session_alpha_{uuid.uuid4()}"
    session_b = f"session_beta_{uuid.uuid4()}"

    # Add Dosa to session A
    client.post(
        "/cart/add",
        json={"item_id": "ghee_plain_dosa", "quantity": 1, "session_id": session_a},
    )

    # Add Bisi Bele Bath to session B
    client.post(
        "/cart/add",
        json={"item_id": "bisi_bele_bath", "quantity": 2, "session_id": session_b},
    )

    # Verify session A cart
    cart_a = client.get(f"/cart?session_id={session_a}").json()
    assert cart_a["itemCount"] == 1
    assert cart_a["total"] == 70.0
    assert cart_a["cart"][0]["id"] == "ghee_plain_dosa"

    # Verify session B cart
    cart_b = client.get(f"/cart?session_id={session_b}").json()
    assert cart_b["itemCount"] == 2
    assert cart_b["total"] == 120.0
    assert cart_b["cart"][0]["id"] == "bisi_bele_bath"

    # Clearing session A does not touch session B
    client.post(f"/cart/clear?session_id={session_a}")
    assert client.get(f"/cart?session_id={session_a}").json()["itemCount"] == 0
    assert client.get(f"/cart?session_id={session_b}").json()["itemCount"] == 2


def test_cart_session_header_resolution():
    session_hdr = f"session_hdr_{uuid.uuid4()}"

    # Add item using X-Session-ID header
    resp = client.post(
        "/cart/add",
        json={"item_id": "ghee_plain_dosa", "quantity": 1},
        headers={"X-Session-ID": session_hdr},
    )
    assert resp.status_code == 200
    assert resp.json()["itemCount"] == 1

    # Fetch using X-Session-ID header
    fetch_resp = client.get("/cart", headers={"X-Session-ID": session_hdr})
    assert fetch_resp.status_code == 200
    assert fetch_resp.json()["itemCount"] == 1


def test_cart_idempotency():
    test_session = f"test_session_{uuid.uuid4()}"
    idem_key = f"idem_key_{uuid.uuid4()}"

    # First add with idempotency key
    resp1 = client.post(
        "/cart/add",
        json={
            "item_id": "ghee_plain_dosa",
            "quantity": 1,
            "session_id": test_session,
            "idempotency_key": idem_key,
        },
    )
    assert resp1.status_code == 200
    assert resp1.json()["itemCount"] == 1

    # Exact retry with same idempotency key
    resp2 = client.post(
        "/cart/add",
        json={
            "item_id": "ghee_plain_dosa",
            "quantity": 1,
            "session_id": test_session,
            "idempotency_key": idem_key,
        },
    )
    assert resp2.status_code == 200
    # Must NOT increment quantity again
    assert resp2.json()["itemCount"] == 1


def test_cart_concurrency():
    import concurrent.futures

    test_session = f"test_session_concurrent_{uuid.uuid4()}"
    num_threads = 8
    dishes = ["ghee_plain_dosa", "bisi_bele_bath"]

    def add_concurrent_item(dish_id):
        return client.post(
            "/cart/add",
            json={
                "item_id": dish_id,
                "quantity": 1,
                "session_id": test_session,
            },
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(add_concurrent_item, dishes[i % 2]) for i in range(num_threads)]
        results = [f.result() for f in futures]

    for r in results:
        assert r.status_code == 200

    final_cart = client.get(f"/cart?session_id={test_session}").json()
    assert final_cart["itemCount"] == num_threads
    # 4 Dosa (70 * 4 = 280) + 4 Bisi Bele (60 * 4 = 240) = 520
    assert final_cart["total"] == 520.0


def test_order_unavailable_item_at_checkout_rollback():
    from api import ALL_ITEMS_BY_ID

    test_session = f"test_session_{uuid.uuid4()}"

    # Add available item
    client.post(
        "/cart/add",
        json={"item_id": "ghee_plain_dosa", "quantity": 1, "session_id": test_session},
    )

    # Temporarily mark item unavailable in database/catalogue
    orig_avail = ALL_ITEMS_BY_ID["ghee_plain_dosa"]["available"]
    ALL_ITEMS_BY_ID["ghee_plain_dosa"]["available"] = False

    try:
        # Checkout should fail with 400
        resp = client.post(
            "/order/complete",
            json={"session_id": test_session, "payment_method": "demo_upi"},
        )
        assert resp.status_code == 400
        assert "unavailable" in resp.json()["detail"].lower()

        # Transaction rollback: Cart must NOT be cleared!
        cart_after = client.get(f"/cart?session_id={test_session}").json()
        assert cart_after["itemCount"] == 1
    finally:
        # Restore original availability
        ALL_ITEMS_BY_ID["ghee_plain_dosa"]["available"] = orig_avail


def test_order_idempotency_avoids_duplicate_orders():
    test_session = f"test_session_{uuid.uuid4()}"
    idem_key = f"order_idem_{uuid.uuid4()}"

    client.post(
        "/cart/add",
        json={"item_id": "ghee_plain_dosa", "quantity": 1, "session_id": test_session},
    )

    # First checkout
    resp1 = client.post(
        "/order/complete",
        json={
            "session_id": test_session,
            "payment_method": "demo_upi",
            "idempotency_key": idem_key,
        },
    )
    assert resp1.status_code == 200
    order1 = resp1.json()["order"]

    # Second checkout with identical idempotency key
    resp2 = client.post(
        "/order/complete",
        json={
            "session_id": test_session,
            "payment_method": "demo_upi",
            "idempotency_key": idem_key,
        },
    )
    assert resp2.status_code == 200
    order2 = resp2.json()["order"]

    # Must return identical order without duplicating
    assert order1["order_id"] == order2["order_id"]
    assert order1["order_number"] == order2["order_number"]


def test_order_payment_status_distinction():
    # Demo UPI
    sess_upi = f"sess_upi_{uuid.uuid4()}"
    client.post("/cart/add", json={"item_id": "ghee_plain_dosa", "quantity": 1, "session_id": sess_upi})
    resp_upi = client.post("/order/complete", json={"session_id": sess_upi, "payment_method": "demo_upi"})
    assert resp_upi.status_code == 200
    order_upi = resp_upi.json()["order"]
    assert order_upi["payment_method"] == "demo_upi"
    assert order_upi["payment_status"] == "demo_completed"
    assert order_upi["status"] == "confirmed"

    # Demo Cash at counter
    sess_cash = f"sess_cash_{uuid.uuid4()}"
    client.post("/cart/add", json={"item_id": "ghee_plain_dosa", "quantity": 1, "session_id": sess_cash})
    resp_cash = client.post("/order/complete", json={"session_id": sess_cash, "payment_method": "demo_cash"})
    assert resp_cash.status_code == 200
    order_cash = resp_cash.json()["order"]
    assert order_cash["payment_method"] == "demo_cash"
    assert order_cash["payment_status"] == "payment_pending_at_counter"
    assert order_cash["status"] == "confirmed"


def test_order_retrieval_by_number_and_hash():
    test_session = f"test_session_{uuid.uuid4()}"
    client.post("/cart/add", json={"item_id": "ghee_plain_dosa", "quantity": 1, "session_id": test_session})
    resp = client.post("/order/complete", json={"session_id": test_session, "payment_method": "demo_upi"})
    assert resp.status_code == 200
    order = resp.json()["order"]
    num = order["order_number"]  # e.g. P-1234

    # Lookup by P-1234
    res1 = client.get(f"/order/{num}")
    assert res1.status_code == 200
    assert res1.json()["order"]["order_id"] == order["order_id"]

    # Lookup by #P-1234
    res2 = client.get(f"/order/%23{num}")
    assert res2.status_code == 200
    assert res2.json()["order"]["order_id"] == order["order_id"]

    # Nonexistent order returns 404
    res_bad = client.get("/order/non_existent_order_id_404")
    assert res_bad.status_code == 404


def test_conversation_greeting():
    resp = client.post("/message", json={"message": "namaskara", "session_id": "test_conv_1"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "greeting"
    assert "Namaskara" in data["message"]
    assert data["screen"] == "categories"


def test_conversation_add_to_cart_and_state_sync():
    sess = f"test_conv_add_{uuid.uuid4()}"
    resp = client.post("/message", json={"message": "add 2 ghee roast masala dosa", "session_id": sess})
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "add_to_cart"
    assert "Ghee Roast Masala Dosa" in data["message"]
    assert len(data["actions"]) == 1
    assert data["actions"][0]["type"] == "add_to_cart"
    assert data["data"]["cart_count"] == 2
    assert data["data"]["cart_total"] == 190.0

    # Direct cart endpoint verification
    cart_resp = client.get(f"/cart?session_id={sess}")
    assert cart_resp.status_code == 200
    cart_data = cart_resp.json()
    assert cart_data["itemCount"] == 2
    assert cart_data["total"] == 190.0


def test_conversation_clarify_ambiguous_dish():
    resp = client.post("/message", json={"message": "i want dosa", "session_id": "test_conv_clarify"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "clarify_item"
    assert "multiple options" in data["message"]


def test_conversation_dietary_query():
    resp = client.post("/message", json={"message": "is this pure veg?", "session_id": "test_conv_diet"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "dietary_query"
    assert "pure vegetarian" in data["message"].lower()


def test_conversation_checkout_intent():
    sess = f"test_conv_chk_{uuid.uuid4()}"
    client.post("/cart/add", json={"item_id": "bisi_bele_bath", "quantity": 1, "session_id": sess})

    resp = client.post("/message", json={"message": "proceed to checkout", "session_id": sess})
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "checkout"
    assert data["requires_confirmation"] is True
    assert data["screen"] == "cart"
    assert "totaling ₹60" in data["message"]


def test_tts_endpoint():
    resp = client.post("/tts", json={"text": "Welcome to The Atom Prasadam"})
    assert resp.status_code == 200
    assert resp.headers.get("content-type") == "audio/wav"
    assert resp.headers.get("x-tts-engine") == "kokoro"
    assert resp.headers.get("x-sample-rate") == "24000"
    assert resp.content[:4] == b"RIFF"
    assert len(resp.content) > 1000


def test_tts_status_endpoint():
    resp = client.get("/tts/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ready"] is True
    assert data["engine"] == "kokoro"
    assert data["sample_rate"] == 24000
    assert "af_heart" in data["supported_voices"]


def test_tts_empty_request_returns_400():
    resp = client.post("/tts", json={"text": ""})
    assert resp.status_code == 400


def test_stt_empty_file_handling():
    files = {"file": ("empty.webm", b"", "audio/webm")}
    resp = client.post("/stt", files=files)
    assert resp.status_code == 200
    assert resp.json()["success"] is False


def test_conversation_kannada_order():
    session_id = f"test-kannada-{uuid.uuid4()}"
    resp = client.post("/message", json={
        "message": "ondu masala dosa kodi",
        "session_id": session_id
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "add_to_cart"
    assert "Masala Dosa" in data["message"] or "ಮಸಾಲೆ ದೋಸೆ" in data["message"]
    # Check cart state
    cart = data["data"].get("cart", [])
    assert len(cart) == 1
    assert cart[0]["quantity"] == 1
    assert "masala_dosa" in cart[0]["id"]


def test_conversation_multi_turn_contextual_dialogue():
    session_id = f"test-multi-turn-{uuid.uuid4()}"

    # Turn 1: Customer asks to explore dosas
    t1 = client.post("/message", json={
        "message": "Show me dosa",
        "session_id": session_id
    }).json()
    assert t1["intent"] == "show_section"
    assert t1["screen"] == "menu_items"

    # Turn 2: Customer asks which one is cheaper
    t2 = client.post("/message", json={
        "message": "Which one is cheaper?",
        "session_id": session_id
    }).json()
    assert t2["intent"] == "price_comparison"
    assert "Ghee Plain Dosa" in t2["message"]
    assert "70" in t2["message"]

    # Turn 3: Customer says "Add that one"
    t3 = client.post("/message", json={
        "message": "Add that one",
        "session_id": session_id
    }).json()
    assert t3["intent"] == "add_to_cart"
    assert "Ghee Plain Dosa" in t3["message"]
    cart = t3["data"]["cart"]
    assert len(cart) == 1
    assert cart[0]["id"] == "ghee_plain_dosa"
    assert cart[0]["quantity"] == 1

    # Turn 4: Customer says "Make that two"
    t4 = client.post("/message", json={
        "message": "Make that two",
        "session_id": session_id
    }).json()
    assert t4["intent"] == "set_quantity"
    cart = t4["data"]["cart"]
    assert len(cart) == 1
    assert cart[0]["quantity"] == 2

    # Turn 5: Customer corrects "No, I meant one"
    t5 = client.post("/message", json={
        "message": "No, I meant one",
        "session_id": session_id
    }).json()
    assert t5["intent"] == "set_quantity"
    cart = t5["data"]["cart"]
    assert len(cart) == 1
    assert cart[0]["quantity"] == 1

    # Turn 6: Customer says "Remove the last item"
    t6 = client.post("/message", json={
        "message": "Remove the last item",
        "session_id": session_id
    }).json()
    assert t6["intent"] == "remove_from_cart"
    cart = t6["data"]["cart"]
    assert len(cart) == 0


def test_conversation_cancellation_preserves_cart():
    session_id = f"test-cancel-{uuid.uuid4()}"
    # Add an item first
    client.post("/message", json={
        "message": "Add Filter Coffee",
        "session_id": session_id
    })

    # Customer says "I want to pay"
    t1 = client.post("/message", json={
        "message": "I want to pay",
        "session_id": session_id
    }).json()
    assert t1["intent"] == "checkout"
    assert t1["requires_confirmation"] is True

    # Customer says "Cancel that"
    t2 = client.post("/message", json={
        "message": "Cancel that",
        "session_id": session_id
    }).json()
    assert t2["intent"] == "cancel_checkout"
    assert "Checkout cancelled" in t2["message"]

    # Cart must still be intact
    cart_resp = client.get(f"/cart?session_id={session_id}").json()
    assert cart_resp["itemCount"] == 1
    assert cart_resp["cart"][0]["id"] == "jaggery_coffee"


def test_conversation_recommendations_and_crispy():
    session_id = f"test-rec-{uuid.uuid4()}"

    # Crispy request
    t1 = client.post("/message", json={
        "message": "Show me something crispy",
        "session_id": session_id
    }).json()
    assert t1["intent"] == "recommendation"
    assert "Ghee Roast Masala Dosa" in t1["message"]
    assert "Maddur Vada" in t1["message"]

    # Recommendations request
    t2 = client.post("/message", json={
        "message": "What else do you recommend?",
        "session_id": session_id
    }).json()
    assert t2["intent"] == "recommendation"
    assert "Filter Coffee" in t2["message"]


def test_conversation_budget_filter():
    session_id = f"test-budget-{uuid.uuid4()}"
    t1 = client.post("/message", json={
        "message": "Show items under 50 rupees",
        "session_id": session_id
    }).json()
    assert t1["intent"] == "budget_filter"
    assert "under ₹50" in t1["message"]
    options = t1["data"].get("options", [])
    assert len(options) > 0
    for opt in options:
        assert opt["price"] <= 50.0


def test_conversation_jain_and_without_onion():
    session_id = f"test-jain-{uuid.uuid4()}"
    t1 = client.post("/message", json={
        "message": "Can I get that without onion?",
        "session_id": session_id
    }).json()
    assert t1["intent"] == "jain_query"
    assert "North Indian Jain Items" in t1["message"]
    assert t1["actions"][0]["payload"]["section_id"] == "north_indian_jain_items"


def test_conversation_navigation_and_change_order():
    session_id = f"test-nav-{uuid.uuid4()}"

    t1 = client.post("/message", json={
        "message": "Go back",
        "session_id": session_id
    }).json()
    assert t1["intent"] == "go_back"
    assert t1["screen"] == "previous"
    assert any(a.get("type") == "go_back" for a in t1.get("actions", []))

    t2 = client.post("/message", json={
        "message": "I want to change my order",
        "session_id": session_id
    }).json()
    assert t2["intent"] == "modify_order"
    assert t2["screen"] == "cart"


def test_conversation_unavailable_item_alternative():
    session_id = f"test-unavail-{uuid.uuid4()}"
    t1 = client.post("/message", json={
        "message": "I want idly 1 vada",
        "session_id": session_id
    }).json()
    assert t1["intent"] == "item_unavailable"
    assert "unavailable" in t1["message"]
    assert "individually" in t1["message"]


def test_conversation_clarification_resolution_and_ordinals():
    session_id = f"test-clarify-{uuid.uuid4()}"

    # Turn 1: ambiguous dish request triggers clarification
    t1 = client.post("/message", json={
        "message": "I want kofta",
        "session_id": session_id
    }).json()
    assert t1["intent"] == "clarify_item"
    assert "multiple options" in t1["message"]

    # Turn 2: resolve using ordinal ("The second one" -> Kadai Kofta)
    t2 = client.post("/message", json={
        "message": "The second one",
        "session_id": session_id
    }).json()
    assert t2["intent"] == "add_to_cart"
    assert "Kadai Kofta" in t2["message"]

    # Verify cart has Kadai Kofta
    cart_resp = client.get(f"/cart?session_id={session_id}").json()
    assert cart_resp["itemCount"] == 1
    assert cart_resp["cart"][0]["name"] == "Kadai Kofta"


def test_conversation_dish_price_inquiries():
    session_id = f"test-price-{uuid.uuid4()}"

    t1 = client.post("/message", json={
        "message": "How much is Ghee Plain Dosa?",
        "session_id": session_id
    }).json()
    assert t1["intent"] == "product_details"
    assert "70" in t1["message"]
    assert t1["actions"][0]["type"] == "open_product"

    t2 = client.post("/message", json={
        "message": "What is the price of Filter Coffee?",
        "session_id": session_id
    }).json()
    assert t2["intent"] == "product_details"
    assert "25" in t2["message"]


def test_conversation_faqs_payment_pickup_hours():
    session_id = f"test-faq-{uuid.uuid4()}"

    t_pay = client.post("/message", json={
        "message": "Can I pay with UPI?",
        "session_id": session_id
    }).json()
    assert t_pay["intent"] == "payment_info"
    assert "UPI" in t_pay["message"]
    assert "demonstrative" in t_pay["message"]

    t_pick = client.post("/message", json={
        "message": "Where do I collect my food?",
        "session_id": session_id
    }).json()
    assert t_pick["intent"] == "pickup_info"
    assert "pickup counter" in t_pick["message"]

    t_hrs = client.post("/message", json={
        "message": "What are your timings?",
        "session_id": session_id
    }).json()
    assert t_hrs["intent"] == "hours_info"
    assert "6:30 AM" in t_hrs["message"]


def test_conversation_kannada_numeral_orders():
    session_id = f"test-kn-num-{uuid.uuid4()}"

    t1 = client.post("/message", json={
        "message": "ondhu plate idli",
        "session_id": session_id
    }).json()
    assert t1["intent"] == "add_to_cart"
    assert "Idly" in t1["message"] or "ಇಡ್ಲಿ" in t1["message"]

    t2 = client.post("/message", json={
        "message": "eradu vada kodi",
        "session_id": session_id
    }).json()
    assert t2["intent"] == "add_to_cart"
    assert "2 Vada" in t2["message"] or "ಎರಡು ವಡೆ" in t2["message"]


def test_conversation_empty_cart_quantity_change_guard():
    session_id = f"test-empty-guard-{uuid.uuid4()}"

    t1 = client.post("/message", json={
        "message": "Make that two",
        "session_id": session_id
    }).json()
    assert t1["intent"] == "set_quantity_empty"
    assert "currently empty" in t1["message"]


def test_screen_sync_endpoint():
    session_id = f"test-screen-{uuid.uuid4()}"
    res1 = client.post("/screen", json={"screen": "categories", "section": None, "session_id": session_id})
    assert res1.status_code == 200
    d1 = res1.json()
    assert d1["success"] is True
    assert d1["screen"] == "categories"
    assert d1["seq"] == 1

    res2 = client.post("/screen", json={"screen": "menu_items", "section": "dose_special", "session_id": session_id})
    assert res2.status_code == 200
    d2 = res2.json()
    assert d2["screen"] == "menu_items"
    assert d2["section"] == "dose_special"
    assert d2["seq"] == 2


def test_voice_navigation_acceptance_scenarios():
    session_id = f"test-voice-nav-{uuid.uuid4()}"
    client.post("/session/start", json={"session_id": session_id})

    # 1. "Show me dosa" -> navigate to dose_special
    r1 = client.post("/message", json={"message": "Show me dosa", "session_id": session_id}).json()
    assert r1["screen"] == "menu_items"
    assert r1["intent"] == "show_section"
    assert any(a["type"] == "navigate" and a["payload"].get("section_id") == "dose_special" for a in r1["actions"])

    # 2. "Show South Indian breakfast" -> navigate to south_indian_breakfast
    r2 = client.post("/message", json={"message": "Show South Indian breakfast", "session_id": session_id}).json()
    assert r2["screen"] == "menu_items"
    assert r2["intent"] == "show_section"
    assert any(a["type"] == "navigate" and a["payload"].get("section_id") == "south_indian_breakfast" for a in r2["actions"])

    # 3. "Go back" -> screen previous, action go_back
    r3 = client.post("/message", json={"message": "Go back", "session_id": session_id}).json()
    assert r3["screen"] == "previous"
    assert r3["intent"] == "go_back"
    assert any(a["type"] == "go_back" for a in r3["actions"])

    # 4. "Show me masala dosa" -> product details for Ghee Roast Masala Dosa
    r4 = client.post("/message", json={"message": "Show me masala dosa", "session_id": session_id}).json()
    assert r4["screen"] == "product"
    assert r4["intent"] == "product_details"
    assert r4["actions"][0]["type"] == "open_product"
    assert r4["actions"][0]["payload"]["item"]["name"] == "Ghee Roast Masala Dosa"

    # 5. "How much is ghee plain dosa?" -> authoritative menu price and product details
    r5 = client.post("/message", json={"message": "How much is ghee plain dosa?", "session_id": session_id}).json()
    assert r5["screen"] == "product"
    assert r5["intent"] == "product_details"
    assert "₹70" in r5["message"] or "70" in r5["message"]
    assert r5["actions"][0]["payload"]["item"]["price"] == 70.0

    # 6. "Add two masala dosas" -> adds Ghee Roast Masala Dosa with quantity 2
    r6 = client.post("/message", json={"message": "Add two masala dosas", "session_id": session_id}).json()
    assert r6["intent"] == "add_to_cart"
    assert any(a["type"] == "add_to_cart" and a["payload"]["quantity"] == 2 for a in r6["actions"])

    # 7. "Remove the last item" -> removes from cart
    r7 = client.post("/message", json={"message": "Remove the last item", "session_id": session_id}).json()
    assert r7["screen"] == "cart"
    assert r7["intent"] == "remove_from_cart"
    assert any(a["type"] == "remove_from_cart" for a in r7["actions"])

    # 8. "What is in my cart?" -> cart screen and speak contents
    r8 = client.post("/message", json={"message": "What is in my cart?", "session_id": session_id}).json()
    assert r8["screen"] == "cart"
    assert r8["intent"] == "view_cart"
    assert any(a["type"] == "navigate" and a["payload"].get("screen") == "cart" for a in r8["actions"])


def test_contextual_price_comparison_and_quantity_anaphora():
    session_id = f"test-ctx-{uuid.uuid4()}"
    client.post("/session/start", json={"session_id": session_id})

    # Customer: "Show me dosa"
    t1 = client.post("/message", json={"message": "Show me dosa", "session_id": session_id}).json()
    assert t1["screen"] == "menu_items"
    assert t1["intent"] == "show_section"

    # Customer: "Which one is cheaper?"
    t2 = client.post("/message", json={"message": "Which one is cheaper?", "session_id": session_id}).json()
    assert t2["intent"] == "price_comparison"
    assert "Ghee Plain Dosa" in t2["message"]
    assert "₹70" in t2["message"]

    # Customer: "Add two"
    t3 = client.post("/message", json={"message": "Add two", "session_id": session_id}).json()
    assert t3["intent"] == "add_to_cart"
    assert any(a["type"] == "add_to_cart" and a["payload"]["quantity"] == 2 and a["payload"]["id"] == "ghee_plain_dosa" for a in t3["actions"])

    # Customer: "Go back"
    t4 = client.post("/message", json={"message": "Go back", "session_id": session_id}).json()
    assert t4["screen"] == "previous"
    assert t4["intent"] == "go_back"


if __name__ == "__main__":
    test_health_endpoint()
    test_start_session_contract()
    test_menu_sections_endpoint()
    test_section_items_integrity()
    test_menu_review_queue()
    test_menu_item_endpoint()
    test_cart_endpoints()
    test_cart_item_patch_endpoint()
    test_order_complete_endpoint()
    test_menu_invalid_section_id_returns_404()
    test_menu_item_optional_fields_and_aliases()
    test_cart_rejects_uncatalogued_item_id()
    test_cart_ignores_client_supplied_price()
    test_cart_rejects_invalid_quantities()
    test_cart_patch_set_quantity_and_invalid_actions()
    test_cart_session_isolation()
    test_cart_session_header_resolution()
    test_cart_idempotency()
    test_cart_concurrency()
    test_order_unavailable_item_at_checkout_rollback()
    test_order_idempotency_avoids_duplicate_orders()
    test_order_payment_status_distinction()
    test_order_retrieval_by_number_and_hash()
    test_conversation_greeting()
    test_conversation_add_to_cart_and_state_sync()
    test_conversation_clarify_ambiguous_dish()
    test_conversation_dietary_query()
    test_conversation_checkout_intent()
    test_tts_endpoint()
    test_tts_status_endpoint()
    test_tts_empty_request_returns_400()
    test_stt_empty_file_handling()
    test_conversation_kannada_order()
    test_conversation_multi_turn_contextual_dialogue()
    test_conversation_cancellation_preserves_cart()
    test_conversation_recommendations_and_crispy()
    test_conversation_budget_filter()
    test_conversation_jain_and_without_onion()
    test_conversation_navigation_and_change_order()
    test_conversation_unavailable_item_alternative()
    test_conversation_clarification_resolution_and_ordinals()
    test_conversation_dish_price_inquiries()
    test_conversation_faqs_payment_pickup_hours()
    test_conversation_kannada_numeral_orders()
    test_conversation_empty_cart_quantity_change_guard()
    test_screen_sync_endpoint()
    test_voice_navigation_acceptance_scenarios()
    test_contextual_price_comparison_and_quantity_anaphora()
    print("All backend tests passed successfully!")


