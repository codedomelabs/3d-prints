import bpy

# 1. Clear existing objects
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# 2. Set Scene Units to Millimeters
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 0.001
scene.unit_settings.length_unit = 'MILLIMETERS'

# --- DIMENSIONS ---
base_diam = 250
base_height = 5
inset_diam = 202
inset_depth = 2

# 3. Create the Main Platform
bpy.ops.mesh.primitive_cylinder_add(
    vertices=128, 
    radius=base_diam / 2, 
    depth=base_height, 
    location=(0, 0, base_height / 2)
)
platform = bpy.context.active_object
platform.name = "Platform_Base"

# 4. Create the "Cutter" Cylinder (the hole)
# We make it slightly taller than the depth to ensure a clean cut through the bottom
bpy.ops.mesh.primitive_cylinder_add(
    vertices=128, 
    radius=inset_diam / 2, 
    depth=inset_depth * 2, 
    location=(0, 0, inset_depth / 2) 
)
cutter = bpy.context.active_object
cutter.name = "Inset_Cutter"

# 5. Apply Boolean Difference
bool_mod = platform.modifiers.new(name="Cut_Hole", type='BOOLEAN')
bool_mod.object = cutter
bool_mod.operation = 'DIFFERENCE'

# Apply the modifier and remove the cutter object
bpy.context.view_layer.objects.active = platform
bpy.ops.object.modifier_apply(modifier="Cut_Hole")
bpy.ops.object.select_all(action='DESELECT')
cutter.select_set(True)
bpy.ops.object.delete()

# Set view to see the result
platform.select_set(True)