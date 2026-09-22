"""
Train and evaluate classifiers on extracted features.
Uses Logistic Regression, Random Forest, KNN, and XGBoost.
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
    """Classify garment attributes using extracted features"""

    def __init__(self, features_path, names_path, labels_path):
        print("📂 Loading data...")

        # Load features and image names
        self.features = np.load(features_path)
        self.image_names = np.load(names_path, allow_pickle=True)

        # Load labels
        with open(labels_path, 'r') as f:
            self.labels = json.load(f)

        print(f"✅ Loaded {len(self.features)} images")
        print(f"   Feature shape: {self.features.shape}")

        # Attributes to predict
        self.attributes = ["neckline type", "length", "silhouette", "waistline"]

        # Map image names to their labels
        self.image_to_labels = self.labels

        # Get labels for each image
        self.targets = self._get_targets()

        # Standardize features
        self.scaler = StandardScaler()
        self.features_scaled = self.scaler.fit_transform(self.features)

        # Store label encoders for each attribute
        self.label_encoders = {}

        # Models to try
        self.models = {
            'Logistic Regression': LogisticRegression(max_iter=1000, random_state=42),
            'Random Forest': RandomForestClassifier(n_estimators=100, random_state=42),
            'KNN': KNeighborsClassifier(n_neighbors=5),
            'XGBoost': XGBClassifier(n_estimators=100, random_state=42, verbosity=0, eval_metric='mlogloss')
        }

    def _get_targets(self):
        """Get the attribute labels for each image"""
        targets = {}

        for attr in self.attributes:
            targets[attr] = []

        for name in self.image_names:
            for attr in self.attributes:
                value = self.image_to_labels.get(name, {}).get(attr)
                targets[attr].append(value if value is not None else 'unknown')

        return targets

    def _encode_labels(self, y):
        """Convert string labels to numeric labels for XGBoost"""
        le = LabelEncoder()
        y_encoded = le.fit_transform(y)
        return y_encoded, le

    def _filter_rare_classes(self, X, y, min_samples=2):
        """Remove classes with fewer than min_samples"""
        # Get unique classes and their counts
        unique, counts = np.unique(y, return_counts=True)

        # Find classes with enough samples
        keep_classes = unique[counts >= min_samples]

        # Keep only samples from classes with enough samples
        mask = np.isin(y, keep_classes)
        X_filtered = X[mask]
        y_filtered = y[mask]

        return X_filtered, y_filtered, len(keep_classes)

    def train_and_evaluate(self):
        """Train and evaluate classifiers for each attribute"""

        print("\n" + "=" * 60)
        print("TRAINING CLASSIFIERS")
        print("=" * 60)

        results = {}

        for i, attr in enumerate(self.attributes):
            print(f"\n📊 Attribute: {attr.upper()}")
            print("-" * 40)

            # Get labels for this attribute
            y = np.array(self.targets[attr])

            # Filter out 'unknown' labels
            valid_indices = y != 'unknown'
            X = self.features_scaled[valid_indices]
            y_clean = y[valid_indices]

            if len(np.unique(y_clean)) < 2:
                print(f"⚠️ Not enough classes for {attr}, skipping...")
                continue

            # Filter out rare classes (less than 2 samples)
            X_filtered, y_filtered, num_classes = self._filter_rare_classes(X, y_clean, min_samples=2)

            if num_classes < 2:
                print(f"⚠️ After filtering rare classes, not enough classes for {attr}, skipping...")
                continue

            print(f"   Original samples: {len(y_clean)}")
            print(f"   Original classes: {len(np.unique(y_clean))}")
            print(f"   Filtered samples: {len(y_filtered)}")
            print(f"   Filtered classes: {num_classes}")

            # Encode labels to numbers
            y_encoded, le = self._encode_labels(y_filtered)
            self.label_encoders[attr] = le

            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X_filtered, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded
            )

            # Train and evaluate each model
            best_acc = 0
            best_model = None
            best_name = ''
            results[attr] = {}

            for model_name, model in self.models.items():
                try:
                    model.fit(X_train, y_train)
                    y_pred = model.predict(X_test)
                    acc = accuracy_score(y_test, y_pred)

                    # Store results
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
                    print(f"   {model_name}: Error - {str(e)[:50]}")

            if best_model is not None:
                print(f"   ✅ Best: {best_name} with {best_acc:.4f}")

                # Store best model and its label encoder
                results[attr]['best'] = {
                    'name': best_name,
                    'accuracy': best_acc,
                    'model': best_model,
                    'label_encoder': le
                }
            else:
                print(f"   ❌ No model trained successfully for {attr}")

        # Save results
        self._save_results(results)

        return results

    def _save_results(self, results):
        """Save model results"""
        output_dir = Path("output/models")
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save summary
        summary = {}
        for attr, attr_results in results.items():
            if 'best' in attr_results:
                summary[attr] = {
                    'best_model': attr_results['best']['name'],
                    'accuracy': attr_results['best']['accuracy']
                }

        # Print summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        for attr, info in summary.items():
            print(f"   {attr}: {info['best_model']} - {info['accuracy']:.4f}")

        # Average accuracy
        if summary:
            avg_acc = np.mean([info['accuracy'] for info in summary.values()])
            print(f"\n   Average Accuracy: {avg_acc:.4f}")

        # Save summary
        summary_path = output_dir / "model_summary.json"
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)

        print(f"\n💾 Summary saved to: {summary_path}")

        # Save best models
        models_dir = Path("data/models")
        models_dir.mkdir(parents=True, exist_ok=True)

        # Also save the scaler
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

        print(f"💾 Models saved to: {models_dir}/")
        print(f"   - scaler.pkl (for standardizing features)")
        print(f"   - neckline_type_model.pkl")
        print(f"   - length_model.pkl")
        print(f"   - silhouette_model.pkl")
        print(f"   - waistline_model.pkl")


def main():
    print("=" * 60)
    print("GARMENT CLASSIFIER")
    print("=" * 60)

    # Paths
    FEATURES_DIR = Path("data/features")
    features_path = FEATURES_DIR / "features.npy"
    names_path = FEATURES_DIR / "image_names.npy"
    labels_path = Path("data/processed/labels.json")

    # Check if files exist
    if not features_path.exists():
        print(f"❌ Features not found at: {features_path}")
        print("   Run feature_extractor.py first!")
        return

    # Initialize classifier
    classifier = GarmentClassifier(features_path, names_path, labels_path)

    # Train and evaluate
    results = classifier.train_and_evaluate()

    print("\n" + "=" * 60)
    print("✅ CLASSIFIER TRAINING COMPLETE!")
    print("=" * 60)


if __name__ == "__main__":
    main()