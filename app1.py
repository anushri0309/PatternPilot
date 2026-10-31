import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import os
import time
import base64

# --- IMPORT YOUR EXISTING PIPELINE LOGIC ---
from test_full_pipeline import predict, get_measurement_defaults, get_gender_label, get_garment_category
from src.attribute_schema import build_garment_spec
from src.pattern_generator import PatternGenerator

# ============================================================
# 1. PAGE CONFIG & CUTESY CSS STYLING
# ============================================================
st.set_page_config(page_title="Pattern Pilot", page_icon="🧵", layout="wide")

# Custom CSS for the pastel/cutesy professional theme
st.markdown("""
    <style>
    /* Main background */
    .stApp {
        background-color: #FFF5F7; /* Very pale pink */
    }

    /* Headers */
    h1, h2, h3 {
        color: #6D4C5E !important; /* Deep mauve */
        font-family: 'Georgia', serif;
    }

    /* Buttons */
    .stButton>button {
        background-color: #FFB6C1; /* Light pink */
        color: #4A3B42;
        border-radius: 20px;
        border: 2px solid #FF69B4;
        font-weight: bold;
        transition: 0.3s;
    }
    .stButton>button:hover {
        background-color: #FF69B4; /* Hot pink */
        color: white;
        border: 2px solid #FF69B4;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #F8E8EE; /* Pale lavender/pink */
    }

    /* Cards / Info boxes */
    .stAlert {
        border-radius: 15px;
    }
    </style>
""", unsafe_allow_html=True)

# ============================================================
# 2. LOGIN / REGISTRATION SETUP
# ============================================================
CONFIG_FILE = 'auth_config.yaml'

# Create a local config file for authentication if it doesn't exist
if not os.path.exists(CONFIG_FILE):
    config = {
        'credentials': {
            'usernames': {
                'admin': {
                    'email': 'admin@patternpilot.com',
                    'name': 'Demo User',
                    'password': 'password123'  # PLAIN TEXT - Auto-hashed by library
                }
            }
        },
        'cookie': {'expiry_days': 30, 'key': 'pattern_pilot_key', 'name': 'pattern_pilot_cookie'}
    }
    with open(CONFIG_FILE, 'w') as file:
        yaml.dump(config, file, default_flow_style=False)

# Load config
with open(CONFIG_FILE) as file:
    config = yaml.load(file, Loader=SafeLoader)

# Initialize Authenticator with auto_hash=True
authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days'],
    auto_hash=True
)

# Render Login UI (New API way)
authenticator.login()

# Read authentication status from session state
authentication_status = st.session_state.get("authentication_status")

if authentication_status == False:
    st.error('Username/password is incorrect')
elif authentication_status == None:
    st.warning('Please enter your username and password (Use: admin / password123)')
elif authentication_status:
    # ============================================================
    # 3. MAIN APP (Only runs if logged in)
    # ============================================================
    name = st.session_state.get("name")
    authenticator.logout('Logout', 'sidebar')
    st.sidebar.markdown(f"Welcome, **{name}**! ✨")

    st.title("Pattern Pilot")
    st.markdown("##### *Upload a garment, let our AI understand it, and receive a professional, cuttable pattern.*")

    # --- STEP 1: IMAGE UPLOAD ---
    st.markdown("### 1. Upload Garment Image")
    uploaded_file = st.file_uploader("Choose a clear image of a single garment...", type=["jpg", "jpeg", "png"])

    if uploaded_file is not None:
        # Save uploaded file temporarily
        temp_img_path = f"temp_upload_{int(time.time())}.png"
        with open(temp_img_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        col1, col2 = st.columns([1, 2])
        with col1:
            st.image(uploaded_file, caption="Uploaded Garment", use_container_width=True)

        with col2:
            st.markdown("#### AI Predictions")
            if st.button("Analyze Image 🔍"):
                with st.spinner("ResNet50 is analyzing textures and shapes..."):
                    predictions = predict(temp_img_path)
                    st.session_state['predictions'] = predictions
                    st.session_state['category'] = get_garment_category(str(predictions.get('category', '')))
                    st.success("Analysis Complete!")

            if 'predictions' in st.session_state:
                preds = st.session_state['predictions']
                gender_label = get_gender_label(preds.get('gender', 'Female'))
                st.info(f"**Detected Category:** {st.session_state['category'].upper()} | **Gender:** {gender_label}")

                # Editable Dropdowns
                user_input = {}

                col_a, col_b = st.columns(2)
                with col_a:
                    user_input['garment_type'] = st.selectbox("Garment Type",
                                                              ['Dresses', 'Blouses', 'Shirts', 'T-Shirts', 'Skirts',
                                                               'Pants', 'Jeans', 'Shorts', 'Jackets', 'Coats'],
                                                              index=0 if 'dress' in str(
                                                                  preds.get('category', '')).lower() else 1)

                    user_input['silhouette'] = st.selectbox("Silhouette",
                                                            ['fitted', 'a-line', 'flared', 'loose', 'oversized',
                                                             'straight_regular', 'bodycon', 'circle', 'bootcut',
                                                             'wide_leg_family'])

                    user_input['sleeve'] = st.selectbox("Sleeve Length",
                                                        ['Sleeveless', 'Short Sleeves', 'Elbow Sleeves',
                                                         'Three-Quarter Sleeves', 'Long Sleeved'],
                                                        index=1)

                with col_b:
                    user_input['neckline'] = st.selectbox("Neckline",
                                                          ['Round Neck', 'V-Neck', 'Scoop Neck', 'Sweetheart',
                                                           'Square Neck', 'Halter', 'Off-Shoulder', 'One-Shoulder',
                                                           'Collared', 'Turtleneck', 'Cowl', 'Keyhole'])

                    user_input['waistline'] = st.selectbox("Waistline",
                                                           ['natural_waist', 'high_waist', 'low_waist',
                                                            'empire_waistline', 'dropped_waistline', 'no_waistline'])

                    user_input['length'] = st.selectbox("Length",
                                                        ['mini_length', 'knee_length', 'midi', 'maxi_length',
                                                         'floor_length', 'hip_length'],
                                                        index=1)

        st.divider()

        # --- STEP 2: MEASUREMENTS ---
        st.markdown("### 2. Your Measurements")
        st.write("We've pre-filled standard measurements. Adjust them to fit you perfectly.")

        gender = st.session_state['predictions'].get('gender', 'Female')
        defaults = get_measurement_defaults(user_input['garment_type'], gender)

        m_col1, m_col2, m_col3 = st.columns(3)
        with m_col1:
            bust = st.number_input("Bust/Chest (cm)", value=float(defaults['bust']), step=1.0)
            waist = st.number_input("Waist (cm)", value=float(defaults['waist']), step=1.0)
        with m_col2:
            hips = st.number_input("Hips (cm)", value=float(defaults['hips']), step=1.0)
            shoulder = st.number_input("Shoulder Width (cm)", value=float(defaults['shoulder']), step=1.0)
        with m_col3:
            length = st.number_input("Garment Length (cm)", value=float(defaults['length']), step=1.0)
            sleeve_length = st.number_input("Sleeve Length (cm)", value=float(defaults['sleeve_length']), step=1.0)

        st.divider()

        # --- STEP 3: GENERATE ---
        st.markdown("### 3. Generate Pattern")

        if st.button("Generate My Pattern! ✂️", use_container_width=True):
            with st.spinner("Drafting blocks with Aldrich math..."):
                # Build measurements
                measurements = {
                    'bust': bust,
                    'waist': waist,
                    'hips': hips,
                    'shoulder': shoulder,
                    'back_length': defaults['back_length'],
                    'garment_length': length,
                    'sleeve_length': sleeve_length,
                    'neck_depth': 8
                }

                # Build spec
                spec = build_garment_spec(st.session_state['predictions'], user_input, measurements)

                # Generate
                generator = PatternGenerator()
                pattern = generator.generate(spec)

                # Save SVG
                output_dir = "output/web_generated"
                os.makedirs(output_dir, exist_ok=True)
                output_path = f"{output_dir}/pattern_{int(time.time())}.svg"
                generator.export_svg(pattern, output_path)

                st.success("Pattern Generated Successfully!")
                st.balloons()

                # --- STEP 4: PREVIEW & DOWNLOAD ---
                st.markdown("### 4. Your Pattern")

                with open(output_path, "r", encoding="utf-8") as f:
                    svg_data = f.read()

                b64 = base64.b64encode(svg_data.encode('utf-8')).decode('utf-8')
                st.markdown(
                    f'<iframe src="data:image/svg+xml;base64,{b64}" width="100%" height="600px" style="border: 2px solid #FFB6C1; border-radius: 15px; background-color: white;"></iframe>',
                    unsafe_allow_html=True)

                with open(output_path, "rb") as f:
                    st.download_button(
                        label="Download Pattern (SVG) 💾",
                        data=f,
                        file_name=os.path.basename(output_path),
                        mime="image/svg+xml"
                    )

                if os.path.exists(temp_img_path):
                    os.remove(temp_img_path)