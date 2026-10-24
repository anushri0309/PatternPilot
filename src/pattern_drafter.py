"""
Parametric pattern drafting engine with full measurement metadata.
Supports: bodice, skirt, sleeve, pants + jeans pieces.
"""

import math
try:
    from src.geometry_utils import point_on_segment
except ImportError:
    try:
        from geometry_utils import point_on_segment
    except ImportError:
        from .geometry_utils import point_on_segment


class PatternDrafter:
    def __init__(self, spec):
        self.spec = spec
        self.m = spec['measurements']
        self.ease = spec.get('ease', {'bust_ease': 2.0, 'waist_ease': 1.0, 'hip_ease': 2.0})

    def draft_all(self):
        gtype = self.spec['garment_type'].lower().strip()
        pieces = {}

        TOP_KEYWORDS = ['blouse', 'shirt', 'top', 't-shirt', 'tee', 'tank',
                        'sweater', 'hoodie', 'sweatshirt', 'camisole']
        DRESS_KEYWORDS = ['dress', 'gown']
        SKIRT_KEYWORDS = ['skirt']
        PANTS_KEYWORDS = ['pants', 'jeans', 'trousers', 'shorts', 'leggings']
        OUTERWEAR_KEYWORDS = ['jacket', 'coat', 'blazer', 'cardigan']

        is_top = any(k in gtype for k in TOP_KEYWORDS)
        is_dress = any(k in gtype for k in DRESS_KEYWORDS)
        is_skirt = any(k in gtype for k in SKIRT_KEYWORDS)
        is_pants = any(k in gtype for k in PANTS_KEYWORDS)
        is_outerwear = any(k in gtype for k in OUTERWEAR_KEYWORDS)

        sleeve_type = self.spec.get('sleeve', 'short').lower()
        is_sleeveless = 'sleeveless' in sleeve_type or 'none' in sleeve_type

        print(f"🔧 Drafter: gtype='{gtype}', top={is_top}, dress={is_dress}, "
              f"skirt={is_skirt}, pants={is_pants}, outerwear={is_outerwear}, "
              f"sleeveless={is_sleeveless}")

        if is_dress:
            pieces['front_bodice'] = self.draft_bodice_front()
            pieces['back_bodice'] = self.draft_bodice_back()
            pieces['skirt_front'] = self.draft_skirt_front()
            pieces['skirt_back'] = self.draft_skirt_back()
            if not is_sleeveless:
                pieces['sleeve'] = self.draft_sleeve()

        elif is_skirt:
            pieces['skirt_front'] = self.draft_skirt_front()
            pieces['skirt_back'] = self.draft_skirt_back()

        elif is_pants:
            pieces['pants_front'] = self.draft_pants_front()
            pieces['pants_back'] = self.draft_pants_back()
            pieces['waistband'] = self.draft_waistband()
            pieces['back_yoke'] = self.draft_back_yoke()
            pieces['front_fly'] = self.draft_front_fly()
            pieces['pocket_bag'] = self.draft_front_pocket_bag()
            # No sleeve for pants

        elif is_top or is_outerwear:
            pieces['front_bodice'] = self.draft_bodice_front()
            pieces['back_bodice'] = self.draft_bodice_back()
            if not is_sleeveless:
                pieces['sleeve'] = self.draft_sleeve()

        else:
            pieces['front_bodice'] = self.draft_bodice_front()
            pieces['back_bodice'] = self.draft_bodice_back()

        return pieces

    def _get_neckline_params(self):
        neckline = self.spec.get('neckline', 'round').lower()
        base_depth = self.m.get('neck_depth', 8)
        if 'v' in neckline and 'scoop' not in neckline:
            return {'type': 'v', 'depth': base_depth + 4}
        elif 'scoop' in neckline:
            return {'type': 'scoop', 'depth': base_depth + 3}
        elif 'sweetheart' in neckline:
            return {'type': 'sweetheart', 'depth': base_depth + 2}
        elif 'square' in neckline:
            return {'type': 'square', 'depth': base_depth + 3}
        elif 'halter' in neckline:
            return {'type': 'halter', 'depth': base_depth + 5}
        else:
            return {'type': 'round', 'depth': base_depth}

    # ============================================================
    # BODICE
    # ============================================================

    def draft_bodice_front(self):
        bust = self.m['bust'] + self.ease['bust_ease']
        waist = self.m['waist'] + self.ease['waist_ease']
        back_length = self.m['back_length']
        shoulder = self.m['shoulder']

        bust_quarter = bust / 4
        waist_quarter = waist / 4
        neck_width = 7.0  # Slightly wider for a t-shirt
        shoulder_drop = 4
        armhole_depth = (bust / 10) + 10

        neck = self._get_neckline_params()
        neck_depth = neck['depth']

        silhouette = self.spec.get('silhouette', 'fitted').lower()
        if 'fitted' in silhouette or 'bodycon' in silhouette:
            waist_side_x = waist_quarter
        elif 'loose' in silhouette or 'oversized' in silhouette:
            waist_side_x = bust_quarter
        else:
            waist_side_x = waist_quarter + 2

        garment_type = self.spec.get('garment_type', 'top').lower()
        hem_length = back_length + (35 if 'dress' in garment_type else 15)
        if 't-shirt' in garment_type or 'loose' in silhouette:
            hem_side_x = waist_side_x
        else:
            hem_side_x = waist_side_x + 2

        neckline = self.spec.get('neckline', 'round').lower()

        # --- NECKLINE CUSTOMIZATION LOGIC ---
        if 'halter' in neckline:
            shoulder_x = neck_width + 1.5
            armhole_y = armhole_depth + 2
            neck_corner = (neck_width, 0)
            neck_drop = (0, neck_depth + 4)
            neck_ctrl = (neck_width * 0.3, neck_depth * 0.8)

        elif 'v-neck' in neckline or ('v' in neckline and 'scoop' not in neckline):
            shoulder_x = (shoulder / 2) + 1
            armhole_y = armhole_depth
            neck_corner = (neck_width, 0)
            neck_drop = (0, neck_depth + 6)  # Deep V
            neck_ctrl = (neck_width * 0.2, neck_depth * 0.5)  # Straight line down

        elif 'square' in neckline:
            shoulder_x = (shoulder / 2) + 1
            armhole_y = armhole_depth
            neck_corner = (neck_width, neck_depth * 0.5)
            neck_drop = (0, neck_depth * 0.5)
            neck_ctrl = (neck_width * 0.5, neck_depth * 0.5)

        elif 'scoop' in neckline:
            shoulder_x = (shoulder / 2) + 1
            armhole_y = armhole_depth
            neck_corner = (neck_width + 2, 0)  # Wider
            neck_drop = (0, neck_depth + 4)  # Deeper
            neck_ctrl = (neck_width * 0.5, neck_depth * 0.9)
        elif 'sweetheart' in neckline:
            shoulder_x = (shoulder / 2) + 1
            armhole_y = armhole_depth
            neck_corner = (neck_width, -2)        # Goes UP
            neck_drop = (0, neck_depth + 2)       # Goes DOWN in center
            neck_ctrl = (neck_width * 0.3, neck_depth * 0.9)
        elif 'off-shoulder' in neckline or 'one-shoulder' in neckline:
            shoulder_x = (shoulder / 2) + 4       # Extends past the shoulder
            armhole_y = armhole_depth
            neck_corner = (neck_width + 3, 0)     # Wide across the chest
            neck_drop = (0, neck_depth)
            neck_ctrl = (neck_width * 0.6, neck_depth * 0.5)
        elif 'collared' in neckline:
            shoulder_x = (shoulder / 2) + 1
            armhole_y = armhole_depth
            neck_corner = (neck_width - 1, 0)     # Tight to the neck
            neck_drop = (0, 2)                    # High in the front
            neck_ctrl = (neck_width * 0.3, 1)
        elif 'turtleneck' in neckline:
            shoulder_x = (shoulder / 2) + 1
            armhole_y = armhole_depth
            neck_corner = (neck_width - 1, -2)    # Goes up above the shoulder
            neck_drop = (0, -2)                   # Goes up above the shoulder
            neck_ctrl = (neck_width * 0.5, -1)
        else:  # Round / Crew neck
            shoulder_x = (shoulder / 2) + 1
            armhole_y = armhole_depth
            neck_corner = (neck_width, 0)
            neck_drop = (0, neck_depth)
            neck_ctrl = (neck_width * 0.4, neck_depth * 0.8)

        # --- FIXED NECKLINE POINT ORDER ---
        points = [
            (0, 0),                                     # 0: CF neck top
            neck_drop,                                  # 1: Neck drop (dynamic)
            neck_corner,                                # 2: Side neck (dynamic)
            (shoulder_x, shoulder_drop),                # 3: Shoulder tip
            (bust_quarter, armhole_y),                  # 4: Underarm
            (waist_side_x, back_length),                # 5: Waist
            (hem_side_x, hem_length),                   # 6: Hem
            (0, hem_length),                            # 7: CF Hem
            (0, back_length),                           # 8: CF Waist
        ]

        curves = [
            {'type': 'neck_center', 'points': [points[1], neck_ctrl, points[2]]},
            {'type': 'armhole_s_curve',
             'points': [points[3],
                        (bust_quarter - 2, shoulder_drop + 3),
                        (bust_quarter - 1, armhole_y - 4),
                        points[4]]}
        ]



        edge_allowances = [
            0.0,  # 0->1 CF fold
            1.0,  # 1->2 Neckline curve
            1.0,  # 2->3 Neck to shoulder
            1.0,  # 3->4 Shoulder
            1.0,  # 4->5 Armhole
            1.5,  # 5->6 Side seam
            2.0,  # 6->7 Hem
            0.0,  # 7->8 CF fold
            0.0,  # 8->0 CF fold
        ]

        return {
            'name': 'front_bodice',
            'points': points,
            'curves': curves,
            'darts': [],
            'edge_allowances': edge_allowances,
            'notches': [
                {'center': point_on_segment(points[2], points[3], 0.5), 'direction': (0, 1), 'kind': 'single'},
                {'center': point_on_segment(points[3], points[4], 0.5), 'direction': (-1, 0), 'kind': 'single'},
            ],
            'grainline': {'start': (bust_quarter * 0.35, armhole_depth + 8),
                          'end': (bust_quarter * 0.35, hem_length - 5)},
            'measurements': {}
        }

    def draft_bodice_back(self):
        bust = self.m['bust'] + self.ease['bust_ease']
        waist = self.m['waist'] + self.ease['waist_ease']
        back_length = self.m['back_length']
        shoulder = self.m['shoulder']

        bust_quarter = bust / 4
        waist_quarter = waist / 4
        neck_width = 7.0
        shoulder_drop = 4
        armhole_depth = (bust / 10) + 10
        back_neck_depth = 2.5

        silhouette = self.spec.get('silhouette', 'fitted').lower()
        if 'fitted' in silhouette or 'bodycon' in silhouette:
            waist_side_x = waist_quarter
        elif 'loose' in silhouette or 'oversized' in silhouette:
            waist_side_x = bust_quarter
        else:
            waist_side_x = waist_quarter + 2

        garment_type = self.spec.get('garment_type', 'top').lower()
        hem_length = back_length + (35 if 'dress' in garment_type else 15)
        if 't-shirt' in garment_type or 'loose' in silhouette:
            hem_side_x = waist_side_x
        else:
            hem_side_x = waist_side_x + 2

        neckline = self.spec.get('neckline', 'round').lower()

        if 'halter' in neckline:
            shoulder_x = neck_width + 1.5
            armhole_y = armhole_depth + 2
            back_neck_depth = 10  # Halters scoop low in the back
            neck_corner = (neck_width, 0)
            neck_drop = (0, back_neck_depth)
            neck_ctrl = (neck_width * 0.4, back_neck_depth * 0.8)
        elif 'v-neck' in neckline or ('v' in neckline and 'scoop' not in neckline):
            shoulder_x = (shoulder / 2) + 1
            armhole_y = armhole_depth
            back_neck_depth = 6  # Moderate V in back
            neck_corner = (neck_width, 0)
            neck_drop = (0, back_neck_depth)
            neck_ctrl = (neck_width * 0.2, back_neck_depth * 0.5)
        elif 'square' in neckline:
            shoulder_x = (shoulder / 2) + 1
            armhole_y = armhole_depth
            back_neck_depth = 8
            neck_corner = (neck_width, back_neck_depth)
            neck_drop = (0, back_neck_depth)
            neck_ctrl = (neck_width * 0.5, back_neck_depth)

        else:  # Round
            shoulder_x = (shoulder / 2) + 1
            armhole_y = armhole_depth
            back_neck_depth = 2.5
            neck_corner = (neck_width, 0)
            neck_drop = (0, back_neck_depth)
            neck_ctrl = (neck_width * 0.4, back_neck_depth * 0.8)

        points = [
            (0, 0),                                     # 0: CB neck top
            neck_drop,                                  # 1: Neck drop
            neck_corner,                                # 2: Side neck
            (shoulder_x, shoulder_drop),                # 3: Shoulder tip
            (bust_quarter, armhole_y),                  # 4: Underarm
            (waist_side_x, back_length),                # 5: Waist
            (hem_side_x, hem_length),                   # 6: Hem
            (0, hem_length),                            # 7: CB Hem
            (0, back_length),                           # 8: CB Waist
        ]

        curves = [
            {'type': 'back_neck', 'points': [points[1], neck_ctrl, points[2]]},
            {'type': 'armhole_s_curve',
             'points': [points[3],
                        (bust_quarter - 2, shoulder_drop + 3),
                        (bust_quarter - 1, armhole_y - 4),
                        points[4]]}
        ]

        edge_allowances = [
            0.0,  # 0->1 CB fold
            1.0,  # 1->2 Neckline curve
            1.0,  # 2->3 Neck to shoulder
            1.0,  # 3->4 Shoulder
            1.0,  # 4->5 Armhole
            1.5,  # 5->6 Side seam
            2.0,  # 6->7 Hem
            0.0,  # 7->8 CB fold
            0.0,  # 8->0 CB fold
        ]

        return {
            'name': 'back_bodice',
            'points': points,
            'curves': curves,
            'darts': [],
            'edge_allowances': edge_allowances,
            'notches': [
                {'center': point_on_segment(points[2], points[3], 0.5), 'direction': (0, 1), 'kind': 'single'},
                {'center': point_on_segment(points[3], points[4], 0.5), 'direction': (-1, 0), 'kind': 'double'},
            ],
            'grainline': {'start': (bust_quarter * 0.35, armhole_depth + 8),
                          'end': (bust_quarter * 0.35, hem_length - 5)},
            'measurements': {}
        }

    def draft_sleeve(self):
        bust = self.m['bust']
        bicep = (bust / 4) + 5
        armhole = (bust / 4) - 2
        cap_height = armhole * 0.4

        sleeve_type = self.spec.get('sleeve', 'short').lower()
        sleeve_length = 20
        if 'long' in sleeve_type:
            sleeve_length = 60
        elif 'wrist' in sleeve_type:
            sleeve_length = 62
        elif 'three' in sleeve_type:
            sleeve_length = 50
        elif 'elbow' in sleeve_type:
            sleeve_length = 35
        elif 'short' in sleeve_type:
            sleeve_length = 20

        cuff_width = bicep * 0.65

        points = [
            (bicep / 2, 0),  # 0: Cap peak
            (bicep, cap_height),  # 1: Underarm right
            (bicep, cap_height + 2),  # 2: Side right
            (cuff_width + (bicep - cuff_width) / 2, sleeve_length),  # 3: Hem right
            (bicep / 2 - cuff_width / 2, sleeve_length),  # 4: Hem left
            (0, cap_height + 2),  # 5: Side left
            (0, cap_height),  # 6: Underarm left
        ]

        curves = [
            {'type': 'sleeve_cap',
             'points': [points[6], (bicep * 0.15, cap_height * 0.2), (bicep * 0.3, 0), points[0]]},
            {'type': 'sleeve_cap',
             'points': [points[0], (bicep * 0.7, 0), (bicep * 0.85, cap_height * 0.2), points[1]]}
        ]

        edge_allowances = [1.0, 1.0, 1.5, 2.0, 1.5, 1.0, 1.0]

        return {
            'name': 'sleeve',
            'points': points,
            'curves': curves,
            'darts': [],
            'edge_allowances': edge_allowances,
            'notches': [
                {'center': point_on_segment(points[6], points[0], 0.5), 'direction': (0, -1), 'kind': 'single'},
                {'center': point_on_segment(points[0], points[1], 0.5), 'direction': (0, -1), 'kind': 'double'},
            ],
            'grainline': {'start': (bicep / 2, 8), 'end': (bicep / 2, sleeve_length - 5)},
            'measurements': {}
        }

    # ============================================================
    # SLEEVE
    # ============================================================

    def draft_sleeve(self):
        bust = self.m['bust']
        bicep = (bust / 4) + 5
        armhole = (bust / 4) - 2
        cap_height = armhole * 0.4

        sleeve_type = self.spec.get('sleeve', 'short').lower()
        sleeve_length = 20
        if 'long' in sleeve_type: sleeve_length = 60
        elif 'wrist' in sleeve_type: sleeve_length = 62
        elif 'three' in sleeve_type: sleeve_length = 50
        elif 'elbow' in sleeve_type: sleeve_length = 35
        elif 'short' in sleeve_type: sleeve_length = 20

        cuff_width = bicep * 0.65

        points = [
            (bicep / 2, 0), (bicep, cap_height), (bicep * 0.95, cap_height + 2),
            (cuff_width + (bicep - cuff_width) / 2, sleeve_length),
            (bicep / 2 - cuff_width / 2, sleeve_length),
            (bicep * 0.05, cap_height + 2), (0, cap_height),
        ]

        curves = [
            {'type': 'sleeve_cap', 'start': points[6],
             'control': (bicep * 0.15, cap_height * 0.15), 'end': points[0]},
            {'type': 'sleeve_cap', 'start': points[0],
             'control': (bicep * 0.85, cap_height * 0.15), 'end': points[1]}
        ]

        measurements = {
            'Cap height': f"{cap_height:.1f} cm",
            'Bicep width': f"{bicep:.1f} cm",
            'Cuff width': f"{cuff_width:.1f} cm",
            'Sleeve length': f"{sleeve_length:.1f} cm",
        }

        edge_allowances = [
            1.0,   # 0->1 sleeve cap (back half)
            1.0,   # 1->2 cap to underarm
            1.5,   # 2->3 side seam
            2.0,   # 3->4 hem
            1.5,   # 4->5 side seam
            1.0,   # 5->6 underarm to cap
            1.0,   # 6->0 sleeve cap (front half)
        ]
        notches = [
            {'center': point_on_segment(points[6], points[0], 0.5), 'direction': (0, -1), 'kind': 'single'},
            {'center': point_on_segment(points[0], points[1], 0.5), 'direction': (0, -1), 'kind': 'double'},
        ]
        return {
            'name': 'sleeve',
            'points': points,
            'curves': curves,
            'darts': [],
            'edge_allowances': edge_allowances,
            'notches': notches,
            'grainline': {'start': (bicep / 2, 8), 'end': (bicep / 2, sleeve_length - 5)},
            'measurements': measurements
        }

    # ============================================================
    # SKIRT
    # ============================================================

    def draft_skirt_front(self):
        waist = self.m['waist'] + self.ease['waist_ease']
        hips = self.m['hips'] + self.ease['hip_ease']
        garment_type = self.spec.get('garment_type', 'skirt').lower()
        length = 60 if 'dress' in garment_type else self.m.get('garment_length', 60)

        waist_quarter = waist / 4
        hip_quarter = hips / 4
        hip_depth = 20

        silhouette = self.spec.get('silhouette', '').lower()
        if 'a-line' in silhouette: flare = 10
        elif 'flared' in silhouette or 'circle' in silhouette: flare = 18
        elif 'pencil' in silhouette or 'fitted' in silhouette: flare = 0
        else: flare = 5

        waist_curve_up = 1.5

        points = [
            (0, waist_curve_up), (waist_quarter, 0), (hip_quarter, hip_depth),
            (hip_quarter + flare, length), (0, length),
        ]

        curves = [
            {'type': 'skirt_waist', 'start': points[0],
             'control': (waist_quarter * 0.5, -0.5), 'end': points[1]},
            {'type': 'hip_curve', 'start': points[1],
             'control': (waist_quarter + 1, hip_depth * 0.6), 'end': points[2]}
        ]

        measurements = {
            'Waist width (1/4)': f"{waist_quarter:.1f} cm",
            'Hip width (1/4)': f"{hip_quarter:.1f} cm",
            'Hem width (1/4)': f"{hip_quarter + flare:.1f} cm",
            'Hip depth': f"{hip_depth:.1f} cm",
            'Total length': f"{length:.1f} cm",
            'Waist curve up': f"{waist_curve_up:.1f} cm",
        }

        edge_allowances = [
            0.0,   # 0->1 CF waist (fold)
            1.0,   # 1->2 waist
            1.5,   # 2->3 side seam
            4.0,   # 3->4 hem (deep skirt hem)
            0.0,   # 4->0 CF (fold)
        ]

        return {
            'name': 'skirt_front',
            'points': points,
            'curves': curves,
            'darts': [],
            'edge_allowances': edge_allowances,
            'grainline': {'start': (0, 5), 'end': (0, length - 5)},
            'measurements': measurements
        }

    def draft_skirt_back(self):
        piece = self.draft_skirt_front()
        piece['name'] = 'skirt_back'
        return piece

    # ============================================================
    # PANTS
    # ============================================================

    def draft_pants_front(self):
        """Front pants - Strict Aldrich geometry"""
        waist = self.m['waist'] + self.ease['waist_ease']
        hips = self.m['hips'] + self.ease['hip_ease']
        length = self.m.get('garment_length', 100)

        waist_q = waist / 4
        hip_q = hips / 4
        crotch_depth = (hips / 4) + 2

        thigh_width = hip_q + 2
        knee_width = 22
        hem_width = 18

        leg_center = thigh_width * 0.65

        points = [
            (0, 0),  # 0: CF Waist
            (waist_q, 0),  # 1: Side Waist
            (hip_q + 1, 20),  # 2: Side Hip
            (thigh_width, crotch_depth),  # 3: Side Crotch (widest)
            (leg_center + (knee_width / 2), crotch_depth + ((length - crotch_depth) * 0.5)),  # 4: Outer Knee
            (leg_center + (hem_width / 2), length),  # 5: Outer Hem
            (leg_center - (hem_width / 2), length),  # 6: Inner Hem
            (leg_center - (knee_width / 2), crotch_depth + ((length - crotch_depth) * 0.5)),  # 7: Inner Knee
            (leg_center - (thigh_width / 2) + 2, crotch_depth + 5),  # 8: Inner Thigh
            (hip_q * 0.3, crotch_depth + 2),  # 9: Crotch Point
            (0, crotch_depth),  # 10: CF Crotch
        ]

        curves = [
            {'type': 'pants_side_curve', 'points': [points[1], points[2], points[3], points[4], points[5]]},
            {'type': 'pants_inseam_curve', 'points': [points[6], points[7], points[8]]},
            {'type': 'pants_crotch_curve',
             'points': [points[10], (hip_q * 0.1, crotch_depth + 1), points[9], (hip_q * 0.2, crotch_depth + 4), points[8]]}
        ]

        return {
            'name': 'pants_front', 'points': points, 'curves': curves, 'darts': [],
            'edge_allowances': [1.5, 1.5, 1.5, 1.5, 1.5, 2.0, 1.5, 1.5, 1.5, 1.0, 1.0],
            'grainline': {'start': (leg_center, crotch_depth + 10), 'end': (leg_center, length - 10)},
            'measurements': {}
        }

    def draft_pants_back(self):
        """Back pants - Strict Aldrich geometry"""
        waist = self.m['waist'] + self.ease['waist_ease']
        hips = self.m['hips'] + self.ease['hip_ease']
        length = self.m.get('garment_length', 100)

        waist_q = waist / 4
        hip_q = hips / 4
        crotch_depth = (hips / 4) + 3

        thigh_width = hip_q + 4
        knee_width = 24
        hem_width = 20

        leg_center = thigh_width * 0.65

        points = [
            (0, -2),  # 0: CB Waist
            (waist_q + 2, 0),  # 1: Side Waist
            (hip_q + 2, 20),  # 2: Side Hip
            (thigh_width, crotch_depth),  # 3: Side Crotch
            (leg_center + (knee_width / 2), crotch_depth + ((length - crotch_depth) * 0.5)),  # 4: Outer Knee
            (leg_center + (hem_width / 2), length),  # 5: Outer Hem
            (leg_center - (hem_width / 2), length),  # 6: Inner Hem
            (leg_center - (knee_width / 2), crotch_depth + ((length - crotch_depth) * 0.5)),  # 7: Inner Knee
            (leg_center - (thigh_width / 2) + 2, crotch_depth + 6),  # 8: Inner Thigh
            (hip_q * 0.5, crotch_depth + 3),  # 9: Crotch Point
            (0, crotch_depth + 2),  # 10: CB Crotch
        ]

        curves = [
            {'type': 'pants_side_curve', 'points': [points[1], points[2], points[3], points[4], points[5]]},
            {'type': 'pants_inseam_curve', 'points': [points[6], points[7], points[8]]},
            {'type': 'pants_crotch_curve',
             'points': [points[10], (hip_q * 0.2, crotch_depth + 2), points[9], (hip_q * 0.4, crotch_depth + 5), points[8]]}
        ]

        return {
            'name': 'pants_back', 'points': points, 'curves': curves, 'darts': [],
            'edge_allowances': [1.5, 1.5, 1.5, 1.5, 1.5, 2.0, 1.5, 1.5, 1.5, 1.0, 1.0],
            'grainline': {'start': (leg_center, crotch_depth + 10), 'end': (leg_center, length - 10)},
            'measurements': {}
        }

    # ============================================================
    # JEANS EXTRA PIECES
    # ============================================================

    def draft_waistband(self):
        waist = self.m['waist'] + self.ease['waist_ease']
        band_height = 8
        waistband_width = waist + 2

        points = [
            (0, 0), (waistband_width, 0),
            (waistband_width, band_height), (0, band_height),
        ]

        return {
            'name': 'waistband',
            'points': points,
            'curves': [],
            'darts': [],
            'edge_allowances': [1.0, 1.0, 1.0, 1.0],
            'grainline': {'start': (waistband_width * 0.5, 2), 'end': (waistband_width * 0.5, band_height - 2)},
            'measurements': {}
        }

    def draft_back_yoke(self):
        waist = self.m['waist'] + self.ease['waist_ease']
        hips = self.m['hips'] + self.ease['hip_ease']

        waist_q = waist / 4
        hip_q = hips / 4
        yoke_height = 9

        points = [
            (0, 0),                              # 0: CB Top
            (waist_q + 1, -1),                   # 1: Side Top
            (hip_q + 1, yoke_height - 1),        # 2: Side Bottom
            (hip_q * 0.5, yoke_height + 2),      # 3: CB Bottom (curves down)
        ]

        curves = [
            {'type': 'yoke_bottom', 'start': points[0],
             'control': (hip_q * 0.25, yoke_height + 1), 'end': points[3]}
        ]

        return {
            'name': 'back_yoke',
            'points': points,
            'curves': curves,
            'darts': [],
            'edge_allowances': [1.0, 1.0, 1.0, 1.0],
            'grainline': {'start': (hip_q * 0.5, 2), 'end': (hip_q * 0.5, yoke_height - 2)},
            'measurements': {}
        }

    def draft_front_fly(self):
        fly_length = 20
        fly_width = 4

        points = [(0, 0), (fly_width, 0), (fly_width, fly_length), (0, fly_length)]

        return {
            'name': 'front_fly',
            'points': points,
            'curves': [],
            'darts': [],
            'edge_allowances': [1.0, 1.0, 1.0, 1.0],
            'grainline': {'start': (fly_width * 0.5, 3), 'end': (fly_width * 0.5, fly_length - 3)},
            'measurements': {}
        }

    def draft_front_pocket_bag(self):
        pocket_width = 12
        pocket_height = 18

        # Corrected shape: tapered pocket bag
        points = [
            (0, 0),                              # 0: Top Left (closest to fly)
            (pocket_width, 2),                   # 1: Top Right (curve down)
            (pocket_width, pocket_height),       # 2: Bottom Right
            (0, pocket_height - 2),              # 3: Bottom Left
        ]

        curves = [
            {'type': 'pocket_curve', 'start': points[0],
             'control': (pocket_width * 0.3, 1), 'end': points[1]}
        ]

        return {
            'name': 'pocket_bag',
            'points': points,
            'curves': curves,
            'darts': [],
            'edge_allowances': [1.0, 1.0, 1.0, 1.0],
            'grainline': {'start': (pocket_width * 0.5, 3), 'end': (pocket_width * 0.5, pocket_height - 3)},
            'measurements': {}
        }