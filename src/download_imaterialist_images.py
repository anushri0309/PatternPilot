"""
Download iMaterialist Fashion Attribute Dataset images.
Memory-safe, resume-safe downloader.
"""

import json
import requests
from pathlib import Path
from tqdm import tqdm
import time
import gc

# ============================================================
# CONFIGURATION
# ============================================================

DATA_DIR = Path("data/raw/imaterialist")
IMAGES_DIR = DATA_DIR / "images"
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

# Dataset split to download
DATASET_SPLIT = "train"

# JSON file
JSON_FILE = DATA_DIR / f"{DATASET_SPLIT}.json"

# Maximum images to download
MAX_IMAGES = 100000

# ✅ Skip already downloaded images
SKIP_EXISTING = True

# Timeout for each request
TIMEOUT = 15

# Free memory every N images
GC_INTERVAL = 1000


# ============================================================
# THE CODE
# ============================================================

def load_json():
    """Load the annotation JSON file"""
    print(f"📂 Loading: {JSON_FILE}")
    with open(JSON_FILE, 'r') as f:
        data = json.load(f)

    print(f"   Images: {len(data['images'])}")
    print(f"   Annotations: {len(data['annotations'])}")

    return data


def download_image(item, idx):
    """Download a single image"""
    url = item.get('url')
    image_id = str(item.get('imageId', idx))

    if not url:
        return None, False, "no_url"

    filename = f"{DATASET_SPLIT}_{image_id}.jpg"
    filepath = IMAGES_DIR / filename

    # ✅ KEY FIX: Skip if already exists
    if SKIP_EXISTING and filepath.exists():
        return filename, True, "already_exists"

    try:
        response = requests.get(url, timeout=TIMEOUT)
        if response.status_code == 200:
            if len(response.content) > 1000:
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                return filename, True, "downloaded"
            else:
                return filename, False, "too_small"
        else:
            return filename, False, f"status_{response.status_code}"
    except requests.exceptions.Timeout:
        return filename, False, "timeout"
    except requests.exceptions.ConnectionError:
        return filename, False, "connection_error"
    except Exception:
        return filename, False, "error"
    finally:
        try:
            response.close()
        except:
            pass


def main():
    print("=" * 60)
    print("iMATERIALIST IMAGE DOWNLOADER")
    print(f"Downloading: {DATASET_SPLIT} set")
    print(f"Skip existing: {SKIP_EXISTING}")
    print("=" * 60)

    if not JSON_FILE.exists():
        print(f"❌ ERROR: {JSON_FILE} not found!")
        return

    # Count existing images BEFORE starting
    existing_count = len(list(IMAGES_DIR.glob(f"{DATASET_SPLIT}_*.jpg")))
    print(f"📁 Already have: {existing_count} images")

    # Load data
    data = load_json()
    images = data['images']

    if MAX_IMAGES:
        images = images[:MAX_IMAGES]
        print(f"📊 Processing {len(images)} images")

    print("\n📥 Starting download...")
    print("   (Press Ctrl+C to pause - progress is saved)")

    downloaded = 0
    failed = 0
    skipped = 0

    failure_reasons = {}

    try:
        for idx, item in enumerate(tqdm(images, desc="Downloading")):
            filename, success, reason = download_image(item, idx)

            if reason == "already_exists":
                skipped += 1
            elif success:
                downloaded += 1
            else:
                failed += 1
                failure_reasons[reason] = failure_reasons.get(reason, 0) + 1

            # Free memory periodically
            if idx % GC_INTERVAL == 0 and idx > 0:
                gc.collect()
                tqdm.write(
                    f"   Progress: {idx}/{len(images)} | New: {downloaded} | Skipped: {skipped} | Failed: {failed}")

            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\n\n⚠️ Download paused by user!")
        print("   Progress saved. Run again to resume.")

    finally:
        # Count total after
        final_count = len(list(IMAGES_DIR.glob(f"{DATASET_SPLIT}_*.jpg")))

        print("\n" + "=" * 60)
        print("✅ DOWNLOAD COMPLETE")
        print("=" * 60)
        print(f"   Newly downloaded: {downloaded}")
        print(f"   Skipped (already had): {skipped}")
        print(f"   Failed: {failed}")
        print(f"   Total images now: {final_count}")
        print(f"   Location: {IMAGES_DIR}")

        if failure_reasons:
            print(f"\n📊 Failure reasons:")
            for reason, count in sorted(failure_reasons.items(), key=lambda x: x[1], reverse=True):
                print(f"   {reason}: {count}")


if __name__ == "__main__":
    main()