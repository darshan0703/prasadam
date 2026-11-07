"""
TheAtom Prasadam — Colloquial Kannada Transliteration & Linguistic Understanding Layer
Handles spoken Bengaluru Kannada, Kannada written in Latin script, phonetic normalization,
and natural language detection.
"""

import re
from typing import Tuple, Optional, Set

# Comprehensive lexicon of colloquial Bengaluru Kannada tokens written in Latin characters
KANNADA_COLLOQUIAL_TOKENS: Set[str] = {
    # Question & Inquiry words
    "yen", "yenu", "en", "enu", "yestu", "eshtu", "yeshtu", "yavdu", "yaavdu", "yavudhu",
    "yava", "yaava", "hege", "henge", "yavdadru", "enadru", "yenadru", "yavathu",
    
    # Existence & Availability words
    "ide", "idhe", "ideya", "idheya", "ideye", "idheye", "irutte", "irutta", "iruttu",
    "sigutta", "sigutte", "sigutteya", "sikkidheya", "untte", "unto", "untta", "iroru",
    
    # Action & Request words
    "kodi", "kodu", "beku", "bekittu", "beda", "saaku", "saku", "haaki", "haki",
    "serisu", "serisi", "madu", "maadi", "torisi", "torisu", "thorisi", "thorisu",
    "thodisi", "thodisu", "heli", "helu", "thinnoke", "tinnoke", "thinnakke", "tinnakke",
    "kudiyoke", "kudioke", "kudiyakke", "thago", "thagoli", "tagoli", "banni", "hogi", "hogu",
    "nodi", "nodona", "kelu", "keli",
    
    # Numerals & Quantifiers
    "ondu", "ondhu", "eradu", "yeradu", "mooru", "muru", "naalku", "nalku", "aidu", "aydu",
    "aaru", "elu", "entu", "ombattu", "hatthu", "innu", "innondu", "innondhu", "innondh",
    "ondhe", "bere", "swalpa", "kammi", "jaasti", "tumba", "hecchu",
    
    # Pronouns & Discourse Postpositions
    "nanage", "nange", "namage", "nimma", "nammalli", "nimalli", "alli", "ge",
    "jothe", "jothege", "kooda", "adanna", "adaralli", "idanna", "idaralli", "avu", "ivu",
    "dayavittu", "aytu", "aaythu", "ayt", "sari", "khachitha", "khachithapadisu",
    
    # Common Greetings
    "namaskara", "namaskaram", "namaste",
    
    # Food & Category descriptors in Kannada
    "thindi", "tindi", "upahara", "oota", "bhojana", "dose", "dosai", "kaapi", "chaha",
    "rotti", "bisi", "bele", "sihi", "tannage", "kharavada", "khara", "karam", "garigari",
    "kurukuru", "mane", "puta", "putakke", "hindakke", "hinde", "mundhe"
}

# Phonetic normalization map for colloquial Latin-Kannada words
PHONETIC_NORMALIZATION_MAP = [
    (r"\b(yen|yenu)\b", "en"),
    (r"\b(idhe|idheya|ideya|idheye|ideye)\b", "ide"),
    (r"\b(ondhu|ond)\b", "ondu"),
    (r"\b(yeradu)\b", "eradu"),
    (r"\b(muru)\b", "mooru"),
    (r"\b(nalku)\b", "naalku"),
    (r"\b(aydu)\b", "aidu"),
    (r"\b(thindi)\b", "tindi"),
    (r"\b(thorisi|thorisu|thodisi|thodisu)\b", "torisi"),
    (r"\b(thinnoke|tinnakke|thinnakke)\b", "tinnoke"),
    (r"\b(kudiyoke|kudiyakke)\b", "kudioke"),
    (r"\b(thagoli|tagoli)\b", "thago"),
    (r"\b(kaapi)\b", "coffee"),
    (r"\b(chaha|chai)\b", "tea"),
    (r"\b(dosai|dose)\b", "dosa"),
    (r"\b(rotti)\b", "roti"),
    (r"\b(sihi)\b", "sweet"),
    (r"\b(aaythu|aytu|ayt)\b", "aaytu"),
    (r"\b(saku)\b", "saaku"),
]


def is_kannada_input(text: str) -> bool:
    """
    Determines whether the input is Kannada (either Kannada Unicode script
    or colloquial Kannada transliterated into Latin characters).
    """
    if not text or not text.strip():
        return False
    
    # 1. Check for native Kannada Unicode script (\u0C80-\u0CFF)
    if re.search(r"[\u0C80-\u0CFF]", text):
        return True
    
    # 2. Check for colloquial Latin-script Kannada tokens
    tokens = set(re.findall(r"[a-z0-9]+", text.lower()))
    matches = tokens.intersection(KANNADA_COLLOQUIAL_TOKENS)
    if matches:
        return True
    
    # 3. Check for typical Kannada grammatical suffixes (e.g. -alli, -ge, -kodi, -beku)
    for token in tokens:
        if len(token) >= 5:
            if token.endswith("alli") or token.endswith("idhe") or token.endswith("ideya") or token.endswith("beku") or token.endswith("kodi"):
                return True
                
    return False


def normalize_kannada_transliteration(text: str) -> str:
    """
    Normalizes colloquial phonetic variations of Latin-script Kannada
    into canonical query terms for robust intent and category matching.
    """
    if not text:
        return ""
    
    cleaned = text.lower().strip()
    for pattern, replacement in PHONETIC_NORMALIZATION_MAP:
        cleaned = re.sub(pattern, replacement, cleaned)
        
    return cleaned


def classify_utterance_language(text: str, session_lang: str = "en") -> str:
    """
    Classifies the language of an utterance into:
    - 'kn': Pure Kannada (native script or Latin Kannada)
    - 'en': Pure English
    - 'mixed_kn_en': Code-switched Kannada with English food/restaurant vocabulary
    - 'unknown': Ambiguous or unclassifiable
    """
    if not text or not text.strip():
        return session_lang or "en"
        
    cleaned = text.strip()
    has_kannada_script = bool(re.search(r"[\u0C80-\u0CFF]", cleaned))
    
    tokens = set(re.findall(r"[a-z0-9]+", cleaned.lower()))
    kannada_token_matches = tokens.intersection(KANNADA_COLLOQUIAL_TOKENS)
    
    # Check English food/action words commonly mixed into spoken Kannada
    english_terms = {
        "sweet", "sweets", "coffee", "tea", "dosa", "masala", "idli", "vada", "order",
        "parcel", "menu", "section", "category", "cup", "plate", "change", "total",
        "checkout", "cart", "card", "cash", "upi", "light", "spicy", "breakfast", "lunch"
    }
    english_matches = tokens.intersection(english_terms)
    pure_english_indicators = {
        "can", "could", "would", "please", "what", "which", "where", "how", "much", "many",
        "i", "want", "like", "to", "have", "give", "me", "show", "is", "are", "there",
        "do", "you", "good", "morning", "evening", "take", "away"
    }
    pure_english_matches = tokens.intersection(pure_english_indicators)
    
    if has_kannada_script:
        if english_matches:
            return "mixed_kn_en"
        return "kn"
        
    if kannada_token_matches:
        if english_matches or pure_english_matches:
            return "mixed_kn_en"
        return "kn"
        
    if pure_english_matches or english_matches:
        return "en"
        
    return session_lang or "en"
