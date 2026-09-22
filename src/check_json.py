import json
from pathlib import Path

JSON_FILE = Path("data/raw/imaterialist/validation.json")

with open(JSON_FILE, 'r') as f:
    data = json.load(f)

print(f"Type of data: {type(data)}")
print(f"Keys: {data.keys() if isinstance(data, dict) else 'Not a dict'}")

if isinstance(data, dict):
    print("\nKeys in the JSON file:")
    for key in data.keys():
        print(f"  - {key}")

    # Check what's inside
    if 'images' in data:
        print(f"\nNumber of images: {len(data['images'])}")
        if len(data['images']) > 0:
            print("\nFirst image keys:")
            print(data['images'][0].keys())
            print("\nFirst image:")
            print(json.dumps(data['images'][0], indent=2)[:500])

    if 'annotations' in data:
        print(f"\nNumber of annotations: {len(data['annotations'])}")
        if len(data['annotations']) > 0:
            print("\nFirst annotation keys:")
            print(data['annotations'][0].keys())