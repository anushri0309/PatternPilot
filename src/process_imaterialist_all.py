"""
Process iMaterialist Fashion Attribute Dataset.
Extracts ALL attributes (not just neckline) for multi-task learning.
"""

import json
from pathlib import Path
import pandas as pd
from tqdm import tqdm
import shutil
from collections import defaultdict

# ============================================================
# CONFIGURATION
# ============================================================

DATA_DIR = Path("data/raw/imaterialist")
IMAGES_DIR = DATA_DIR / "images"
ANNOTATIONS_FILE = DATA_DIR / "validation.json"  # Change to "train.json" for training
LABEL_MAP_FILE = DATA_DIR / "label_map_228.xlsx"

PROCESSED_DIR = Path("data/processed_imaterialist_all")
IMAGES_OUT = PROCESSED_DIR / "images"
LABELS_OUT = PROCESSED_DIR / "labels.json"


# ============================================================
# THE CODE
# ============================================================

def load_label_map():
    """Load the label map and organize by task"""
    print("📂 Loading label map...")
    df = pd.read_excel(LABEL_MAP_FILE)

    # Organize labels by task
    task_labels = defaultdict(dict)
    label_to_task = {}

    for idx, row in df.iterrows():
        task_name = str(row['taskName']).lower()
        label_id = str(row['labelId'])
        label_name = str(row['labelName'])
        task_labels[task_name][label_id] = label_name
        label_to_task[label_id] = task_name

    # Print summary
    print(f"   Found {len(df)} total labels across {len(task_labels)} tasks:")
    for task, labels in task_labels.items():
        print(f"      {task}: {len(labels)} labels")

    return task_labels, label_to_task


def process_annotations():
    """Process annotations and extract ALL attributes"""

    print("\n📂 Loading annotations...")
    with open(ANNOTATIONS_FILE, 'r') as f:
        data = json.load(f)

    # Create image_id to image mapping
    image_lookup = {}
    for img in data['images']:
        image_lookup[str(img['imageId'])] = img['url']

    # Create image_id to labels mapping
    label_lookup = {}
    for ann in data['annotations']:
        image_id = str(ann['imageId'])
        label_ids = ann['labelId']  # This is a LIST!

        # If label_ids is a list, flatten it
        if isinstance(label_ids, list):
            # Some labels might be nested lists
            flat_labels = []
            for item in label_ids:
                if isinstance(item, list):
                    flat_labels.extend(item)
                else:
                    flat_labels.append(item)
            label_lookup[image_id] = [str(l) for l in flat_labels]
        else:
            label_lookup[image_id] = [str(label_ids)]

    print(f"   Images: {len(image_lookup)}")
    print(f"   Annotations: {len(label_lookup)}")

    # Load label map
    task_labels, label_to_task = load_label_map()

    # Get split name
    split_name = ANNOTATIONS_FILE.stem

    # Check downloaded images
    print(f"\n📁 Checking downloaded images...")
    downloaded_images = list(IMAGES_DIR.glob(f"{split_name}_*.jpg"))
    print(f"   Found {len(downloaded_images)} downloaded images")

    if len(downloaded_images) == 0:
        print("   ⚠️ No images found! Download images first.")
        return {}

    # Process each image
    labels = {}
    processed = 0
    skipped = 0
    attribute_counts = defaultdict(lambda: defaultdict(int))

    IMAGES_OUT.mkdir(parents=True, exist_ok=True)

    for img_path in tqdm(downloaded_images, desc="Processing"):
        # Extract image ID
        filename = img_path.stem
        image_id = filename.split('_')[1]

        # Get labels for this image
        label_ids = label_lookup.get(str(image_id), [])

        if not label_ids:
            skipped += 1
            continue

        # Map labels to tasks
        image_attributes = {}
        for label_id in label_ids:
            if label_id in label_to_task:
                task = label_to_task[label_id]
                # Get the label name from task_labels
                if task in task_labels and label_id in task_labels[task]:
                    label_name = task_labels[task][label_id]
                    # Only add if not already set (take first value)
                    if task not in image_attributes:
                        image_attributes[task] = label_name
                        attribute_counts[task][label_name] += 1

        if not image_attributes:
            skipped += 1
            continue

        # Copy image
        out_name = f"imat_{processed:06d}.jpg"
        shutil.copy(img_path, IMAGES_OUT / out_name)

        labels[out_name] = {
            "image_id": image_id,
            **image_attributes
        }
        processed += 1

    print(f"\n✅ Done!")
    print(f"   Images saved: {processed}")
    print(f"   Skipped: {skipped}")

    # Print attribute distribution
    print(f"\n📊 Attribute distribution:")
    for task, counts in attribute_counts.items():
        print(f"\n   {task.upper()}:")
        for attr, count in sorted(counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"      {attr}: {count}")

    return labels


def main():
    print("=" * 60)
    print("iMATERIALIST DATA PROCESSOR - ALL ATTRIBUTES")
    print("Extracting all attributes for multi-task learning")
    print("=" * 60)

    labels = process_annotations()

    import json as json_lib
    with open(LABELS_OUT, 'w') as f:
        json_lib.dump(labels, f, indent=2)

    print(f"\n💾 Labels saved to: {LABELS_OUT}")
    print(f"   Total images: {len(labels)}")


if __name__ == "__main__":
    main()
