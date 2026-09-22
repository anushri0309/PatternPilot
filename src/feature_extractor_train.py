"""
Extract features from TRAINING dataset using pretrained ResNet50.
"""

import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image
import numpy as np
from pathlib import Path
import json
from tqdm import tqdm


class FeatureExtractor:
    def __init__(self, device='cpu'):
        self.device = device
        print(f"🖥️ Using device: {self.device}")

        print("📦 Loading pretrained ResNet50...")
        self.model = models.resnet50(weights=models.ResNet50_Weights.DEFAULT)
        self.model.fc = nn.Identity()
        self.model = self.model.to(device)
        self.model.eval()

        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                 std=[0.229, 0.224, 0.225])
        ])

        print(f"✅ ResNet50 loaded! Feature size: 2048 dimensions")

    def extract_features(self, image_path):
        try:
            image = Image.open(image_path).convert('RGB')
            input_tensor = self.transform(image).unsqueeze(0).to(self.device)

            with torch.no_grad():
                features = self.model(input_tensor)

            return features.squeeze().cpu().numpy()
        except Exception as e:
            print(f"⚠️ Error processing {image_path}: {e}")
            return None

    def extract_features_batch(self, image_paths):
        features = []
        successful = 0
        failed = 0

        for path in tqdm(image_paths, desc="Extracting features"):
            feat = self.extract_features(path)
            if feat is not None:
                features.append(feat)
                successful += 1
            else:
                failed += 1

        print(f"✅ Successfully processed: {successful}")
        print(f"⚠️ Failed: {failed}")
        return np.array(features)


def main():
    print("=" * 60)
    print("FEATURE EXTRACTION - TRAINING SET")
    print("=" * 60)

    # Paths
    DATA_DIR = Path("data/processed_train")
    IMAGES_DIR = DATA_DIR / "images"
    LABELS_FILE = DATA_DIR / "labels.json"
    FEATURES_DIR = Path("data/features_train")
    FEATURES_DIR.mkdir(parents=True, exist_ok=True)

    # Load labels
    print(f"📂 Loading labels from: {LABELS_FILE}")
    with open(LABELS_FILE, 'r') as f:
        labels = json.load(f)

    print(f"📊 Total images with labels: {len(labels)}")

    # Get all image paths
    image_paths = []
    image_names = []
    for name in labels.keys():
        img_path = IMAGES_DIR / name
        if img_path.exists():
            image_paths.append(img_path)
            image_names.append(name)

    print(f"📸 Found {len(image_paths)} images")

    # Process ALL images (no limit!)
    print(f"🔬 Processing all {len(image_paths)} images...")

    # Initialize feature extractor
    device = "cuda" if torch.cuda.is_available() else "cpu"
    extractor = FeatureExtractor(device)

    # Extract features
    features = extractor.extract_features_batch(image_paths)

    # Save features
    features_path = FEATURES_DIR / "features.npy"
    names_path = FEATURES_DIR / "image_names.npy"

    np.save(features_path, features)
    np.save(names_path, np.array(image_names))

    print(f"\n💾 Features saved to: {features_path}")
    print(f"   Shape: {features.shape}")

    print("\n✅ Feature extraction complete!")


if __name__ == "__main__":
    main()