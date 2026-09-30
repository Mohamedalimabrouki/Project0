"""
Shared Blender helpers for the Resonance scenes (tested with Blender 5.0.1).

These scripts build every scene from scratch with Python, so the .blend
files can always be regenerated. They can run inside Blender (Scripting
tab) or headless with the `bpy` module from PyPI (pip install bpy==5.0.1).
"""

import json
import math
import os

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

PALETTE = {
    "force": "#D55E00", "motion": "#0072B2", "energy": "#E69F00", "fluid": "#56B4E9",
    "field": "#CC79A7", "balance": "#009E73", "highlight": "#F0E442",
    "ink": "#12161C", "steel": "#8C96A0", "paper": "#F4F3EF",
}


def srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hex_linear(hex_code, alpha=1.0):
    h = hex_code.lstrip("#")
    return tuple(srgb_to_linear(int(h[i:i + 2], 16) / 255) for i in (0, 2, 4)) + (alpha,)


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    # every keyframe is computed from physics, one per frame: no easing between them
    bpy.context.preferences.edit.keyframe_new_interpolation_type = "LINEAR"
    return scene


def render_settings(scene, samples=8, fps=30, width=1920, height=1080, motion_blur=True):
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    # EP_DEVICE=OPTIX / CUDA / HIP / METAL / ONEAPI renders on the graphics card (much faster on a laptop
    # with a good GPU); the default stays CPU, which is what the cloud sessions have
    device = os.environ.get("EP_DEVICE", "CPU").upper()
    if device != "CPU":
        try:
            prefs = bpy.context.preferences.addons["cycles"].preferences
            prefs.compute_device_type = device
            prefs.get_devices()
            gpus = [d for d in prefs.devices if d.type == device]
            if not gpus:
                raise RuntimeError("no such graphics card found")
            for d in prefs.devices:
                d.use = d.type == device
            scene.cycles.device = "GPU"
            print(f"Cycles on the GPU: {', '.join(d.name for d in gpus)}", flush=True)
        except Exception as e:  # unknown device type or no GPU: stay on the CPU
            print(f"GPU {device} not available ({e}); rendering on the CPU", flush=True)
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.fps = fps
    scene.cycles.samples = samples
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.adaptive_threshold = 0.02
    scene.cycles.use_denoising = True
    scene.cycles.denoiser = "OPENIMAGEDENOISE"
    scene.cycles.denoising_prefilter = "FAST"
    scene.cycles.denoising_input_passes = "RGB_ALBEDO_NORMAL"
    scene.cycles.seed = 7
    scene.cycles.use_animated_seed = False      # same noise pattern every frame: no flicker
    scene.cycles.max_bounces = 4
    scene.cycles.diffuse_bounces = 2
    scene.cycles.glossy_bounces = 2
    scene.cycles.transmission_bounces = 2
    scene.cycles.transparent_max_bounces = 4
    scene.cycles.caustics_reflective = False
    scene.cycles.caustics_refractive = False
    scene.cycles.blur_glossy = 1.0
    scene.cycles.use_light_tree = False
    scene.render.use_persistent_data = True
    scene.render.use_motion_blur = motion_blur
    scene.render.motion_blur_shutter = 0.5
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "None"
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.color_depth = "8"
    scene.render.film_transparent = False


def world(scene, hex_code=PALETTE["ink"], strength=1.0):
    w = bpy.data.worlds.new("EP World")
    scene.world = w
    bg = w.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = hex_linear(hex_code)
    bg.inputs["Strength"].default_value = strength
    return w


def principled(name, color, metallic=0.0, roughness=0.4, coat=0.0, emission=None, emission_strength=0.0):
    m = bpy.data.materials.new(name)
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = color if len(color) == 4 else tuple(color) + (1.0,)
    b.inputs["Metallic"].default_value = metallic
    b.inputs["Roughness"].default_value = roughness
    if coat:
        b.inputs["Coat Weight"].default_value = coat
        b.inputs["Coat Roughness"].default_value = 0.08
    if emission is not None:
        b.inputs["Emission Color"].default_value = emission
        b.inputs["Emission Strength"].default_value = emission_strength
    m.diffuse_color = b.inputs["Base Color"].default_value
    return m


def grid_floor_material(name="EP Grid Floor", spacing=0.5, base=PALETTE["ink"],
                        line=PALETTE["steel"], line_strength=0.10, roughness=0.32,
                        fade_start=6.0, fade_end=26.0, base_scale=1.0, specular=0.35):
    """Dark floor with thin grid lines that keep a constant width on screen and fade with distance."""
    m = bpy.data.materials.new(name)
    nt = m.node_tree
    nodes, links = nt.nodes, nt.links
    bsdf = nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Specular IOR Level"].default_value = specular

    tex = nodes.new("ShaderNodeTexCoord")
    sep = nodes.new("ShaderNodeSeparateXYZ")
    links.new(tex.outputs["Object"], sep.inputs[0])
    cam = nodes.new("ShaderNodeCameraData")

    def math(op, a=None, b=None, val_a=None, val_b=None):
        n = nodes.new("ShaderNodeMath")
        n.operation = op
        if a is not None:
            links.new(a, n.inputs[0])
        elif val_a is not None:
            n.inputs[0].default_value = val_a
        if b is not None:
            links.new(b, n.inputs[1])
        elif val_b is not None:
            n.inputs[1].default_value = val_b
        return n.outputs[0]

    # line half-width grows with distance, so lines stay about 1.2 px wide
    half_w = math("MULTIPLY", cam.outputs["View Distance"], val_b=0.00052)
    half_w = math("MAXIMUM", half_w, val_b=0.0015)

    def axis_line(coord, width=None):
        width = width or half_w
        u = math("DIVIDE", coord, val_b=spacing)
        u = math("ADD", u, val_b=0.5)
        fr = math("FRACT", u)
        d = math("SUBTRACT", fr, val_b=0.5)
        d = math("ABSOLUTE", d)
        d = math("MULTIPLY", d, val_b=spacing)             # metres to the nearest line
        ratio = math("DIVIDE", d, width)
        return math("SUBTRACT", val_a=1.0, b=ratio)       # >0 on the line

    lx = axis_line(sep.outputs["X"])
    # lines running across the view are foreshortened: widen them by 1/|incoming.z|
    geo = nodes.new("ShaderNodeNewGeometry")
    sep_i = nodes.new("ShaderNodeSeparateXYZ")
    links.new(geo.outputs["Incoming"], sep_i.inputs[0])
    fore = math("ABSOLUTE", sep_i.outputs["Z"])
    fore = math("MAXIMUM", fore, val_b=0.12)
    half_w_across = math("DIVIDE", half_w, fore)
    half_w_across = math("MULTIPLY", half_w_across, val_b=0.8)
    ly = axis_line(sep.outputs["Y"], half_w_across)
    lm = math("MAXIMUM", lx, ly)
    lm = math("MAXIMUM", lm, val_b=0.0)
    lm = math("MINIMUM", lm, val_b=1.0)
    # fade the grid with distance (avoids shimmering far away)
    fade = nodes.new("ShaderNodeMapRange")
    links.new(cam.outputs["View Distance"], fade.inputs["Value"])
    fade.inputs["From Min"].default_value = fade_start
    fade.inputs["From Max"].default_value = fade_end
    fade.inputs["To Min"].default_value = 1.0
    fade.inputs["To Max"].default_value = 0.0
    lm = math("MULTIPLY", lm, fade.outputs["Result"])
    # grid only on the flat floor, not on the curved backdrop
    zmask = math("LESS_THAN", sep.outputs["Z"], val_b=0.02)
    lm = math("MULTIPLY", lm, zmask)
    lm = math("MULTIPLY", lm, val_b=line_strength)

    mix = nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    b = hex_linear(base)
    mix.inputs[6].default_value = tuple(c * base_scale for c in b[:3]) + (1.0,)
    mix.inputs[7].default_value = hex_linear(line)
    links.new(lm, mix.inputs[0])
    links.new(mix.outputs[2], bsdf.inputs["Base Color"])
    return m


def area_light(name, location, target, size, energy, color=(1, 1, 1), size_y=None):
    light = bpy.data.lights.new(name, "AREA")
    light.energy = energy
    light.color = color
    if size_y is None:
        light.shape = "DISK"
        light.size = size
    else:
        light.shape = "RECTANGLE"
        light.size = size
        light.size_y = size_y
    obj = bpy.data.objects.new(name, light)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = location
    aim(obj, target)
    return obj


def spot_light(name, location, target, energy, spot_size_deg=40, blend=0.6, radius=0.3, color=(1, 1, 1)):
    light = bpy.data.lights.new(name, "SPOT")
    light.energy = energy
    light.spot_size = math.radians(spot_size_deg)
    light.spot_blend = blend
    light.shadow_soft_size = radius
    light.color = color
    obj = bpy.data.objects.new(name, light)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = location
    aim(obj, target)
    return obj


def aim(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def camera(name, location, target, lens=50.0, sensor=36.0, dof_distance=None, fstop=5.6):
    cam = bpy.data.cameras.new(name)
    cam.lens = lens
    cam.sensor_width = sensor
    cam.sensor_fit = "HORIZONTAL"
    cam.clip_start = 0.05
    cam.clip_end = 300.0
    if dof_distance is not None:
        cam.dof.use_dof = True
        cam.dof.focus_distance = dof_distance
        cam.dof.aperture_fstop = fstop
    obj = bpy.data.objects.new(name, cam)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = location
    aim(obj, target)
    bpy.context.scene.camera = obj
    return obj


def link(obj, collection=None):
    (collection or bpy.context.scene.collection).objects.link(obj)
    return obj


def cylinder_between(name, p0, p1, radius, material, vertices=24):
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=d.length,
                                        location=(p0 + p1) / 2)
    obj = bpy.context.object
    obj.name = name
    obj.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    obj.data.materials.append(material)
    bpy.ops.object.shade_smooth()
    return obj


def bevel(obj, width, segments=3):
    mod = obj.modifiers.new("Bevel", "BEVEL")
    mod.width = width
    mod.segments = segments
    mod.limit_method = "ANGLE"
    return mod


def export_projection(scene, cam_obj, points_fn, frames, path):
    """
    For every frame, project named 3D points to screen pixels (origin top-left).
    points_fn(frame) returns {name: (x, y, z)}. Used to pin 2D arrows and labels
    exactly onto the 3D objects.
    """
    w, h = scene.render.resolution_x, scene.render.resolution_y
    out = {}
    for f in frames:
        scene.frame_set(f)
        pts = {}
        for key, p in points_fn(f).items():
            co = world_to_camera_view(scene, cam_obj, Vector(p))
            pts[key] = [co.x * w, (1.0 - co.y) * h, co.z]
        out[f] = pts
    with open(path, "w") as fh:
        json.dump(out, fh)


def render_frames(scene, out_dir, prefix, start, end, step=1, skip_existing=True):
    os.makedirs(out_dir, exist_ok=True)
    for f in range(start, end + 1, step):
        path = os.path.join(out_dir, f"{prefix}_{f:04d}.png")
        if skip_existing and os.path.exists(path) and os.path.getsize(path) > 0:
            continue
        scene.frame_set(f)
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        print(f"rendered {path}", flush=True)


def cove(name, material, width=120.0, front=-40.0, flat_to=7.0, radius=5.0, height=30.0, segments=24):
    """A photo-studio infinity cove: flat floor that curves up into a back wall (no horizon line)."""
    prof = [(front, 0.0), (flat_to, 0.0)]
    for i in range(1, segments + 1):
        a = (math.pi / 2) * i / segments
        prof.append((flat_to + radius * math.sin(a), radius - radius * math.cos(a)))
    prof.append((flat_to + radius, height))
    verts, faces = [], []
    for x in (-width / 2, width / 2):
        for (y, z) in prof:
            verts.append((x, y, z))
    n = len(prof)
    for i in range(n - 1):
        faces.append((i, i + 1, n + i + 1, n + i))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.data.materials.append(material)
    for poly in mesh.polygons:
        poly.use_smooth = True
    return obj
