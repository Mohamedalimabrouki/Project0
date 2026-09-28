"""
Engineering Phenomena - house colours for Blender.

How to use (no coding needed):
  1. In Blender, open the "Scripting" tab at the top of the window.
  2. Click "Open", pick this file, then press the Run button (the triangle).
  3. The house materials appear in the file, for example:
       "EP Force"       - a normal material for 3D objects (reacts to light)
       "EP Force Flat"  - a flat colour for arrows, labels and diagrams
     A colour palette called "Engineering Phenomena" is also added for
     Grease Pencil and painting.

Running it again is safe: it resets the EP materials to the house values
instead of making copies. Other materials are never touched.

Tip: with Colour Management set to "Standard", the Flat materials render
at the hex codes of the style guide (difference invisible to the eye).
"""

import bpy

PALETTE_NAME = "Engineering Phenomena"
PREFIX = "EP "

# Same values as assets/palette/palette.json and docs/STYLE_GUIDE.md
COLOURS = [
    ("Force", "#D55E00"),
    ("Motion", "#0072B2"),
    ("Energy", "#E69F00"),
    ("Fluid", "#56B4E9"),
    ("Field", "#CC79A7"),
    ("Balance", "#009E73"),
    ("Highlight", "#F0E442"),
    ("Ink", "#12161C"),
    ("Steel", "#8C96A0"),
    ("Paper", "#F4F3EF"),
]


def hex_to_srgb(hex_code):
    hex_code = hex_code.lstrip("#")
    return tuple(int(hex_code[i:i + 2], 16) / 255 for i in (0, 2, 4))


def srgb_to_linear(value):
    # Blender stores material colours in linear light, the style guide uses sRGB hex
    if value <= 0.04045:
        return value / 12.92
    return ((value + 0.055) / 1.055) ** 2.4


def hex_to_linear_rgba(hex_code):
    return tuple(srgb_to_linear(c) for c in hex_to_srgb(hex_code)) + (1.0,)


def fresh_node_tree(material):
    # Blender 5 always uses nodes and deprecates this switch; older versions need it
    if bpy.app.version < (5, 0, 0):
        material.use_nodes = True
    tree = material.node_tree
    tree.nodes.clear()
    output = tree.nodes.new("ShaderNodeOutputMaterial")
    output.location = (300, 0)
    return tree, output


def build_shaded(name, rgba):
    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    tree, output = fresh_node_tree(material)
    bsdf = tree.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = rgba
    bsdf.inputs["Roughness"].default_value = 0.45
    tree.links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
    material.diffuse_color = rgba  # colour shown in the Solid viewport
    return material


def build_flat(name, rgba):
    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    tree, output = fresh_node_tree(material)
    emission = tree.nodes.new("ShaderNodeEmission")
    emission.inputs["Color"].default_value = rgba
    emission.inputs["Strength"].default_value = 1.0
    tree.links.new(emission.outputs["Emission"], output.inputs["Surface"])
    material.diffuse_color = rgba
    return material


def palette_value(hex_code):
    # Older Blender stores palette colours as sRGB, Blender 5 as linear
    subtype = bpy.types.PaletteColor.bl_rna.properties["color"].subtype
    if subtype == "COLOR_GAMMA":
        return hex_to_srgb(hex_code)
    return hex_to_linear_rgba(hex_code)[:3]


def build_palette():
    palette = bpy.data.palettes.get(PALETTE_NAME) or bpy.data.palettes.new(PALETTE_NAME)
    palette.colors.clear()
    for _, hex_code in COLOURS:
        palette.colors.new().color = palette_value(hex_code)
    return palette


def main():
    for label, hex_code in COLOURS:
        rgba = hex_to_linear_rgba(hex_code)
        build_shaded(f"{PREFIX}{label}", rgba)
        build_flat(f"{PREFIX}{label} Flat", rgba)
    build_palette()
    print(f"{PALETTE_NAME}: {len(COLOURS) * 2} materials and 1 palette ready.")


if __name__ == "__main__":
    main()
