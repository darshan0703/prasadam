"""
Prasadam Intent & Action Schemas
Defines structured intent representations based on Intelligent-agent patterns.
"""

from typing import Optional, Literal, Dict, Any, List
from pydantic import BaseModel, Field


class OrderIntent(BaseModel):
    """
    Structured interpretation of customer request returned by LLM Intent Classifier.
    Grounded in canonical category, subcategory, and menu item IDs.
    """
    action: str = "unknown"
    # Supported canonical actions:
    # "show_category", "show_subcategory", "show_section",
    # "ask_about_menu", "search_menu_item", "show_product", "product_details",
    # "add_to_cart", "remove_from_cart", "replace_item", "modify_order", "set_quantity",
    # "navigate_back", "go_back", "navigate_home", "view_cart", "checkout",
    # "clarify", "clarify_item", "greeting", "cancel",
    # "beverage_inquiry", "pairing_recommendation", "recommend_light",
    # "general_food_inquiry", "dosa_varieties", "finish_order", "other", "unknown"

    intent_type: str = "inquiry"       # "action", "inquiry", "correction", "clarification", "chit_chat"
    target_type: Optional[str] = None  # "category", "subcategory", "item", "none"
    target_id: Optional[str] = None    # Canonical ID (e.g. "south_indian_favourites", "dose_special", "ghee_roast_masala_dosa")
    category: Optional[str] = None     # Canonical category ID
    section_id: Optional[str] = None   # Canonical section ID
    item_name: Optional[str] = None    # Customer-specified or resolved item name
    quantity: int = 1
    language: str = "en"               # "kn" (Kannada) or "en" (English)
    detected_language: str = "en"      # "en", "kn", "mixed_kn_en", "unknown"
    confidence: float = 1.0
    clarification_required: bool = False
    clarification_question: Optional[str] = None
    candidate_item_ids: List[str] = Field(default_factory=list)
    resolved_from_context: bool = False
    response_text: Optional[str] = None
    response_kn: Optional[str] = None
    response_en: Optional[str] = None
    raw_response: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
