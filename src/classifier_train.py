"""
Train classifiers on TRAINING dataset features.
"""

import numpy as np
from pathlib import Path
import json
import pickle
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from sklearn.preprocessing import StandardScaler, LabelEncoder
from xgboost import XGBClassifier
import warnings

warnings.filterwarnings('ignore')


class GarmentClassifier:
    def __init__(self, features_path, names_path, labels_path):
        print("📂 Loading data...")

        self.features = np.load(features_path)
        self.image_names = np.load(names_path, allow_pickle=True)

        with open(labels_path, 'r') as f:
            self.labels = json.load(f)

        print(f"✅ Loaded {len(self.features)} images")
        print(f"   Feature shape: {self.features.shape}")

        self.attributes = ["neckline type", "length", "silhouette", "waistline"]
        self.image_to_labels = self.labels
        self.targets = self._get_targets()

        self.scaler = StandardScaler()
        self.features_scaled = self.scaler.fit_transform(self.features)

        self.label_encoders = {}

        self.models = {
            'Logistic Regression': LogisticRegression(max_iter=1000, random_state=42),
            'Random Forest': RandomForestClassifier(n_estimators=100, random_state=42),
            'KNN': KNeighborsClassifier(n_neighbors=5),
            'XGBoost': XGBClassifier(n_estimators=100, random_state=42, verbosity=0, eval_metric='mlogloss')
        }

    def _get_targets(self):
        targets = {}
        for attr in self.attributes:
            targets[attr] = []

        for name in self.image_names:
            for attr in self.attributes:
                value = self.image_to_labels.get(name, {}).get(attr)
                targets[attr].append(value if value is not None else 'unknown')

        return targets

    def _filter_rare_classes(self, X, y, min_samples=2):
        unique, counts = np.unique(y, return_counts=True)
        keep_classes = unique[counts >= min_samples]
        mask = np.isin(y, keep_classes)
        return X[mask], y[mask], len(keep_classes)

    def train_and_evaluate(self):
        print("\n" + "=" * 60)
        print("TRAINING CLASSIFIERS - TRAINING SET")
        print("=" * 60)

        results = {}

        for attr in self.attributes:
            print(f"\n📊 Attribute: {attr.upper()}")
            print("-" * 40)

            y = np.array(self.targets[attr])
            valid_indices = y != 'unknown'
            X = self.features_scaled[valid_indices]
            y_clean = y[valid_indices]

            if len(np.unique(y_clean)) < 2:
                print(f"⚠️ Not enough classes for {attr}, skipping...")
                continue

            X_filtered, y_filtered, num_classes = self._filter_rare_classes(X, y_clean, min_samples=2)

            print(f"   Samples: {len(y_filtered)}")
            print(f"   Classes: {num_classes}")

            le = LabelEncoder()
            y_encoded = le.fit_transform(y_filtered)
            self.label_encoders[attr] = le

            X_train, X_test, y_train, y_test = train_test_split(
                X_filtered, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded
            )

            best_acc = 0
            best_model = None
            best_name = ''
            results[attr] = {}

            for model_name, model in self.models.items():
                try:
                    model.fit(X_train, y_train)
                    y_pred = model.predict(X_test)
                    acc = accuracy_score(y_test, y_pred)

                    results[attr][model_name] = {
                        'accuracy': acc,
                        'model': model,
                        'predictions': y_pred,
                        'true_labels': y_test
                    }

                    if acc > best_acc:
                        best_acc = acc
                        best_model = model
                        best_name = model_name

                    print(f"   {model_name}: {acc:.4f}")
                except Exception as e:
                    print(f"   {model_name}: Error")

            if best_model is not None:
                print(f"   ✅ Best: {best_name} with {best_acc:.4f}")
                results[attr]['best'] = {
                    'name': best_name,
                    'accuracy': best_acc,
                    'model': best_model,
                    'label_encoder': le
                }

        self._save_results(results)
        return results

    def _save_results(self, results):
        output_dir = Path("output/models_train")
        output_dir.mkdir(parents=True, exist_ok=True)

        summary = {}
        for attr, attr_results in results.items():
            if 'best' in attr_results:
                summary[attr] = {
                    'best_model': attr_results['best']['name'],
                    'accuracy': attr_results['best']['accuracy']
                }

        print("\n" + "=" * 60)
        print("SUMMARY - TRAINING SET")
        print("=" * 60)
        for attr, info in summary.items():
            print(f"   {attr}: {info['best_model']} - {info['accuracy']:.4f}")

        if summary:
            avg_acc = np.mean([info['accuracy'] for info in summary.values()])
            print(f"\n   Average Accuracy: {avg_acc:.4f}")

        summary_path = output_dir / "model_summary.json"
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)

        models_dir = Path("data/models_train")
        models_dir.mkdir(parents=True, exist_ok=True)

        scaler_path = models_dir / "scaler.pkl"
        with open(scaler_path, 'wb') as f:
            pickle.dump(self.scaler, f)

        for attr, attr_results in results.items():
            if 'best' in attr_results:
                model = attr_results['best']['model']
                le = attr_results['best']['label_encoder']
                model_path = models_dir / f"{attr.replace(' ', '_')}_model.pkl"
                with open(model_path, 'wb') as f:
                    pickle.dump({'model': model, 'label_encoder': le}, f)

        print(f"\n💾 Models saved to: {models_dir}/")


def main():
    print("=" * 60)
    print("GARMENT CLASSIFIER - TRAINING SET")
    print("=" * 60)

    FEATURES_DIR = Path("data/features_train")
    features_path = FEATURES_DIR / "features.npy"
    names_path = FEATURES_DIR / "image_names.npy"
    labels_path = Path("data/processed_train/labels.json")

    if not features_path.exists():
        print(f"❌ Features not found at: {features_path}")
        print("   Run feature_extractor_train.py first!")
        return

    classifier = GarmentClassifier(features_path, names_path, labels_path)
    results = classifier.train_and_evaluate()

    print("\n✅ CLASSIFIER TRAINING COMPLETE!")


if __name__ == "__main__":
    main()