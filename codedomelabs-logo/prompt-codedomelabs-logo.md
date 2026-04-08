# Gemini Prompt for Claude

# Claude Task: Blender 5.01 Python Script Generation

**Objective:** You are an expert Python developer specializing in the **Blender 5.01 bpy API**. Your task is to write a script that processes an attached 2D vector logo (`<logo>`) and transforms it into a 3D, hollowed, multi-colored capsule.

### 1. Parameters & Configuration

Use the following variables (all dimensions in **mm**):

- `<logo>`: Attached PNG vector illustration.
- `<overall_height_mm>`: [User: Insert Value]
- `<radius_mm>`: [User: Insert Value]
- `<wall_thickness_mm>`: [User: Insert Value]
- `<cutter_kerf_mm>`: [User: Insert Value] (Extremely thin)
- `<tessellation_density>`: 64 segments.

### 2. Required Execution Steps

**Step A: Vision Analysis**

- Analyze `<logo>` to identify 6 distinct color regions.
- Extract the **Hex codes** for these 6 regions and store them in an array.
- Identify the boundary paths between these regions to serve as cutting guides.

**Step B: 3D Base Generation**

- Create a **Spherocylinder** (pill shape) by revolving a 2D profile 360° around the **Y-axis**.
- The profile consists of a central line segment of length `(<overall_height_mm> - (2 * <radius_mm>))` and two semi-circular arcs.
- **Hollowing:** Use a Shell or Solidify operation to create a hollow interior with a thickness of `<wall_thickness_mm>`.

**Step C: The Z-Axis "Cookie Cutter"**

- Project the internal boundary paths of the `<logo>` as a 2D mesh.
- **Extrude** these paths along the **Z-axis** to create a 3D "cookie cutter" grid.
- The thickness of these cutting walls must be exactly `<cutter_kerf_mm>`.
- Ensure the cutter is centered and deep enough to penetrate both the front and back walls of the hollow capsule.

**Step D: Boolean Operation & Partitioning**

- Perform a **Boolean Difference** operation using the "cookie cutter" against the hollow capsule.
- The result should be 6 distinct mesh segments (or groups of segments) that remain in contact but are mathematically separate.

**Step E: Material & Color Assignment**

- Create 6 Blender materials named according to their respective Hex codes.
- Assign these materials to the 6 segments identified during the Boolean process, matching the spatial layout of the original `<logo>`.

### 3. Technical Constraints

- **API Target:** Ensure compatibility with **Blender 5.01** `bpy` methods.
- **Mesh Integrity:** Ensure all normals are oriented correctly (outward for the shell, inward for the hollow) and the mesh is manifold.
- **Cleanup:** The script should remove the temporary "cookie cutter" object after the operation is complete.