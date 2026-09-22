"""
Process iMaterialist Fashion Attribute Dataset.
Processes BOTH validation and training sets.
Extracts all attributes.
"""

import json
from pathlib import Path
from PIL import Image
import pandas as pd
from tqdm import tqdm
import shutil
from collections import defaultdict

# ============================================================
# CONFIGURATION
# ============================================================

DATA_DIR = Path("data/raw/imaterialist")
IMAGES_DIR = DATA_DIR / "images"
LABEL_MAP_FILE = DATA_DIR / "label_map_228.xlsx"

PROCESSED_DIR = Path("data/processed_imaterialist_combined")
IMAGES_OUT = PROCESSED_DIR / "images"
LABELS_OUT = PROCESSED_DIR / "labels.json"

# Process BOTH splits
SPLITS = ["validation", "train"]


# ============================================================
# THE CODE
# ============================================================

def load_label_map():
    """Load the label map"""
    print("📂 Loading label map...")
    df = pd.read_excel(LABEL_MAP_FILE)

    task_labels = defaultdict(dict)
    label_to_task = {}

    for idx, row in df.iterrows():
        task_name = str(row['taskName']).lower()
        label_id = str(row['labelId'])
        label_name = str(row['labelName'])
        task_labels[task_name][label_id] = label_name
        label_to_task[label_id] = task_name

    print(f"   Tasks: {list(task_labels.keys())}")
    return task_labels, label_to_task


def process_split(split_name, task_labels, label_to_task, all_labels):
    """Process a single split (validation or train)"""
    print(f"\n{'=' * 60}")
    print(f"Processing: {split_name}")
    print(f"{'=' * 60}")

    json_file = DATA_DIR / f"{split_name}.json"

    if not json_file.exists():
        print(f"   ⚠️ Not found: {json_file}")
        return all_labels

    print(f"📂 Loading: {json_file}")
    with open(json_file, 'r') as f:
        data = json.load(f)

    label_lookup = defaultdict(list)
    for ann in data['annotations']:
        image_id = str(ann['imageId'])
        label_ids = ann['labelId']
        if isinstance(label_ids, list):
            label_lookup[image_id] = [str(l) for l in label_ids]
        else:
            label_lookup[image_id] = [str(label_ids)]

    downloaded = list(IMAGES_DIR.glob(f"{split_name}_*.jpg"))
    print(f"📸 Found {len(downloaded)} downloaded images")

    processed = 0
    skipped = 0

    IMAGES_OUT.mkdir(parents=True, exist_ok=True)

    for img_path in tqdm(downloaded, desc=f"Processing {split_name}"):
        image_id = img_path.stem.split('_', 1)[1]

        label_ids = label_lookup.get(image_id, [])
        if not label_ids:
            skipped += 1
            continue

        image_attributes = {}
        for label_id in label_ids:
            if label_id in label_to_task:
                task = label_to_task[label_id]
                if task in task_labels and label_id in task_labels[task]:
                    label_name = task_labels[task][label_id]
                    if task not in image_attributes:
                        image_attributes[task] = label_name

        if not image_attributes:
            skipped += 1
            continue

        out_name = f"{split_name[:3]}_{processed:06d}.jpg"
        shutil.copy(img_path, IMAGES_OUT / out_name)

        all_labels[out_name] = {
            "image_id": image_id,
            "source": split_name,
            **image_attributes
        }
        processed += 1

    print(f"\n✅ {split_name}: {processed} images saved, {skipped} skipped")
    return all_labels


def main():
    print("=" * 60)
    print("iMATERIALIST PROCESSOR - COMBINED")
    print("=" * 60)

    task_labels, label_to_task = load_label_map()

    all_labels = {}
    for split in SPLITS:
        all_labels = process_split(split, task_labels, label_to_task, all_labels)

    print(f"\n💾 Saving {len(all_labels)} labels to: {LABELS_OUT}")
    with open(LABELS_OUT, 'w') as f:
        json.dump(all_labels, f, indent=2)

    print(f"\n📊 Final Summary:")
    print(f"   Total images: {len(all_labels)}")

    attr_totals = defaultdict(int)
    for info in all_labels.values():
        for key, value in info.items():
            if key not in ['image_id', 'source'] and value:
                attr_totals[key] += 1

    for attr, count in sorted(attr_totals.items(), key=lambda x: x[1], reverse=True):
        print(f"   {attr}: {count}")


if __name__ == "__main__":
    main()