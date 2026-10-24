"""
Pattern Generator - SVG output with dimension arrows for ALL measurements.
"""

import json
import math
from pathlib import Path
import svgwrite

try:
    from src.pattern_drafter import PatternDrafter
except ImportError:
    try:
        from pattern_drafter import PatternDrafter
    except ImportError:
        from .pattern_drafter import PatternDrafter
try:
    from src.geometry_utils import offset_polygon, notch_marker
except ImportError:
    try:
        from geometry_utils import offset_polygon, notch_marker
    except ImportError:
        from .geometry_utils import offset_polygon, notch_marker

class PatternGenerator:
    def __init__(self, templates_dir="data/patterns"):
        self.templates_dir = Path(templates_dir)
        self.templates = self._load_templates()
        print(f"✅ Loaded {len(self.templates)} pattern templates")

    def _load_templates(self):
        templates = {}
        if self.templates_dir.exists():
            for f in self.templates_dir.glob("*.json"):
                with open(f, 'r') as fp:
                    t = json.load(fp)
                    templates[t['name']] = t
        return templates

    def generate(self, spec: dict) -> dict:
        print("🔧 PatternGenerator.generate() called")
        drafter = PatternDrafter(spec)
        pieces = drafter.draft_all()
        print(f"🔧 Drafter returned {len(pieces)} pieces: {list(pieces.keys())}")
        return {'spec': spec, 'pieces': pieces}

    # ============================================================
    # DIMENSION HELPERS
    # ============================================================

    def _arrow_h(self, dwg, x1, x2, y, label, color='#0066cc', size=12):
        dwg.add(dwg.line(start=(x1, y), end=(x2, y), stroke=color, stroke_width=1))
        dwg.add(dwg.polygon(points=[(x1, y), (x1 + 6, y - 3), (x1 + 6, y + 3)], fill=color))
        dwg.add(dwg.polygon(points=[(x2, y), (x2 - 6, y - 3), (x2 - 6, y + 3)], fill=color))
        dwg.add(dwg.line(start=(x1, y - size/2), end=(x1, y + size/2), stroke=color, stroke_width=1))
        dwg.add(dwg.line(start=(x2, y - size/2), end=(x2, y + size/2), stroke=color, stroke_width=1))
        mid_x = (x1 + x2) / 2
        dwg.add(dwg.text(label, insert=(mid_x - 15, y - 4),
                         font_size='10px', font_weight='bold',
                         font_family='Arial', fill=color))

    def _arrow_v(self, dwg, x, y1, y2, label, color='#0066cc', size=12):
        dwg.add(dwg.line(start=(x, y1), end=(x, y2), stroke=color, stroke_width=1))
        dwg.add(dwg.polygon(points=[(x, y1), (x - 3, y1 + 6), (x + 3, y1 + 6)], fill=color))
        dwg.add(dwg.polygon(points=[(x, y2), (x - 3, y2 - 6), (x + 3, y2 - 6)], fill=color))
        dwg.add(dwg.line(start=(x - size/2, y1), end=(x + size/2, y1), stroke=color, stroke_width=1))
        dwg.add(dwg.line(start=(x - size/2, y2), end=(x + size/2, y2), stroke=color, stroke_width=1))
        mid_y = (y1 + y2) / 2
        dwg.add(dwg.text(label, insert=(x + 4, mid_y),
                         font_size='10px', font_weight='bold',
                         font_family='Arial', fill=color))

    def _ext_line(self, dwg, x1, y1, x2, y2, color='#999'):
        dwg.add(dwg.line(start=(x1, y1), end=(x2, y2),
                         stroke=color, stroke_width=0.8, stroke_dasharray='3,3'))

    # ============================================================
    # BUILD OUTLINE PATH
    # ============================================================

    def _build_outline_path(self, piece, points_px, x_offset, y_offset, SCALE):
        curve_map = {}
        skip_types = ( 'yoke_bottom')

        for curve in piece.get('curves', []):
            ctype = curve.get('type', '')
            if ctype in skip_types:
                continue
            if 'start' in curve and 'end' in curve:
                start_idx = end_idx = None
                for i, pt in enumerate(piece['points']):
                    if abs(pt[0] - curve['start'][0]) < 0.1 and abs(pt[1] - curve['start'][1]) < 0.1: start_idx = i
                    if abs(pt[0] - curve['end'][0]) < 0.1 and abs(pt[1] - curve['end'][1]) < 0.1: end_idx = i
                if start_idx is not None and end_idx is not None:
                    curve_map[(start_idx, end_idx)] = curve
            elif ctype in (
                'armhole_s_curve', 'pants_side_curve', 'pants_inseam_curve', 'sleeve_cap', 'neck_center', 'back_neck',
                'round_neck', 'v_neck'):
                pts = curve.get('points', [])
                if len(pts) >= 2:
                    start_idx = end_idx = None
                    for i, pt in enumerate(piece['points']):
                        if abs(pt[0] - pts[0][0]) < 0.1 and abs(pt[1] - pts[0][1]) < 0.1: start_idx = i
                        if abs(pt[0] - pts[-1][0]) < 0.1 and abs(pt[1] - pts[-1][1]) < 0.1: end_idx = i
                    if start_idx is not None and end_idx is not None:
                        curve_map[(start_idx, end_idx)] = curve

        path_parts = [f"M {points_px[0][0]:.1f},{points_px[0][1]:.1f}"]
        n = len(points_px)
        i = 1
        while i < n:
            found_curve = None
            end_idx = None

            # Find if a curve starts at the previous point (i-1)
            for (start_idx, e_idx), curve in curve_map.items():
                if start_idx == i - 1:
                    found_curve = curve
                    end_idx = e_idx
                    break

            if found_curve:
                ctype = found_curve.get('type', '')

                # 1. Handle list-of-points curves (pants, armholes, necklines, sleeves)
                if 'points' in found_curve:
                    pts = found_curve['points']

                    if ctype == 'armhole_s_curve':
                        cx1 = pts[1][0] * SCALE + x_offset;
                        cy1 = pts[1][1] * SCALE + y_offset
                        cx2 = pts[2][0] * SCALE + x_offset;
                        cy2 = pts[2][1] * SCALE + y_offset
                        ex = pts[3][0] * SCALE + x_offset;
                        ey = pts[3][1] * SCALE + y_offset
                        path_parts.append(f"Q {cx1:.1f},{cy1:.1f} {cx2:.1f},{cy2:.1f}")
                        path_parts.append(f"Q {cx2:.1f},{cy2:.1f} {ex:.1f},{ey:.1f}")
                    elif ctype == 'pants_crotch_curve':
                        cx = pts[1][0] * SCALE + x_offset;
                        cy = pts[1][1] * SCALE + y_offset
                        ex = pts[2][0] * SCALE + x_offset;
                        ey = pts[2][1] * SCALE + y_offset
                        path_parts.append(f"Q {cx:.1f},{cy:.1f} {ex:.1f},{ey:.1f}")
                    elif ctype in ('pants_side_curve', 'pants_inseam_curve'):
                        for j in range(1, len(pts) - 1):
                            cx = pts[j][0] * SCALE + x_offset;
                            cy = pts[j][1] * SCALE + y_offset
                            ex = pts[j + 1][0] * SCALE + x_offset;
                            ey = pts[j + 1][1] * SCALE + y_offset
                            path_parts.append(f"Q {cx:.1f},{cy:.1f} {ex:.1f},{ey:.1f}")
                    elif ctype == 'sleeve_cap':
                        if len(pts) >= 4:
                            cx1 = pts[1][0] * SCALE + x_offset;
                            cy1 = pts[1][1] * SCALE + y_offset
                            cx2 = pts[2][0] * SCALE + x_offset;
                            cy2 = pts[2][1] * SCALE + y_offset
                            ex = pts[3][0] * SCALE + x_offset;
                            ey = pts[3][1] * SCALE + y_offset
                            path_parts.append(f"Q {cx1:.1f},{cy1:.1f} {cx2:.1f},{cy2:.1f}")
                            path_parts.append(f"Q {cx2:.1f},{cy2:.1f} {ex:.1f},{ey:.1f}")
                    elif ctype in ('neck_center', 'back_neck', 'round_neck', 'v_neck'):
                        # DRAW THE NECKLINE CURVES
                        if len(pts) >= 3:
                            cx = pts[1][0] * SCALE + x_offset;
                            cy = pts[1][1] * SCALE + y_offset
                            ex = pts[2][0] * SCALE + x_offset;
                            ey = pts[2][1] * SCALE + y_offset
                            path_parts.append(f"Q {cx:.1f},{cy:.1f} {ex:.1f},{ey:.1f}")

                # 2. Handle control-point curves (legacy)
                elif 'control' in found_curve and 'end' in found_curve:
                    cx = found_curve['control'][0] * SCALE + x_offset
                    cy = found_curve['control'][1] * SCALE + y_offset
                    ex = found_curve['end'][0] * SCALE + x_offset
                    ey = found_curve['end'][1] * SCALE + y_offset
                    path_parts.append(f"Q {cx:.1f},{cy:.1f} {ex:.1f},{ey:.1f}")

                # Skip the index to the end of the curve
                i = max(i + 1, end_idx + 1)
            else:
                path_parts.append(f"L {points_px[i][0]:.1f},{points_px[i][1]:.1f}")
                i += 1

        path_parts.append("Z")
        return " ".join(path_parts)
    # ============================================================
    # DRAW SPECIAL CURVES
    # ============================================================

    def _draw_special_curves(self, dwg, piece, x_offset, y_offset, SCALE):
        for curve in piece.get('curves', []):
            ctype = curve.get('type', '')

            if ctype == 'neck_center':
                if 'control' in curve and 'end' in curve:
                    sx = curve['start'][0] * SCALE + x_offset
                    sy = curve['start'][1] * SCALE + y_offset
                    cx = curve['control'][0] * SCALE + x_offset
                    cy = curve['control'][1] * SCALE + y_offset
                    ex = curve['end'][0] * SCALE + x_offset
                    ey = curve['end'][1] * SCALE + y_offset
                    path_d = f"M {sx:.1f},{sy:.1f} Q {cx:.1f},{cy:.1f} {ex:.1f},{ey:.1f}"
                    dwg.add(dwg.path(d=path_d, fill='none', stroke='#000', stroke_width=2))

            elif ctype == 'pants_crotch_curve':
                pts = curve['points']
                sx = pts[0][0] * SCALE + x_offset
                sy = pts[0][1] * SCALE + y_offset
                cx = pts[1][0] * SCALE + x_offset
                cy = pts[1][1] * SCALE + y_offset
                ex = pts[2][0] * SCALE + x_offset
                ey = pts[2][1] * SCALE + y_offset
                path_d = f"M {sx:.1f},{sy:.1f} Q {cx:.1f},{cy:.1f} {ex:.1f},{ey:.1f}"
                dwg.add(dwg.path(d=path_d, fill='none', stroke='#000', stroke_width=2))

            elif ctype == 'pants_inseam_curve':
                pts = curve['points']
                sx = pts[0][0] * SCALE + x_offset
                sy = pts[0][1] * SCALE + y_offset
                cx = pts[1][0] * SCALE + x_offset
                cy = pts[1][1] * SCALE + y_offset
                ex = pts[2][0] * SCALE + x_offset
                ey = pts[2][1] * SCALE + y_offset
                path_d = f"M {sx:.1f},{sy:.1f} Q {cx:.1f},{cy:.1f} {ex:.1f},{ey:.1f}"
                dwg.add(dwg.path(d=path_d, fill='none', stroke='#000', stroke_width=2))

            elif ctype == 'pants_side_curve':
                pts = curve['points']
                path_parts = [f"M {pts[0][0] * SCALE + x_offset:.1f},{pts[0][1] * SCALE + y_offset:.1f}"]
                for i in range(1, len(pts) - 1):
                    cx = pts[i][0] * SCALE + x_offset
                    cy = pts[i][1] * SCALE + y_offset
                    ex = pts[i + 1][0] * SCALE + x_offset
                    ey = pts[i + 1][1] * SCALE + y_offset
                    path_parts.append(f"Q {cx:.1f},{cy:.1f} {ex:.1f},{ey:.1f}")
                dwg.add(dwg.path(d=" ".join(path_parts), fill='none',
                                 stroke='#000', stroke_width=2))

            elif ctype == 'yoke_bottom':
                if 'control' in curve and 'end' in curve:
                    sx = curve['start'][0] * SCALE + x_offset
                    sy = curve['start'][1] * SCALE + y_offset
                    cx = curve['control'][0] * SCALE + x_offset
                    cy = curve['control'][1] * SCALE + y_offset
                    ex = curve['end'][0] * SCALE + x_offset
                    ey = curve['end'][1] * SCALE + y_offset
                    path_d = f"M {sx:.1f},{sy:.1f} Q {cx:.1f},{cy:.1f} {ex:.1f},{ey:.1f}"
                    dwg.add(dwg.path(d=path_d, fill='none', stroke='#000', stroke_width=2))

    # ============================================================
    # DRAW POCKETS
    # ============================================================

    def _draw_pockets(self, dwg, piece, x_offset, y_offset, SCALE):
        for pocket in piece.get('pockets', []):
            ptype = pocket.get('type', '')

            if ptype == 'front_pocket':
                curve_pts = pocket.get('curve', [])
                if len(curve_pts) >= 3:
                    px_pts = [(p[0] * SCALE + x_offset, p[1] * SCALE + y_offset) for p in curve_pts]
                    dwg.add(dwg.polyline(points=px_pts, fill='none',
                                         stroke='#666', stroke_width=1.5,
                                         stroke_dasharray='6,3'))
                    dwg.add(dwg.text(pocket['label'],
                                     insert=(px_pts[0][0], px_pts[0][1] - 5),
                                     font_size='9px', fill='#666', font_family='Arial'))

            elif ptype == 'back_pocket':
                rect = pocket.get('rect', [])
                if len(rect) >= 2:
                    (rx1, ry1), (rx2, ry2) = rect
                    px1 = rx1 * SCALE + x_offset
                    py1 = ry1 * SCALE + y_offset
                    px2 = rx2 * SCALE + x_offset
                    py2 = ry2 * SCALE + y_offset
                    dwg.add(dwg.rect(insert=(px1, py1),
                                     size=(px2 - px1, py2 - py1),
                                     fill='none', stroke='#666',
                                     stroke_width=1.5, stroke_dasharray='6,3'))
                    dwg.add(dwg.text(pocket['label'],
                                     insert=(px1, py1 - 5),
                                     font_size='9px', fill='#666', font_family='Arial'))

    # ============================================================
    # MEASUREMENT ARROWS
    # ============================================================

    def _draw_measurement_arrows(self, dwg, piece, x_offset, y_offset, SCALE,
                                  min_x, max_x, min_y, max_y, width_cm, height_cm):
        pts = piece['points']
        pname = piece['name']

        if 'bodice' in pname:
            if len(pts) >= 3:
                nk_x1 = pts[0][0] * SCALE + x_offset
                nk_x2 = pts[1][0] * SCALE + x_offset
                nk_top_y = min_y - 40
                self._ext_line(dwg, nk_x1, min_y - 20, nk_x1, nk_top_y - 5, '#cc0000')
                self._ext_line(dwg, nk_x2, min_y - 20, nk_x2, nk_top_y - 5, '#cc0000')
                self._arrow_h(dwg, nk_x1, nk_x2, nk_top_y,
                              f"{abs(pts[1][0]-pts[0][0]):.1f}cm", color='#cc0000')

                nk_bot_y = pts[2][1] * SCALE + y_offset
                nk_left_x = min_x - 40
                self._ext_line(dwg, min_x - 5, min_y, nk_left_x - 5, min_y, '#cc0000')
                self._ext_line(dwg, min_x - 5, nk_bot_y, nk_left_x - 5, nk_bot_y, '#cc0000')
                self._arrow_v(dwg, nk_left_x, min_y, nk_bot_y,
                              f"{abs(pts[2][1]-pts[0][1]):.1f}cm", color='#cc0000')

            if len(pts) >= 5:
                arm_y1 = pts[3][1] * SCALE + y_offset
                arm_y2 = pts[4][1] * SCALE + y_offset
                arm_right_x = max_x + 40
                self._ext_line(dwg, max_x + 5, arm_y1, arm_right_x - 5, arm_y1, '#0066cc')
                self._ext_line(dwg, max_x + 5, arm_y2, arm_right_x - 5, arm_y2, '#0066cc')
                self._arrow_v(dwg, arm_right_x, arm_y1, arm_y2,
                              f"{abs(pts[4][1]-pts[3][1]):.1f}cm", color='#0066cc')

        elif 'skirt' in pname:
            if len(pts) >= 2:
                w_x1 = pts[0][0] * SCALE + x_offset
                w_x2 = pts[1][0] * SCALE + x_offset
                w_y = min_y - 40
                self._ext_line(dwg, w_x1, min_y - 20, w_x1, w_y - 5, '#0066cc')
                self._ext_line(dwg, w_x2, min_y - 20, w_x2, w_y - 5, '#0066cc')
                self._arrow_h(dwg, w_x1, w_x2, w_y,
                              f"{abs(pts[1][0]-pts[0][0]):.1f}cm", color='#0066cc')

            if len(pts) >= 3:
                hip_d_y1 = pts[1][1] * SCALE + y_offset
                hip_d_y2 = pts[2][1] * SCALE + y_offset
                hip_right_x = max_x + 40
                self._ext_line(dwg, max_x + 5, hip_d_y1, hip_right_x - 5, hip_d_y1, '#0066cc')
                self._ext_line(dwg, max_x + 5, hip_d_y2, hip_right_x - 5, hip_d_y2, '#0066cc')
                self._arrow_v(dwg, hip_right_x, hip_d_y1, hip_d_y2,
                              f"{abs(pts[2][1]-pts[1][1]):.1f}cm", color='#0066cc')

        elif 'sleeve' in pname:
            if len(pts) >= 7:
                cap_y1 = min_y
                cap_y2 = pts[6][1] * SCALE + y_offset
                cap_right_x = max_x + 40
                self._ext_line(dwg, max_x + 5, cap_y1, cap_right_x - 5, cap_y1, '#cc0000')
                self._ext_line(dwg, max_x + 5, cap_y2, cap_right_x - 5, cap_y2, '#cc0000')
                self._arrow_v(dwg, cap_right_x, cap_y1, cap_y2,
                              f"{abs(pts[6][1]-pts[0][1]):.1f}cm", color='#cc0000')

        elif 'pants' in pname:
            if len(pts) >= 8:
                w_x1 = pts[0][0] * SCALE + x_offset
                w_x2 = pts[1][0] * SCALE + x_offset
                w_y = min_y - 40
                self._ext_line(dwg, w_x1, min_y - 20, w_x1, w_y - 5, '#0066cc')
                self._ext_line(dwg, w_x2, min_y - 20, w_x2, w_y - 5, '#0066cc')
                self._arrow_h(dwg, w_x1, w_x2, w_y,
                              f"{abs(pts[1][0]-pts[0][0]):.1f}cm", color='#0066cc')

                c_y1 = min_y
                c_y2 = pts[9][1] * SCALE + y_offset
                c_right_x = max_x + 40
                self._ext_line(dwg, max_x + 5, c_y1, c_right_x - 5, c_y1, '#cc0000')
                self._ext_line(dwg, max_x + 5, c_y2, c_right_x - 5, c_y2, '#cc0000')
                self._arrow_v(dwg, c_right_x, c_y1, c_y2,
                              f"{abs(pts[9][1]-pts[0][1]):.1f}cm", color='#cc0000')

    def _draw_notches(self, dwg, piece, x_offset, y_offset, SCALE):
        for notch in piece.get('notches', []):
            center_cm = notch['center']
            direction_cm = notch['direction']
            kind = notch.get('kind', 'single')

            cx = center_cm[0] * SCALE + x_offset
            cy = center_cm[1] * SCALE + y_offset

            pts = notch_marker((cx, cy), direction_cm, depth=4, width=3)
            dwg.add(dwg.polyline(points=pts, fill='none', stroke='#000', stroke_width=1.5))

            if kind == 'double':
                offset = 0.6
                perp = (-direction_cm[1], direction_cm[0])
                c2 = (cx + perp[0] * offset * SCALE, cy + perp[1] * offset * SCALE)
                pts2 = notch_marker(c2, direction_cm, depth=4, width=3)
                dwg.add(dwg.polyline(points=pts2, fill='none', stroke='#000', stroke_width=1.5))
    # ============================================================
    # EXPORT SVG
    # ============================================================

    def export_svg(self, pattern: dict, output_path: str):
        print(f"🔧 export_svg() called with output: {output_path}")

        spec = pattern['spec']
        pieces = pattern['pieces']
        m = spec['measurements']

        PAGE_W = 3508  # A3 width in pixels at 300dpi
        PAGE_H = 2480  # A3 height in pixels at 300dpi
        SCALE = 8      # 1cm = 8px (adjusts layout to fit the larger page)

        dwg = svgwrite.Drawing(output_path, size=(f'{PAGE_W}px', f'{PAGE_H}px'))

        # Title
        dwg.add(dwg.text(
            f"Pattern: {spec['garment_type'].title()} ({spec['silhouette'].title()})",
            insert=(30, 35), font_size='20px', font_weight='bold',
            font_family='Arial', fill='black'
        ))
        dwg.add(dwg.text(
            f"Bust: {m['bust']:.0f}cm | Waist: {m['waist']:.0f}cm | Hips: {m['hips']:.0f}cm | Length: {m['garment_length']:.0f}cm",
            insert=(30, 58), font_size='12px', font_family='Arial', fill='#333'
        ))
        dwg.add(dwg.text(
            f"Neckline: {spec['neckline']} | Sleeve: {spec['sleeve']} | Length: {spec['length']}",
            insert=(30, 78), font_size='12px', font_family='Arial', fill='#333'
        ))

        # 3-column layout for up to 6 pieces
        # 3-column layout for up to 6 pieces
        x_positions = [200, 1250, 2300]
        y_current = 200
        col_index = 0
        max_height_in_row = 0
        drawn_count = 0
        total_height_cm = 0

        for piece_name, piece in pieces.items():
            if piece is None:
                continue
            pts = piece.get('points', [])
            if not pts:
                continue

            print(f"   ✅ Drawing {piece_name} with {len(pts)} points")

            x_offset = x_positions[col_index]
            y_offset = y_current

            points_px = [(pt[0] * SCALE + x_offset, pt[1] * SCALE + y_offset) for pt in pts]

            xs = [p[0] for p in points_px]
            ys = [p[1] for p in points_px]
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            piece_w = max_x - min_x
            piece_h = max_y - min_y

            pts_cm = piece['points']
            xs_cm = [p[0] for p in pts_cm]
            ys_cm = [p[1] for p in pts_cm]
            width_cm = max(xs_cm) - min(xs_cm)
            height_cm = max(ys_cm) - min(ys_cm)
            total_height_cm += height_cm * 2

            print(f"      Bounds: ({min_x:.0f},{min_y:.0f}) to ({max_x:.0f},{max_y:.0f}) | {width_cm:.0f}x{height_cm:.0f} cm")

            # Piece label
            dwg.add(dwg.text(
                piece['name'].replace('_', ' ').title(),
                insert=(min_x, min_y - 60),
                font_size='14px', font_weight='bold',
                font_family='Arial', fill='#000'
            ))

            # Main outline
            outline_path = self._build_outline_path(piece, points_px, x_offset, y_offset, SCALE)
            dwg.add(dwg.path(d=outline_path, fill='#e8e8e8', stroke='#000', stroke_width=2))

            # --- NEW: cutting line (seam allowance) ---
            allowances = piece.get('edge_allowances')
            if allowances is None or len(allowances) != len(pts_cm):
                allowances = [1.5] * len(pts_cm)
            cut_points_cm = offset_polygon(pts_cm, allowances)
            cut_points_px = [(p[0] * SCALE + x_offset, p[1] * SCALE + y_offset)
                             for p in cut_points_cm]
            dwg.add(dwg.polygon(points=cut_points_px, fill='none',
                                stroke='#cc0000', stroke_width=1.2,
                                stroke_dasharray='6,3'))
            dwg.add(dwg.text("cutting line",
                             insert=(min_x + 4, min_y - 32),
                             font_size='8px', fill='#cc0000', font_family='Arial'))

            # Special curves
            self._draw_special_curves(dwg, piece, x_offset, y_offset, SCALE)

            # --- NEW: Draw notches ---
            self._draw_notches(dwg, piece, x_offset, y_offset, SCALE)
            # Pockets
            self._draw_pockets(dwg, piece, x_offset, y_offset, SCALE)

            # Grainline
            gl = piece.get('grainline')
            if gl:
                gx1 = gl['start'][0] * SCALE + x_offset
                gy1 = gl['start'][1] * SCALE + y_offset
                gx2 = gl['end'][0] * SCALE + x_offset
                gy2 = gl['end'][1] * SCALE + y_offset
                dwg.add(dwg.line(start=(gx1, gy1), end=(gx2, gy2),
                                 stroke='red', stroke_width=1.5, stroke_dasharray='8,4'))
                dwg.add(dwg.text("grainline", insert=(gx1 + 5, gy1 + 12),
                                 font_size='9px', fill='red', font_family='Arial'))

            # Overall dimensions
            self._arrow_h(dwg, min_x, max_x, max_y + 45, f"{width_cm:.0f} cm")
            self._arrow_v(dwg, max_x + 45, min_y, max_y, f"{height_cm:.0f} cm")

            # Measurement arrows
            self._draw_measurement_arrows(dwg, piece, x_offset, y_offset, SCALE,
                                            min_x, max_x, min_y, max_y, width_cm, height_cm)

            # Cut instruction
            dwg.add(dwg.text(
                f"✂ Cut 2 | Seam allowance: 1.5cm",
                insert=(min_x, max_y + 75),
                font_size='11px', fill='#000', font_weight='bold',
                font_family='Arial'
            ))

            max_height_in_row = max(max_height_in_row, piece_h)

            col_index += 1
            if col_index >= 3:
                col_index = 0
                y_current += max_height_in_row + 250
                max_height_in_row = 0

            drawn_count += 1

        fabric_m = (total_height_cm * 1.2) / 100

        dwg.add(dwg.text(
            f"TOTAL FABRIC NEEDED: ~{fabric_m:.2f} meters (45-inch / 115cm width)",
            insert=(30, PAGE_H - 60),
            font_size='16px', font_weight='bold',
            font_family='Arial', fill='#0066cc'
        ))
        dwg.add(dwg.text(
            f"Scale: 1cm = {SCALE}px | {drawn_count} pieces | Add 1.5cm seam allowance",
            insert=(30, PAGE_H - 25), font_size='10px', fill='#666', font_family='Arial'
        ))



        dwg.save()
        print(f"✅ SVG saved: {output_path}")
        print(f"   {drawn_count} pieces drawn")
        print(f"   Fabric needed: ~{fabric_m:.2f}m")

    def export_svg_tiled(self, pattern, output_dir, scale=1.0,
                         page_w_cm=21.0, page_h_cm=29.7,
                         margin_cm=1.0, overlap_cm=1.0):
        """
        Export the pattern as a set of A4 pages at 100% scale.
        """
        import os
        import math
        from pathlib import Path
        import svgwrite

        spec = pattern['spec']
        pieces = pattern['pieces']

        # 1. Compute overall bounding box in cm
        all_x, all_y = [], []
        for piece in pieces.values():
            if piece is None:
                continue
            for pt in piece['points']:
                all_x.append(pt[0])
                all_y.append(pt[1])
        if not all_x:
            raise ValueError("No pieces to tile")

        min_x, min_y = min(all_x), min(all_y)
        max_x, max_y = max(all_x), max(all_y)
        content_w = (max_x - min_x) + 2 * margin_cm
        content_h = (max_y - min_y) + 2 * margin_cm

        step_x = page_w_cm - margin_cm - overlap_cm
        step_y = page_h_cm - margin_cm - overlap_cm
        n_cols = max(1, int(math.ceil(content_w / step_x)))
        n_rows = max(1, int(math.ceil(content_h / step_y)))

        Path(output_dir).mkdir(parents=True, exist_ok=True)
        manifest = []

        # 2. Generate each page
        for row in range(n_rows):
            for col in range(n_cols):
                page_index = row * n_cols + col + 1
                fname = f"pattern_page_{page_index:02d}_r{row + 1}c{col + 1}.svg"
                fpath = os.path.join(output_dir, fname)

                # Origin of this tile in cm-space
                tile_origin_x = min_x - margin_cm + col * step_x
                tile_origin_y = min_y - margin_cm + row * step_y

                # Create SVG canvas for A4. The viewBox is CRITICAL for Chrome to render it right.
                dwg = svgwrite.Drawing(fpath, size=(f'{page_w_cm}cm', f'{page_h_cm}cm'),
                                       viewBox=f"0 0 {page_w_cm} {page_h_cm}")
                dwg.add(dwg.rect(insert=(0, 0), size=('100%', '100%'), fill='white'))

                def to_cm(pt_cm):
                    return ((pt_cm[0] - tile_origin_x), (pt_cm[1] - tile_origin_y))

                # Draw pieces
                for piece in pieces.values():
                    if piece is None:
                        continue

                    pts_cm = piece['points']
                    pts_page = [to_cm(p) for p in pts_cm]

                    # 1. Stitching line (Using the curve-aware path builder!)
                    # We temporarily trick the builder by passing offsets to shift it.
                    outline_path = self._build_outline_path(piece, pts_page, 0, 0, 1)
                    dwg.add(dwg.path(d=outline_path, fill='#e8e8e8', stroke='#000', stroke_width=0.1))

                    # 2. Cutting line
                    allowances = piece.get('edge_allowances')
                    if allowances is None or len(allowances) != len(pts_cm):
                        allowances = [1.5] * len(pts_cm)
                    cut_pts_cm = offset_polygon(pts_cm, allowances)
                    cut_pts_page = [to_cm(p) for p in cut_pts_cm]
                    dwg.add(dwg.polygon(points=cut_pts_page, fill='none', stroke='#cc0000', stroke_width=0.05,
                                        stroke_dasharray='0.3,0.2'))

                    # 3. Grainline
                    gl = piece.get('grainline')
                    if gl:
                        g_start = to_cm(gl['start'])
                        g_end = to_cm(gl['end'])
                        dwg.add(dwg.line(start=g_start, end=g_end, stroke='red', stroke_width=0.05,
                                         stroke_dasharray='0.5,0.3'))

                    # 4. Notches
                    for notch in piece.get('notches', []):
                        c_pt = to_cm(notch['center'])
                        d = notch['direction']
                        dwg.add(dwg.line(start=(c_pt[0], c_pt[1]), end=(c_pt[0] + d[0] * 0.8, c_pt[1] + d[1] * 0.8),
                                         stroke='#000', stroke_width=0.1))

                    # 5. Piece Label (only print it once per piece per page so it doesn't overlap)
                    label_pt = to_cm((pts_cm[0][0], pts_cm[0][1] - 1.5))
                    dwg.add(dwg.text(piece['name'].replace('_', ' ').title(),
                                     insert=label_pt, font_size='0.3cm', fill='#000', font_family='Arial'))

                # Margin border
                dwg.add(dwg.rect(
                    insert=(margin_cm, margin_cm),
                    size=((page_w_cm - 2 * margin_cm), (page_h_cm - 2 * margin_cm)),
                    fill='none', stroke='#aaa', stroke_width=0.02, stroke_dasharray='0.2,0.2'))

                # Overlap alignment marks
                if col < n_cols - 1:
                    x_line = (page_w_cm - margin_cm - overlap_cm)
                    dwg.add(dwg.line(start=(x_line, 0), end=(x_line, page_h_cm),
                                     stroke='#888', stroke_width=0.02, stroke_dasharray='0.2,0.2'))
                if row < n_rows - 1:
                    y_line = (page_h_cm - margin_cm - overlap_cm)
                    dwg.add(dwg.line(start=(0, y_line), end=(page_w_cm, y_line),
                                     stroke='#888', stroke_width=0.02, stroke_dasharray='0.2,0.2'))

                # Page label
                dwg.add(dwg.text(
                    f"Page {page_index}/{n_rows * n_cols} | Row {row + 1}, Col {col + 1} | Print at 100%",
                    insert=(margin_cm, margin_cm - 0.3),
                    font_size='0.3cm', fill='#333', font_family='Arial'))

                dwg.save()
                manifest.append(fname)

        # 3. Write manifest
        with open(os.path.join(output_dir, 'manifest.txt'), 'w') as f:
            f.write("Pattern Pilot — A4 Tiled Output\n")
            f.write(f"Total pages: {len(manifest)}\n")
            f.write(f"Grid: {n_rows} rows x {n_cols} cols\n")
            f.write("Print all pages at 100% scale. Assemble by aligning the\n")
            f.write("dashed overlap lines. Do not scale to fit.\n\n")
            for i, name in enumerate(manifest, 1):
                f.write(f"{i:02d}: {name}\n")

        print(f"✅ Tiled output: {len(manifest)} pages in {output_dir}")
        return manifest