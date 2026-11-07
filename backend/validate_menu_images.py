#!/usr/bin/env python3
"""
Prasadam Kiosk Menu & Image Pipeline Automated Validation Suite
Audits every active menu item, image resolution, file hashes, and visual assets.
"""
import os
import sys
import json
import hashlib
from PIL import Image

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PUB_MENU_ITEMS = os.path.join(BASE_DIR, "frontend/public/menu-items")
ASSET_MENU_ITEMS = os.path.join(BASE_DIR, "frontend/src/assets/images/menu-items")

# Add backend directory to sys.path
sys.path.insert(0, os.path.join(BASE_DIR, "backend"))
from menu_data import SECTION_ITEMS_DB, REVIEW_ITEMS_DB

def audit_menu_images():
    print("==================================================================")
    print("PRASADAM RESTAURANT MENU IMAGE PIPELINE AUDIT")
    print("==================================================================")
    
    total_sections = len(SECTION_ITEMS_DB)
    total_items = sum(len(items) for items in SECTION_ITEMS_DB.values())
    
    print(f"Total Canonical Sections: {total_sections}")
    print(f"Total Menu Dishes: {total_items}")
    
    image_paths = []
    missing_paths = []
    file_hashes = {}
    duplicate_hashes = {}
    corrupted_images = []
    review_items = []
    
    for sec_id, dishes in SECTION_ITEMS_DB.items():
        for item in dishes:
            item_id = item["id"]
            img_rel = item.get("image")
            
            if item.get("requires_review"):
                review_items.append((sec_id, item["name"], item.get("review_reason", "Review flagged")))
            
            if not img_rel:
                missing_paths.append((sec_id, item_id, "No image property"))
                continue
                
            image_paths.append(img_rel)
            
            # Check public and asset copies
            file_name = os.path.basename(img_rel)
            pub_file = os.path.join(PUB_MENU_ITEMS, file_name)
            asset_file = os.path.join(ASSET_MENU_ITEMS, file_name)
            
            if not os.path.exists(pub_file):
                missing_paths.append((sec_id, item_id, f"Missing in public: {pub_file}"))
                continue
                
            if not os.path.exists(asset_file):
                missing_paths.append((sec_id, item_id, f"Missing in assets: {asset_file}"))
                continue
                
            # Verify file integrity with PIL
            try:
                with Image.open(pub_file) as im:
                    w, h = im.size
                    if w < 400 or h < 250:
                        corrupted_images.append((item_id, f"Undersized image: {w}x{h}"))
            except Exception as e:
                corrupted_images.append((item_id, str(e)))
                continue
                
            # Compute SHA-256
            with open(pub_file, "rb") as f:
                h = hashlib.sha256(f.read()).hexdigest()
                
            if h in file_hashes:
                duplicate_hashes[item_id] = (file_hashes[h], h[:12])
            else:
                file_hashes[h] = item_id

    # Duplicate image path assignments
    duplicate_assignments = [p for p in image_paths if image_paths.count(p) > 1]
    duplicate_assignments = list(set(duplicate_assignments))
    
    print("\n--- AUDIT RESULTS ---")
    print(f"1. Total Active Menu Items:            {total_items}")
    print(f"2. Items with Valid Image Paths:       {len(image_paths)}")
    print(f"3. Missing Image Paths:                {len(missing_paths)}")
    print(f"4. Duplicate Image Assignments:        {len(duplicate_assignments)}")
    print(f"5. Total Unique Image File Hashes:     {len(file_hashes)}")
    print(f"6. Duplicate File Hashes:              {len(duplicate_hashes)}")
    print(f"7. Corrupted/Unreadable Images:        {len(corrupted_images)}")
    print(f"8. Review Quarantined Items:           {len(review_items)}")

    if review_items:
        print("\nReview Quarantined Items:")
        for sec, name, reason in review_items:
            print(f"  • [{sec}] {name}: {reason}")

    if missing_paths:
        print("\nERROR: Missing Image Paths:")
        for m in missing_paths:
            print(f"  • {m}")
            
    if duplicate_hashes:
        print("\nERROR: Duplicate File Hashes Detected:")
        for item, (orig, h) in duplicate_hashes.items():
            print(f"  • {item} has identical hash {h} to {orig}")
            
    if duplicate_assignments:
        print("\nERROR: Duplicate Image Path Assignments:")
        for d in duplicate_assignments:
            print(f"  • {d}")

    # Assertions
    assert len(missing_paths) == 0, f"Found {len(missing_paths)} missing images"
    assert len(duplicate_hashes) == 0, f"Found {len(duplicate_hashes)} duplicate file hashes"
    assert len(duplicate_assignments) == 0, f"Found {len(duplicate_assignments)} duplicate path assignments"
    assert len(corrupted_images) == 0, f"Found {len(corrupted_images)} corrupted images"
    assert total_items == 262, f"Expected 262 items, got {total_items}"
    assert len(file_hashes) == 262, f"Expected 262 unique hashes, got {len(file_hashes)}"

    # Check Queue File
    queue_file = os.path.join(BASE_DIR, "backend/menu_item_generation_queue.json")
    if os.path.exists(queue_file):
        with open(queue_file, "r") as qf:
            qdata = json.load(qf)
            meta = qdata.get("metadata", {})
            summary = meta.get("status_summary", {})
            print("\n--- RESUMABLE QUEUE LIFECYCLE AUDIT ---")
            for st, cnt in summary.items():
                if cnt > 0:
                    print(f"  • {st:25}: {cnt}")
            blocker = meta.get("upstream_api_blocker", {})
            if blocker:
                print(f"  • Upstream API Status  : {blocker.get('status')} ({blocker.get('error_code')})")
                print(f"  • Quota Reset Timestamp: {blocker.get('quota_reset_timestamp')}")

    print("\nALL AUDIT CHECKS PASSED PERFECTLY (100% UNIQUE DEDICATED DISH IMAGES)!")
    return True

if __name__ == "__main__":
    audit_menu_images()
