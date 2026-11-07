"""
Prasadam Human-Like Cashier Response Generator (Stage B)
Generates warm, authentic, natural cashier responses grounded in validated
business action results, conversation memory, and real menu facts.
"""

import os
import json
import logging
import urllib.request
from typing import Dict, Any, Optional
from conversation_memory import SessionConversationMemory
from menu_knowledge import MenuKnowledge
from kannada_transliteration import is_kannada_input

logger = logging.getLogger("prasadam.cashier")

CASHIER_SYSTEM_PROMPT = """You are the friendly, attentive restaurant cashier at The Atom Prasadam, an authentic traditional South Indian pure vegetarian restaurant in Bengaluru.
You speak directly to the customer in a warm, polite, and confident tone.

PERSONALITY & RULES:
1. Speak in short, natural sentences (1-2 sentences, maximum 25 words).
2. NEVER use robotic formulas like "I'd be happy to help", "Sure thing!", or "How may I assist you today?".
3. Sound like a real South Indian cashier: hospitable, respectful, attentive, and knowledgeable about traditional food.
4. When confirming cart additions, mention the dish naturally (e.g., "Added two Masala Dosas to your order. Would you like a filter coffee with that?").
5. When answering questions, use ONLY the verified menu facts provided. Never invent ingredients, secret recipes, or fake popularity claims.
6. When an item is unavailable or unsupported (like pizza), explain politely and suggest an authentic option from our menu.
7. Ask at most ONE useful question, and only when natural.
8. If customer speaks Kannada, respond in authentic, natural Kannada (ಕನ್ನಡ). Otherwise respond in clear, warm English.
9. 10. In Kannada, always spell Masala Dosa as "ಮಸಾಲೆ ದೋಸೆ" (not ಮಸಲಾ).
Output ONLY the spoken response text. No prefixes, no markdown, no quotes.
"""


class CashierResponseGenerator:
    """Generates natural conversational cashier responses using Gemini / Groq with deterministic fallback."""

    def __init__(self, model_adapter=None):
        self.model_adapter = model_adapter
        self.gemini_key = (os.getenv("GEMINI_API_KEY") or "").strip()
        self.gemini_model = (os.getenv("GEMINI_MODEL") or "gemini-flash-lite-latest").strip()
        self.gemini_timeout = float(os.getenv("GEMINI_TIMEOUT", "15.0"))

    def generate_cashier_response(
        self,
        customer_message: Optional[str] = None,
        memory: Optional[Any] = None,
        action_result: Optional[Dict[str, Any]] = None,
        is_kn: bool = False,
        user_input: Optional[str] = None,
        **kwargs,
    ) -> str:
        """
        Main Stage B entrypoint: Synthesizes conversational response from
        customer utterance, validated action outcome, and memory context.
        """
        raw_msg = (customer_message or user_input or kwargs.get("message") or "").strip()
        action_result = action_result or {}

        target_lang = (kwargs.get("target_language") or kwargs.get("language") or "").strip().lower()
        if target_lang in ["kn", "kannada"] or target_lang.startswith("kn"):
            is_kn = True
        elif target_lang in ["en", "english"]:
            is_kn = False
        elif not is_kn:
            if hasattr(memory, "customer_language") and memory.customer_language == "kn":
                is_kn = True
            elif is_kannada_input(raw_msg):
                is_kn = True

        # Safely handle memory if None or dict
        if memory is None:
            memory = SessionConversationMemory(session_id="default")
        elif isinstance(memory, dict):
            state_dict = memory
            memory = SessionConversationMemory(session_id="default")
            memory.customer_language = state_dict.get("customer_language", "en")
            memory.active_section = state_dict.get("active_section")
            memory.active_category = state_dict.get("active_category")
            memory.selected_item_id = state_dict.get("last_mentioned_item")
            memory.last_added_item_id = state_dict.get("last_added_item_id")

        # Build context block
        history_text = memory.format_history_for_prompt(max_turns=4) if hasattr(memory, "format_history_for_prompt") else ""
        active_screen = getattr(memory, "active_screen", "home") or "home"
        active_sec = getattr(memory, "active_section", "None") or "None"
        mentioned_id = getattr(memory, "selected_item_id", None) or getattr(memory, "last_added_item_id", None)
        menu_facts = MenuKnowledge.get_grounded_facts_for_context(
            active_section=getattr(memory, "active_section", None),
            mentioned_item_id=mentioned_id,
            query=raw_msg
        )

        action_summary = self._summarize_action_result(action_result, is_kn)

        prompt = f"""{CASHIER_SYSTEM_PROMPT}

CONVERSATION SO FAR:
{history_text}

CURRENT CONTEXT:
- Customer just said: "{raw_msg}"
- Language: {'Kannada (kn)' if is_kn else 'English (en)'}
- Kiosk Screen: {active_screen} (Section: {active_sec})
- Verified Menu Facts:
{menu_facts}

BACKEND ACTION RESULT (SOURCE OF TRUTH):
{action_summary}

Generate the cashier's spoken response now:"""

        # Call Gemini if available
        if self.gemini_key and not self.gemini_key.startswith("your_"):
            try:
                spoken = self._call_gemini(prompt)
                if spoken and len(spoken.strip()) > 3:
                    # Clean up quotes or role markers if returned
                    clean_spoken = spoken.strip().strip('"').strip("'")
                    if clean_spoken.lower().startswith("cashier:"):
                        clean_spoken = clean_spoken[8:].strip()
                    clean_spoken = clean_spoken.replace("ಮಸಲಾ ದೋಸೆ", "ಮಸಾಲೆ ದೋಸೆ").replace("ಮಸಾಲ ದೋಸೆ", "ಮಸಾಲೆ ದೋಸೆ")
                    return clean_spoken
            except Exception as e:
                logger.warning("Stage B Gemini generation failed: %s. Using deterministic response.", e)

        # Deterministic Grounded Fallback
        det = self._generate_deterministic_response(raw_msg, action_result, is_kn)
        return det.replace("ಮಸಲಾ ದೋಸೆ", "ಮಸಾಲೆ ದೋಸೆ").replace("ಮಸಾಲ ದೋಸೆ", "ಮಸಾಲೆ ದೋಸೆ")

    def _call_gemini(self, prompt: str) -> Optional[str]:
        """Invokes Gemini generateContent for Stage B."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:generateContent?key={self.gemini_key}"
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 100,
            }
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=self.gemini_timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "").strip()
        return None

    def _summarize_action_result(self, res: Dict[str, Any], is_kn: bool) -> str:
        """Formats the validated backend result for prompt injection."""
        action = res.get("action") or res.get("action_type") or "unknown"
        status = res.get("status", "success")

        if action in ["add_to_cart", "add"]:
            name = res.get("item_name") or res.get("name") or res.get("item")
            qty = res.get("quantity", 1)
            price = res.get("item_price") or res.get("price", 0.0)
            total = res.get("cart_total", 0.0)
            count = res.get("cart_count", qty)
            return (
                f"ACTION EXECUTED: Successfully added {qty}x '{name}' (₹{price:.0f} each) to cart. "
                f"You MUST explicitly confirm adding '{name}' in your spoken reply! Cart total: ₹{total:.0f}."
            )

        if action in ["set_quantity", "update_quantity"]:
            name = res.get("item_name") or res.get("name") or res.get("item")
            qty = res.get("quantity", 1)
            total = res.get("cart_total", 0.0)
            return f"ACTION EXECUTED: Successfully updated '{name}' quantity to {qty}. Cart total: ₹{total:.0f}."

        if action in ["remove_from_cart", "remove"]:
            name = res.get("item_name") or res.get("name") or res.get("item", "item")
            return f"ACTION EXECUTED: Successfully removed '{name}' from cart."

        if action == "clear_cart":
            return "STATUS: Success. Cart cleared."

        if action == "show_section":
            sec_name = res.get("section_title") or res.get("section_id")
            avail = res.get("available_items") or []
            avail_str = f" Available dishes: {', '.join(avail[:4])}." if avail else ""
            return (
                f"STATUS: Customer asked about menu section '{sec_name}'.{avail_str} "
                f"Naturally offer these available dishes and ask which one they prefer! "
                f"Do NOT say 'Opening section' or 'Look at the screen'."
            )

        if action == "show_category":
            cat_name = res.get("category_title") or res.get("category_id")
            sec_list = res.get("sections") or []
            sec_str = f" Sections in this category: {', '.join(sec_list[:3])}." if sec_list else ""
            return (
                f"STATUS: Customer asked about menu category '{cat_name}'.{sec_str} "
                f"Naturally mention the available sections and ask what they would like to explore."
            )

        if action == "clarify":
            candidates = res.get("candidates", [])
            base = res.get("base_name", "this dish")
            return f"STATUS: Ambiguous dish. Multiple options exist for {base}: {', '.join(candidates)}."

        if action == "item_unavailable":
            name = res.get("item_name", "requested item")
            alt = res.get("alternative", "")
            return f"STATUS: Rejected. '{name}' is currently unavailable. Alternative: {alt}."

        if action == "unsupported_cuisine":
            item = res.get("item_name", "this item")
            return f"STATUS: Unsupported food. We do not serve '{item}' at this traditional South Indian restaurant. Recommend authentic items like dosas, bisi bele bath, or filter coffee."

        if action == "checkout":
            total = res.get("cart_total", 0.0)
            count = res.get("cart_count", 0)
            return f"STATUS: Checkout initiated for {count} items totaling ₹{total:.0f}. Awaiting confirmation."

        if action == "dietary_query":
            return "STATUS: Dietary confirmation. The Atom Prasadam is a 100% pure vegetarian restaurant with dedicated Jain preparation options."

        if action == "greeting":
            return "STATUS: Greeting customer at The Atom Prasadam."

        if action == "inquiry":
            info = res.get("info", "")
            return f"STATUS: Answered food inquiry. Details: {info}"

        return f"STATUS: {status}. Action: {action}."

    def _generate_deterministic_response(
        self,
        query: str,
        res: Dict[str, Any],
        is_kn: bool
    ) -> str:
        """Crisp, natural fallback response if LLM generation is unavailable."""
        action = res.get("action") or res.get("action_type") or "unknown"

        if action == "greeting":
            if is_kn:
                return "ನಮಸ್ಕಾರ! ದಿ ಆಟಂ ಪ್ರಸಾದಂಗೆ ಸುಸ್ವಾಗತ. ನಿಮಗೆ ಏನು ಬೇಕು? ಮಸಾಲೆ ದೋಸೆ, ಕಾಫಿ, ಅಥವಾ ಸಿಹಿ ತಿಂಡಿಗಳನ್ನು ಕೇಳಬಹುದು."
            return "Namaskara! Welcome to The Atom Prasadam. How may I serve you today? You can ask for our special dosas, filter coffee, sweets, or explore any section."

        if action == "dietary_query":
            if is_kn:
                return "ದಿ ಆಟಂ ಪ್ರಸಾದಂ ೧೦೦% ಶುದ್ಧ ಸಸ್ಯಾಹಾರಿ (Pure Vegetarian) ಉಪಹಾರ ಗೃಹ. ಯಾವುದೇ ಮಾಂಸಾಹಾರ ಅಥವಾ ಮೊಟ್ಟೆ ಬಳಸುವುದಿಲ್ಲ."
            return "The Atom Prasadam is a 100% pure vegetarian restaurant. All our preparations use pure ghee, fresh ingredients, and no non-veg or eggs."

        if action in ["add_to_cart", "add"]:
            name = res.get("item_name") or res.get("name") or res.get("item")
            qty = res.get("quantity", 1)
            q_str = f"{qty} " if qty > 1 else ""
            if is_kn:
                kn_name = res.get("kannada_name") or res.get("kannadaName") or name
                num_kn = {1: "ಒಂದು", 2: "ಎರಡು", 3: "ಮೂರು", 4: "ನಾಲ್ಕು", 5: "ಐದು"}.get(qty, str(qty))
                if qty > 1:
                    return f"ಆಯ್ತು! {num_kn} {kn_name}ಗಳನ್ನು ಕಾರ್ಟ್ಗೆ ಸೇರಿಸಿದ್ದೇನೆ."
                return f"ಆಯ್ತು! {num_kn} {kn_name} ಕಾರ್ಟ್ಗೆ ಸೇರಿಸಿದ್ದೇನೆ."
            return f"Sure, {q_str}{name} added to your tray."

        if action in ["set_quantity", "update_quantity"]:
            name = res.get("item_name") or res.get("name") or res.get("item")
            qty = res.get("quantity", 1)
            if is_kn:
                kn_name = res.get("kannada_name") or res.get("kannadaName") or name
                return f"ಆಯ್ತು, {kn_name} ಪ್ರಮಾಣ {qty}."
            return f"Sure, updated to {qty} {name}."

        if action in ["remove_from_cart", "remove"]:
            name = res.get("item_name") or res.get("name") or res.get("item", "item")
            if is_kn:
                return f"{name} ಅನ್ನು ತೆಗೆದುಹಾಕಲಾಗಿದೆ."
            return f"I have removed {name} from your cart."

        if action == "show_section":
            sec_id = res.get("section_id")
            title = res.get("section_title") or res.get("kannada_title") or "ವಿಭಾಗ"
            items = res.get("available_items") or []
            
            if sec_id == "sweet_items":
                if is_kn:
                    return "ಸ್ವೀಟ್ನಲ್ಲಿ ನಮ್ಮ ಹತ್ರ ಜಾಮೂನ್, ಕ್ಯಾರೆಟ್ ಹಲ್ವಾ, ಕಾಶಿ ಹಲ್ವಾ ಮತ್ತು ಹಾಲ್ ಬಾಯಿ ಇದೆ. ನಿಮಗೆ ಯಾವುದು ಬೇಕು?"
                return "In sweets we have Jamoon, Carrot Halwa, Kashi Halwa, and Hal Bai. Which one would you like?"
                
            if sec_id == "dose_special":
                if is_kn:
                    return "ನಮ್ಮಲ್ಲಿ ಮಸಾಲೆ ದೋಸೆ, ಸೆಟ್ ದೋಸೆ, ನೀರ್ ದೋಸೆ ಮತ್ತು ರವಾ ದೋಸೆ ಇದೆ. ನಿಮಗೆ ಯಾವುದು ಬೇಕು?"
                return "We have multiple options for dosa such as Masala Dosa, Set Dosa, Plain Dosa, and Rava Dosa. Which one would you prefer?"
                
            if sec_id == "south_indian_breakfast":
                if is_kn:
                    return "ಬೆಳಗಿನ ಉಪಾಹಾರಕ್ಕೆ ಇಡ್ಲಿ ವಡೆ, ಮಸಾಲೆ ದೋಸೆ, ಪೂರಿ ಸಾಗು ಮತ್ತು ಖಾರಾ ಬಾತ್ ರೆಡಿ ಇದೆ. ಏನು ತಗೋತೀರಾ?"
                return "For breakfast we have hot idlis, crispy vadas, fresh dosas, and poori saagu. What would you like to have?"
                
            if sec_id == "hot_beverages":
                if is_kn:
                    return "ಬಿಸಿ ಫಿಲ್ಟರ್ ಕಾಫಿ, ಟೀ, ಬಾದಾಮಿ ಹಾಲು ಮತ್ತು ಕಷಾಯ ಇದೆ. ಏನು ಕುಡಿತೀರಾ?"
                return "We have authentic Filter Coffee, Tea, and Badam Milk piping hot. What would you like?"
                
            if items:
                opts = ", ".join(items[:3])
                if is_kn:
                    kn_title = res.get("kannada_title") or title
                    return f"{kn_title}ದಲ್ಲಿ ನಮ್ಮ ಹತ್ರ {opts} ಇದೆ. ಏನು ಕೊಡ್ಲಿ?"
                return f"In {title} we have {opts}. Which one would you like?"
                
            if is_kn:
                return f"{title} ವಿಭಾಗದಲ್ಲಿ ಹಲವು ಉತ್ತಮ ಆಯ್ಕೆಗಳಿವೆ. ಯಾವುದು ಬೇಕು?"
            return f"Here are the options in {title}. What would you like?"

        if action == "show_category":
            cat_id = res.get("category_id")
            title = res.get("category_title") or "categories"
            
            if cat_id == "south_indian_favourites":
                if is_kn:
                    return "ದಕ್ಷಿಣ ಭಾರತೀಯ ತಿಂಡಿಗಳಲ್ಲಿ ನಮ್ಮಲ್ಲಿ ಉಪಾಹಾರ, ದೋಸೆ ವಿಶೇಷ ಮತ್ತು ಬಜ್ಜಿ ಬೋಂಡಾ ತಿಂಡಿಗಳಿವೆ. ಯಾವುದು ನೋಡೋಣ?"
                return "In South Indian Favourites we have our breakfast specials, signature dosas, and evening snacks. Which would you like to explore?"
                
            if cat_id == "meals_and_rice":
                if is_kn:
                    return "ಊಟ ಮತ್ತು ರೈಸ್ ವಿಭಾಗದಲ್ಲಿ ಸೌತ್ ಇಂಡಿಯನ್ ಮೀಲ್ಸ್, ಚೈನೀಸ್ ರೈಸ್ ಮತ್ತು ನಾರ್ತ್ ಇಂಡಿಯನ್ ರೈಸ್ ಐಟಮ್ಸ್ ಇವೆ. ಏನು ಕೊಡ್ಲಿ?"
                return "In Meals & Rice we have full South Indian Meals, Chinese Fried Rice, and North Indian Rice specialties. What are you in the mood for?"
                
            if cat_id == "beverages_and_sweets":
                if is_kn:
                    return "ನಮ್ಮಲ್ಲಿ ಬಿಸಿ ಪಾನೀಯಗಳು ಮತ್ತು ಸಿಹಿ ಪದಾರ್ಥಗಳು ಇವೆ. ಏನು ತಗೋತೀರಾ?"
                return "We have piping hot beverages and delicious sweets. What would you like?"
                
            if is_kn:
                return f"{title} ವಿಭಾಗದಲ್ಲಿ ಹಲವು ಬಗೆಯ ತಿಂಡಿಗಳಿವೆ. ಯಾವುದು ನೋಡೋಣ?"
            return f"In {title} we have several delicious dishes. Which would you like to see?"

        if action == "clarify":
            cands = res.get("candidate_names") or res.get("candidates") or []
            base = res.get("base_name") or "that"
            if cands:
                opts = ", ".join(cands[:3])
                if is_kn:
                    return f"ನಮ್ಮಲ್ಲಿ ಹಲವು ಆಯ್ಕೆಗಳಿವೆ: {opts}. ನಿಮಗೆ ಯಾವುದು ಬೇಕು?"
                return f"We have multiple options for {base} such as {opts}. Which one would you prefer?"
            if is_kn:
                return "ನಮ್ಮಲ್ಲಿ ಹಲವು ಆಯ್ಕೆಗಳಿವೆ. ದಯವಿಟ್ಟು ಯಾವ ಪದಾರ್ಥವೆಂದು ತಿಳಿಸಿ."
            return f"We have multiple options available. Which one would you like?"

        if action == "unsupported_cuisine":
            item = res.get("item_name", "that")
            if is_kn:
                return f"ಕ್ಷಮಿಸಿ, ನಮ್ಮಲ್ಲಿ {item} ಲಭ್ಯವಿಲ್ಲ. ನಾವು ಸಾಂಪ್ರದಾಯಿಕ ದಕ್ಷಿಣ ಭಾರತೀಯ ತಿಂಡಿಗಳಾದ ಮಸಾಲೆ ದೋಸೆ, ಇಡ್ಲಿ ವಡೆ, ಬಿಸಿ ಬೇಳೆ ಬಾತ್ ನೀಡುತ್ತೇವೆ."
            return f"We don't serve {item} here as we are an authentic South Indian pure vegetarian restaurant. May I suggest our crispy Masala Dosa, Bisi Bele Bath, or Filter Coffee?"

        if action == "item_unavailable":
            name = res.get("item_name", "That dish")
            alt = res.get("alternative", "")
            if is_kn:
                return f"ಕ್ಷಮಿಸಿ, {name} ಸದ್ಯಕ್ಕೆ ಲಭ್ಯವಿಲ್ಲ. {alt}"
            return f"Sorry, {name} is currently unavailable today. {alt}"

        if action == "checkout":
            total = res.get("cart_total", 0.0)
            count = res.get("cart_count", 0)
            if is_kn:
                return f"ನಿಮ್ಮ ಆರ್ಡರ್‌ನಲ್ಲಿ {count} ಪದಾರ್ಥಗಳಿವೆ, ಒಟ್ಟು ಮೊತ್ತ ₹{total:.0f}. ಖಚಿತಪಡಿಸುವುದೇ?"
            return f"Your cart has {count} item(s), totaling ₹{total:.0f}. Would you like to confirm and proceed to payment?"

        if action == "inquiry":
            info = res.get("info", "")
            if info:
                return info

        # Default friendly greeting or inquiry
        if is_kn:
            return "ನಮಸ್ಕಾರ! ನಿಮಗೆ ಏನು ಇಷ್ಟ? ಮಸಾಲೆ ದೋಸೆ, ಕಾಫಿ ಅಥವಾ ತಿಂಡಿಗಳನ್ನು ಕೇಳಬಹುದು."
        return "Namaskara! Welcome to The Atom Prasadam. How may I serve you today?"

