"""
Prasadam Session-Isolated Conversation Memory Engine
Maintains structured dialogue history, entity references, pending clarifications,
and customer preferences across multiple turns for TheAtom Prasadam kiosk.
"""

import time
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class DialogueTurn(BaseModel):
    """Represents a single conversational turn between customer and cashier."""
    turn_index: int
    user_message: str
    assistant_response: str
    intent: Optional[str] = None
    target_id: Optional[str] = None
    action_type: Optional[str] = None
    timestamp: float = Field(default_factory=time.time)


class SessionConversationMemory:
    """
    Structured, session-isolated memory for a kiosk customer.
    Maintains a sliding window of raw dialogue turns combined with
    durable structured references so context survives multi-turn conversations.
    """

    def __init__(self, session_id: str, max_turns: int = 8):
        self.session_id: str = session_id
        self.max_turns: int = max_turns
        self.dialogue_turns: List[DialogueTurn] = []
        self.active_screen: str = "home"
        self.active_category: Optional[str] = None
        self.active_section: Optional[str] = None
        self.recently_discussed_items: List[str] = []  # Item IDs in recency order (max 6)
        self.selected_item_id: Optional[str] = None     # Current item in focus/detail
        self.last_added_item_id: Optional[str] = None   # Last item successfully added to cart
        self.last_action_result: Optional[Dict[str, Any]] = None
        self.pending_clarification: Optional[Dict[str, Any]] = None  # E.g. {"candidates": ["ghee_plain_dosa", "ghee_roast_masala_dosa"]}
        self.customer_preferences: Dict[str, Any] = {}  # E.g. {"dietary": "pure_veg", "likes_spicy": True}
        self.customer_language: str = "en"              # "en" or "kn"
        self.created_at: float = time.time()
        self.updated_at: float = time.time()

    def record_turn(
        self,
        user_message: Optional[str] = None,
        assistant_response: str = "",
        intent: Optional[str] = None,
        target_id: Optional[str] = None,
        action_type: Optional[str] = None,
        user_utterance: Optional[str] = None,
        actions: Optional[List[str]] = None,
        items_mentioned: Optional[List[str]] = None,
        **kwargs
    ) -> DialogueTurn:
        """Appends a completed dialogue turn and shifts window if max size exceeded."""
        msg = (user_utterance or user_message or "").strip()
        act = action_type or (actions[0] if actions else None)
        tgt = target_id or (items_mentioned[0] if items_mentioned else None)
        turn = DialogueTurn(
            turn_index=len(self.dialogue_turns) + 1,
            user_message=msg,
            assistant_response=assistant_response.strip(),
            intent=intent,
            target_id=tgt,
            action_type=act,
            timestamp=time.time(),
        )
        self.dialogue_turns.append(turn)
        if len(self.dialogue_turns) > self.max_turns:
            self.dialogue_turns = self.dialogue_turns[-self.max_turns:]
        if items_mentioned:
            for itm in items_mentioned:
                self.record_item_discussion(itm)
        self.updated_at = time.time()
        return turn

    def record_item_discussion(self, item_id: str):
        """Records an item ID as recently discussed, keeping the 6 most recent unique items."""
        if not item_id:
            return
        if item_id in self.recently_discussed_items:
            self.recently_discussed_items.remove(item_id)
        self.recently_discussed_items.insert(0, item_id)
        if len(self.recently_discussed_items) > 6:
            self.recently_discussed_items = self.recently_discussed_items[:6]
        self.selected_item_id = item_id
        self.updated_at = time.time()

    def set_last_added_item(self, item_id: str):
        """Tracks the last item successfully added to the customer's cart."""
        self.last_added_item_id = item_id
        self.record_item_discussion(item_id)
        self.updated_at = time.time()

    def set_pending_clarification(self, candidates: List[str], prompt: str = ""):
        """Sets a pending clarification choice with candidate IDs."""
        self.pending_clarification = {
            "candidates": candidates,
            "prompt": prompt,
            "timestamp": time.time(),
        }
        self.updated_at = time.time()

    def clear_pending_clarification(self):
        """Clears any active clarification request once resolved."""
        self.pending_clarification = None
        self.updated_at = time.time()

    def reset_session(self):
        """Clears all session-specific dialogue turns, items, and state."""
        self.dialogue_turns.clear()
        self.recently_discussed_items.clear()
        self.selected_item_id = None
        self.last_added_item_id = None
        self.pending_clarification = None
        self.pending_order_quantity = 1
        self.customer_preferences.clear()
        self.customer_language = "en"
        self.language_preference = "AUTO"
        self.active_screen = "home"
        self.active_category = None
        self.active_section = None
        self.updated_at = time.time()

    def update_screen_context(
        self,
        screen: str,
        category: Optional[str] = None,
        section: Optional[str] = None
    ):
        """Updates the visible kiosk navigation context."""
        if screen:
            self.active_screen = screen
        if category:
            self.active_category = category
        if section:
            self.active_section = section
        self.updated_at = time.time()

    def format_history_for_prompt(self, max_turns: int = 5) -> str:
        """
        Formats recent turns into a readable conversation transcript for LLM prompts.
        """
        turns = self.dialogue_turns[-max_turns:]
        if not turns:
            return "No previous dialogue in this session."

        formatted_lines = []
        for t in turns:
            formatted_lines.append(f"Customer: {t.user_message}")
            formatted_lines.append(f"Cashier: {t.assistant_response}")
        return "\n".join(formatted_lines)

    def to_state_dict(self) -> Dict[str, Any]:
        """Exports structured state dictionary for backward compatibility with legacy consumers."""
        return {
            "dialogue_turn": len(self.dialogue_turns),
            "last_intent": self.dialogue_turns[-1].intent if self.dialogue_turns else None,
            "last_mentioned_item": self.selected_item_id or (self.recently_discussed_items[0] if self.recently_discussed_items else None),
            "last_added_item_id": self.last_added_item_id,
            "last_added_items": [self.last_added_item_id] if self.last_added_item_id else [],
            "last_options_shown": [],
            "cheapest_item": None,
            "pending_clarification": self.pending_clarification.get("candidates") if self.pending_clarification else None,
            "pending_checkout": False,
            "rejected_items": [],
            "customer_language": self.customer_language,
            "conversational_phase": "browsing",
            "active_section": self.active_section,
            "active_category": self.active_category,
            "recently_discussed_items": list(self.recently_discussed_items),
        }


class ConversationMemoryManager:
    """Thread-safe manager holding isolated SessionConversationMemory instances."""

    def __init__(self):
        self._memories: Dict[str, SessionConversationMemory] = {}

    def get_memory(self, session_id: str) -> SessionConversationMemory:
        sid = (session_id or "default-kiosk-session").strip()
        if sid not in self._memories:
            self._memories[sid] = SessionConversationMemory(session_id=sid)
        return self._memories[sid]

    def reset_session(self, session_id: str):
        sid = (session_id or "").strip()
        if sid in self._memories:
            del self._memories[sid]

    def clear_all(self):
        self._memories.clear()


# Global Singleton Manager
memory_manager = ConversationMemoryManager()
