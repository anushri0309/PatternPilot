import json
from pathlib import Path

ANNOTATIONS_FILE = Path("data/raw/imaterialist/validation.json")

with open(ANNOTATIONS_FILE, 'r') as f:
    data = json.load(f)

print("=" * 60)
print("IMATERIALIST ANNOTATION STRUCTURE")
print("=" * 60)

print(f"\nTotal images: {len(data['images'])}")
print(f"Total annotations: {len(data['annotations'])}")

# Show first image
print("\n📸 First image:")
print(json.dumps(data['images'][0], indent=2))

# Show first annotation
print("\n📝 First annotation:")
print(json.dumps(data['annotations'][0], indent=2))

# Check how many images have labels
image_ids_with_labels = set()
for ann in data['annotations']:
    image_ids_with_labels.add(str(ann['imageId']))

print(f"\n📊 Images with labels: {len(image_ids_with_labels)}")
print(f"📊 Images without labels: {len(data['images']) - len(image_ids_with_labels)}")

# Check what image IDs we downloaded
downloaded_images = list(Path("data/raw/imaterialist/images").glob("validation_*.jpg"))
downloaded_ids = [f.stem.split('_')[1] for f in downloaded_images]

print(f"\n📁 Downloaded images: {len(downloaded_images)}")
print(f"   First 5 downloaded IDs: {downloaded_ids[:5]}")

# Check overlap
overlap = set(downloaded_ids) & image_ids_with_labels
print(f"\n🔗 Overlap (downloaded + has labels): {len(overlap)}")

if len(overlap) == 0:
    print("\n❌ No overlap! The downloaded images don't have labels in the annotations file.")
    print("   This could mean:")
    print("   1. The annotations are for different images")
    print("   2. The image IDs don't match")
    print("   3. We need to use a different split (train.json)")