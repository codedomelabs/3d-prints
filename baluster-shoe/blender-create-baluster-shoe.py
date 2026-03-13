"""
══════════════════════════════════════════════════════════════════════════════
  Blender Python Script: 3D-Printable Interlocking Baluster Shoe
  Compatible with: Blender 5.0.x
══════════════════════════════════════════════════════════════════════════════

  PURPOSE
  ───────
  Generates a two-part decorative base cover ("shoe") for a wrought-iron
  stair post. The shoe is sliced diagonally so it can be snapped around
  a post that is already installed. Alignment pins and sockets allow the
  two halves to lock together precisely after 3D printing.

  GEOMETRY OVERVIEW
  ─────────────────
  • Outer shape  : Truncated square pyramid (frustum)
                   Base 45 × 45 mm  |  Top 22 × 22 mm  |  Height 15 mm
  • Center hole  : Vertical square prism, 13.5 × 13.5 mm
                   (≈ 0.4 mm clearance on each face of a 12.7 mm / ½″ post)
  • Split plane  : x = y  (diagonal from corner −,− to corner +,+)
  • Shoe_Half_A  : x ≥ y region  →  carries 2 alignment pins
  • Shoe_Half_B  : x ≤ y region  →  carries 2 matching sockets

  ALIGNMENT SYSTEM
  ────────────────
  Pins  : Ø 3.0 mm × 4 mm protrusion, embedded 1 mm into Half A
  Sockets : Ø 3.2 mm × 5 mm deep  (0.2 mm diametral clearance for FDM)
  Pin axis : perpendicular to the cut plane, i.e. (−1, +1, 0) / √2

  HOW TO RUN
  ──────────
  1.  Open Blender 5.0
  2.  Switch to the Scripting workspace
  3.  Paste this entire script into the editor
  4.  Click "Run Script"
  5.  Two objects appear: Shoe_Half_A (blue tint) and Shoe_Half_B (offset)

  HOW TO EXPORT FOR 3D PRINTING
  ──────────────────────────────
  File → Export → STL (.stl)
  • Select "Shoe_Half_A" only → enable "Selection Only" → Export
  • Repeat for "Shoe_Half_B"
  Print each half flat-side-down (the mating face) — no supports needed.

══════════════════════════════════════════════════════════════════════════════
"""

import bpy
import bmesh
import math
from mathutils import Vector, Matrix

# ══════════════════════════════════════════════════════════════════════════════
#  §0  SCENE SETUP
# ══════════════════════════════════════════════════════════════════════════════

# Remove everything in the current scene (the default cube, lights, camera)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Configure metric units — set scale_length so that
# 1 Blender unit displays as 1 mm in the viewport.
scene = bpy.context.scene
scene.unit_settings.system      = 'METRIC'
scene.unit_settings.length_unit = 'MILLIMETERS'
scene.unit_settings.scale_length = 0.001   # 1 BU = 1 mm

# ══════════════════════════════════════════════════════════════════════════════
#  §1  DESIGN PARAMETERS  (all values in millimetres)
# ══════════════════════════════════════════════════════════════════════════════

# ── Frustum (truncated pyramid) ─────────────────────────────────────────────
BASE_HALF  = 22.5   # half of 45 mm base  → full base = 45 × 45 mm
TOP_HALF   = 11.0   # half of 22 mm top   → full top  = 22 × 22 mm
HEIGHT     = 15.0   # total height of shoe

# ── Square through-hole ──────────────────────────────────────────────────────
HOLE_HALF  = 6.75   # half of 13.5 mm     → full hole = 13.5 × 13.5 mm
                    # 12.7 mm post + 0.8 mm total clearance (0.4 mm each side)

# ── Alignment pins & sockets ─────────────────────────────────────────────────
PIN_R      = 1.5    # pin radius   → 3.0 mm diameter
SOC_R      = 1.6    # socket radius → 3.2 mm diameter  (0.2 mm clearance)
PIN_PROT   = 3.0    # protruding length of pin beyond the mating face (mm)
PIN_EMBED  = 1.0    # depth the pin sinks INTO Half A for a solid boolean union
SOC_EXTRA  = 1.0    # socket is this much deeper than the pin (tolerance budget)

# ── Quality / misc ───────────────────────────────────────────────────────────
CYL_SEGS   = 24     # number of facets on cylindrical features
BIG        = 250.0  # over-size dimension for boolean cutter geometry

# Derived
PIN_TOTAL  = PIN_PROT + PIN_EMBED               # full length of pin cylinder
SOC_DEPTH  = PIN_PROT + SOC_EXTRA               # total socket bore depth

# ══════════════════════════════════════════════════════════════════════════════
#  §2  UTILITY FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def deselect_all():
    bpy.ops.object.select_all(action='DESELECT')


def make_active(obj):
    """Deselect everything, then select and activate obj."""
    deselect_all()
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def link_to_scene(obj):
    """Link a bare object into the active collection."""
    bpy.context.collection.objects.link(obj)
    return obj


def apply_boolean(target, cutter, operation='DIFFERENCE'):
    """
    Apply a boolean modifier to *target* using *cutter*, then delete *cutter*.
    operation : 'DIFFERENCE' | 'UNION' | 'INTERSECT'
    """
    make_active(target)
    mod             = target.modifiers.new('_bool_op', 'BOOLEAN')
    mod.operation   = operation
    mod.solver      = 'EXACT'      # best accuracy; fall back to 'FAST' if needed
    mod.object      = cutter
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter, do_unlink=True)


def bm_to_object(name, bm):
    """
    Recalculate outward-facing normals, bake a BMesh into a new mesh,
    wrap it in an Object, link it to the scene, and return the Object.
    """
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name + '_mesh')
    bm.to_mesh(me)
    bm.free()
    me.update()
    obj = bpy.data.objects.new(name, me)
    return link_to_scene(obj)


def rotation_matrix_z_to_vec(target_vec):
    """
    Return a 4×4 rotation Matrix that maps the local Z-axis (0,0,1)
    to *target_vec*.  Used to orient cylinder axes.
    """
    v = target_vec.normalized()
    z = Vector((0.0, 0.0, 1.0))
    dot = z.dot(v)
    if dot > 0.9999:
        return Matrix.Identity(4)
    if dot < -0.9999:
        return Matrix.Rotation(math.pi, 4, Vector((1.0, 0.0, 0.0)))
    axis  = z.cross(v).normalized()
    angle = math.acos(max(-1.0, min(1.0, dot)))
    return Matrix.Rotation(angle, 4, axis)


# ══════════════════════════════════════════════════════════════════════════════
#  §3  GEOMETRY BUILDERS
# ══════════════════════════════════════════════════════════════════════════════

def build_frustum():
    """
    Build the truncated square pyramid (frustum) centred at the origin.
    Base 45 × 45 mm at z = 0, Top 22 × 22 mm at z = HEIGHT.
    The pyramid tapers symmetrically on all four sides.
    """
    s, t, h = BASE_HALF, TOP_HALF, HEIGHT
    bm = bmesh.new()

    # ── Base ring (z = 0) ──────────────────────────────────────────────────
    b0 = bm.verts.new((-s, -s, 0))   # front-left
    b1 = bm.verts.new(( s, -s, 0))   # front-right
    b2 = bm.verts.new(( s,  s, 0))   # back-right
    b3 = bm.verts.new((-s,  s, 0))   # back-left

    # ── Top ring (z = h) ───────────────────────────────────────────────────
    t0 = bm.verts.new((-t, -t, h))
    t1 = bm.verts.new(( t, -t, h))
    t2 = bm.verts.new(( t,  t, h))
    t3 = bm.verts.new((-t,  t, h))

    # ── Faces (winding order → outward normals after recalc) ───────────────
    bm.faces.new([b3, b2, b1, b0])          # bottom cap
    bm.faces.new([t0, t1, t2, t3])          # top cap
    bm.faces.new([b0, b1, t1, t0])          # side: –y face
    bm.faces.new([b1, b2, t2, t1])          # side: +x face
    bm.faces.new([b2, b3, t3, t2])          # side: +y face
    bm.faces.new([b3, b0, t0, t3])          # side: –x face

    return bm_to_object('_Frustum', bm)


def build_square_prism(name, half_w, z_bot, z_top):
    """
    Build an axis-aligned square prism from z_bot to z_top
    with half-width *half_w* in both X and Y.
    Used for the through-hole cutter and for the diagonal split cutters.
    """
    w = half_w
    bm = bmesh.new()

    bot = [bm.verts.new((-w, -w, z_bot)),
           bm.verts.new(( w, -w, z_bot)),
           bm.verts.new(( w,  w, z_bot)),
           bm.verts.new((-w,  w, z_bot))]

    top = [bm.verts.new((-w, -w, z_top)),
           bm.verts.new(( w, -w, z_top)),
           bm.verts.new(( w,  w, z_top)),
           bm.verts.new((-w,  w, z_top))]

    bm.faces.new([bot[3], bot[2], bot[1], bot[0]])   # bottom
    bm.faces.new([top[0], top[1], top[2], top[3]])   # top
    for i in range(4):
        j = (i + 1) % 4
        bm.faces.new([bot[i], bot[j], top[j], top[i]])

    return bm_to_object(name, bm)


def build_diagonal_cutter(side):
    """
    Build a triangular prism that covers exactly one diagonal half of the XY plane.

    The diagonal split runs along the line x = y
    (i.e. from the (−,−) corner to the (+,+) corner of the base square).

      side='A' → keeps the region where x ≥ y  (Half A)
      side='B' → keeps the region where x ≤ y  (Half B)

    The prism is tall enough (±5 mm beyond the shoe) to cleanly intersect
    the entire frustum.
    """
    B        = BIG
    z_low    = -5.0
    z_high   = HEIGHT + 5.0

    # Each triangle fills one of the two diagonal half-planes.
    # All three vertices of the triangle lie on or outside the cut plane x = y,
    # so the interior of the triangle covers the desired half-space.
    if side == 'A':
        # Triangle covering x ≥ y
        #   (B, -B): x >> y  ✓
        #   (B,  B): x = y   boundary ✓
        #   (-B,-B): x = y   boundary ✓
        pts_2d = [( B, -B), ( B,  B), (-B, -B)]
    else:
        # Triangle covering x ≤ y
        #   (-B,  B): x << y  ✓
        #   (-B, -B): x = y   boundary ✓
        #   ( B,  B): x = y   boundary ✓
        pts_2d = [(-B,  B), (-B, -B), ( B,  B)]

    bm = bmesh.new()
    bot = [bm.verts.new((x, y, z_low))  for x, y in pts_2d]
    top = [bm.verts.new((x, y, z_high)) for x, y in pts_2d]

    bm.faces.new([bot[2], bot[1], bot[0]])          # bottom cap
    bm.faces.new([top[0], top[1], top[2]])          # top cap
    for i in range(3):
        j = (i + 1) % 3
        bm.faces.new([bot[i], bot[j], top[j], top[i]])

    return bm_to_object(f'_DiagCut_{side}', bm)


def build_cylinder_along_axis(name, radius, length, center, axis_vec):
    """
    Build a closed cylinder.
      center   : mathutils.Vector — midpoint of the cylinder axis
      axis_vec : mathutils.Vector — direction of the cylinder axis (any magnitude)
      length   : total length (cylinder extends ±length/2 from *center* along axis)
      radius   : cylinder radius

    The cylinder is built in local space (axis = Z) then rotated to align
    with axis_vec before baking into world-space vertex positions.
    """
    R    = rotation_matrix_z_to_vec(axis_vec.normalized())
    half = length / 2.0
    bm   = bmesh.new()

    def ring(z_local):
        """Return a ring of BMesh vertices at the given local Z offset."""
        verts = []
        for i in range(CYL_SEGS):
            a     = 2.0 * math.pi * i / CYL_SEGS
            local = Vector((radius * math.cos(a), radius * math.sin(a), z_local))
            world = center + (R @ local)
            verts.append(bm.verts.new(world))
        return verts

    bot = ring(-half)
    top = ring( half)

    # Side quads
    for i in range(CYL_SEGS):
        j = (i + 1) % CYL_SEGS
        bm.faces.new([bot[i], bot[j], top[j], top[i]])

    # End caps
    bm.faces.new(bot[::-1])   # bottom — reversed for outward normal
    bm.faces.new(top)          # top

    return bm_to_object(name, bm)


# ══════════════════════════════════════════════════════════════════════════════
#  §4  CONSTRUCT THE BASE SHAPE
#       frustum → subtract square through-hole
# ══════════════════════════════════════════════════════════════════════════════

print("[1/6] Building frustum ...")
shoe = build_frustum()

print("[2/6] Subtracting square centre hole ...")
hole_cutter = build_square_prism('_HoleCut', HOLE_HALF, -1.0, HEIGHT + 1.0)
apply_boolean(shoe, hole_cutter, 'DIFFERENCE')


# ══════════════════════════════════════════════════════════════════════════════
#  §5  DUPLICATE & SPLIT DIAGONALLY
# ══════════════════════════════════════════════════════════════════════════════

print("[3/6] Splitting diagonally into two halves ...")

# Duplicate the base shape — one copy per half
make_active(shoe)
bpy.ops.object.duplicate()
half_b = bpy.context.active_object   # duplicate becomes Half B
half_a = shoe                         # original becomes Half A

# Intersect each copy with its respective triangular prism
# INTERSECT retains only the geometry that lies inside the cutter volume.
apply_boolean(half_a, build_diagonal_cutter('A'), 'INTERSECT')
apply_boolean(half_b, build_diagonal_cutter('B'), 'INTERSECT')


# ══════════════════════════════════════════════════════════════════════════════
#  §6  ALIGNMENT PIN & SOCKET SYSTEM
# ══════════════════════════════════════════════════════════════════════════════
#
#  Cut plane  :  x = y
#  Pin axis   :  (-1, +1, 0) / √2  — perpendicular to cut plane,
#                pointing FROM Half A INTO Half B
#
#  PIN FACE POINTS (on the x = y plane, verified within the pyramid walls):
#
#    fp0 = ( 9,  9,  4)
#      z =  4 → pyramid half-side ≈ 19.4 mm  → 9 < 19.4 ✓ (inside pyramid)
#              → hole  half-side  =  6.75 mm  → 9 > 6.75 ✓ (outside hole)
#      x = y = 9  ✓  (on cut plane)
#
#    fp1 = (-9, -9, 11)
#      z = 11 → pyramid half-side ≈ 14.1 mm  → 9 < 14.1 ✓ (inside pyramid)
#              → hole  half-side  =  6.75 mm  → 9 > 6.75 ✓ (outside hole)
#      x = y = -9 ✓  (on cut plane)
#
#  PIN CYLINDER PLACEMENT:
#    bottom end = face_pt − PIN_EMBED × axis  (1 mm inside Half A)
#    top    end = face_pt + PIN_PROT  × axis  (4 mm into Half B)
#    cylinder centre = face_pt + (PIN_PROT − PIN_EMBED)/2 × axis
#
#  SOCKET CYLINDER PLACEMENT:
#    Goes entirely into Half B.
#    Centre = face_pt + (SOC_DEPTH/2) × axis
# ──────────────────────────────────────────────────────────────────────────────

print("[4/6] Adding alignment pins to Half A ...")

PIN_AXIS  = Vector((-1.0, 1.0, 0.0)).normalized()

FACE_POINTS = [
    Vector(( 9.0,  9.0,  4.0)),   # lower pin
    Vector((-9.0, -9.0, 11.0)),   # upper pin
]

# ── Pins on Half A ─────────────────────────────────────────────────────────
for i, fp in enumerate(FACE_POINTS):
    # The pin cylinder straddles the mating face:
    #   embedded portion: 1 mm into Half A  (below fp along −PIN_AXIS)
    #   protruding portion: 4 mm into Half B (above fp along +PIN_AXIS)
    pin_center = fp + ((PIN_PROT - PIN_EMBED) / 2.0) * PIN_AXIS
    pin = build_cylinder_along_axis(
        f'_Pin_{i}', PIN_R, PIN_TOTAL, pin_center, PIN_AXIS
    )
    # UNION adds the protruding pin to Half A's mesh
    apply_boolean(half_a, pin, 'UNION')

print("[5/6] Adding alignment sockets to Half B ...")

# ── Sockets in Half B ──────────────────────────────────────────────────────
for i, fp in enumerate(FACE_POINTS):
    # Socket bore starts at the mating face and goes entirely into Half B.
    sock_center = fp + (SOC_DEPTH / 2.0) * PIN_AXIS
    sock = build_cylinder_along_axis(
        f'_Sock_{i}', SOC_R, SOC_DEPTH, sock_center, PIN_AXIS
    )
    # DIFFERENCE cuts the socket void into Half B
    apply_boolean(half_b, sock, 'DIFFERENCE')


# ══════════════════════════════════════════════════════════════════════════════
#  §7  FINAL NAMING, MATERIALS & VIEWPORT LAYOUT
# ══════════════════════════════════════════════════════════════════════════════

print("[6/6] Finalising objects ...")

half_a.name = 'Shoe_Half_A'   # the half with protruding pins
half_b.name = 'Shoe_Half_B'   # the half with socket bores

# Offset Half B along X so both halves are visible side-by-side in the viewport
half_b.location.x = 60.0   # 60 mm gap

# Optional: assign distinct viewport colours so the two halves are easy to tell apart
def assign_viewport_color(obj, rgba):
    """Set the object's viewport display colour (no material needed)."""
    obj.color = rgba

assign_viewport_color(half_a, (0.2, 0.5, 1.0, 1.0))   # blue  → pins
assign_viewport_color(half_b, (1.0, 0.5, 0.2, 1.0))   # orange → sockets

# Smooth shading (non-critical — geometry is valid either way)
for obj in (half_a, half_b):
    make_active(obj)
    try:
        bpy.ops.object.shade_smooth()
    except Exception:
        pass

# Deselect all and make Half A active for inspection
make_active(half_a)


# ══════════════════════════════════════════════════════════════════════════════
#  §8  SUMMARY REPORT
# ══════════════════════════════════════════════════════════════════════════════

print()
print("╔══════════════════════════════════════════════════════════╗")
print("║        Baluster Shoe — Generation Complete               ║")
print("╠══════════════════════════════════════════════════════════╣")
print(f"║  Outer shape  : {BASE_HALF*2:.0f}×{BASE_HALF*2:.0f} mm base → {TOP_HALF*2:.0f}×{TOP_HALF*2:.0f} mm top    ║")
print(f"║  Height       : {HEIGHT:.0f} mm                                  ║")
print(f"║  Centre hole  : {HOLE_HALF*2:.1f}×{HOLE_HALF*2:.1f} mm  (12.7 mm post + clearance)  ║")
print(f"║  Split plane  : x = y  (corner-to-corner diagonal)      ║")
print("╠══════════════════════════════════════════════════════════╣")
print(f"║  Shoe_Half_A (blue)  : 2 pins  Ø{PIN_R*2:.0f} mm × {PIN_PROT:.0f} mm long       ║")
print(f"║  Shoe_Half_B (orange): 2 bores Ø{SOC_R*2:.1f} mm × {SOC_DEPTH:.0f} mm deep       ║")
print(f"║  Diametral clearance : {(SOC_R-PIN_R)*2*1000:.0f} µm  (0.2 mm)                ║")
print("╠══════════════════════════════════════════════════════════╣")
print("║  EXPORT INSTRUCTIONS                                     ║")
print("║  File → Export → STL                                     ║")
print("║  Select Half A only → ✓ Selection Only → Export STL      ║")
print("║  Repeat for Half B                                       ║")
print("║  Print each half mating-face-down — no supports needed   ║")
print("╚══════════════════════════════════════════════════════════╝")