# Pattern Pilot

AI-powered garment pattern generation from photos.

## Overview

Takes a garment photo -> AI predicts 10 attributes -> Generates SVG pattern draft.

## Quick Start

git clone https://github.com/anushri0309/PatternPilot.git
cd PatternPilot
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python test_full_pipeline.py "path/to/image.jpg"

## Structure

- src/ - Python code (AI + pattern generation)
- data/patterns/ - Pattern templates (JSON)
- test_full_pipeline.py - End-to-end test

## Data Setup

Large data folders are NOT in Git. Contact team for Google Drive link.

## Status

- AI classification (10 attributes) - working
- Pattern generation (SVG output) - working, needs refinement
- Streamlit UI - pending

## Team

- Person A - AI + pattern generation
- Person B - Model improvement
- Person C - UI
