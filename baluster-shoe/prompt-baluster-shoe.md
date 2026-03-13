## **The Prompt**

**Subject:** Blender Python Script for a 3D-Printable Interlocking Baluster Shoe

**Task:** Please write a Python script for Blender (version 5.0.1) that generates a two-part, 3D-printable "shoe" or base cover for a wrought iron stair post.

**Technical Requirements:**

1. **Units:** The script must use metric units (millimeters).  
2. **Main Geometry:** Create a **truncated square pyramid** (a pyramid with a flat top).  
   * **Base Dimensions:** 45mm x 45mm.  
   * **Top Dimensions:** 22mm x 22mm.  
   * **Total Height:** 15mm.  
3. **Center Hole:** Create a vertical square cutout through the center.  
   * **Hole Size:** 13.5mm x 13.5mm (This provides a clearance fit for a standard 1/2 inch or 12.7mm post).  
4. **The Split:**  
   * The model must be split into two identical halves using a **diagonal vertical cut** (from one corner of the base to the opposite corner). This allows the shoe to be placed around a post that is already installed.  
5. **Alignment/Joining Mechanism:** \- On the mating faces of the two halves, add a "pin and socket" system.  
   * **Pins:** Two cylindrical pins (3mm diameter, 4mm length) on one half.  
   * **Sockets:** Two corresponding holes on the other half with a 0.2mm tolerance (3.2mm diameter) to ensure a snug fit after 3D printing.  
6. **Blender Execution:**  
   * The script should clear the existing scene (delete the default cube).  
   * Use `bpy.ops.mesh` or `bmesh` to construct the geometry.  
   * Ensure the two halves are separate objects in Blender, named "Shoe\_Half\_A" and "Shoe\_Half\_B," so they can be exported as individual STLs.

