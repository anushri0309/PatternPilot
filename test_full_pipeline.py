"""
Test the FULL pipeline:
Image → AI predictions → User confirmation → Pattern generation
Gender-aware defaults + category-aware measurements + smart attribute filtering.
"""

import sys
from pathlib import Path
import pickle
import torch
from torchvision import models, transforms
from PIL import Image

from src.attribute_schema import build_garment_spec
from src.pattern_generator import PatternGenerator


# ============================================================
# GARMENT CATEGORY & RELEVANCE
# ============================================================

TOP_KEYWORDS = ['blouse', 'shirt', 'top', 't-shirt', 'tee', 'sweater',
                'hoodie', 'sweatshirt', 'tank', 'camisole', 'dress',
                'jacket', 'coat', 'blazer', 'cardigan']
BOTTOM_KEYWORDS = ['pants', 'jeans', 'trousers', 'shorts', 'skirt',
                   'leggings', 'joggers', 'culottes']


def get_garment_category(garment_type):
    """Return 'top', 'bottom', or 'other'."""
    g = str(garment_type).lower()
    if any(k in g for k in TOP_KEYWORDS):
        return 'top'
    if any(k in g for k in BOTTOM_KEYWORDS):
        return 'bottom'
    return 'other'


def get_relevant_attributes(garment_type):
    """Which attributes make sense for this garment?"""
    cat = get_garment_category(garment_type)
    if cat == 'top':
        return ['garment_type', 'silhouette', 'neckline', 'sleeve',
                'waistline', 'length']
    elif cat == 'bottom':
        return ['garment_type', 'silhouette', 'waistline', 'length']
    else:
        return ['garment_type', 'silhouette', 'waistline', 'length']


def is_male(gender_str):
    """Determine if gender is male."""
    g = str(gender_str).lower()
    return 'male' in g and 'female' not in g


def is_female(gender_str):
    """Determine if gender is female."""
    g = str(gender_str).lower()
    return 'female' in g


def get_gender_label(gender_str):
    """Friendly gender label."""
    if is_male(gender_str):
        return "Men's"
    elif is_female(gender_str):
        return "Women's"
    return "Unisex"


# ============================================================
# MEASUREMENT DEFAULTS (gender + category aware)
# ============================================================

def get_measurement_defaults(garment_type, gender='Female'):
    """Return defaults suited for the garment type AND gender."""
    cat = get_garment_category(garment_type)
    male = is_male(gender)

    # ===== MEN'S DEFAULTS =====
    if male:
        if cat == 'bottom':
            return {
                'bust': 102,      # chest
                'waist': 86,
                'hips': 102,
                'shoulder': 46,
                'back_length': 44,
                'length': 108,    # outseam for pants
                'sleeve_length': 65,
            }
        else:  # top
            return {
                'bust': 102,      # chest
                'waist': 86,
                'hips': 102,
                'shoulder': 46,
                'back_length': 44,
                'length': 68,     # torso length
                'sleeve_length': 65,
            }

    # ===== WOMEN'S DEFAULTS =====
    if cat == 'bottom':
        return {
            'bust': 91,
            'waist': 71,
            'hips': 97,
            'shoulder': 38,
            'back_length': 40,
            'length': 105,        # outseam
            'sleeve_length': 60,
        }
    else:  # top
        return {
            'bust': 91,
            'waist': 71,
            'hips': 97,
            'shoulder': 38,
            'back_length': 40,
            'length': 60,         # torso length
            'sleeve_length': 60,
        }


# ============================================================
# LOAD MODELS
# ============================================================

def load_models():
    """Load all trained AI models."""
    models_dir = Path("data/models_train")

    with open(models_dir / "scaler.pkl", 'rb') as f:
        fp_scaler = pickle.load(f)

    classifiers = {}

    # Fashionpedia models
    for attr in ["length", "silhouette", "waistline"]:
        model_path = models_dir / f"{attr}_model.pkl"
        if model_path.exists():
            with open(model_path, 'rb') as f:
                data = pickle.load(f)
                classifiers[attr] = {
                    'model': data['model'] if isinstance(data, dict) else data,
                    'label_encoder': data.get('label_encoder') if isinstance(data, dict) else None,
                    'scaler': data.get('scaler', fp_scaler) if isinstance(data, dict) else fp_scaler
                }

    # iMaterialist neckline
    imat_neckline = models_dir / "imat_neckline_model.pkl"
    if imat_neckline.exists():
        with open(imat_neckline, 'rb') as f:
            data = pickle.load(f)
            classifiers['neckline_type'] = {
                'model': data['model'],
                'label_encoder': data.get('label_encoder'),
                'scaler': data.get('scaler', fp_scaler)
            }
        print("✅ Using iMaterialist neckline model")

    # Other iMaterialist models
    for attr in ["category", "sleeve", "color", "material", "pattern", "style", "gender"]:
        model_path = models_dir / f"imat_{attr}_model.pkl"
        if model_path.exists():
            with open(model_path, 'rb') as f:
                data = pickle.load(f)
                classifiers[attr] = {
                    'model': data['model'],
                    'label_encoder': data.get('label_encoder'),
                    'scaler': data.get('scaler', fp_scaler)
                }

    backbone = models.resnet50(weights=models.ResNet50_Weights.DEFAULT)
    backbone.fc = torch.nn.Identity()
    backbone.eval()

    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406],
                             std=[0.229, 0.224, 0.225])
    ])

    return fp_scaler, classifiers, backbone, transform


def predict(image_path):
    """Predict attributes for a single image."""
    fp_scaler, classifiers, backbone, transform = load_models()

    image = Image.open(image_path).convert('RGB')
    input_tensor = transform(image).unsqueeze(0)

    with torch.no_grad():
        features = backbone(input_tensor).squeeze().cpu().numpy()

    predictions = {}
    for attr, bundle in classifiers.items():
        features_scaled = bundle['scaler'].transform([features])
        raw = bundle['model'].predict(features_scaled)[0]
        if bundle['label_encoder'] is not None:
            pred = bundle['label_encoder'].inverse_transform([raw])[0]
        else:
            pred = raw
        predictions[attr] = pred
    return predictions


# ============================================================
# USER CONFIRMATION (loop - allows multiple corrections)
# ============================================================

def confirm_attributes(predictions):
    """Let user confirm or correct AI predictions."""
    user_input = {
        'garment_type': str(predictions.get('category', 'dress')),
        'silhouette': str(predictions.get('silhouette', 'fitted')),
        'neckline': str(predictions.get('neckline_type', 'round')),
        'sleeve': str(predictions.get('sleeve', 'short')),
        'waistline': str(predictions.get('waistline', 'natural_waist')),
        'length': str(predictions.get('length', 'knee_length')),
    }

    while True:
        print("\n   Current AI predictions:")
        print(f"     [1] Garment:    {user_input['garment_type']}")
        print(f"     [2] Silhouette: {user_input['silhouette']}")
        print(f"     [3] Neckline:   {user_input['neckline']}")
        print(f"     [4] Sleeve:     {user_input['sleeve']}")
        print(f"     [5] Waistline:  {user_input['waistline']}")
        print(f"     [6] Length:     {user_input['length']}")
        print(f"     [0] Accept all and continue")

        to_fix = input("\n   Correct which? (comma-separated, 0 to accept): ").strip()

        if not to_fix or to_fix == "0":
            break

        fix_list = [x.strip() for x in to_fix.split(",")]

        if "1" in fix_list:
            options = ['Dresses', 'Blouses', 'Shirts', 'T-Shirts', 'Skirts',
                       'Pants', 'Jeans', 'Shorts', 'Jackets', 'Coats']
            print("\n       Options:")
            for i, t in enumerate(options, 1):
                print(f"         [{i}] {t}")
            pick = input("       Pick number: ").strip()
            try:
                user_input['garment_type'] = options[int(pick) - 1]
            except (ValueError, IndexError):
                pass

        if "2" in fix_list:
            options = ['fitted', 'a-line', 'flared', 'loose', 'oversized',
                       'straight_regular', 'bodycon', 'circle', 'bootcut',
                       'wide_leg_family']
            print("\n       Options:")
            for i, s in enumerate(options, 1):
                print(f"         [{i}] {s}")
            pick = input("       Pick number: ").strip()
            try:
                user_input['silhouette'] = options[int(pick) - 1]
            except (ValueError, IndexError):
                pass

        if "3" in fix_list:
            options = ['Round Neck', 'V-Neck', 'Scoop Neck', 'Sweetheart',
                       'Square Neck', 'Halter', 'Off-Shoulder', 'One-Shoulder',
                       'Collared', 'Turtleneck', 'Cowl', 'Keyhole']
            print("\n       Options:")
            for i, n in enumerate(options, 1):
                print(f"         [{i}] {n}")
            pick = input("       Pick number: ").strip()
            try:
                user_input['neckline'] = options[int(pick) - 1]
            except (ValueError, IndexError):
                pass

        if "4" in fix_list:
            options = ['Sleeveless', 'Short Sleeves', 'Elbow Sleeves',
                       'Three-Quarter Sleeves', 'Long Sleeved']
            print("\n       Options:")
            for i, s in enumerate(options, 1):
                print(f"         [{i}] {s}")
            pick = input("       Pick number: ").strip()
            try:
                user_input['sleeve'] = options[int(pick) - 1]
            except (ValueError, IndexError):
                pass

        if "5" in fix_list:
            options = ['natural_waist', 'high_waist', 'low_waist',
                       'empire_waistline', 'dropped_waistline', 'no_waistline']
            print("\n       Options:")
            for i, w in enumerate(options, 1):
                print(f"         [{i}] {w}")
            pick = input("       Pick number: ").strip()
            try:
                user_input['waistline'] = options[int(pick) - 1]
            except (ValueError, IndexError):
                pass

        if "6" in fix_list:
            options = ['mini_length', 'knee_length', 'midi', 'maxi_length',
                       'floor_length', 'hip_length']
            print("\n       Options:")
            for i, l in enumerate(options, 1):
                print(f"         [{i}] {l}")
            pick = input("       Pick number: ").strip()
            try:
                user_input['length'] = options[int(pick) - 1]
            except (ValueError, IndexError):
                pass

    return user_input


# ============================================================
# MEASUREMENTS (gender + category aware)
# ============================================================

def get_measurements(garment_type, gender='Female'):
    """Get measurements with gender + garment-aware defaults."""
    cat = get_garment_category(garment_type)
    defaults = get_measurement_defaults(garment_type, gender)
    gender_label = get_gender_label(gender)

    print(f"\n📏 Step 3: Your measurements")
    print(f"   Category: {cat.upper()} | Gender: {gender_label}")
    print(f"   Press ENTER to accept each default (shown in brackets)")

    unit = input(f"\n   Unit (cm/inch) [cm]: ").strip().lower() or "cm"
    multiplier = 2.54 if unit.startswith('in') else 1.0
    unit_label = "in" if unit.startswith('in') else "cm"

    def get_val(name, default_cm):
        default_display = int(round(default_cm / multiplier))
        val = input(f"   {name.capitalize()} [{default_display} {unit_label}]: ").strip()
        return float(val) * multiplier if val else default_cm

    bust = get_val('bust/chest', defaults['bust'])
    waist = get_val('waist', defaults['waist'])
    hips = get_val('hips', defaults['hips'])
    shoulder = get_val('shoulder', defaults['shoulder'])
    length = get_val('length', defaults['length'])

    measurements = {
        'bust': bust,
        'waist': waist,
        'hips': hips,
        'shoulder': shoulder,
        'back_length': defaults['back_length'],
        'garment_length': length,
        'sleeve_length': defaults['sleeve_length'],
        'neck_depth': 8
    }

    print(f"\n   ✅ Bust/Chest: {bust:.1f}cm ({bust/2.54:.1f}\")")
    print(f"   ✅ Waist: {waist:.1f}cm ({waist/2.54:.1f}\")")
    print(f"   ✅ Hips: {hips:.1f}cm ({hips/2.54:.1f}\")")
    print(f"   ✅ Shoulder: {shoulder:.1f}cm ({shoulder/2.54:.1f}\")")
    print(f"   ✅ Length: {length:.1f}cm ({length/2.54:.1f}\")")

    return measurements


# ============================================================
# MAIN
# ============================================================

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_full_pipeline.py <image_path>")
        print("Example: python test_full_pipeline.py data/processed_train/images/train_000002.jpg")
        return

    image_path = sys.argv[1]
    if not Path(image_path).exists():
        print(f"❌ Image not found: {image_path}")
        return

    print("=" * 60)
    print(f"Testing: {image_path}")
    print("=" * 60)

    # ============================================================
    # STEP 1: AI PREDICTION
    # ============================================================
    print("\n📸 Step 1: AI prediction...")
    predictions = predict(image_path)

    garment_cat = get_garment_category(str(predictions.get('category', '')))
    relevant = get_relevant_attributes(str(predictions.get('category', '')))
    gender_label = get_gender_label(predictions.get('gender', 'Female'))

    print(f"   Garment category: {garment_cat.upper()}")
    print(f"   Gender detected:  {gender_label}")
    print()
    print("   All predictions:")
    for attr, value in predictions.items():
        marker = "✓" if attr in relevant or attr in ['category', 'color', 'material', 'gender'] else "·"
        print(f"   [{marker}] {attr}: {value}")

    # ============================================================
    # STEP 2: USER CONFIRMATION
    # ============================================================
    print("\n👤 Step 2: Confirm AI predictions")
    user_input = confirm_attributes(predictions)

    # ============================================================
    # STEP 3: MEASUREMENTS (gender + category aware)
    # ============================================================
    gender = predictions.get('gender', 'Female')
    measurements = get_measurements(user_input['garment_type'], gender)

    # ============================================================
    # STEP 4: BUILD SPEC
    # ============================================================
    print("\n🔧 Step 4: Building spec...")
    spec = build_garment_spec(predictions, user_input, measurements)

    # ============================================================
    # STEP 5: GENERATE PATTERN
    # ============================================================
    print("\n🧵 Step 5: Generating pattern...")
    generator = PatternGenerator()
    pattern = generator.generate(spec)

    import time
    output_path = f"output/full_pipeline_pattern_{int(time.time())}.svg"
    generator.export_svg(pattern, output_path)

    print(f"\n✅ Complete! Open {output_path}")


if __name__ == "__main__":
    main()