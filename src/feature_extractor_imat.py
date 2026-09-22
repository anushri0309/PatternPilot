"""
Extract features from iMaterialist combined images using ResNet50.
"""

import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image
import numpy as np
from pathlib import Path
import json
from tqdm import tqdm


def main():
    print("=" * 60)
    print("FEATURE EXTRACTION - iMATERIALIST COMBINED")
    print("=" * 60)

    DATA_DIR = Path("data/processed_imaterialist_combined")
    IMAGES_DIR = DATA_DIR / "images"
    LABELS_FILE = DATA_DIR / "labels.json"
    FEATURES_DIR = Path("data/features_imat_combined")
    FEATURES_DIR.mkdir(parents=True, exist_ok=True)

    print(f"📂 Loading labels from: {LABELS_FILE}")
    with open(LABELS_FILE, 'r') as f:
        labels = json.load(f)

    print(f"📊 Total images: {len(labels)}")

    image_paths = []
    image_names = []
    for name in labels.keys():
        img_path = IMAGES_DIR / name
        if img_path.exists():
            image_paths.append(img_path)
            image_names.append(name)

    print(f"📸 Found {len(image_paths)} images")

    if len(image_paths) == 0:
        print("❌ No images found!")
        return

    device = "cpu"
    print(f"🖥️ Using device: {device}")
    print("📦 Loading ResNet50...")

    model = models.resnet50(weights=models.ResNet50_Weights.DEFAULT)
    model.fc = nn.Identity()
    model = model.to(device)
    model.eval()

    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406],
                             std=[0.229, 0.224, 0.225])
    ])

    print("\n🔬 Extracting features...")
    features = []
    failed = 0

    for path in tqdm(image_paths, desc="Extracting"):
        try:
            img = Image.open(path).convert('RGB')
            tensor = transform(img).unsqueeze(0).to(device)
            with torch.no_grad():
                feat = model(tensor).squeeze().cpu().numpy()
            features.append(feat)
        except Exception:
            features.append(np.zeros(2048))
            failed += 1

    features = np.array(features)

    np.save(FEATURES_DIR / "features.npy", features)
    np.save(FEATURES_DIR / "image_names.npy", np.array(image_names))

    print(f"\n✅ Features saved:")
    print(f"   Shape: {features.shape}")
    print(f"   Failed: {failed}")
    print(f"   Location: {FEATURES_DIR}")


if __name__ == "__main__":
    main()
