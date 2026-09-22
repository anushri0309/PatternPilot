"""Diagnose what the drafter returns."""

from attribute_schema import build_garment_spec
from pattern_drafter import PatternDrafter
import json

spec = build_garment_spec(
    predictions={},
    user_input={
        'garment_type': 'dress',
        'silhouette': 'fitted',
        'neckline': 'v-neck',
        'sleeve': 'short',
        'waistline': 'natural'
    },
    measurements={
        'bust': 90,
        'waist': 70,
        'hips': 95,
        'shoulder': 38,
        'back_length': 40,
        'garment_length': 100,
        'sleeve_length': 25
    }
)

print("Spec:")
print(json.dumps(spec, indent=2, default=str))

drafter = PatternDrafter(spec)
pieces = drafter.draft_all()

print(f"\nPieces returned: {list(pieces.keys())}")
for name, piece in pieces.items():
    if piece is None:
        print(f"  {name}: None")
    else:
        print(f"  {name}: {len(piece.get('points', []))} points")
        print(f"    First point: {piece['points'][0] if piece.get('points') else 'N/A'}")