"""
Predict garment attributes using trained models.
"""

import numpy as np
import pickle
from pathlib import Path
from PIL import Image
import torch
from torchvision import models, transforms


class GarmentPredictor:
    def __init__(self, models_dir="data/models_train"):
        self.models_dir = Path(models_dir)

        # Load scaler
        with open(self.models_dir / "scaler.pkl", 'rb') as f:
            self.scaler = pickle.load(f)

        # Load models
        self.models = {}
        for attr in ["neckline_type", "length", "silhouette", "waistline"]:
            with open(self.models_dir / f"{attr}_model.pkl", 'rb') as f:
                self.models[attr] = pickle.load(f)

        # Load feature extractor
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = models.resnet50(weights=models.ResNet50_Weights.DEFAULT)
        self.model.fc = torch.nn.Identity()
        self.model = self.model.to(self.device)
        self.model.eval()

        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                 std=[0.229, 0.224, 0.225])
        ])

    def predict(self, image_path):
        # Extract features
        image = Image.open(image_path).convert('RGB')
        input_tensor = self.transform(image).unsqueeze(0).to(self.device)

        with torch.no_grad():
            features = self.model(input_tensor).squeeze().cpu().numpy()

        # Scale features
        features_scaled = self.scaler.transform([features])

        # Predict each attribute
        results = {}
        for attr, model in self.models.items():
            pred = model.predict(features_scaled)[0]
            results[attr] = pred

        return results


# Usage
predictor = GarmentPredictor()
results = predictor.predict("test_image.png")
print(results)