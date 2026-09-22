"""
Extract features from garment images using pretrained ResNet50.
This model was trained on millions of images and understands fashion concepts.
"""

import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image
import numpy as np
from pathlib import Path
import json
import sys
from tqdm import tqdm


class FeatureExtractor:
    """Extract features from garment images using pretrained ResNet50"""

    def __init__(self, device='cpu'):
        self.device = device
        print(f"🖥️ Using device: {self.device}")

        # Load pretrained ResNet50 (trained on 1.4 million images)
        print("📦 Loading pretrained ResNet50...")
        self.model = models.resnet50(weights=models.ResNet50_Weights.DEFAULT)

        # Remove the classification head (we want features, not predictions)
        self.model.fc = nn.Identity()
        self.model = self.model.to(device)
        self.model.eval()

        # Image preprocessing (must match what ResNet50 expects)
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                 std=[0.229, 0.224, 0.225])
        ])

        print(f"✅ ResNet50 loaded! Feature size: 2048 dimensions")

    def extract_features(self, image_path):
        """Extract feature vector for a single image"""
        try:
            # Load and preprocess image
            image = Image.open(image_path).convert('RGB')
            input_tensor = self.transform(image).unsqueeze(0).to(self.device)

            # Extract features
            with torch.no_grad():
                features = self.model(input_tensor)

            # Convert to numpy array
            return features.squeeze().cpu().numpy()
        except Exception as e:
            print(f"⚠️ Error processing {image_path}: {e}")
            return None

    def extract_features_batch(self, image_paths):
        """Extract features for multiple images"""
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
    """Extract features for all processed images"""

    print("=" * 60)
    print("FEATURE EXTRACTION")
    print("=" * 60)

    # Paths
    DATA_DIR = Path("data/processed")
    IMAGES_DIR = DATA_DIR / "images"
    LABELS_FILE = DATA_DIR / "labels.json"
    FEATURES_DIR = Path("data/features")
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

    # Initialize feature extractor
    device = "cuda" if torch.cuda.is_available() else "cpu"
    extractor = FeatureExtractor(device)

    # Extract features (limited to first 1000 for speed)
    print("\n🔬 Extracting features...")
    if len(image_paths) > 1000:
        print(f"⚠️ Processing first 1000 images (out of {len(image_paths)})")
        image_paths = image_paths[:1000]
        image_names = image_names[:1000]

    features = extractor.extract_features_batch(image_paths)

    # Save features
    features_path = FEATURES_DIR / "features.npy"
    names_path = FEATURES_DIR / "image_names.npy"

    np.save(features_path, features)
    np.save(names_path, np.array(image_names))

    print(f"\n💾 Features saved to: {features_path}")
    print(f"   Shape: {features.shape}")
    print(f"   Image names saved to: {names_path}")

    # Save a small sample for verification
    sample_path = FEATURES_DIR / "feature_sample.txt"
    with open(sample_path, 'w') as f:
        f.write(f"Feature shape: {features.shape}\n")
        f.write(f"First image: {image_names[0]}\n")
        f.write(f"First 10 feature values: {features[0][:10]}")

    print(f"📄 Sample saved to: {sample_path}")

    print("\n✅ Feature extraction complete!")


if __name__ == "__main__":
    main()