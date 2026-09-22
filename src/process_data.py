"""
Step 1: Process the Fashionpedia dataset.
This script crops garments from images using bounding boxes.
"""

import json
import shutil
from pathlib import Path
from PIL import Image
import sys

# ============================================================
# CONFIGURATION - CHANGE THESE PATHS IF NEEDED
# ============================================================

# Where your raw data is
RAW_DATA_DIR = Path("data/raw")
IMAGES_DIR = RAW_DATA_DIR / "val_test2020" / "test"
ANNOTATIONS_FILE = RAW_DATA_DIR / "instances_attributes_val2020.json"

# Where processed data will go
PROCESSED_DIR = Path("data/processed")
IMAGES_OUT = PROCESSED_DIR / "images"
LABELS_OUT = PROCESSED_DIR / "labels.json"

# What attributes we want to extract
TARGET_ATTRIBUTES = ["neckline type", "length", "silhouette", "waistline"]


# ============================================================
# THE CODE
# ============================================================

def clean_name(name):
    """Convert Fashionpedia names to clean folder names"""
    return name.replace(",", "").replace("(", "").replace(")", "").replace(" ", "_").lower()


def load_annotation_file():
    """Load the Fashionpedia annotation JSON"""
    print(f"📂 Loading annotations from: {ANNOTATIONS_FILE}")
    with open(ANNOTATIONS_FILE, 'r') as f:
        return json.load(f)


def prepare_directories():
    """Create all necessary directories"""
    IMAGES_OUT.mkdir(parents=True, exist_ok=True)
    print(f"✅ Created output directory: {IMAGES_OUT}")


def process_annotations(data):
    """
    Process all annotations:
    1. Find garments with our target attributes
    2. Crop them using bounding boxes
    3. Save the cropped images
    4. Save the labels
    """

    # Build lookup dictionaries (for speed)
    image_id_to_filename = {img["id"]: img["file_name"] for img in data["images"]}
    attr_id_to_info = {a["id"]: (a["name"], a["supercategory"]) for a in data["attributes"]}

    labels = {}
    processed = 0
    skipped = 0

    total_annotations = len(data["annotations"])
    print(f"📊 Total annotations to process: {total_annotations}")

    for idx, ann in enumerate(data["annotations"]):
        # Show progress
        if idx % 500 == 0:
            print(f"   Processing: {idx}/{total_annotations}")

        # Get the image filename
        image_id = ann["image_id"]
        filename = image_id_to_filename.get(image_id)
        if not filename:
            skipped += 1
            continue

        # Get the bounding box
        bbox = ann.get("bbox")
        if not bbox:
            skipped += 1
            continue

        # Check if this garment has any target attributes
        attribute_ids = ann.get("attribute_ids", [])
        if not attribute_ids:
            skipped += 1
            continue

        # Extract the attributes we care about
        garment_labels = {}
        for attr_id in attribute_ids:
            attr_info = attr_id_to_info.get(attr_id)
            if not attr_info:
                continue
            attr_name, attr_supercategory = attr_info
            if attr_supercategory in TARGET_ATTRIBUTES:
                garment_labels[attr_supercategory] = clean_name(attr_name)

        # Skip if no target attributes found
        if not garment_labels:
            skipped += 1
            continue

        # Load the image and crop
        image_path = IMAGES_DIR / filename
        if not image_path.exists():
            skipped += 1
            continue

        try:
            # Open and crop
            img = Image.open(image_path).convert("RGB")
            x, y, w, h = bbox
            crop = img.crop((x, y, x + w, y + h))

            # Save the cropped image
            out_name = f"img_{processed:06d}.jpg"
            crop.save(IMAGES_OUT / out_name)

            # Save the labels
            labels[out_name] = {
                "original_file": filename,
                **garment_labels,
                # Fill in missing attributes with None
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
    """Save labels to JSON file"""
    import json as json_lib
    print(f"\n💾 Saving labels to: {LABELS_OUT}")
    with open(LABELS_OUT, 'w') as f:
        json_lib.dump(labels, f, indent=2)

    # Print summary
    print(f"\n📊 Summary by attribute:")
    for attr in TARGET_ATTRIBUTES:
        count = sum(1 for v in labels.values() if v.get(attr) is not None)
        print(f"   {attr}: {count} labeled garments")


def main():
    print("=" * 60)
    print("FASHION DATA PROCESSOR")
    print("=" * 60)

    # 1. Check if files exist
    if not ANNOTATIONS_FILE.exists():
        print(f"❌ ERROR: Annotation file not found at: {ANNOTATIONS_FILE}")
        print("   Please make sure you downloaded the annotation file.")
        return

    if not IMAGES_DIR.exists():
        print(f"❌ ERROR: Images directory not found at: {IMAGES_DIR}")
        print("   Please make sure you extracted the images.")
        return

    # 2. Prepare directories
    prepare_directories()

    # 3. Load data
    data = load_annotation_file()

    # 4. Process annotations
    labels = process_annotations(data)

    # 5. Save labels
    save_labels(labels)

    print("\n✅ Processing complete!")
    print(f"   Processed images: {len(labels)}")
    print(f"   Location: {IMAGES_OUT}")


if __name__ == "__main__":
    main()