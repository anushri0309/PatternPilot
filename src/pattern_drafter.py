"""
Parametric pattern drafting engine with full measurement metadata.
Supports: bodice, skirt, sleeve, pants + jeans pieces.
Pants use absolute thigh/knee/hem widths for proper taper.
"""

import math


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
        neck_width = 6.5
        shoulder_drop = 4
        armhole_depth = (bust / 10) + 10

        neck = self._get_neckline_params()
        neck_depth = neck['depth']
        neck_type = neck['type']

        silhouette = self.spec.get('silhouette', 'fitted').lower()
        if 'fitted' in silhouette or 'bodycon' in silhouette:
            waist_side_x = waist_quarter
        elif 'loose' in silhouette:
            waist_side_x = bust_quarter
        else:
            waist_side_x = waist_quarter + 2

        garment_type = self.spec.get('garment_type', 'top').lower()
        hem_length = back_length + (35 if 'dress' in garment_type else 15)
        hem_side_x = waist_side_x + 2

        points = [
            (0, 0), (neck_width, 0), (neck_width + 1, neck_depth),
            (shoulder / 2 + 1, shoulder_drop), (bust_quarter, armhole_depth),
            (waist_side_x, back_length), (hem_side_x, hem_length),
            (0, hem_length), (0, back_length),
        ]

        curves = []
        if neck_type == 'v':
            curves.append({'type': 'v_neck', 'start': points[1],
                           'control': ((points[1][0] + points[2][0]) / 2,
                                       (points[1][1] + points[2][1]) / 2),
                           'end': points[2]})
        else:
            curves.append({'type': 'round_neck', 'start': points[1],
                           'control': (neck_width + 0.3, neck_depth * 0.5),
                           'end': points[2]})

        curves.append({'type': 'neck_center', 'start': points[2],
                       'control': (neck_width * 0.5, neck_depth * 0.7),
                       'end': points[0]})

        curves.append({'type': 'armhole_s_curve',
                       'points': [points[3],
                                  (points[3][0] + 1, points[3][1] + 3),
                                  (points[4][0] - 1, (points[3][1] + points[4][1]) / 2),
                                  points[4]]})

        measurements = {
            'Neckline width': f"{neck_width:.1f} cm",
            'Neckline depth': f"{neck_depth:.1f} cm",
            'Shoulder width': f"{shoulder/2 + 1:.1f} cm",
            'Armhole depth': f"{armhole_depth - shoulder_drop:.1f} cm",
            'Bust width (1/4)': f"{bust_quarter:.1f} cm",
            'Waist width (1/4)': f"{waist_side_x:.1f} cm",
            'Hem width (1/4)': f"{hem_side_x:.1f} cm",
            'Side seam length': f"{hem_length - shoulder_drop:.1f} cm",
        }

        return {
            'name': 'front_bodice',
            'points': points,
            'curves': curves,
            'darts': [],
            'grainline': {'start': (bust_quarter * 0.35, armhole_depth + 8),
                          'end': (bust_quarter * 0.35, hem_length - 5)},
            'measurements': measurements
        }

    def draft_bodice_back(self):
        bust = self.m['bust'] + self.ease['bust_ease']
        waist = self.m['waist'] + self.ease['waist_ease']
        back_length = self.m['back_length']
        shoulder = self.m['shoulder']

        bust_quarter = bust / 4
        waist_quarter = waist / 4
        neck_width = 6.5
        shoulder_drop = 4
        armhole_depth = (bust / 10) + 10
        back_neck_depth = 2

        silhouette = self.spec.get('silhouette', 'fitted').lower()
        if 'fitted' in silhouette or 'bodycon' in silhouette:
            waist_side_x = waist_quarter
        elif 'loose' in silhouette:
            waist_side_x = bust_quarter
        else:
            waist_side_x = waist_quarter + 2

        garment_type = self.spec.get('garment_type', 'top').lower()
        hem_length = back_length + (35 if 'dress' in garment_type else 15)
        hem_side_x = waist_side_x + 2

        points = [
            (0, 0), (neck_width, 0), (neck_width + 0.5, back_neck_depth),
            (shoulder / 2 + 1, shoulder_drop), (bust_quarter, armhole_depth),
            (waist_side_x, back_length), (hem_side_x, hem_length),
            (0, hem_length), (0, back_length),
        ]

        curves = [
            {'type': 'back_neck', 'start': points[1],
             'control': (neck_width * 0.5, back_neck_depth * 0.7),
             'end': points[0]},
            {'type': 'armhole_s_curve',
             'points': [points[3],
                        (points[3][0] + 1, points[3][1] + 3),
                        (points[4][0] - 1, (points[3][1] + points[4][1]) / 2),
                        points[4]]}
        ]

        measurements = {
            'Neckline width': f"{neck_width:.1f} cm",
            'Neckline depth': f"{back_neck_depth:.1f} cm",
            'Shoulder width': f"{shoulder/2 + 1:.1f} cm",
            'Armhole depth': f"{armhole_depth - shoulder_drop:.1f} cm",
            'Bust width (1/4)': f"{bust_quarter:.1f} cm",
            'Waist width (1/4)': f"{waist_side_x:.1f} cm",
            'Hem width (1/4)': f"{hem_side_x:.1f} cm",
            'Side seam length': f"{hem_length - shoulder_drop:.1f} cm",
        }

        return {
            'name': 'back_bodice',
            'points': points,
            'curves': curves,
            'darts': [],
            'grainline': {'start': (bust_quarter * 0.35, armhole_depth + 8),
                          'end': (bust_quarter * 0.35, hem_length - 5)},
            'measurements': measurements
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

        return {
            'name': 'sleeve',
            'points': points,
            'curves': curves,
            'darts': [],
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

        return {
            'name': 'skirt_front',
            'points': points,
            'curves': curves,
            'darts': [],
            'grainline': {'start': (waist_quarter * 0.4, 5),
                          'end': (waist_quarter * 0.4, length - 5)},
            'measurements': measurements
        }

    def draft_skirt_back(self):
        piece = self.draft_skirt_front()
        piece['name'] = 'skirt_back'
        return piece

    # ============================================================
    # PANTS - Absolute leg widths for proper taper
    # ============================================================

    def draft_pants_front(self):
        """Front pants leg - absolute widths for proper taper."""
        waist = self.m['waist'] + self.ease['waist_ease']
        hips = self.m['hips'] + self.ease['hip_ease']
        length = self.m.get('garment_length', 100)

        waist_quarter = waist / 4
        hip_quarter = hips / 4

        # Depth markers
        hip_depth = length * 0.20
        crotch_depth = length * 0.35
        knee_depth = length * 0.62

        # Block width based on hip (used for top of piece)
        block_width = hip_quarter + 2   # ~26.25 cm for hips=97

        # ============================================================
        # CRITICAL: ABSOLUTE leg widths (NOT derived from hip)
        # These are standard values for a medium build
        # ============================================================
        thigh_width = 30         # ~30 cm at widest (thigh level)
        knee_width = 20          # ~20 cm at knee (proper taper)
        hem_width = 14           # ~14 cm at ankle (narrow hem)

        # Center of leg (for centering the leg)
        leg_center = block_width * 0.55   # shift slightly right

        points = [
            (0, 0),                                          # 0: CF waist
            (waist_quarter, 0),                              # 1: Side waist
            (waist_quarter + 1, hip_depth),                  # 2: Side hip
            (block_width, crotch_depth - 5),                 # 3: Side above crotch
            (leg_center + thigh_width / 2, crotch_depth),    # 4: THIGH outer
            (leg_center + knee_width / 2, knee_depth),       # 5: Knee outer
            (leg_center + hem_width / 2, length),            # 6: Hem outer
            (leg_center - hem_width / 2, length),            # 7: Hem inner
            (leg_center - knee_width / 2, knee_depth),       # 8: Knee inner
            (leg_center - thigh_width / 2 + 3, crotch_depth + 3),  # 9: Thigh inner
            (3.5, crotch_depth - 4),                         # 10: Crotch point
            (0, crotch_depth - 6),                           # 11: Crotch curve start
        ]

        curves = [
            {'type': 'pants_side_curve',
             'points': [points[1],
                        (waist_quarter + 1, hip_depth * 0.5),
                        points[2],
                        points[3],
                        points[4],
                        points[5],
                        points[6]]},
            {'type': 'pants_inseam_curve',
             'points': [points[9],
                        ((points[9][0] + points[8][0]) / 2, (crotch_depth + knee_depth) / 2),
                        points[8],
                        ((points[8][0] + points[7][0]) / 2, (knee_depth + length) / 2),
                        points[7]]},
            {'type': 'pants_crotch_curve',
             'points': [points[11],
                        (1.5, crotch_depth - 3),
                        points[10],
                        (2.5, crotch_depth - 1),
                        points[9]]},
        ]

        pockets = [
            {'type': 'front_pocket',
             'curve': [(0, 8), (waist_quarter * 0.5, 6),
                       (waist_quarter * 0.2, hip_depth * 0.6)],
             'label': 'Front Pocket'}
        ]

        measurements = {
            'Waist (1/4)': f"{waist_quarter:.1f} cm",
            'Hip (1/4)': f"{hip_quarter:.1f} cm",
            'Block width': f"{block_width:.1f} cm",
            'Thigh width': f"{thigh_width:.1f} cm",
            'Crotch depth': f"{crotch_depth:.1f} cm",
            'Knee width': f"{knee_width:.1f} cm",
            'Hem width': f"{hem_width:.1f} cm",
            'Total length': f"{length:.1f} cm",
        }

        return {
            'name': 'pants_front',
            'points': points,
            'curves': curves,
            'darts': [],
            'pockets': pockets,
            'grainline': {'start': (leg_center, hip_depth + 15),
                          'end': (leg_center, length - 10)},
            'measurements': measurements
        }

    def draft_pants_back(self):
        """Back pants leg - absolute widths."""
        waist = self.m['waist'] + self.ease['waist_ease']
        hips = self.m['hips'] + self.ease['hip_ease']
        length = self.m.get('garment_length', 100)

        waist_quarter = waist / 4
        hip_quarter = hips / 4

        hip_depth = length * 0.20
        crotch_depth = length * 0.37
        knee_depth = length * 0.62

        block_width = hip_quarter + 4   # back is wider

        # ABSOLUTE leg widths (slightly wider than front)
        thigh_width = 32
        knee_width = 22
        hem_width = 16

        leg_center = block_width * 0.55

        points = [
            (0, -2),                                         # 0: CB waist (raised)
            (waist_quarter + 1, 0),                          # 1: Side waist
            (waist_quarter + 2, hip_depth),                  # 2: Side hip
            (block_width, crotch_depth - 5),                 # 3: Side above crotch
            (leg_center + thigh_width / 2, crotch_depth),    # 4: THIGH outer
            (leg_center + knee_width / 2, knee_depth),       # 5: Knee outer
            (leg_center + hem_width / 2, length),            # 6: Hem outer
            (leg_center - hem_width / 2, length),            # 7: Hem inner
            (leg_center - knee_width / 2, knee_depth),       # 8: Knee inner
            (leg_center - thigh_width / 2 + 3, crotch_depth + 3),  # 9: Thigh inner
            (5, crotch_depth - 4),                           # 10: Crotch point
            (0, crotch_depth - 6),                           # 11: Crotch curve start
        ]

        curves = [
            {'type': 'pants_side_curve',
             'points': [points[1],
                        (waist_quarter + 2, hip_depth * 0.5),
                        points[2],
                        points[3],
                        points[4],
                        points[5],
                        points[6]]},
            {'type': 'pants_inseam_curve',
             'points': [points[9],
                        ((points[9][0] + points[8][0]) / 2, (crotch_depth + knee_depth) / 2),
                        points[8],
                        ((points[8][0] + points[7][0]) / 2, (knee_depth + length) / 2),
                        points[7]]},
            {'type': 'pants_crotch_curve',
             'points': [points[11],
                        (2, crotch_depth - 3),
                        points[10],
                        (3, crotch_depth - 1),
                        points[9]]},
        ]

        pockets = [
            {'type': 'back_pocket',
             'rect': [(hip_quarter * 0.35, hip_depth * 1.1),
                      (hip_quarter * 0.65, hip_depth * 1.9)],
             'label': 'Back Pocket'}
        ]

        measurements = {
            'Waist (1/4)': f"{waist_quarter + 1:.1f} cm",
            'Hip (1/4)': f"{hip_quarter + 1:.1f} cm",
            'Block width': f"{block_width:.1f} cm",
            'Thigh width': f"{thigh_width:.1f} cm",
            'Crotch depth': f"{crotch_depth:.1f} cm",
            'Knee width': f"{knee_width:.1f} cm",
            'Hem width': f"{hem_width:.1f} cm",
            'Total length': f"{length:.1f} cm",
            'Back rise': f"{crotch_depth + 2:.1f} cm",
        }

        return {
            'name': 'pants_back',
            'points': points,
            'curves': curves,
            'darts': [],
            'pockets': pockets,
            'grainline': {'start': (leg_center, hip_depth + 15),
                          'end': (leg_center, length - 10)},
            'measurements': measurements
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

        measurements = {
            'Total width': f"{waistband_width:.1f} cm",
            'Height': f"{band_height:.1f} cm",
            'Cut': 'Cut 2 (interfaced)',
        }

        return {
            'name': 'waistband',
            'points': points,
            'curves': [],
            'darts': [],
            'grainline': {'start': (waistband_width * 0.5, 2),
                          'end': (waistband_width * 0.5, band_height - 2)},
            'measurements': measurements
        }

    def draft_back_yoke(self):
        waist = self.m['waist'] + self.ease['waist_ease']
        hips = self.m['hips'] + self.ease['hip_ease']

        waist_quarter = waist / 4
        hip_quarter = hips / 4
        yoke_height = 8

        points = [
            (0, 0), (waist_quarter + 1, -1.5),
            (hip_quarter + 1, yoke_height - 1),
            (hip_quarter * 0.5, yoke_height + 1), (0, yoke_height),
        ]

        curves = [
            {'type': 'yoke_bottom', 'start': points[0],
             'control': (hip_quarter * 0.5, yoke_height + 2), 'end': points[4]},
        ]

        measurements = {
            'Waist width': f"{waist_quarter + 1:.1f} cm",
            'Hip width': f"{hip_quarter + 1:.1f} cm",
            'Yoke height': f"{yoke_height:.1f} cm",
            'Cut': 'Cut 2 (interfaced)',
        }

        return {
            'name': 'back_yoke',
            'points': points,
            'curves': curves,
            'darts': [],
            'grainline': {'start': (hip_quarter * 0.5, 2),
                          'end': (hip_quarter * 0.5, yoke_height - 2)},
            'measurements': measurements
        }

    def draft_front_fly(self):
        fly_length = 20
        fly_width = 4

        points = [(0, 0), (fly_width, 0), (fly_width, fly_length), (0, fly_length)]

        measurements = {
            'Width': f"{fly_width:.1f} cm",
            'Length': f"{fly_length:.1f} cm",
            'Cut': 'Cut 2 (mirrored)',
        }

        return {
            'name': 'front_fly',
            'points': points,
            'curves': [],
            'darts': [],
            'grainline': {'start': (fly_width * 0.5, 3),
                          'end': (fly_width * 0.5, fly_length - 3)},
            'measurements': measurements
        }

    def draft_front_pocket_bag(self):
        pocket_width = 12
        pocket_height = 18

        points = [(0, 0), (pocket_width, 0),
                  (pocket_width, pocket_height), (0, pocket_height)]

        curves = [
            {'type': 'pocket_curve', 'start': points[0],
             'control': (pocket_width * 0.3, pocket_height * 0.1),
             'end': points[3]},
        ]

        measurements = {
            'Width': f"{pocket_width:.1f} cm",
            'Height': f"{pocket_height:.1f} cm",
            'Cut': 'Cut 4 (2 per side)',
        }

        return {
            'name': 'pocket_bag',
            'points': points,
            'curves': curves,
            'darts': [],
            'grainline': {'start': (pocket_width * 0.5, 3),
                          'end': (pocket_width * 0.5, pocket_height - 3)},
            'measurements': measurements
        }