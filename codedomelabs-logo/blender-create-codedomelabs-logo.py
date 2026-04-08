"""
Blender 5.01 – 3D Hollowed Multi-Colour Capsule  (v5 – contour-based)
======================================================================
Colour boundaries are extracted from the logo PNG as smooth polylines
and embedded below.  Each capsule face is classified using ray-casting
point-in-polygon tests against these contours — giving smooth, curved
region boundaries that match the logo exactly.

Classification logic (hierarchical):
  1. Is the face inside the blue/red boundary?  → blue group
     • Inside navy contour?  → Dark Navy
     • Otherwise             → Royal Blue
  2. Otherwise                                  → red group
     • Inside maroon contour? → Dark Maroon
     • Otherwise              → Bright Red

Run:  Scripting ▸ Open ▸ Run Script
"""

import bpy
import bmesh
import math

# ═══════════════════════════════════════════════════════════════
#  PARAMETERS
# ═══════════════════════════════════════════════════════════════
OVERALL_HEIGHT_MM  = 160.0
RADIUS_MM          = 40.0
WALL_THICKNESS_MM  = 2.0
CAP_HEIGHT_MM      = 18.0       # flattened dome height
SEGMENTS           = 128
SUBDIVISIONS       = 4          # subdivision levels before classification (0-4)
                                # higher = smoother boundaries, slower
SEPARATE_PIECES    = True       # split into individual mesh objects
CONTOUR_PADDING_MM = 7.0       # push edge contour points beyond capsule surface


# ═══════════════════════════════════════════════════════════════
#  MATERIALS
# ═══════════════════════════════════════════════════════════════
MAT_DEFS = {
    "royal_blue":  "#2B4EA2",
    "dark_navy":   "#1B2A5B",
    "bright_red":  "#E01E32",
    "dark_maroon": "#8B1A2B",
}


# ═══════════════════════════════════════════════════════════════
#  BOUNDARY CONTOURS  –  extracted from the logo image
# ═══════════════════════════════════════════════════════════════
#  Each contour is a closed polyline of (X_mm, Z_mm) points.
#  X = horizontal,  Z = vertical (+ up).
#  These are the boundaries between colour regions as they appear
#  in the front view of the logo, projected along the Y axis.

# Main boundary separating the blue group from the red group.
# Points INSIDE this contour belong to the blue group.
BLUE_RED_MAIN = [
    [-1.86, -12.04], [-17.11, -11.6], [-26.11, -9.41],
    [-30.02, -7.66], [-33.35, -5.47], [-37.75, -0.55],
    [-38.83, 1.86], [-39.02, 4.27], [-40.2, 43.45],
    [-40.2, 47.17], [-39.41, 53.08], [-37.85, 58.55],
    [-36.28, 62.05], [-32.57, 67.74], [-28.46, 71.68],
    [-21.81, 75.84], [-13.59, 78.69], [-5.57, 80.0],
    [5.18, 80.22], [16.72, 78.69], [24.94, 75.84],
    [31.2, 71.9], [35.5, 67.31], [38.63, 61.4],
    [40.2, 54.83], [40.0, 20.9], [38.53, 23.75],
    [35.5, 27.36], [28.46, 31.74], [21.81, 33.93],
    [14.96, 35.24], [3.03, 35.68], [2.54, 35.13],
    [1.86, 26.05], [-4.99, 25.61], [-12.81, 23.86],
    [-17.7, 22.11], [-23.18, 18.6], [-26.01, 14.99],
    [-26.6, 10.83], [-25.43, 7.77], [-22.4, 5.03],
    [-17.51, 2.85], [-11.83, 1.53], [0.78, 0.98],
    [0.39, -11.49], [-1.86, -12.04],
]

# Inner blue ellipse — the "blue tongue" extending into the red zone.
# Points INSIDE this contour also belong to the blue group.
BLUE_RED_TONGUE = [
    [3.42, 1.09], [0.78, 1.42], [2.05, 26.05],
    [9.1, 26.05], [17.9, 24.3], [23.18, 21.67],
    [26.21, 18.28], [27.19, 15.21], [26.99, 12.59],
    [26.01, 10.18], [23.77, 7.66], [20.05, 5.25],
    [15.16, 3.28], [3.42, 1.09],
]

# Navy boundary within the blue group.
# Points INSIDE = Dark Navy,  outside (but still blue) = Royal Blue.
NAVY_BOUNDARY = [
    [39.8, 20.68], [38.44, 23.75], [35.5, 27.25],
    [32.57, 29.44], [26.11, 32.5], [26.41, 58.33],
    [23.47, 62.27], [21.42, 64.13], [16.72, 66.98],
    [8.12, 69.38], [-4.6, 69.17], [-19.27, 65.88],
    [-37.65, 58.99], [-33.74, 66.21], [-28.46, 71.68],
    [-21.81, 75.84], [-13.59, 78.69], [-2.25, 80.22],
    [8.51, 80.0], [16.72, 78.69], [24.94, 75.84],
    [31.2, 71.9], [34.52, 68.62], [37.26, 64.46],
    [39.22, 59.64], [40.2, 54.83], [39.8, 20.68],
]

# Maroon boundary within the red group.
# Points INSIDE = Dark Maroon,  outside (but still red) = Bright Red.
MAROON_BOUNDARY = [
    [4.21, -80.22], [-10.07, -79.34], [-15.75, -78.25],
    [-22.4, -76.06], [-27.09, -73.65], [-30.61, -71.03],
    [-32.76, -68.84], [-35.31, -64.9], [-37.07, -58.99],
    [-38.83, -2.3], [-38.63, 1.86], [-36.48, -2.3],
    [-32.18, -6.24], [-27.29, -8.86], [-21.61, -10.62],
    [-24.16, -10.07], [-24.45, -10.4], [-24.45, -56.8],
    [-22.49, -59.86], [-18.48, -63.69], [-13.99, -66.1],
    [-8.31, -67.85], [3.62, -68.29], [11.64, -67.2],
    [20.64, -65.01], [38.04, -58.55], [36.28, -62.93],
    [32.96, -68.18], [29.83, -71.46], [26.11, -74.31],
    [21.61, -76.72], [14.96, -78.91], [4.21, -80.22],
]


# ═══════════════════════════════════════════════════════════════
#  CONTOUR PADDING  –  push silhouette-adjacent points outward
# ═══════════════════════════════════════════════════════════════

def _capsule_silhouette_radius(z):
    """Return the capsule's X-extent at height Z (the 2-D silhouette)."""
    cap = CAP_HEIGHT_MM
    cyl_half = (OVERALL_HEIGHT_MM - 2.0 * cap) / 2.0
    r = RADIUS_MM

    if abs(z) <= cyl_half:
        return r
    elif z > cyl_half:
        dz = z - cyl_half
        if dz >= cap:
            return 0.0
        cos_t = dz / cap
        return r * math.sqrt(max(0.0, 1.0 - cos_t * cos_t))
    else:
        dz = -z - cyl_half
        if dz >= cap:
            return 0.0
        cos_t = dz / cap
        return r * math.sqrt(max(0.0, 1.0 - cos_t * cos_t))


def pad_contour(contour, pad):
    """
    For each contour point that sits near the capsule silhouette,
    push it outward so the contour extends *past* the capsule edge.
    Interior points (well inside the capsule) are left unchanged.
    """
    cap = CAP_HEIGHT_MM
    cyl_half = (OVERALL_HEIGHT_MM - 2.0 * cap) / 2.0
    half_h = cyl_half + cap

    out = []
    for x, z in contour:
        nx, nz = x, z

        # ── X: push outward if close to silhouette radius ──
        sil_r = _capsule_silhouette_radius(z)
        if sil_r > 0 and abs(x) > sil_r - pad:
            sign = 1.0 if x >= 0 else -1.0
            nx = sign * (sil_r + pad)

        # ── Z: push outward if close to top / bottom poles ──
        if z > half_h - pad:
            nz = half_h + pad
        elif z < -half_h + pad:
            nz = -half_h - pad

        out.append([nx, nz])
    return out


# Apply padding to all contours at module load time
BLUE_RED_MAIN   = pad_contour(BLUE_RED_MAIN,   CONTOUR_PADDING_MM)
BLUE_RED_TONGUE = pad_contour(BLUE_RED_TONGUE,  CONTOUR_PADDING_MM)
NAVY_BOUNDARY   = pad_contour(NAVY_BOUNDARY,    CONTOUR_PADDING_MM)
MAROON_BOUNDARY = pad_contour(MAROON_BOUNDARY,  CONTOUR_PADDING_MM)


# ═══════════════════════════════════════════════════════════════
#  POINT-IN-POLYGON  (ray casting)
# ═══════════════════════════════════════════════════════════════

def point_in_polygon(x, z, poly):
    """Return True if (x, z) is inside the closed polygon."""
    n = len(poly)
    inside = False
    j = n - 1
    for i in range(n):
        xi, zi = poly[i]
        xj, zj = poly[j]
        if ((zi > z) != (zj > z)) and \
           (x < (xj - xi) * (z - zi) / (zj - zi) + xi):
            inside = not inside
        j = i
    return inside


def classify_face(x, z):
    """
    Classify a point (X, Z) into one of four colour regions.
    Returns: 'royal_blue', 'dark_navy', 'bright_red', or 'dark_maroon'.
    """
    # Step 1: blue group or red group?
    is_blue = (point_in_polygon(x, z, BLUE_RED_MAIN) or
               point_in_polygon(x, z, BLUE_RED_TONGUE))

    if is_blue:
        # Step 2a: navy or royal blue?
        if point_in_polygon(x, z, NAVY_BOUNDARY):
            return "dark_navy"
        return "royal_blue"
    else:
        # Step 2b: maroon or bright red?
        if point_in_polygon(x, z, MAROON_BOUNDARY):
            return "dark_maroon"
        return "bright_red"


# ═══════════════════════════════════════════════════════════════
#  UTILITIES
# ═══════════════════════════════════════════════════════════════

def srgb_to_linear(c):
    return (c / 12.92) if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

def hex_to_linear(h):
    h = h.lstrip("#")
    return tuple(srgb_to_linear(int(h[i:i+2], 16) / 255.0) for i in (0, 2, 4))

def purge_scene():
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    for store in (bpy.data.meshes, bpy.data.materials, bpy.data.node_groups):
        for b in list(store):
            if b.users == 0:
                store.remove(b)

def setup_units():
    s = bpy.context.scene
    s.unit_settings.system       = 'METRIC'
    s.unit_settings.scale_length = 0.001
    s.unit_settings.length_unit  = 'MILLIMETERS'

def make_material(name, hex_colour):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    r, g, b = hex_to_linear(hex_colour)
    bsdf.inputs["Base Color"].default_value = (r, g, b, 1.0)
    bsdf.inputs["Roughness"].default_value  = 0.35
    return mat


# ═══════════════════════════════════════════════════════════════
#  CAPSULE WITH ELLIPTICAL (FLATTENED) CAPS
# ═══════════════════════════════════════════════════════════════

def build_capsule(name, height, radius, cap_h, segments):
    cyl_half = (height - 2.0 * cap_h) / 2.0
    assert cyl_half >= 0, "height must be >= 2 × cap_height"

    arc_n = max(8, segments // 4)
    cyl_n = max(4, segments // 4)

    bm = bmesh.new()
    pts = []

    # Top pole
    pts.append(bm.verts.new((0.0, 0.0, cyl_half + cap_h)))

    # Top elliptical cap
    for i in range(1, arc_n + 1):
        t = (math.pi / 2.0) * i / arc_n
        x = radius * math.sin(t)
        z = cyl_half + cap_h * math.cos(t)
        pts.append(bm.verts.new((x, 0.0, z)))

    # Cylinder wall
    for i in range(1, cyl_n):
        z = cyl_half * (1.0 - 2.0 * i / cyl_n)
        pts.append(bm.verts.new((radius, 0.0, z)))

    # Bottom elliptical cap
    for i in range(0, arc_n + 1):
        t = (math.pi / 2.0) * i / arc_n
        x = radius * math.cos(t)
        z = -cyl_half - cap_h * math.sin(t)
        pts.append(bm.verts.new((x, 0.0, z)))

    edges = [bm.edges.new((pts[i], pts[i + 1]))
             for i in range(len(pts) - 1)]

    bmesh.ops.spin(
        bm, geom=edges + pts,
        axis=(0, 0, 1), cent=(0, 0, 0), dvec=(0, 0, 0),
        angle=math.pi * 2.0, steps=segments,
        use_merge=True, use_normal_flip=False, use_duplicate=False,
    )
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.001)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    mesh.update()
    bm.free()

    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj


# ═══════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════

def main():
    purge_scene()
    setup_units()

    h   = OVERALL_HEIGHT_MM
    r   = RADIUS_MM
    w   = WALL_THICKNESS_MM
    cap = CAP_HEIGHT_MM
    seg = SEGMENTS

    # ── 1.  Build & hollow capsule ─────────────────────────────
    print("[1/4]  Building capsule …")
    capsule = build_capsule("Capsule", h, r, cap, seg)

    print("[2/4]  Hollowing (Solidify) …")
    bpy.context.view_layer.objects.active = capsule
    capsule.select_set(True)
    mod = capsule.modifiers.new("Shell", 'SOLIDIFY')
    mod.thickness       = w
    mod.offset          = -1.0
    mod.use_even_offset = True
    mod.use_rim         = True
    bpy.ops.object.modifier_apply(modifier=mod.name)

    # Subdivide mesh for smoother colour boundaries
    if SUBDIVISIONS > 0:
        print(f"       Subdividing ×{SUBDIVISIONS} for smooth boundaries …")
        sub = capsule.modifiers.new("Subsurf", 'SUBSURF')
        sub.levels = SUBDIVISIONS
        sub.render_levels = SUBDIVISIONS
        sub.subdivision_type = 'SIMPLE'   # SIMPLE preserves shape exactly
        bpy.ops.object.modifier_apply(modifier=sub.name)
        print(f"       → {len(capsule.data.polygons)} faces")

    # ── 2.  Create materials ───────────────────────────────────
    print("[3/4]  Classifying faces via contour boundaries …")
    materials = {}
    mat_indices = {}
    for mat_name, hex_col in MAT_DEFS.items():
        mat = make_material(mat_name, hex_col)
        capsule.data.materials.append(mat)
        idx = len(capsule.data.materials) - 1
        materials[mat_name] = mat
        mat_indices[mat_name] = idx

    # ── 3.  Classify every face ────────────────────────────────
    mesh = capsule.data
    counts = {"royal_blue": 0, "dark_navy": 0, "bright_red": 0, "dark_maroon": 0}

    for poly in mesh.polygons:
        cx, cy, cz = poly.center
        # Project onto XZ plane (ignore Y — "cookie cutter" extrusion)
        region = classify_face(cx, cz)
        poly.material_index = mat_indices[region]
        counts[region] += 1

    mesh.update()
    print(f"   Face counts: {counts}")

    # ── 4.  Separate by material ───────────────────────────────
    if SEPARATE_PIECES:
        print("[4/4]  Separating into individual objects …")
        bpy.context.view_layer.objects.active = capsule
        capsule.select_set(True)
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.separate(type='MATERIAL')
        bpy.ops.object.mode_set(mode='OBJECT')

    # Fix normals
    for obj in bpy.context.scene.objects:
        if obj.type != 'MESH':
            continue
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.normals_make_consistent(inside=False)
        bpy.ops.object.mode_set(mode='OBJECT')
        obj.select_set(False)

    # Select all pieces
    for obj in bpy.context.scene.objects:
        obj.select_set(True)

    n = len([o for o in bpy.context.scene.objects if o.type == 'MESH'])
    print(f"✓  Done – {n} piece(s).")


if __name__ == "__main__":
    main()