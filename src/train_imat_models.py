"""
Train models on iMaterialist data.
Trains: neckline, category, sleeve, color, material, pattern, style, gender
"""

import json
import numpy as np
import pickle
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import warnings

warnings.filterwarnings('ignore')


def train_attribute(attr_name, labels, features, image_names, models_dir):
    """Train a single attribute classifier"""
    print(f"\n📊 Training: {attr_name}")

    y_list = []
    valid_indices = []

    for idx, name in enumerate(image_names):
        info = labels.get(name, {})
        value = info.get(attr_name)
        if value and str(value) != 'None' and str(value).strip():
            y_list.append(str(value))
            valid_indices.append(idx)

    if len(valid_indices) < 100:
        print(f"   ⚠️ Only {len(valid_indices)} samples — skipping")
        return None

    X = features[valid_indices]
    y = np.array(y_list)

    print(f"   Samples: {len(y)}")
    print(f"   Classes: {len(set(y))}")

    # Encode
    le = LabelEncoder()
    y_encoded = le.fit_transform(y)

    # Scale
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Split
    try:
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded
        )
    except ValueError as e:
        print(f"   ⚠️ Stratify failed: {e}")
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y_encoded, test_size=0.2, random_state=42
        )

    # Train
    model = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
    model.fit(X_train, y_train)

    # Evaluate
    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"   ✅ Accuracy: {acc:.4f}")

    # Save
    model_path = models_dir / f"imat_{attr_name}_model.pkl"
    with open(model_path, 'wb') as f:
        pickle.dump({
            'model': model,
            'label_encoder': le,
            'scaler': scaler,
            'accuracy': acc,
            'num_classes': len(set(y))
        }, f)

    return acc


def main():
    print("=" * 60)
    print("TRAINING iMATERIALIST MODELS")
    print("=" * 60)

    DATA_DIR = Path("data/processed_imaterialist_combined")
    FEATURES_DIR = Path("data/features_imat_combined")
    MODELS_DIR = Path("data/models_train")
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    print("\n📂 Loading labels...")
    with open(DATA_DIR / "labels.json", 'r') as f:
        labels = json.load(f)

    print("📂 Loading features...")
    features = np.load(FEATURES_DIR / "features.npy")
    image_names = np.load(FEATURES_DIR / "image_names.npy", allow_pickle=True)

    print(f"   Features: {features.shape}")

    # Attributes to train
    attributes_to_train = [
        'neckline',
        'category',
        'sleeve',
        'color',
        'material',
        'pattern',
        'style',
        'gender'
    ]

    results = {}
    for attr in attributes_to_train:
        acc = train_attribute(attr, labels, features, image_names, MODELS_DIR)
        if acc:
            results[attr] = acc

    print("\n" + "=" * 60)
    print("SUMMARY - iMATERIALIST MODELS")
    print("=" * 60)
    for attr, acc in sorted(results.items(), key=lambda x: x[1], reverse=True):
        print(f"   {attr}: {acc:.4f}")

    if results:
        avg = np.mean(list(results.values()))
        print(f"\n   Average: {avg:.4f}")


if __name__ == "__main__":
    main()