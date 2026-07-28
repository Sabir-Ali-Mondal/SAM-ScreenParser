"""
 DUPLICATE REMOVER - element_dataset.json

 Last element_dataset.json ::
============================================================
  SUMMARY
============================================================
  Original entries:    5552
  Invalid removed:     0
  Duplicates removed:  424
  Final unique:        5128
  Unique types:        42
============================================================
"""


import json
import os
import time
from collections import Counter

FILE_PATH = r"D:\Projects\SAM-ScreenParser\element_dataset.json"
OUTPUT_PATH = r"D:\Projects\SAM-ScreenParser\element_dataset_clean.json"

def main():
    print("=" * 60)
    print("  DUPLICATE REMOVER - element_dataset.json")
    print("=" * 60)

    if not os.path.exists(FILE_PATH):
        print(f"[ERROR] File not found: {FILE_PATH}")
        return

    file_size = os.path.getsize(FILE_PATH)
    print(f"\n[INFO] File: {FILE_PATH}")
    print(f"[INFO] Size: {file_size / 1024:.1f} KB")

    print("\n[STEP 1] Loading JSON...")
    start = time.time()
    with open(FILE_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    load_time = time.time() - start
    print(f"[OK] Loaded {len(data)} entries in {load_time:.2f}s")

    print("\n[STEP 2] Checking for invalid entries...")
    invalid = 0
    valid_entries = []
    for i, entry in enumerate(data):
        if not isinstance(entry, dict):
            invalid += 1
            continue
        if "name" not in entry or "type" not in entry:
            invalid += 1
            continue
        if not isinstance(entry["name"], str) or not isinstance(entry["type"], str):
            invalid += 1
            continue
        if entry["name"].strip() == "":
            invalid += 1
            continue
        valid_entries.append(entry)
    print(f"[OK] Valid: {len(valid_entries)} | Invalid removed: {invalid}")

    print("\n[STEP 3] Normalizing names (lowercase, strip)...")
    for entry in valid_entries:
        entry["name"] = entry["name"].strip().lower()
        entry["type"] = entry["type"].strip().lower()
    print("[OK] Done")

    print("\n[STEP 4] Removing duplicates (by name)...")
    seen = {}
    unique = []
    duplicates = 0
    dup_examples = []

    for entry in valid_entries:
        key = entry["name"]
        if key in seen:
            duplicates += 1
            if len(dup_examples) < 10:
                dup_examples.append(key)
        else:
            seen[key] = entry
            unique.append(entry)

    print(f"[OK] Unique: {len(unique)} | Duplicates removed: {duplicates}")
    if dup_examples:
        print(f"[INFO] Sample duplicates: {dup_examples}")

    print("\n[STEP 5] Type distribution:")
    type_counts = Counter(e["type"] for e in unique)
    for t, c in type_counts.most_common():
        bar = "█" * (c // 20)
        print(f"  {t:<20} {c:>5}  {bar}")

    print(f"\n[STEP 6] Saving to: {OUTPUT_PATH}")
    start = time.time()
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(unique, f, indent=2, ensure_ascii=False)
    save_time = time.time() - start
    out_size = os.path.getsize(OUTPUT_PATH)
    print(f"[OK] Saved {len(unique)} entries in {save_time:.2f}s")
    print(f"[OK] Output size: {out_size / 1024:.1f} KB")

    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    print(f"  Original entries:    {len(data)}")
    print(f"  Invalid removed:     {invalid}")
    print(f"  Duplicates removed:  {duplicates}")
    print(f"  Final unique:        {len(unique)}")
    print(f"  Unique types:        {len(type_counts)}")
    print("=" * 60)

if __name__ == "__main__":
    main()
