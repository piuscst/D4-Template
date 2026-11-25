# /// script
# requires-python = "==3.13.*"
# dependencies = ["bpy==5.2.*"]
# ///
"""Blender as a library: build the kit, art/dragon_kit.glb and art/dragon_kit.blend.

deno task art      uses Blender 5.2 (the header above)
deno task art:lts  uses Blender 4.5 LTS, for Intel Macs, which Blender 5 dropped
deno task blender  opens art/dragon_kit.blend in the Blender app, to look around

Every piece fits in one 1x1 grid cell and is made by a builder function listed in
PIECES, TILES, or PICKUPS. The starter's builders all use voxels(),
but a builder can make any geometry: swap one out and the game picks it up by name.

Conventions the game relies on (Blender coordinates, Z up):
  - A cell spans x and y from -0.5 to 0.5. +Y is the direction of travel.
  - Openings must match Kit.OPENINGS in core/kit.gd: the head and tail join the
    body at the back and front, the turn joins the back and the right side.
  - Floors lie with their top at z = 0; everything else stands on z = 0.

Editing by hand in Blender instead:
  The game loads only art/dragon_kit.glb, never the .blend. After editing a .blend in
  Blender, export it yourself with File > Export > glTF 2.0 (.glb/.gltf):
    Format: glTF Binary (.glb)        File: art/dragon_kit.glb
    Include: no Limit to boxes ticked; Cameras and Punctual Lights unticked
    Transform: +Y Up ticked           Mesh: Apply Modifiers ticked
  and keep the object names (head, straight, turn, tail, floor, wall, ...).
  WARNING: deno task art rewrites BOTH art/dragon_kit.blend and art/dragon_kit.glb,
  erasing hand edits. Before editing, File > Save As a copy such as art/my_kit.blend
  (deno task blender art/my_kit.blend reopens it). The tradeoff: from then on the
  kit lives in that file, not in this script, so a change here no longer reaches it
  unless you redo it by hand, and a .blend is hard to review in a diff.
"""

from math import pi
from pathlib import Path

import bpy  # first: importing bpy is what makes bmesh and mathutils available
import bmesh
from mathutils import Matrix

# Paths from this file, not the current directory, so the script works from anywhere.
# Build them with pathlib rather than gluing strings together, as Blender's gotchas advise:
# https://docs.blender.org/api/current/info_gotchas_file_paths_and_encoding.html
ART = Path(__file__).resolve().parent.parent / "art"
GLB = ART / "dragon_kit.glb"
BLEND = ART / "dragon_kit.blend"

VOXELS = 4  # voxels per cell edge

MATERIALS = []  # every material, in order; a face's material_index points into this list
PALETTE = {}  # voxel character -> index in MATERIALS; filled in by make_materials()


def reset_scene():
    """Start from an empty file, so nothing from Blender's default scene (cube, camera,
    light) or an earlier run leaks into the kit."""
    bpy.ops.wm.read_factory_settings(use_empty=True)


# --- Materials ------------------------------------------------------------------


def pbr_material(name, color, metallic=0.0, roughness=0.5, emission=None, strength=1.0):
    """A Principled BSDF using only inputs glTF keeps. Returns its index in MATERIALS.
    Emission above about 1 blooms in the game, because the stage has glow switched on."""
    material = bpy.data.materials.new(name)
    if bpy.app.version < (5, 0):  # 4.x starts without nodes; 5.x always has them and deprecates use_nodes
        material.use_nodes = True
    # Find the node by type, not by its name, which a non-English Blender may translate:
    # https://terminalskills.io/skills/blender-scripting (section 9, Assign materials)
    bsdf = next(node for node in material.node_tree.nodes if node.type == 'BSDF_PRINCIPLED')
    bsdf.inputs["Base Color"].default_value = srgb(color)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    if emission:  # glTF keeps a color up to 1 plus a strength (KHR_materials_emissive_strength)
        bsdf.inputs["Emission Color"].default_value = srgb(emission)
        bsdf.inputs["Emission Strength"].default_value = strength
    material.diffuse_color = srgb(color)  # the viewport's solid color, for the GUI
    MATERIALS.append(material)
    return len(MATERIALS) - 1


def srgb(hex_code):
    """A hex color as Blender wants it: linear RGBA."""
    channels = [int(hex_code.lstrip("#")[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels) + (1.0,)


def make_materials():
    """One material per voxel character. Runs after reset_scene(), which would erase them."""
    PALETTE.update({
        "#": pbr_material("Train Paint", "#b82f35", metallic=0.1, roughness=0.42),
        "*": pbr_material("Gold", "#f2bf3a", metallic=1.0, roughness=0.3),
        "e": pbr_material("Headlamp", "#ffe4a6", emission="#ffc962", strength=1.6),
        "o": pbr_material("Tail Lamp", "#fb5a37", emission="#f53720", strength=1.2),
        "s": pbr_material("Yard Pavers", "#777f84", roughness=0.85),
        "t": pbr_material("Inset Pavers", "#626b71", roughness=0.9),
        "w": pbr_material("Brick", "#6b4d3d", roughness=0.9),
        "p": pbr_material("Passenger Jacket", "#45b8ed", roughness=0.7),
        "m": pbr_material("Dark Steel", "#283137", metallic=0.25, roughness=0.65),
        "c": pbr_material("Coach Cream", "#e8c9a0", roughness=0.55),
        "g": pbr_material("Windows", "#455e70", roughness=0.28),
    })


# --- Builders: each adds one piece's geometry to a bmesh ------------------------------
# bmesh builds meshes from data alone, with no edit mode or selection involved; Blender
# calls it the best way to create and edit faces:
# https://docs.blender.org/api/current/info_gotchas_meshes.html


def voxels(bm, layers, below_ground=0):
    """Add one cube per palette character. Each layer is a top-down view of the cell,
    from the ground up: the top row is the front (+Y), the bottom row is the back."""
    for z, layer in enumerate(layers):
        for row, line in enumerate(layer.split()):
            for column, char in enumerate(line):
                if char not in PALETTE:
                    continue
                center = (
                    (column + 0.5) / VOXELS - 0.5,
                    0.5 - (row + 0.5) / VOXELS,
                    (z - below_ground + 0.5) / VOXELS,
                )
                cube = bmesh.ops.create_cube(bm, size=1 / VOXELS, matrix=Matrix.Translation(center))
                for face in {f for v in cube["verts"] for f in v.link_faces}:
                    face.material_index = PALETTE[char]


def box(bm, center, size, color):
    matrix = Matrix.Translation(center) @ Matrix.Diagonal((*size, 1.0))
    cube = bmesh.ops.create_cube(bm, size=1.0, matrix=matrix)
    for face in {f for v in cube["verts"] for f in v.link_faces}:
        face.material_index = PALETTE[color]


def cylinder(bm, center, radius, length, color, axis="Z"):
    rotation = Matrix.Identity(4) if axis == "Z" else Matrix.Rotation(pi / 2, 4, axis)
    shape = bmesh.ops.create_cone(
        bm, cap_ends=True, segments=12, radius1=radius, radius2=radius,
        depth=length, matrix=Matrix.Translation(center) @ rotation,
    )
    for face in {f for v in shape["verts"] for f in v.link_faces}:
        face.material_index = PALETTE[color]


def chassis(bm):
    box(bm, (0, 0, 0.18), (0.62, 0.72, 0.15), "m")
    for x in (-0.32, 0.32):
        for y in (-0.23, 0.23):
            cylinder(bm, (x, y, 0.11), 0.11, 0.09, "m", axis="Y")


def coupler(bm, x, y):
    # Every connection reaches the cell edge with the same height and width.
    size = (0.22, 0.18, 0.12) if x else (0.18, 0.22, 0.12)
    box(bm, (x * 0.39, y * 0.39, 0.18), size, "m")


def build_head(bm):
    chassis(bm)
    coupler(bm, 0, -1)
    box(bm, (0, -0.16, 0.44), (0.54, 0.31, 0.42), "#")
    box(bm, (0, -0.16, 0.68), (0.62, 0.37, 0.08), "m")
    for x in (-0.272, 0.272):
        box(bm, (x, -0.16, 0.51), (0.015, 0.16, 0.14), "g")
    cylinder(bm, (0, 0.15, 0.41), 0.185, 0.43, "#", axis="X")
    cylinder(bm, (0, 0.36, 0.41), 0.153, 0.04, "m", axis="X")
    cylinder(bm, (0, 0.38, 0.42), 0.066, 0.045, "e", axis="X")
    cylinder(bm, (0, 0.25, 0.68), 0.068, 0.18, "m")
    cylinder(bm, (0, 0.25, 0.78), 0.087, 0.045, "m")
    box(bm, (0, 0.4, 0.17), (0.54, 0.14, 0.10), "#")


def build_straight(bm):
    chassis(bm)
    coupler(bm, 0, 1)
    coupler(bm, 0, -1)
    box(bm, (0, 0, 0.42), (0.56, 0.65, 0.36), "#")
    box(bm, (0, 0, 0.49), (0.57, 0.66, 0.19), "c")
    box(bm, (0, 0, 0.63), (0.61, 0.70, 0.08), "m")
    for x in (-0.289, 0.289):
        for y in (-0.20, 0, 0.20):
            box(bm, (x, y, 0.49), (0.018, 0.13, 0.10), "g")


def build_turn(bm):
    # A short square coach connects the back of the tile to its right side.
    chassis(bm)
    coupler(bm, 0, -1)
    coupler(bm, 1, 0)
    box(bm, (0.035, -0.035, 0.42), (0.55, 0.55, 0.36), "#")
    box(bm, (0.035, -0.035, 0.49), (0.56, 0.56, 0.19), "c")
    box(bm, (0.035, -0.035, 0.63), (0.60, 0.60, 0.08), "m")
    for offset in (-0.10, 0.10):
        box(bm, (0.325, offset - 0.035, 0.49), (0.02, 0.14, 0.10), "g")
        box(bm, (offset + 0.035, -0.325, 0.49), (0.14, 0.02, 0.10), "g")


def build_tail(bm):
    chassis(bm)
    coupler(bm, 0, 1)
    box(bm, (0, 0.02, 0.40), (0.52, 0.53, 0.32), "#")
    box(bm, (0, 0.02, 0.58), (0.60, 0.61, 0.075), "m")
    box(bm, (0, 0.055, 0.66), (0.35, 0.27, 0.12), "#")
    box(bm, (0, 0.055, 0.75), (0.40, 0.32, 0.064), "m")
    for x in (-0.17, 0.17):
        box(bm, (x, -0.25, 0.37), (0.08, 0.035, 0.07), "o")


def build_floor(bm):
    voxels(bm, ["""
        ssss
        stts
        stss
        ssss
        """], below_ground=1)


def build_wall(bm):
    box(bm, (0, 0, 0.10), (1.0, 1.0, 0.20), "w")
    box(bm, (0, 0, 0.34), (0.91, 0.91, 0.29), "m")
    box(bm, (0, 0, 0.50), (0.96, 0.96, 0.065), "*")
    box(bm, (0, 0, 0.558), (0.91, 0.91, 0.052), "m")


def build_passenger(bm):
    voxels(bm, ["""
        ....
        .ww.
        .ww.
        ....
        """, """
        ....
        .pp.
        .pp.
        ....
        """, """
        ....
        pppp
        .pp.
        ....
        """, """
        ....
        .**.
        .**.
        ....
        """])


PIECES = {  # the train kit; the game finds each mesh by these names
    "head": build_head,
    "straight": build_straight,
    "turn": build_turn,
    "tail": build_tail,
}
TILES = {  # one entry per kind in core/board.gd's TILES; a new kind is one builder and one line
    "floor": build_floor,
    "wall": build_wall,
}
PICKUPS = {"passenger": build_passenger}


# --- Objects and layout ---------------------------------------------------------


def make_object(scene, name, build, location=(0, 0, 0)):
    """Run a builder on a fresh bmesh and turn the result into a mesh object called name.
    The game uses only the mesh; location just spreads the kit out for model viewers."""
    bm = bmesh.new()
    build(bm)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    # Keep only the materials this object uses, renumbering faces to match.
    used = sorted({p.material_index for p in mesh.polygons})
    mesh.polygons.foreach_set("material_index", [used.index(p.material_index) for p in mesh.polygons])
    for index in used:
        mesh.materials.append(MATERIALS[index])
    # bpy.data creates the object directly; bpy.ops.mesh.primitive_*_add would depend on
    # the active object and selection, which an operator reads from the context:
    # https://docs.blender.org/api/current/info_gotchas_operators.html
    obj = bpy.data.objects.new(name, mesh)
    # Blender quietly changes a name that is too long or already taken, and the game
    # finds pieces by name, so fail loudly instead:
    # https://docs.blender.org/api/current/info_gotchas_internal_data_and_python_objects.html
    if obj.name != name:
        raise ValueError(f"Blender renamed {name!r} to {obj.name!r}; pick a shorter, unique name")
    obj.location = location
    scene.collection.objects.link(obj)


def lay_out_kit(scene):
    """One row per registry, so a GLB viewer shows a tidy catalog instead of every piece
    stacked on the origin. Each mesh is still modeled around its own cell's center."""
    spacing = 1.5
    for row, registry in enumerate([PIECES, TILES, PICKUPS]):
        for column, (name, build) in enumerate(registry.items()):
            make_object(scene, name, build, location=(column * spacing, -row * spacing, 0))


# --- Export ---------------------------------------------------------------------


def export():
    """Write the .glb the game loads, then the .blend for the Blender app.
    glTF export has no data API, only an operator, so every option that could depend
    on what is selected or active is spelled out. These match the steps in the docstring.
    Enum values such as 'GLB' get single quotes, Blender's own style:
    https://docs.blender.org/api/current/info_best_practice.html"""
    bpy.ops.export_scene.gltf(
        filepath=str(GLB),
        export_format='GLB',
        use_selection=False,
        export_apply=True,
        export_cameras=False,
        export_lights=False,
    )
    # No art/dragon_kit.blend1 backup: the script is the backup, and the next run rewrites this.
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))


def main():
    reset_scene()
    make_materials()
    lay_out_kit(bpy.context.scene)
    export()
    print(f"Built {GLB.name} and {BLEND.name} with Blender {bpy.app.version_string}")


# Run only as a script, not when another file imports this one for its builders:
# https://docs.python.org/3/library/__main__.html
if __name__ == "__main__":
    main()
