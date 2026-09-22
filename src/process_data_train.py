"""
Process the Fashionpedia TRAINING dataset (much larger!).
"""

import json
from pathlib import Path
from PIL import Image
import sys

# ============================================================
# CONFIGURATION - TRAINING DATA
# ============================================================

RAW_DATA_DIR = Path("data/raw")
IMAGES_DIR = RAW_DATA_DIR / "train"  # ← CHANGED: just "train", not "train2020/train"
ANNOTATIONS_FILE = RAW_DATA_DIR / "instances_attributes_train2020.json"

PROCESSED_DIR = Path("data/processed_train")
IMAGES_OUT = PROCESSED_DIR / "images"
LABELS_OUT = PROCESSED_DIR / "labels.json"

# What attributes we want to extract
TARGET_ATTRIBUTES = ["neckline type", "length", "silhouette", "waistline"]

# How many annotations to process (start with 20,000 for speed)
MAX_ANNOTATIONS = 20000  # ← Start with this, increase later
MAX_ANNOTATIONS = None  # Process ALL annotations (152,994)
# ============================================================
# THE CODE (same as before, but with training data)
# ============================================================

def clean_name(name):
    return name.replace(",", "").replace("(", "").replace(")", "").replace(" ", "_").lower()


def load_annotation_file():
    print(f"📂 Loading annotations from: {ANNOTATIONS_FILE}")
    with open(ANNOTATIONS_FILE, 'r') as f:
        return json.load(f)


def prepare_directories():
    IMAGES_OUT.mkdir(parents=True, exist_ok=True)
    print(f"✅ Created output directory: {IMAGES_OUT}")


def process_annotations(data):
    image_id_to_filename = {img["id"]: img["file_name"] for img in data["images"]}
    attr_id_to_info = {a["id"]: (a["name"], a["supercategory"]) for a in data["attributes"]}

    labels = {}
    processed = 0
    skipped = 0

    # Limit annotations for speed
    annotations = data["annotations"][:MAX_ANNOTATIONS]
    total = len(annotations)
    print(f"📊 Processing {total} annotations (out of {len(data['annotations'])})")

    for idx, ann in enumerate(annotations):
        if idx % 1000 == 0:
            print(f"   Processing: {idx}/{total}")

        image_id = ann["image_id"]
        filename = image_id_to_filename.get(image_id)
        if not filename:
            skipped += 1
            continue

        bbox = ann.get("bbox")
        if not bbox:
            skipped += 1
            continue

        attribute_ids = ann.get("attribute_ids", [])
        if not attribute_ids:
            skipped += 1
            continue

        # Extract attributes
        garment_labels = {}
        for attr_id in attribute_ids:
            attr_info = attr_id_to_info.get(attr_id)
            if not attr_info:
                continue
            attr_name, attr_supercategory = attr_info
            if attr_supercategory in TARGET_ATTRIBUTES:
                garment_labels[attr_supercategory] = clean_name(attr_name)

        if not garment_labels:
            skipped += 1
            continue

        image_path = IMAGES_DIR / filename
        if not image_path.exists():
            skipped += 1
            continue

        try:
            img = Image.open(image_path).convert("RGB")
            x, y, w, h = bbox
            crop = img.crop((x, y, x + w, y + h))

            out_name = f"train_{processed:06d}.jpg"
            crop.save(IMAGES_OUT / out_name)

            labels[out_name] = {
                "original_file": filename,
                **garment_labels,
                **{attr: garment_labels.get(attr, None) for attr in TARGET_ATTRIBUTES}
            }

            processed += 1

        except Exception as e:
            skipped += 1
            continue

    print(f"\n✅ Done!")
    print(f"   Images saved: {processed}")
    print(f"   Skipped: {skipped}")

    return labels


def save_labels(labels):
    import json as json_lib
    print(f"\n💾 Saving labels to: {LABELS_OUT}")
    with open(LABELS_OUT, 'w') as f:
        json_lib.dump(labels, f, indent=2)

    print(f"\n📊 Summary by attribute:")
    for attr in TARGET_ATTRIBUTES:
        count = sum(1 for v in labels.values() if v.get(attr) is not None)
        print(f"   {attr}: {count} labeled garments")


def main():
    print("=" * 60)
    print("FASHION DATA PROCESSOR - TRAINING SET")
    print("=" * 60)

    # Check if files exist
    print(f"\n📁 Checking paths...")
    print(f"   Images: {IMAGES_DIR}")
    print(f"   Exists: {IMAGES_DIR.exists()}")
    print(f"   Annotations: {ANNOTATIONS_FILE}")
    print(f"   Exists: {ANNOTATIONS_FILE.exists()}")

    if not ANNOTATIONS_FILE.exists():
        print(f"\n❌ ERROR: Annotation file not found at: {ANNOTATIONS_FILE}")
        print("   Please download instances_attributes_train2020.json")
        return

    if not IMAGES_DIR.exists():
        print(f"\n❌ ERROR: Images directory not found at: {IMAGES_DIR}")
        print("   Please download and extract train2020.zip")
        print(f"\n   Your current data/raw/ folder contains:")
        import os
        for item in os.listdir("data/raw"):
            print(f"     - {item}")
        return

    prepare_directories()
    data = load_annotation_file()
    labels = process_annotations(data)
    save_labels(labels)

    print("\n✅ Processing complete!")


if __name__ == "__main__":
    main()