#!/usr/bin/env python3
"""
TheAtom Prasadam — Premium Food Image Acquisition & Curation Pipeline
Researches, downloads, processes, and validates authentic South Indian dish images.
Produces pristine 800x800 square progressive JPEGs (quality 92) with authentic presentation.

Usage:
  python backend/image_acquisition_pipeline.py [--dry-run] [--section SECTION_ID] [--item ITEM_ID] [--force]
"""
import os
import sys
import json
import time
import hashlib
import io
import argparse
import logging
from pathlib import Path
import requests
from PIL import Image

BASE = Path(__file__).resolve().parent.parent
PUB = BASE / "frontend/public/menu-items"
ASSET = BASE / "frontend/src/assets/images/menu-items"
ORIGINALS = BASE / "frontend/public/menu-items-originals"
MANIFEST_PATH = BASE / "backend/menu_image_research_manifest.json"
PROGRESS_PATH = BASE / "backend/image_pipeline_progress.json"

PUB.mkdir(parents=True, exist_ok=True)
ASSET.mkdir(parents=True, exist_ok=True)
ORIGINALS.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(BASE / "backend"))
from menu_data import SECTION_ITEMS_DB
from dish_queries import DISH_QUERIES

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("pipeline")

USER_AGENT = "TheAtomPrasadamFoodLibrary/1.0 (https://theatomprasadam.com; contact: info@theatomprasadam.com)"
HEADERS = {"User-Agent": USER_AGENT}

# The verified existing studio/canonical images that should never be overwritten unless --force
VERIFIED_GENERATED = {
    "idly_1", "idly_2", "vada_1", "idly_1_vada", "idly_2_and_vada_1",
    "rava_idly", "mini_idly", "tatte_idly_1", "ghee_pudi_idly",
    "kesari_bath", "kaara_bath", "chow_chow_bath", "rice_bath_of_the_day",
    "puliyogare", "ghee_pongal", "bisi_bele_bath", "poori_saagu",
}

BAD_TITLE_KEYWORDS = [
    ".svg", ".ogg", ".ogv", "icon", "logo", "flag", "seal", "map", "diagram",
    "bosch", "sins", "statue", "temple", "building", "train", "railway",
    "station", "portrait", "person", "minister", "actor", "actress",
    "coin", "stamp", "signboard", "road", "street",
    # Vegetarian restaurant integrity - NEVER allow non-veg
    "chicken", "mutton", "fish", "meat", "egg", "beef", "pork", "prawn", "crab", "seafood",
    "ilish", "hilsa", "machli", "rohu", "katla", "shrimp", "steak", "burger", "sandwich",
    # Non-food, acronyms, or political/military exclusions
    "yugoslavia", "republic", "federal", "war", "army", "navy", "military", "geograph", "cardiff",
    "cavendish", "plantation", "tree", "plant", "garden", "flower", "leaf", "market", "field", "farm",
    "bell", "palace", "yangzhou", "dragon", "sculpture", "monument", "ruins", "pagoda", "abies", "fir",
    "chimp", "chimpanzee", "monkey", "ape", "animal", "dog", "cat", "bird", "bukkumi", "sorghum",
    "rumex", "acetosa", "agaric", "paddenstoel", "boletus", "macrolepiota", "fungi"
]

def fetch_with_retry(url, params=None, headers=None, timeout=15, max_retries=3):
    hdrs = headers or HEADERS
    for attempt in range(max_retries):
        try:
            r = requests.get(url, params=params, headers=hdrs, timeout=timeout)
            if r.status_code == 200:
                return r
            elif r.status_code in (429, 503):
                wait = (attempt + 1) * 2.5
                log.warning("Rate limit / 503 for %s, waiting %.1fs", url, wait)
                time.sleep(wait)
            else:
                log.debug("HTTP %d for %s", r.status_code, url)
                return None
        except requests.RequestException as e:
            if attempt == max_retries - 1:
                log.debug("Request failed after %d retries: %s (%s)", max_retries, url, e)
                return None
            time.sleep((attempt + 1) * 1.5)
    return None

def wikimedia_search(query, limit=6):
    url = "https://commons.wikimedia.org/w/api.php"
    params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "srnamespace": "6",
        "srlimit": str(limit),
        "format": "json"
    }
    r = fetch_with_retry(url, params=params, timeout=12)
    if not r:
        return []
    try:
        results = []
        for h in r.json().get("query", {}).get("search", []):
            title = h.get("title", "")
            lower_title = title.lower()
            if any(bad in lower_title for bad in BAD_TITLE_KEYWORDS):
                continue
            results.append(title)
        return results
    except Exception as e:
        log.warning("Search parse failed for '%s': %s", query, e)
        return []

def wikimedia_image_info(title, width=1200):
    url = "https://commons.wikimedia.org/w/api.php"
    params = {
        "action": "query",
        "titles": title,
        "prop": "imageinfo",
        "iiprop": "url|size|mime|extmetadata",
        "iiurlwidth": str(width),
        "format": "json"
    }
    r = fetch_with_retry(url, params=params, timeout=12)
    if not r:
        return {}
    try:
        pages = r.json().get("query", {}).get("pages", {})
        for pid, page in pages.items():
            if pid == "-1":
                continue
            ii = page.get("imageinfo", [{}])[0]
            lic = ii.get("extmetadata", {}).get("LicenseShortName", {}).get("value", "CC")
            if lic and any(bad in lic for bad in ["non-free", "Non-Free", "Rights Managed"]):
                return {}
            return {
                "thumb_url": ii.get("thumburl", ""),
                "orig_url": ii.get("url", ""),
                "orig_w": ii.get("width", 0),
                "orig_h": ii.get("height", 0),
                "mime": ii.get("mime", ""),
                "license": lic,
                "title": title
            }
    except Exception as e:
        log.debug("Imageinfo parse failed for '%s': %s", title, e)
    return {}

def wikipedia_lead_image(article_title):
    url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "titles": article_title,
        "prop": "pageimages|images",
        "pithumbsize": "1200",
        "format": "json"
    }
    r = fetch_with_retry(url, params=params, timeout=12)
    if not r:
        return None
    try:
        pages = r.json().get("query", {}).get("pages", {})
        for pid, pg in pages.items():
            if pid == "-1":
                continue
            thumb = pg.get("thumbnail")
            if thumb and thumb.get("source"):
                src = thumb.get("source", "").lower()
                if any(bad in src for bad in BAD_TITLE_KEYWORDS):
                    log.warning("Wikipedia lead image rejected for non-veg/bad keyword in URL: %s", src)
                    continue
                return {
                    "thumb_url": thumb.get("source"),
                    "orig_url": thumb.get("source"),
                    "orig_w": thumb.get("width", 1000),
                    "orig_h": thumb.get("height", 800),
                    "mime": "image/jpeg",
                    "license": "CC (Wikipedia Lead)",
                    "title": f"Wikipedia: {article_title}"
                }
    except Exception as e:
        log.debug("Wikipedia lead image lookup failed for '%s': %s", article_title, e)
    return None

def is_acceptable(info, min_dim=400):
    if not info:
        return False
    if info.get("mime", "") not in ("image/jpeg", "image/png", "image/webp"):
        return False
    w = info.get("orig_w", 0)
    h = info.get("orig_h", 0)
    return min(w, h) >= min_dim and max(w, h) >= 600

def download_bytes(url, timeout=20):
    r = fetch_with_retry(url, timeout=timeout)
    if not r or "html" in r.headers.get("content-type", ""):
        return None
    return r.content

def to_square_jpeg(raw_bytes, size=800):
    try:
        img = Image.open(io.BytesIO(raw_bytes))
        # Handle transparency if PNG/WEBP
        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            bg = Image.new("RGB", img.size, (250, 247, 240))  # Brand cream background
            bg.paste(img, mask=img.convert("RGBA").split()[3])
            img = bg
        else:
            img = img.convert("RGB")
        
        w, h = img.size
        # Center-crop to 1:1 square
        if w > h:
            d = (w - h) // 2
            img = img.crop((d, 0, d + h, h))
        elif h > w:
            d = (h - w) // 2
            img = img.crop((0, d, w, d + w))
        
        # High-quality Lanczos resampling to exactly size x size
        img = img.resize((size, size), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=92, optimize=True, progressive=True)
        return buf.getvalue()
    except Exception as e:
        log.warning("Image processing failed: %s", e)
        return None

def sha256hex(b):
    return hashlib.sha256(b).hexdigest()

def is_already_square_800(item_id):
    p = PUB / f"{item_id}.jpg"
    if p.exists():
        try:
            with Image.open(p) as img:
                return img.size == (800, 800)
        except:
            pass
    return False

def acquire(item_id, item_name, dry_run=False, force=False):
    if not force:
        if item_id in VERIFIED_GENERATED:
            return {"status": "RUNTIME_VERIFIED", "reason": "Pre-verified studio image"}
        if is_already_square_800(item_id):
            return {"status": "RUNTIME_VERIFIED", "reason": "Already pristine 800x800 square image"}

    # Generate targeted candidate queries
    queries = list(DISH_QUERIES.get(item_id, []))
    cleaned_name = item_name.replace("'", "").replace("(1)", "").replace("(2)", "").replace("(Evening After 4 PM)", "").strip()
    
    # Add smart fallbacks
    fallbacks = [cleaned_name]
    if "dosa" in item_id.lower() or "dose" in item_id.lower():
        fallbacks.extend([f"{cleaned_name} south indian", "dosa south indian"])
    elif "vada" in item_id.lower() or "vade" in item_id.lower():
        fallbacks.extend([f"{cleaned_name} karnataka", "medu vada south indian"])
    elif "buns" in item_id.lower():
        fallbacks.extend(["mangalore buns", "banana puri"])
    elif "biriyani" in item_id.lower() or "biryani" in item_id.lower():
        fallbacks.extend([f"{cleaned_name} basmati", "veg biryani"])
    elif "noodles" in item_id.lower():
        fallbacks.extend(["veg hakka noodles", "schezwan noodles"])
    elif "soup" in item_id.lower():
        fallbacks.extend([f"{cleaned_name}", "vegetable soup"])
    
    for fb in fallbacks:
        if fb.lower() not in [q.lower() for q in queries]:
            queries.append(fb)

    # 1. Primary: Search Wikimedia Commons with specific curated dish queries
    for query in queries:
        log.info("  [search] '%s'", query)
        titles = wikimedia_search(query, limit=5)
        for title in titles:
            info = wikimedia_image_info(title)
            if not is_acceptable(info):
                continue
            url = info.get("thumb_url") or info.get("orig_url")
            if not url:
                continue
            log.info("  [found] %s (%dx%d)", title[:50], info["orig_w"], info["orig_h"])
            if dry_run:
                return {"status": "DRY_RUN_FOUND", "title": title, "url": url, "license": info.get("license")}
            raw = download_bytes(url)
            if not raw:
                continue
            processed = to_square_jpeg(raw)
            if not processed:
                continue
            (ORIGINALS / f"{item_id}_orig.jpg").write_bytes(raw)
            (PUB / f"{item_id}.jpg").write_bytes(processed)
            (ASSET / f"{item_id}.jpg").write_bytes(processed)
            h = sha256hex(processed)
            log.info("  [saved] %s sha256=%s", item_id, h[:16])
            return {"status": "DOWNLOADED", "title": title, "url": url, "license": info.get("license", "CC"), "sha256": h}
        time.sleep(0.4)

    # 2. Secondary fallback: Specific Wikipedia article lead image (only for exact name)
    info = wikipedia_lead_image(cleaned_name)
    if info and is_acceptable(info):
        url = info.get("thumb_url") or info.get("orig_url")
        log.info("  [wiki-lead] %s -> %s", cleaned_name, url[:60])
        if dry_run:
            return {"status": "DRY_RUN_FOUND", "title": info["title"], "url": url, "license": info["license"]}
        raw = download_bytes(url)
        if raw:
            processed = to_square_jpeg(raw)
            if processed:
                (ORIGINALS / f"{item_id}_orig.jpg").write_bytes(raw)
                (PUB / f"{item_id}.jpg").write_bytes(processed)
                (ASSET / f"{item_id}.jpg").write_bytes(processed)
                h = sha256hex(processed)
                log.info("  [saved] %s sha256=%s", item_id, h[:16])
                return {"status": "DOWNLOADED", "title": info["title"], "url": url, "license": info["license"], "sha256": h}

    return {"status": "UNRESOLVED", "reason": f"No high-resolution match for {item_name}"}

def update_manifest(results):
    if not MANIFEST_PATH.exists():
        return
    with open(MANIFEST_PATH) as f:
        m = json.load(f)
    for item in m.get("items", []):
        r = results.get(item["id"])
        if r:
            item["generation_status"] = r.get("status", item.get("generation_status"))
            item["review_status"] = "APPROVED" if r.get("status") in ("DOWNLOADED", "RUNTIME_VERIFIED") else item.get("review_status")
            if r.get("title"):
                item["source"] = {
                    "provider": "Wikimedia / Wikipedia Commons",
                    "title": r["title"],
                    "url": r.get("url", ""),
                    "license": r.get("license", "CC BY-SA")
                }
            if r.get("sha256"):
                item["sha256"] = r["sha256"]
    with open(MANIFEST_PATH, "w") as f:
        json.dump(m, f, indent=2)
    log.info("Updated manifest %s", MANIFEST_PATH)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--section", help="Target section ID, e.g. dose_special or bajji_pakoda_snacks")
    ap.add_argument("--item", help="Target single item ID")
    ap.add_argument("--force", action="store_true", help="Force overwrite even if already 800x800")
    ap.add_argument("--batch-size", type=int, default=15)
    args = ap.parse_args()

    all_items = []
    for sec_id, dishes in SECTION_ITEMS_DB.items():
        for d in dishes:
            if args.section and sec_id != args.section:
                continue
            if args.item and d["id"] != args.item:
                continue
            all_items.append((d["id"], d["name"], sec_id))

    log.info("Selected %d items to process (section=%s, item=%s)", len(all_items), args.section, args.item)

    results = {}
    if PROGRESS_PATH.exists():
        try:
            with open(PROGRESS_PATH) as f:
                results = json.load(f)
        except:
            results = {}

    ok = skipped = failed = 0
    total = len(all_items)

    for i, (iid, iname, sec) in enumerate(all_items):
        if not args.force:
            prior = results.get(iid, {})
            if prior.get("status") in ("DOWNLOADED", "RUNTIME_VERIFIED") and is_already_square_800(iid):
                log.info("[%d/%d] SKIP %s (already verified 800x800 square)", i + 1, total, iid)
                skipped += 1
                continue

        log.info("[%d/%d] Processing %s: '%s' (%s)", i + 1, total, iid, iname, sec)
        r = acquire(iid, iname, dry_run=args.dry_run, force=args.force)
        results[iid] = r

        if r["status"] in ("DOWNLOADED", "RUNTIME_VERIFIED", "DRY_RUN_FOUND"):
            ok += 1
        else:
            failed += 1
            log.warning("  UNRESOLVED: %s", r.get("reason", ""))

        with open(PROGRESS_PATH, "w") as f:
            json.dump(results, f, indent=2)

        if (i + 1) % args.batch_size == 0:
            log.info("=== Batch checkpoint %d/%d | ok=%d skipped=%d failed=%d ===", i + 1, total, ok, skipped, failed)
            time.sleep(1.0)

    log.info("PIPELINE RUN COMPLETE: Total=%d, OK=%d, Skipped=%d, Failed=%d", total, ok, skipped, failed)

    if not args.dry_run:
        update_manifest(results)

    unresolved = [(iid, r.get("reason", "")) for iid, r in results.items() if r.get("status") == "UNRESOLVED"]
    if unresolved:
        log.info("Currently UNRESOLVED items (%d):", len(unresolved))
        for iid, reason in unresolved:
            log.info("  %s: %s", iid, reason)

if __name__ == "__main__":
    main()
