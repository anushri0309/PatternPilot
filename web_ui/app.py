import sys
import os
import base64
from flask import Flask, render_template, request, redirect, url_for, session, jsonify

# PATH SETUP
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from test_full_pipeline import predict
from src.attribute_schema import build_garment_spec
from src.pattern_generator import PatternGenerator

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "pattern_pilot_secret")


# --- HTML ROUTES ---
@app.route('/')
def home():
    return render_template('index.html')


@app.route('/studio')
def studio():
    if not session.get('authenticated'):
        return redirect(url_for('home'))
    return render_template('studio.html')


# --- AUTH API ---
@app.route('/api/auth/login', methods=['POST'])
def api_auth_login():
    data = request.json
    if data.get('email') == "admin" and data.get('password') == "password123":
        session['authenticated'] = True
        return jsonify({"name": "Demo User"})
    return jsonify({"message": "Invalid credentials"}), 401

@app.route('/api/auth/register', methods=['POST'])
def api_auth_register():
    data = request.json
    session['authenticated'] = True
    return jsonify({"name": data.get('name', 'New User')})

@app.route('/api/auth/logout', methods=['POST'])
def api_auth_logout():
    session.pop('authenticated', None)
    session.pop('predictions', None)
    return jsonify({"success": True})


# --- AI & GENERATE ---
@app.route('/api/analyze', methods=['POST'])
def api_analyze():
    if 'image' not in request.files:
        return jsonify({"message": "No image"}), 400
    file = request.files['image']
    temp_path = os.path.join(current_dir, "temp_web_upload.png")
    file.save(temp_path)
    try:
        predictions = predict(temp_path)
        session['predictions'] = predictions

        cat = predictions.get('category', 'Dress').lower()
        garment = 'dress'
        if 'shirt' in cat or 'blouse' in cat or 'top' in cat:
            garment = 'blouse'
        elif 'jean' in cat:
            garment = 'jeans'
        elif 'pant' in cat:
            garment = 'pants'
        elif 'skirt' in cat:
            garment = 'skirt'

        return jsonify({
            "garment_type": garment,
            "gender": predictions.get('gender', 'female').lower(),
            "silhouette": predictions.get('silhouette', 'fitted').lower(),
            "neckline": predictions.get('neckline_type', 'round').lower(),
            "sleeve_length": predictions.get('sleeve', 'short').lower(),
            "waistline": "natural",
            "length": predictions.get('length', 'knee').lower(),
            "confidence": {},
            "alternatives": []
        })
    except Exception as e:
        return jsonify({"message": str(e)}), 500
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@app.route('/api/generate', methods=['POST'])
def api_generate():
    try:
        data = request.json
        spec = data.get('spec', {})
        m = data.get('measurements_cm', {})

        # Force the backend to use the UI selections
        predictions = session.get('predictions', {})
        # 1. OVERRIDE the AI with UI choices
        predictions['category'] = spec.get('garment_type', 'Dress')
        predictions['silhouette'] = spec.get('silhouette', 'Fitted')
        predictions['neckline_type'] = spec.get('neckline', 'Round')
        predictions['sleeve'] = spec.get('sleeve_length', 'Sleeveless')
        predictions['waistline'] = spec.get('waistline', 'natural_waist')
        predictions['length'] = spec.get('length', 'knee')

        # 2. SMART LENGTH TRANSLATION
        garment_type = predictions['category'].lower()
        length_label = spec.get('length', 'knee').lower()

        # If it's pants or jeans, we trust the user's "Garment Length" slider
        if 'jeans' in garment_type or 'pants' in garment_type or 'trouser' in garment_type:
            actual_length = m.get('length', 100)  # Default to 100cm inseam for pants
        else:
            # For dresses and skirts, translate the dropdown label into cm
            if 'floor' in length_label:
                actual_length = 145
            elif 'maxi' in length_label:
                actual_length = 120
            elif 'midi' in length_label:
                actual_length = 85
            elif 'mini' in length_label or 'crop' in length_label:
                actual_length = 45
            elif 'hip' in length_label:
                actual_length = 40
            else:
                actual_length = 60  # Default knee length

        # 3. Map the measurements
        user_input = {
            'garment_type': predictions['category'],
            'silhouette': predictions['silhouette'],
            'neckline': predictions['neckline_type'],
            'sleeve': predictions['sleeve'],
            'waistline': predictions['waistline'],
            'length': predictions['length']
        }

        measurements = {
            'bust': m.get('bust', 91),
            'waist': m.get('waist', 71),
            'hips': m.get('hips', 97),
            'shoulder': m.get('shoulder', 38),
            'garment_length': actual_length,  # <-- Sends 120 for Maxi Dress, or 100 for Jeans
            'sleeve_length': m.get('sleeve', 60),
            'back_length': 40,
            'neck_depth': 8
        }

        garment_spec = build_garment_spec(predictions, user_input, measurements)
        generator = PatternGenerator()
        pattern = generator.generate(garment_spec)

        output_path = os.path.join(current_dir, "static", "generated_pattern.svg")
        generator.export_svg(pattern, output_path)

        with open(output_path, "rb") as f:
            svg_b64 = base64.b64encode(f.read()).decode('utf-8')
        svg_raw = base64.b64decode(svg_b64).decode('utf-8')

        return jsonify({"svg": svg_raw})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"message": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)