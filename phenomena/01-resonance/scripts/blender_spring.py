"""
Resonance - Blender scene: the mass on a spring, with a damper (the engineer's model).

Real, buildable numbers from physics.py: a 2 kg steel block (63 mm cube), a
spring of 1.5 mm wire and 30 mm coil diameter tuned to exactly 1 Hz, and a
small oil damper giving 5 % damping. The block is pulled 55 mm and released;
its motion is the exact damped free vibration x(t) from physics.py.

The spring is built with Geometry Nodes, so it stretches like a real spring
(its coils spread evenly) instead of being scaled.

Run headless:  python blender_spring.py --render
"""

import argparse
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import blender_common as bc  # noqa: E402
import physics  # noqa: E402

BUILD = os.environ.get("EP_BUILD", os.path.join(HERE, "..", "build"))
FPS = 30

SIDE = physics.BLOCK_SIDE          # 0.0634 m
REST_GAP = 0.20                    # m, spring length at rest (post face to block face)
POST_X = 0.0                       # x of the post face (the fixed end)
AXIS_Z = 0.012 + SIDE / 2          # height of the spring axis (block centre)
SPRING_Y = 0.0
DAMPER_Y = 0.0
SPRING_Z = 0.059                   # spring on top (as in the textbook drawing)
DAMPER_Z = 0.0265                  # damper below it
X0 = 0.055                         # m, initial pull
RELEASE = 0.8                      # s, release time within the shot


def spring_node_group(wire_r=0.00075, coil_r=0.015, turns=23):
    ng = bpy.data.node_groups.new("EP Spring", "GeometryNodeTree")
    ng.interface.new_socket(name="Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket(name="Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    length = ng.interface.new_socket(name="Length", in_out="INPUT", socket_type="NodeSocketFloat")
    length.default_value = REST_GAP
    nodes, links = ng.nodes, ng.links
    gin = nodes.new("NodeGroupInput")
    gout = nodes.new("NodeGroupOutput")
    spiral = nodes.new("GeometryNodeCurveSpiral")
    spiral.inputs["Resolution"].default_value = 48
    spiral.inputs["Rotations"].default_value = turns
    spiral.inputs["Start Radius"].default_value = coil_r
    spiral.inputs["End Radius"].default_value = coil_r
    links.new(gin.outputs["Length"], spiral.inputs["Height"])
    prof = nodes.new("GeometryNodeCurvePrimitiveCircle")
    prof.inputs["Resolution"].default_value = 10
    prof.inputs["Radius"].default_value = wire_r
    c2m = nodes.new("GeometryNodeCurveToMesh")
    links.new(spiral.outputs["Curve"], c2m.inputs["Curve"])
    links.new(prof.outputs["Curve"], c2m.inputs["Profile Curve"])
    smooth = nodes.new("GeometryNodeSetShadeSmooth")
    links.new(c2m.outputs["Mesh"], smooth.inputs["Geometry"])
    setmat = nodes.new("GeometryNodeSetMaterial")
    links.new(smooth.outputs["Geometry"], setmat.inputs["Geometry"])
    links.new(setmat.outputs["Geometry"], gout.inputs["Geometry"])
    return ng, setmat, length.identifier


def build_scene():
    scene = bc.reset_scene()
    bc.render_settings(scene, samples=10, fps=FPS)
    bc.world(scene, strength=1.0)

    steel = bc.principled("Block Steel", (0.72, 0.73, 0.75, 1.0), metallic=1.0, roughness=0.16)
    spring_mat = bc.principled("Spring Steel", (0.80, 0.81, 0.83, 1.0), metallic=1.0, roughness=0.12)
    anod = bc.principled("Anodised Base", (0.028, 0.031, 0.037, 1.0), metallic=0.7, roughness=0.34)
    rail_mat = bc.principled("Rail", (0.55, 0.57, 0.6, 1.0), metallic=1.0, roughness=0.22)
    damper_mat = bc.principled("Damper Body", (0.10, 0.11, 0.125, 1.0), metallic=0.9, roughness=0.28)
    rod_mat = bc.principled("Damper Rod", (0.85, 0.86, 0.88, 1.0), metallic=1.0, roughness=0.08)
    floor = bc.grid_floor_material(spacing=0.05, line_strength=0.28, roughness=0.5,
                                   fade_start=0.6, fade_end=2.2, base_scale=1.0, specular=0.25)
    # this floor sits at the scale of a lab bench: grid squares of 5 cm
    bc.cove("Bench Cove", floor, width=12.0, front=-4.0, flat_to=0.9, radius=0.8, height=4.0)

    # base plate and rail
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0.175, 0.0, 0.004))
    base = bpy.context.object
    base.name = "Base"
    base.scale = (0.47, 0.12, 0.008)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bc.bevel(base, 0.002, 3)
    base.data.materials.append(anod)
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0.2, 0.0, 0.0095))
    rail = bpy.context.object
    rail.name = "Rail"
    rail.scale = (0.4, 0.022, 0.005)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bc.bevel(rail, 0.0012, 2)
    rail.data.materials.append(rail_mat)

    # the fixed post
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(POST_X - 0.012, 0.0, 0.058))
    post = bpy.context.object
    post.name = "Post"
    post.scale = (0.024, 0.11, 0.1)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bc.bevel(post, 0.003, 3)
    post.data.materials.append(anod)

    # block (the mass)
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(POST_X + REST_GAP + SIDE / 2, 0.0, AXIS_Z))
    block = bpy.context.object
    block.name = "Mass 2 kg"
    block.scale = (SIDE, SIDE, SIDE)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bc.bevel(block, 0.0035, 5)
    block.data.materials.append(steel)
    bpy.ops.object.shade_smooth()

    # spring (geometry nodes, keyed length)
    mesh = bpy.data.meshes.new("Spring")
    spring = bpy.data.objects.new("Spring", mesh)
    scene.collection.objects.link(spring)
    spring.location = (POST_X, SPRING_Y, SPRING_Z)
    spring.rotation_euler = (0.0, math.radians(90), 0.0)     # the spiral axis (Z) now points along +X
    ng, setmat, length_id = spring_node_group()
    setmat.inputs["Material"].default_value = spring_mat
    mod = spring.modifiers.new("EP Spring", "NODES")
    mod.node_group = ng

    # spring end fittings
    for x in (POST_X + 0.004,):
        fit = bc.cylinder_between("Fitting", (x - 0.004, SPRING_Y, SPRING_Z), (x + 0.004, SPRING_Y, SPRING_Z),
                                  0.017, rail_mat)
    end_fit = bc.cylinder_between("Fitting Block", (-0.004, 0, 0), (0.004, 0, 0), 0.017, rail_mat)
    end_fit.parent = block
    end_fit.location = (-SIDE / 2 - 0.004, SPRING_Y, SPRING_Z - AXIS_Z)

    # damper: body fixed to the post, rod fixed to the block
    body = bc.cylinder_between("Damper Body", (POST_X, DAMPER_Y, DAMPER_Z), (POST_X + 0.105, DAMPER_Y, DAMPER_Z),
                               0.0078, damper_mat, vertices=32)
    ring = bc.cylinder_between("Damper Ring", (POST_X + 0.098, DAMPER_Y, DAMPER_Z),
                               (POST_X + 0.106, DAMPER_Y, DAMPER_Z), 0.0085, rail_mat, vertices=32)
    rod = bc.cylinder_between("Damper Rod", (-0.16, 0, 0), (0.0, 0, 0), 0.0022, rod_mat, vertices=16)
    rod.parent = block
    rod.location = (-SIDE / 2 - 0.08, DAMPER_Y, DAMPER_Z - AXIS_Z)

    # lights: large soft key from above, cool rim from behind, small warm kicker
    bc.spot_light("Key", (0.24, -0.25, 0.85), (0.17, 0.0, 0.03), 26.0, spot_size_deg=42, blend=0.9,
                  radius=0.18, color=(1.0, 0.97, 0.92))
    bc.area_light("Rim", (0.05, 0.6, 0.35), (0.17, 0.0, 0.05), 0.5, 9.0, color=(0.75, 0.86, 1.0))
    bc.area_light("Kicker", (0.75, -0.2, 0.18), (0.25, 0.0, 0.05), 0.25, 2.5, color=(1.0, 0.9, 0.8))
    bc.area_light("Top Strip", (0.17, 0.0, 0.55), (0.17, 0.0, 0.0), 0.7, 4.0, size_y=0.06)
    return scene, block, spring, mod, length_id


def block_positions(n_frames):
    t = np.arange(n_frames) / FPS
    x = np.where(t < RELEASE, X0 * np.clip(t / 0.5, 0, 1) ** 0.5 * 0 + X0,
                 physics.free_decay(t - RELEASE, X0))
    # before the release the block is held at x0 (it was pulled before the shot)
    return t, x


def setup_camera(n_frames):
    cam = bc.camera("Camera Spring", (0.62, -0.62, 0.30), (0.2, 0.0, 0.035), lens=50.0,
                    dof_distance=0.8, fstop=5.6)
    start = Vector((0.60, -0.52, 0.27))
    end = Vector((0.16, -0.80, 0.05))
    tgt0 = Vector((0.17, 0.0, 0.035))
    tgt1 = Vector((0.16, 0.0, 0.05))
    for f in range(n_frames):
        u = f / max(1, n_frames - 1)
        u = u * u * (3 - 2 * u)
        # arc around the rig (not a straight line): keeps the distance nearly constant
        a0 = math.atan2(start.y - tgt0.y, start.x - tgt0.x)
        a1 = math.atan2(end.y - tgt1.y, end.x - tgt1.x)
        r0 = math.hypot(start.x - tgt0.x, start.y - tgt0.y)
        r1 = math.hypot(end.x - tgt1.x, end.y - tgt1.y)
        a = a0 + (a1 - a0) * u
        r = r0 + (r1 - r0) * u
        tgt = tgt0.lerp(tgt1, u)
        cam.location = (tgt.x + r * math.cos(a), tgt.y + r * math.sin(a), start.z + (end.z - start.z) * u)
        bc.aim(cam, tgt)
        cam.data.dof.focus_distance = (Vector(cam.location) - Vector((0.22, 0.0, AXIS_Z))).length
        cam.keyframe_insert("location", frame=f)
        cam.keyframe_insert("rotation_euler", frame=f)
        cam.data.dof.keyframe_insert("focus_distance", frame=f)
    return cam


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", type=int, default=250)
    ap.add_argument("--render", action="store_true")
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--end", type=int, default=None)
    ap.add_argument("--step", type=int, default=1)
    ap.add_argument("--samples", type=int, default=10)
    ap.add_argument("--save-blend", default=None)
    ap.add_argument("--still", default=None, help="render only --start as a still image to this path")
    ap.add_argument("--width", type=int, default=1920)
    ap.add_argument("--height", type=int, default=1080)
    args = ap.parse_args([a for a in sys.argv[1:] if a != "--"])

    scene, block, spring, mod, length_id = build_scene()
    scene.cycles.samples = args.samples
    scene.render.resolution_x, scene.render.resolution_y = args.width, args.height
    n = args.frames
    scene.frame_start, scene.frame_end = 0, n - 1
    t, x = block_positions(n)
    x_rest = POST_X + REST_GAP + SIDE / 2
    for f in range(n):
        block.location.x = x_rest + x[f]
        block.keyframe_insert("location", index=0, frame=f)
        mod[length_id] = REST_GAP + x[f]
        mod.keyframe_insert(data_path=f'["{length_id}"]', frame=f)
    cam = setup_camera(n)

    if args.still:
        # a single high-resolution still (the hero image): no motion blur, careful denoising
        scene.render.use_motion_blur = False
        scene.cycles.denoising_prefilter = "ACCURATE"
        scene.frame_set(args.start)
        scene.render.filepath = os.path.abspath(args.still)
        bpy.ops.render.render(write_still=True)
        return

    out_dir = os.path.join(BUILD, "frames", "spring")
    os.makedirs(out_dir, exist_ok=True)

    def pts(frame):
        bx = x_rest + x[frame]
        return {
            "block": (bx, 0.0, AXIS_Z),
            "block_top": (bx, 0.0, AXIS_Z + SIDE / 2),
            "block_front": (bx + SIDE / 2, SPRING_Y, AXIS_Z),
            "block_back": (bx - SIDE / 2, SPRING_Y, AXIS_Z),
            "post": (POST_X, SPRING_Y, AXIS_Z),
            "spring_post": (POST_X, 0.0, SPRING_Z),
            "spring_block": (bx - SIDE / 2, 0.0, SPRING_Z),
            "damper_post": (POST_X, 0.0, DAMPER_Z),
            "damper_block": (bx - SIDE / 2, 0.0, DAMPER_Z),
            "post_top": (POST_X - 0.012, 0.0, 0.108),
            "post_bottom": (POST_X - 0.012, 0.0, 0.008),
            "rest": (x_rest, 0.0, AXIS_Z),
            "rail_end": (0.46, 0.0, 0.012),
        }
    bc.export_projection(scene, cam, pts, range(n), os.path.join(out_dir, "spring_points.json"))
    if args.save_blend:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(args.save_blend))
    if args.render:
        end = args.end if args.end is not None else n - 1
        bc.render_frames(scene, out_dir, "spring", args.start, end, args.step)


if __name__ == "__main__":
    main()
