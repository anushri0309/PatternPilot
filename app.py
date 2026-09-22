"""
Pattern Pilot - Complete app with Fashionpedia models
"""

import streamlit as st
from PIL import Image
import pickle
import numpy as np
import torch
from torchvision import models, transforms
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.pattern_generator import PatternGenerator

st.set_page_config(page_title="Pattern Pilot", layout="wide")
st.title("🧵 Pattern Pilot")
st.write("Upload a garment image to generate a sewing pattern.")


# ============================================================
# LOAD MODELS (Fashionpedia)
# ============================================================

@st.cache_resource
def load_models():
    models_dir = Path("data/models_train")

    if not models_dir.exists():
        raise FileNotFoundError(f"Models not found at: {models_dir}")

    with open(models_dir / "scaler.pkl", 'rb') as f:
        scaler = pickle.load(f)

    classifiers = {}
    for attr in ["neckline_type", "length", "silhouette", "waistline"]:
        model_path = models_dir / f"{attr}_model.pkl"
        if model_path.exists():
            with open(model_path, 'rb') as f:
                classifiers[attr] = pickle.load(f)

    device = "cpu"
    backbone = models.resnet50(weights=models.ResNet50_Weights.DEFAULT)
    backbone.fc = torch.nn.Identity()
    backbone = backbone.to(device)
    backbone.eval()

    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406],
                             std=[0.229, 0.224, 0.225])
    ])

    return {
        'scaler': scaler,
        'classifiers': classifiers,
        'backbone': backbone,
        'transform': transform,
        'device': device
    }


def predict_attributes(image, models_dict):
    transform = models_dict['transform']
    backbone = models_dict['backbone']
    scaler = models_dict['scaler']
    classifiers = models_dict['classifiers']
    device = models_dict['device']

    input_tensor = transform(image).unsqueeze(0).to(device)
    with torch.no_grad():
        features = backbone(input_tensor).squeeze().cpu().numpy()

    features_scaled = scaler.transform([features])

    predictions = {}
    for attr, model in classifiers.items():
        pred = model.predict(features_scaled)[0]
        predictions[attr] = pred

    return predictions


# ============================================================
# MAIN APP
# ============================================================

try:
    models_dict = load_models()
    models_loaded = True
except Exception as e:
    models_loaded = False
    st.warning(f"⚠️ Models not loaded: {e}")

generator = PatternGenerator()

uploaded = st.file_uploader("Choose an image", type=["jpg", "jpeg", "png"])

if uploaded is not None:
    image = Image.open(uploaded).convert("RGB")
    st.image(image, caption="Uploaded Garment", width=400)

    # AI Prediction
    st.header("Step 1: AI Analysis")
    if models_loaded:
        with st.spinner("Analyzing..."):
            try:
                predictions = predict_attributes(image, models_dict)
                st.write(f"- Length: **{predictions.get('length')}**")
                st.write(f"- Silhouette: **{predictions.get('silhouette')}**")
                st.write(f"- Waistline: **{predictions.get('waistline')}**")
                st.write(f"- Neckline: **{predictions.get('neckline_type')}** (AI guess)")
            except Exception as e:
                st.error(f"Error: {e}")

    # User Confirmation
    st.header("Step 2: Confirm Details")
    st.write("The AI may not be perfect. Please confirm or correct:")

    col1, col2 = st.columns(2)

    with col1:
        garment_type = st.selectbox("Garment Type", ["Dress", "Shirt", "Top", "Skirt", "Pants"])
        length = st.selectbox("Length", ["Mini", "Knee", "Midi", "Maxi", "Hip", "Floor"], index=1)
        silhouette = st.selectbox("Silhouette", ["Fitted", "Straight", "A-Line", "Flared"], index=0)

    with col2:
        neckline = st.selectbox("Neckline", ["Round", "V-Neck", "Scoop", "Sweetheart", "Square", "Collared"], index=0)
        waistline = st.selectbox("Waistline", ["Natural", "High", "Low", "Empire", "None"], index=0)

    # Measurements
    st.header("Step 3: Your Measurements")
    col1, col2, col3 = st.columns(3)
    with col1:
        bust = st.number_input("Bust (in)", 28, 60, 36)
        waist = st.number_input("Waist (in)", 22, 50, 28)
    with col2:
        hips = st.number_input("Hips (in)", 30, 60, 38)
        shoulder = st.number_input("Shoulder (in)", 12, 20, 15)
    with col3:
        length_in = st.number_input("Length (in)", 20, 60, 40)

    # Generate
    st.header("Step 4: Generate Pattern")
    if st.button("🧵 Generate Pattern", type="primary"):
        attributes = {
            'garment_type': garment_type.lower(),
            'length': length.lower(),
            'silhouette': silhouette.lower(),
            'neckline': neckline.lower(),
            'waistline': waistline.lower()
        }

        measurements = {
            'bust': bust,
            'waist': waist,
            'hips': hips,
            'shoulder': shoulder,
            'length': length_in
        }

        with st.spinner("Generating pattern..."):
            pattern = generator.generate(attributes, measurements)

        if pattern:
            output_dir = Path("output")
            output_dir.mkdir(exist_ok=True)
            svg_path = output_dir / "pattern.svg"
            generator.export_svg(pattern, str(svg_path))

            st.success("✅ Pattern generated!")

            with open(svg_path, 'r') as f:
                svg_content = f.read()

            st.components.v1.html(svg_content, height=1000)

            st.download_button(
                "📥 Download Pattern (SVG)",
                svg_content,
                file_name="pattern.svg",
                mime="image/svg+xml"
            )
        else:
            st.error("❌ Could not generate pattern.")