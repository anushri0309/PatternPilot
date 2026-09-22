"""Debug: check if pieces are non-empty before SVG export."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))

# Try both import styles
try:
    from src.attribute_schema import build_garment_spec
    from src.pattern_drafter import PatternDrafter
except ImportError:
    from attribute_schema import build_garment_spec
    from pattern_drafter import PatternDrafter


spec = build_garment_spec(
    predictions={},
    user_input={
        'garment_type': 'dress',
        'silhouette': 'fitted',
        'neckline': 'v-neck',
        'sleeve': 'short',
        'waistline': 'natural',
        'length': 'knee'
    },
    measurements={
        'bust': 90, 'waist': 70, 'hips': 95,
        'shoulder': 38, 'back_length': 40,
        'garment_length': 100, 'sleeve_length': 25,
        'neck_depth': 8
    }
)

print("Spec keys:", list(spec.keys()))
print("Measurements:", spec['measurements'])

drafter = PatternDrafter(spec)
pieces = drafter.draft_all()

print(f"\nPieces: {list(pieces.keys())}")
for name, piece in pieces.items():
    if piece is None:
        print(f"  {name}: None")
    else:
        pts = piece.get('points', [])
        print(f"  {name}: {len(pts)} points, first={pts[0] if pts else 'N/A'}")