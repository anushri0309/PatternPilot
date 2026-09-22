"""
Convert AI predictions into a structured JSON schema.
This is what pattern generators expect as input.
"""


def build_garment_spec(predictions, user_input, measurements):
    """
    Build a clean JSON spec for the pattern generator.

    Args:
        predictions: AI output (length, silhouette, waistline, neckline)
        user_input: User-confirmed values
        measurements: User body measurements

    Returns:
        Clean JSON spec
    """
    spec = {
        "garment_type": user_input.get('garment_type', 'dress'),
        "silhouette": user_input.get('silhouette', 'fitted'),
        "length": user_input.get('length', 'knee'),
        "neckline": user_input.get('neckline', 'round'),
        "sleeve": user_input.get('sleeve', 'short'),
        "waistline": user_input.get('waistline', 'natural'),
        "closures": user_input.get('closures', 'none'),

        "measurements": {
            "bust": measurements['bust'],
            "waist": measurements['waist'],
            "hips": measurements['hips'],
            "shoulder": measurements['shoulder'],
            "back_length": measurements['back_length'],
            "garment_length": measurements['garment_length'],
            "sleeve_length": measurements.get('sleeve_length', 10),
            "neck_depth": measurements.get('neck_depth', 3),
        },

        "ease": {
            "bust_ease": 2.0,  # Standard ease
            "waist_ease": 1.0,
            "hip_ease": 2.0,
        }
    }
    return spec