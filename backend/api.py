import os
import re
import uuid
import time
import shutil
import tempfile
import subprocess
import threading
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv

# Authoritatively load environment variables before initializing adapters
load_dotenv(Path(__file__).parent / ".env")

logger = logging.getLogger("prasadam.api")

from fastapi import FastAPI, HTTPException, Header, Query, Request, Response, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from conversation_service import (
    PrasadamConversationEngine,
    MessageRequest,
    KioskResponse,
)
from tts_service import kokoro_tts


app = FastAPI(
    title="TheAtom Prasadam API",
    description="Backend service for Prasadam Hotel Restaurant Kiosk",
    version="1.0.0",
)

# Concurrency lock ensuring atomic operations across session carts and orders
cart_lock = threading.RLock()

# Enable CORS for local Vite dev server and kiosk instances
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount frontend public assets for direct static resolution
_public_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../frontend/public"))
if os.path.exists(_public_dir):
    _menu_items_dir = os.path.join(_public_dir, "menu-items")
    if os.path.exists(_menu_items_dir):
        app.mount("/menu-items", StaticFiles(directory=_menu_items_dir), name="menu-items")
    _sections_dir = os.path.join(_public_dir, "sections")
    if os.path.exists(_sections_dir):
        app.mount("/sections", StaticFiles(directory=_sections_dir), name="sections")

# Active session tracking
active_sessions: Dict[str, Dict[str, Any]] = {}

# Session carts tracking: session_id -> list of cart items
session_carts: Dict[str, List[Dict[str, Any]]] = {}

# Session screens tracking: session_id -> current screen, sequence, extra data
session_screens: Dict[str, Dict[str, Any]] = {}

# Completed order records tracking: order_id/order_number -> order dict
order_records: Dict[str, Dict[str, Any]] = {}

# Idempotency stores for cart and order operations
processed_cart_idempotency: Dict[str, Dict[str, Any]] = {}
processed_order_idempotency: Dict[str, Dict[str, Any]] = {}

# Canonical Menu Groups and 19 Original Sections (Source of Truth)
MENU_STRUCTURE = [
    {
        "id": "south_indian_favourites",
        "group_letter": "A",
        "title_english": "South Indian Favourites",
        "title_kannada": "ದಕ್ಷಿಣ ಭಾರತೀಯ ವಿಶೇಷಗಳು",
        "sections": [
            {"id": "south_indian_breakfast", "canonical_name": "South Indian Breakfast", "kannada_name": "ದಕ್ಷಿಣ ಭಾರತೀಯ ಉಪಾಹಾರ"},
            {"id": "dose_special", "canonical_name": "Dose Special", "kannada_name": "ದೋಸೆ ವಿಶೇಷ"},
            {"id": "bajji_pakoda_snacks", "canonical_name": "Bajji / Pakoda / Snacks", "kannada_name": "ಬಜ್ಜಿ / ಪಕೋಡ / ತಿಂಡಿಗಳು"}
        ]
    },
    {
        "id": "meals_and_rice",
        "group_letter": "B",
        "title_english": "Meals & Rice",
        "title_kannada": "ಊಟ ಮತ್ತು ಅನ್ನದ ವಿಧಗಳು",
        "sections": [
            {"id": "meals", "canonical_name": "Meals", "kannada_name": "ಊಟ"},
            {"id": "chinese_rice_items", "canonical_name": "Chinese Rice Items", "kannada_name": "ಚೈನೀಸ್ ರೈಸ್ ಐಟಮ್ಸ್"},
            {"id": "north_indian_rice_items", "canonical_name": "North Indian Rice Items", "kannada_name": "ಉತ್ತರ ಭಾರತೀಯ ರೈಸ್ ಐಟಮ್ಸ್"}
        ]
    },
    {
        "id": "curries_and_main_course",
        "group_letter": "C",
        "title_english": "Curries & Main Course",
        "title_kannada": "ಗ್ರೇವಿ ಮತ್ತು ಮುಖ್ಯ ಆಹಾರ",
        "sections": [
            {"id": "chinese_main_course", "canonical_name": "Chinese Main Course", "kannada_name": "ಚೈನೀಸ್ ಮೇನ್ ಕೋರ್ಸ್"},
            {"id": "dal_items", "canonical_name": "Dal Items", "kannada_name": "ದಾಲ್ ಐಟಮ್ಸ್"},
            {"id": "kadai", "canonical_name": "Kadai", "kannada_name": "ಕಡಾಯಿ"},
            {"id": "kofta", "canonical_name": "Kofta", "kannada_name": "ಕೊಫ್ತಾ"},
            {"id": "north_indian_jain_items", "canonical_name": "North Indian Jain Items", "kannada_name": "ಉತ್ತರ ಭಾರತೀಯ ಜೈನ್ ಐಟಮ್ಸ್"},
            {"id": "indian_curries", "canonical_name": "Indian Curries", "kannada_name": "ಭಾರತೀಯ ಮೇಲೋಗರಗಳು (ಕರಿಗಳು)"}
        ]
    },
    {
        "id": "starters_and_sides",
        "group_letter": "D",
        "title_english": "Starters & Sides",
        "title_kannada": "ಸ್ಟಾರ್ಟರ್ಸ್ ಮತ್ತು ಸೈಡ್ ಡಿಶ್ಗಳು",
        "sections": [
            {"id": "soups", "canonical_name": "Soups", "kannada_name": "ಸೂಪ್ಸ್"},
            {"id": "salads_raita_papad", "canonical_name": "Salads / Raita / Papad", "kannada_name": "ಸಲಾಡ್ಸ್ / ರಾಯ್ತ / ಹಪ್ಪಳ"},
            {"id": "chinese_starters", "canonical_name": "Chinese Starters", "kannada_name": "ಚೈನೀಸ್ ಸ್ಟಾರ್ಟರ್ಸ್"},
            {"id": "indian_starters", "canonical_name": "Indian Starters", "kannada_name": "ಭಾರತೀಯ ಸ್ಟಾರ್ಟರ್ಸ್"}
        ]
    },
    {
        "id": "indian_breads",
        "group_letter": "E",
        "title_english": "Indian Breads",
        "title_kannada": "ಭಾರತೀಯ ರೊಟ್ಟಿ ಮತ್ತು ಬ್ರೆಡ್",
        "sections": [
            {"id": "indian_breads_roti", "canonical_name": "Indian Breads / Roti", "kannada_name": "ಭಾರತೀಯ ರೊಟ್ಟಿ ಮತ್ತು ಬ್ರೆಡ್"}
        ]
    },
    {
        "id": "beverages_and_sweets",
        "group_letter": "F",
        "title_english": "Beverages & Sweets",
        "title_kannada": "ಪಾನೀಯಗಳು ಮತ್ತು ಸಿಹಿತಿಂಡಿಗಳು",
        "sections": [
            {"id": "hot_beverages", "canonical_name": "Hot Beverages", "kannada_name": "ಬಿಸಿ ಪಾನೀಯಗಳು"},
            {"id": "sweet_items", "canonical_name": "Sweet Items", "kannada_name": "ಸಿಹಿ ಪದಾರ್ಥಗಳು"}
        ]
    }
]

VALID_SECTION_IDS = {
    s["id"] for g in MENU_STRUCTURE for s in g["sections"]
}

# Production Section items store populated strictly with confirmed records
# Complete digitized menu catalogue containing 262 authentic items across 19 canonical sections
from menu_data import SECTION_ITEMS_DB, REVIEW_ITEMS_DB

# Indexed map of all authentic menu items by their stable ID
ALL_ITEMS_BY_ID: Dict[str, Dict[str, Any]] = {}
for sec_id, items in SECTION_ITEMS_DB.items():
    for item in items:
        ALL_ITEMS_BY_ID[item["id"]] = {
            "id": item["id"],
            "name": item["name"],
            "kannadaName": item.get("kannadaName"),
            "kannada_name": item.get("kannadaName"),
            "price": float(item["price"]),
            "category": item.get("category"),
            "section_id": sec_id,
            "description": item.get("description"),
            "image": item.get("image"),
            "is_veg": item.get("is_veg", True),
            "dietary_type": "pure_veg" if item.get("is_veg", True) else "non_veg",
            "available": bool(item.get("available", True)),
            "requires_review": bool(item.get("requires_review", False)),
        }

# Authoritative conversational AI engine grounded with canonical menu catalogue
conversation_engine = PrasadamConversationEngine(ALL_ITEMS_BY_ID, MENU_STRUCTURE)


def _resolve_session_id(
    body_session_id: Optional[str] = None,
    header_session_id: Optional[str] = None,
    query_session_id: Optional[str] = None
) -> str:
    """Helper to resolve session ownership consistently across body, header, and query."""
    sid = body_session_id or header_session_id or query_session_id or "default"
    return sid.strip() if sid else "default"


def _calculate_cart_totals(cart: List[Dict[str, Any]]) -> tuple[int, float]:
    """Computes authoritative item count and sum total from line items."""
    item_count = sum(int(i.get("quantity", 1)) for i in cart)
    total = round(sum(float(i.get("price", 0)) * int(i.get("quantity", 1)) for i in cart), 2)
    return item_count, total


class AddToCartItemRequest(BaseModel):
    item_id: str
    name: Optional[str] = None
    price: Optional[float] = None
    quantity: int = 1
    session_id: Optional[str] = None
    idempotency_key: Optional[str] = None


class UpdateCartItemRequest(BaseModel):
    item_id: Optional[str] = None
    item_index: Optional[int] = None
    action: str = "increase"  # "increase", "decrease", "remove", "set_quantity"
    quantity: Optional[int] = None
    session_id: Optional[str] = None
    idempotency_key: Optional[str] = None


class CompleteOrderRequest(BaseModel):
    session_id: Optional[str] = None
    payment_method: str = "demo_upi"
    customer_name: Optional[str] = None
    idempotency_key: Optional[str] = None


@app.get("/health")
def health():
    return {
        "status": "running",
        "service": "TheAtom Prasadam Kiosk API",
        "version": "1.0.0"
    }


@app.post("/session/start")
def start_session():
    """Initializes an authoritative isolated session for the kiosk customer."""
    session_id = str(uuid.uuid4())
    session_data = {
        "session_id": session_id,
        "created_at": time.time(),
        "status": "active"
    }
    with cart_lock:
        active_sessions[session_id] = session_data
        session_carts[session_id] = []
        session_screens[session_id] = {"screen": "home"}

    # Initialize fresh conversation memory and state isolated to this session
    conversation_engine.memory_manager.get_memory(session_id).reset_session()
    conversation_engine.session_states[session_id] = {
        "dialogue_turn": 0,
        "last_intent": None,
        "last_mentioned_item": None,
        "last_added_item_id": None,
        "last_added_items": [],
        "last_options_shown": [],
        "cheapest_item": None,
        "pending_clarification": None,
        "pending_order_quantity": 1,
        "pending_checkout": False,
        "rejected_items": [],
        "customer_language": "en",
        "language_preference": "AUTO",
        "conversational_phase": "browsing",
    }

    return {
        "success": True,
        "session_id": session_id,
        "message": "Welcome to Prasadam",
        "created_at": session_data["created_at"]
    }


@app.post("/screen")
def update_screen(request: Dict[str, Any], raw_req: Request = None):
    """
    Synchronizes the customer's current screen context with the backend
    so the conversational engine can contextualize natural spoken requests.
    """
    screen = request.get("screen")
    if not screen:
        return {"success": False, "message": "screen is required"}

    session_id = _resolve_session_id(
        body_session_id=request.get("session_id"),
        header_session_id=raw_req.headers.get("x-session-id") if raw_req else None,
    )

    with cart_lock:
        if session_id not in session_screens:
            session_screens[session_id] = {"screen": "home", "seq": 0, "extra": {}}

        last_seq = session_screens[session_id].get("seq", 0)
        seq = int(request.get("seq")) if request.get("seq") is not None else (last_seq + 1)
        if seq >= last_seq:
            session_screens[session_id] = {
                "screen": screen,
                "seq": seq,
                "extra": {k: v for k, v in request.items() if k not in {"screen", "seq", "session_id"}},
                "updated_at": time.time(),
            }
            is_valid = True
        else:
            is_valid = False

    if not is_valid:
        return {
            "success": True,
            "screen": session_screens[session_id].get("screen"),
            "stale_ignored": True,
            "seq": session_screens[session_id].get("seq"),
        }

    return {
        "success": True,
        "screen": screen,
        "seq": seq,
        **session_screens[session_id].get("extra", {}),
    }


@app.get("/menu/sections")
def get_menu_sections():
    """Returns the 6 macro groups and 19 canonical original sections."""
    total_sections = sum(len(g["sections"]) for g in MENU_STRUCTURE)
    return {
        "success": True,
        "total_groups": len(MENU_STRUCTURE),
        "total_sections": total_sections,
        "groups": MENU_STRUCTURE
    }


@app.get("/menu/sections/{section_id}/items")
def get_section_items(section_id: str):
    """
    Returns items for a canonical section.
    Respects menu data integrity: returns empty list with status if items are pending restaurant digitization.
    Raises 404 if section_id is not a canonical or digitized section.
    """
    if section_id not in VALID_SECTION_IDS and section_id not in SECTION_ITEMS_DB:
        raise HTTPException(status_code=404, detail=f"Menu section '{section_id}' not found")

    items = SECTION_ITEMS_DB.get(section_id, [])
    return {
        "success": True,
        "section_id": section_id,
        "item_count": len(items),
        "items": items,
        "status": "active" if items else "pending_restaurant_digitization"
    }


@app.get("/menu/review-queue")
def get_review_queue():
    """Returns dishes flagged for human review/confirmation separate from production catalogue."""
    total_review_items = sum(len(items) for items in REVIEW_ITEMS_DB.values())
    return {
        "success": True,
        "total_review_items": total_review_items,
        "sections_requiring_review": len(REVIEW_ITEMS_DB),
        "review_queue": REVIEW_ITEMS_DB
    }


@app.get("/menu/items/{item_id}")
def get_menu_item(item_id: str):
    """Returns a single menu item by stable ID from the authentic catalogue."""
    item = ALL_ITEMS_BY_ID.get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Menu item '{item_id}' not found")
    return {
        "success": True,
        "item": item
    }


@app.post("/cart/add")
def add_to_cart(
    request: AddToCartItemRequest,
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID")
):
    """
    Adds an item to the transactional session cart.
    Validates quantity, stable item ID, and live item availability.
    Prices are strictly derived from trusted menu data; client prices are rejected/ignored.
    Thread-safe and supports idempotency.
    """
    session_id = _resolve_session_id(request.session_id, x_session_id)

    with cart_lock:
        # Idempotency check
        if request.idempotency_key:
            idem_key = f"{session_id}:{request.idempotency_key}"
            if idem_key in processed_cart_idempotency:
                return processed_cart_idempotency[idem_key]

        # Validate requested quantity
        if not isinstance(request.quantity, int) or request.quantity <= 0:
            raise HTTPException(status_code=400, detail="Quantity must be at least 1")
        if request.quantity > 99:
            raise HTTPException(status_code=400, detail="Quantity cannot exceed 99 units")

        # Resolve product strictly by stable ID
        matched_item = ALL_ITEMS_BY_ID.get(request.item_id)
        if not matched_item:
            raise HTTPException(status_code=404, detail=f"Menu item '{request.item_id}' not found")

        # Validate availability according to authentic menu model
        if matched_item.get("available") is False or matched_item.get("requires_review") is True:
            raise HTTPException(status_code=400, detail=f"'{matched_item['name']}' is currently unavailable for order")

        if session_id not in session_carts:
            session_carts[session_id] = []

        cart = session_carts[session_id]
        existing_index = next((idx for idx, i in enumerate(cart) if i.get("id") == request.item_id), -1)

        authoritative_price = float(matched_item["price"])

        if existing_index > -1:
            new_qty = cart[existing_index].get("quantity", 1) + request.quantity
            if new_qty > 99:
                raise HTTPException(status_code=400, detail=f"Cannot add {request.quantity} more. Maximum limit of 99 reached for '{matched_item['name']}'")
            cart[existing_index]["quantity"] = new_qty
            cart[existing_index]["price"] = authoritative_price
            cart[existing_index]["subtotal"] = round(authoritative_price * new_qty, 2)
        else:
            cart.append({
                "id": matched_item["id"],
                "name": matched_item["name"],
                "kannadaName": matched_item.get("kannadaName"),
                "kannada_name": matched_item.get("kannada_name"),
                "price": authoritative_price,
                "quantity": request.quantity,
                "subtotal": round(authoritative_price * request.quantity, 2),
                "category": matched_item.get("category"),
                "image": matched_item.get("image"),
                "is_veg": matched_item.get("is_veg", True),
                "dietary_type": matched_item.get("dietary_type", "pure_veg"),
                "_uniqueKey": f"{request.item_id}_{int(time.time() * 1000)}"
            })

        item_count, total = _calculate_cart_totals(cart)
        response_data = {
            "success": True,
            "cart": list(cart),
            "itemCount": item_count,
            "total": total
        }

        if request.idempotency_key:
            idem_key = f"{session_id}:{request.idempotency_key}"
            processed_cart_idempotency[idem_key] = response_data

        return response_data


@app.get("/cart")
def get_cart(
    session_id: Optional[str] = Query(None),
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID")
):
    """Returns authoritative cart state for the requested session."""
    sid = _resolve_session_id(session_id, x_session_id)
    with cart_lock:
        cart_items = list(session_carts.get(sid, []))
        item_count, total = _calculate_cart_totals(cart_items)
        return {
            "cart": cart_items,
            "itemCount": item_count,
            "total": total
        }


@app.post("/cart/clear")
def clear_cart(
    session_id: Optional[str] = Query(None),
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID")
):
    """Authoritatively clears the cart for the specified session."""
    sid = _resolve_session_id(session_id, x_session_id)
    with cart_lock:
        session_carts[sid] = []
        return {
            "success": True,
            "message": "Cart cleared",
            "cart": [],
            "itemCount": 0,
            "total": 0.0
        }


@app.patch("/cart/item")
def update_cart_item(
    request: UpdateCartItemRequest,
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID")
):
    """
    Updates quantity or removes an item in the session cart.
    Supports targeting by item_id, _uniqueKey, or item_index.
    Thread-safe and validates live item availability for increases.
    """
    session_id = _resolve_session_id(request.session_id, x_session_id)

    with cart_lock:
        if session_id not in session_carts:
            session_carts[session_id] = []

        cart = session_carts[session_id]
        target_idx = -1

        if request.item_id:
            target_idx = next(
                (idx for idx, i in enumerate(cart) if i.get("id") == request.item_id or i.get("_uniqueKey") == request.item_id),
                -1
            )
        elif request.item_index is not None and 0 <= request.item_index < len(cart):
            target_idx = request.item_index

        if target_idx == -1:
            raise HTTPException(status_code=404, detail="Cart item not found")

        action = (request.action or "increase").lower()
        target_item = cart[target_idx]
        matched_db_item = ALL_ITEMS_BY_ID.get(target_item["id"])

        if action == "increase":
            if matched_db_item and (matched_db_item.get("available") is False or matched_db_item.get("requires_review") is True):
                raise HTTPException(status_code=400, detail=f"'{target_item['name']}' is currently unavailable for order")
            if target_item.get("quantity", 1) >= 99:
                raise HTTPException(status_code=400, detail="Maximum limit of 99 reached for this item")
            target_item["quantity"] = target_item.get("quantity", 1) + 1
            target_item["subtotal"] = round(target_item["price"] * target_item["quantity"], 2)

        elif action == "decrease":
            new_qty = target_item.get("quantity", 1) - 1
            if new_qty <= 0:
                cart.pop(target_idx)
            else:
                target_item["quantity"] = new_qty
                target_item["subtotal"] = round(target_item["price"] * new_qty, 2)

        elif action == "remove":
            cart.pop(target_idx)

        elif action == "set_quantity":
            if request.quantity is None or request.quantity < 0:
                raise HTTPException(status_code=400, detail="Quantity must be a non-negative integer")
            if request.quantity > 99:
                raise HTTPException(status_code=400, detail="Quantity cannot exceed 99 units")
            if request.quantity == 0:
                cart.pop(target_idx)
            else:
                if request.quantity > target_item.get("quantity", 1):
                    if matched_db_item and (matched_db_item.get("available") is False or matched_db_item.get("requires_review") is True):
                        raise HTTPException(status_code=400, detail=f"'{target_item['name']}' is currently unavailable for order")
                target_item["quantity"] = request.quantity
                target_item["subtotal"] = round(target_item["price"] * request.quantity, 2)

        else:
            raise HTTPException(status_code=400, detail=f"Unsupported action '{action}'")

        item_count, total = _calculate_cart_totals(cart)
        return {
            "success": True,
            "cart": list(cart),
            "itemCount": item_count,
            "total": total
        }


@app.post("/order/complete")
def complete_order(
    request: CompleteOrderRequest,
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID")
):
    """
    Completes order transaction.
    Validates non-empty cart, re-checks availability of all dishes against menu catalogue,
    calculates authoritative totals, creates persistent order record, records honest payment status,
    and clears the cart only upon successful transaction.
    Thread-safe and idempotent.
    """
    session_id = _resolve_session_id(request.session_id, x_session_id)

    with cart_lock:
        # Idempotency check: prevent duplicate orders
        if request.idempotency_key:
            idem_key = f"{session_id}:{request.idempotency_key}"
            if idem_key in processed_order_idempotency:
                return {
                    "success": True,
                    "message": "Order already completed (idempotent)",
                    "order": processed_order_idempotency[idem_key]
                }

        cart = session_carts.get(session_id, [])
        if not cart:
            raise HTTPException(status_code=400, detail="Cannot complete order with an empty cart")

        # Re-validate all dishes against authentic menu catalogue before checkout
        validated_items = []
        for line in cart:
            matched = ALL_ITEMS_BY_ID.get(line["id"])
            if not matched:
                raise HTTPException(
                    status_code=400,
                    detail=f"Item '{line.get('name', line['id'])}' is no longer in the menu catalogue. Please remove it from your tray."
                )
            if matched.get("available") is False or matched.get("requires_review") is True:
                raise HTTPException(
                    status_code=400,
                    detail=f"'{matched['name']}' is currently unavailable for order. Please remove it from your tray before completing order."
                )

            qty = int(line.get("quantity", 1))
            if qty <= 0:
                raise HTTPException(status_code=400, detail=f"Invalid quantity for item '{matched['name']}'")

            unit_price = float(matched["price"])
            validated_items.append({
                "id": matched["id"],
                "name": matched["name"],
                "kannadaName": matched.get("kannadaName"),
                "kannada_name": matched.get("kannada_name"),
                "price": unit_price,
                "quantity": qty,
                "subtotal": round(unit_price * qty, 2),
                "category": matched.get("category"),
                "image": matched.get("image"),
                "is_veg": matched.get("is_veg", True),
                "dietary_type": matched.get("dietary_type", "pure_veg"),
            })

        # Transactional calculations from authoritative data
        item_count = sum(i["quantity"] for i in validated_items)
        total = round(sum(i["subtotal"] for i in validated_items), 2)

        # Generate stable identifiers
        order_id = str(uuid.uuid4())
        random_num = int(time.time() * 1000) % 9000 + 1000
        order_number = f"P-{random_num}"

        # Honest payment status representation
        method = request.payment_method or "demo_upi"
        if method in ["demo_upi", "demo_card"]:
            payment_status = "demo_completed"
        elif method == "demo_cash":
            payment_status = "payment_pending_at_counter"
        else:
            payment_status = "pending"

        order_data = {
            "order_id": order_id,
            "order_number": order_number,
            "items": validated_items,
            "itemCount": item_count,
            "total": total,
            "payment_method": method,
            "payment_status": payment_status,
            "customer_name": request.customer_name or "Kiosk Guest",
            "status": "confirmed",
            "created_at": time.time(),
            "session_id": session_id,
        }

        # Persist to order store
        order_records[order_id] = order_data
        order_records[order_number] = order_data
        order_records[f"#{order_number}"] = order_data

        if request.idempotency_key:
            idem_key = f"{session_id}:{request.idempotency_key}"
            processed_order_idempotency[idem_key] = order_data

        # Clear the session cart authoritatively only AFTER successful order creation
        session_carts[session_id] = []

        return {
            "success": True,
            "message": "Order placed successfully",
            "order": order_data
        }


@app.get("/order/{order_id}")
def get_order(order_id: str):
    """Retrieves a persisted order record by UUID or user-friendly order number."""
    with cart_lock:
        order = order_records.get(order_id)
        if not order and order_id.startswith("#"):
            order = order_records.get(order_id[1:])
        elif not order and not order_id.startswith("#"):
            order = order_records.get(f"#{order_id}")

        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        return {
            "success": True,
            "order": order
        }


# ==============================================================================
# Conversational AI Assistant & Shared Dialogue Processing
# ==============================================================================

@app.post("/message", response_model=KioskResponse)
def handle_conversation_message(request: MessageRequest, raw_req: Request = None):
    """
    Central conversational processing endpoint shared by voice transcripts,
    typed messages, and quick suggestion chips. Grounded in canonical menu data.
    """
    session_id = _resolve_session_id(
        body_session_id=request.session_id,
        header_session_id=raw_req.headers.get("x-session-id") if raw_req else None,
    )

    tracked_screen = session_screens.get(session_id, {}).get("screen") or "home"
    current_screen = request.screen or tracked_screen
    logger.info("INCOMING /message request: session=%s, screen=%s, message='%s'", session_id, current_screen, request.message)

    with cart_lock:
        if request.cart_items is not None and not session_carts.get(session_id):
            session_carts[session_id] = list(request.cart_items)
        if session_id not in session_carts:
            session_carts[session_id] = []
        cart_items = list(request.cart_items) if request.cart_items is not None else list(session_carts[session_id])

    # Process conversational intent with the catalogue engine
    response = conversation_engine.process_message(
        message=request.message,
        session_id=session_id,
        current_screen=current_screen,
        cart_items=cart_items,
        orders_store=order_records,
        language_preference=request.language_preference,
    )
    logger.info("OUTGOING /message response: intent=%s, screen=%s, actions=%s, message='%s'", response.intent, response.screen, response.actions, response.message)


    # Execute validated cart mutations returned in actions
    with cart_lock:
        for action in response.actions:
            action_type = action.get("type")
            payload = action.get("payload", {})

            if action_type == "add_to_cart":
                item_id = payload.get("id")
                qty = int(payload.get("quantity", 1))
                if item_id in ALL_ITEMS_BY_ID:
                    cat_item = ALL_ITEMS_BY_ID[item_id]
                    existing = next(
                        (i for i in session_carts[session_id] if i.get("id") == item_id or i.get("item_id") == item_id),
                        None
                    )
                    if existing:
                        existing["quantity"] += qty
                        existing["subtotal"] = round(existing["quantity"] * cat_item["price"], 2)
                    else:
                        session_carts[session_id].append({
                            "id": item_id,
                            "item_id": item_id,
                            "name": cat_item["name"],
                            "price": cat_item["price"],
                            "quantity": qty,
                            "subtotal": round(cat_item["price"] * qty, 2),
                            "image": cat_item.get("image", ""),
                            "section_id": cat_item.get("section_id", ""),
                            "kannadaName": cat_item.get("kannadaName"),
                        })
            elif action_type == "remove_from_cart":
                rem_id = payload.get("id")
                session_carts[session_id] = [
                    i for i in session_carts[session_id]
                    if i.get("id") != rem_id and i.get("item_id") != rem_id
                ]
            elif action_type == "set_quantity":
                target_id = payload.get("id")
                new_qty = int(payload.get("quantity", 1))
                if new_qty <= 0:
                    session_carts[session_id] = [
                        i for i in session_carts[session_id]
                        if i.get("id") != target_id and i.get("item_id") != target_id
                    ]
                else:
                    for i in session_carts[session_id]:
                        if i.get("id") == target_id or i.get("item_id") == target_id:
                            i["quantity"] = new_qty
                            i["subtotal"] = round(new_qty * i["price"], 2)
                            break
            elif action_type == "clear_cart":
                session_carts[session_id] = []

        # Synchronize latest cart state in response data
        current_cart = list(session_carts[session_id])
        item_count, total = _calculate_cart_totals(current_cart)
        response.data["cart"] = current_cart
        response.data["cart_count"] = item_count
        response.data["cart_total"] = total

    return response


# ==============================================================================
# Text to Speech (TTS) Endpoint
# ==============================================================================

@app.post("/tts")
def text_to_speech(request: Dict[str, Any], raw_req: Request = None):
    """
    Synthesizes customer-facing response text into clean 24 kHz WAV audio.
    Automatically routes Kannada script to native Soumya (kn_IN) neural voice
    and English to Kokoro-82M.
    """
    text = (request.get("text") or "").strip()
    if not text:
        return Response(content=b"", media_type="audio/wav", status_code=400)

    voice = request.get("voice") or os.getenv("KOKORO_VOICE", "af_heart")
    speed = float(request.get("speed", 1.0))
    logger.info("INCOMING /tts request: voice=%s, text='%s'", voice, text[:80])


    try:
        meta = kokoro_tts.synthesize_with_metadata(text, voice=voice, speed=speed)
        audio_bytes = meta["audio_bytes"]
        return Response(
            content=audio_bytes,
            media_type="audio/wav",
            headers={
                "Content-Length": str(len(audio_bytes)),
                "X-TTS-Engine": meta["engine"],
                "X-TTS-Language": meta["lang"],
                "X-Sample-Rate": "24000",
                "Cache-Control": "no-cache",
            },
        )
    except Exception as e:
        print("TTS GENERATION ERROR:", repr(e))
        return Response(
            content=f"TTS generation failed: {e}".encode(),
            media_type="text/plain",
            status_code=500,
        )


@app.get("/tts/status")
def tts_status():
    """Returns TTS dual-engine status and diagnostic information."""
    return kokoro_tts.get_status()


# ==============================================================================
# Speech to Text (STT) Endpoint
# ==============================================================================

@app.post("/stt")
async def speech_to_text(file: UploadFile = File(...), language: Optional[str] = None, raw_req: Request = None):
    """
    Accepts uploaded audio blob from frontend microphone, converts via ffmpeg,
    and transcribes using multilingual Whisper (base) supporting Kannada and English.
    """
    ffmpeg_bin = shutil.which("ffmpeg") or "/Users/pavan/.local/bin/ffmpeg"
    whisper_bin = "/Users/pavan/Downloads/Intelligent-agent/backend/venv/bin/whisper"

    audio_bytes = await file.read()
    if not audio_bytes:
        return {"success": False, "message": "Uploaded audio file is empty."}

    orig_ext = "webm"
    if file.filename and "." in file.filename:
        orig_ext = file.filename.rsplit(".", 1)[-1].lower()
    elif file.content_type:
        if "mp4" in file.content_type:
            orig_ext = "mp4"
        elif "ogg" in file.content_type:
            orig_ext = "ogg"
        elif "wav" in file.content_type:
            orig_ext = "wav"

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            in_file = temp_path / f"raw_audio.{orig_ext}"
            wav_file = temp_path / "converted.wav"
            in_file.write_bytes(audio_bytes)

            # Convert uploaded audio to 16 kHz mono WAV
            conv = subprocess.run([
                ffmpeg_bin, "-y", "-i", str(in_file),
                "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(wav_file)
            ], capture_output=True, text=True, timeout=15)

            if conv.returncode != 0 or not wav_file.exists():
                return {"success": False, "message": f"Audio conversion failed: {conv.stderr}"}

            if os.path.exists(whisper_bin):
                cmd = [
                    whisper_bin, str(wav_file),
                    "--model", "base",
                    "--output_dir", str(temp_path),
                    "--output_format", "txt"
                ]
                if language:
                    cmd.extend(["--language", language])

                whisper_res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

                txt_file = temp_path / "converted.txt"
                if txt_file.exists():
                    transcript = txt_file.read_text().strip()
                    return {"success": True, "text": transcript}

            return {"success": False, "message": "Whisper transcription engine not available."}
    except subprocess.TimeoutExpired:
        return {"success": False, "message": "Speech recognition timed out."}
    except Exception as e:
        return {"success": False, "message": f"Speech recognition failed: {str(e)}"}


if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8002"))
    uvicorn.run("api:app", host=host, port=port, reload=True)
