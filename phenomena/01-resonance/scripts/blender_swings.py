"""
Resonance - Blender scene: the two swings (hook) and the single swing (natural rhythm).

The swing angles come from physics.py (a nonlinear pendulum with light
damping, pushed by identical half-sine pushes). One keyframe per frame.

Run headless:
  python blender_swings.py --shot hook --render
  python blender_swings.py --shot rhythm --render --start 0 --end 120
Or in Blender: Scripting tab, open this file, set SHOT below, Run.
"""

import argparse
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Euler, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import blender_common as bc  # noqa: E402
import physics  # noqa: E402

BUILD = os.environ.get("EP_BUILD", os.path.join(HERE, "..", "build"))
FPS = 30

PIVOT_H = 2.35           # m, height of the chain top
CHAIN_L = physics.SWING_L
SET_X = {"rhythm": -2.6, "random": 2.6}
CHAIN_Y = 0.22           # m, half distance between the two chains of one swing


def make_materials():
    steel = bc.principled("Swing Steel", bc.hex_linear(bc.PALETTE["steel"]), metallic=0.85, roughness=0.3)
    chain = bc.principled("Chain", (0.75, 0.77, 0.79, 1.0), metallic=1.0, roughness=0.2)
    rubber = bc.principled("Seat Rubber", (0.30, 0.31, 0.32, 1.0), roughness=0.6)
    floor = bc.grid_floor_material(spacing=0.5, line_strength=0.32, roughness=0.55,
                                   fade_start=7.0, fade_end=21.0, base_scale=1.35, specular=0.22)
    return dict(steel=steel, chain=chain, rubber=rubber, floor=floor)


def chain_link_mesh(material):
    """One chain link (an elongated torus), shared by every link as instances."""
    bpy.ops.mesh.primitive_torus_add(major_radius=0.0105, minor_radius=0.0032,
                                     major_segments=20, minor_segments=8)
    link = bpy.context.object
    link.scale = (1.0, 1.0, 1.0)
    # stretch along the chain axis (local Z after rotating the torus upright)
    link.rotation_euler = (math.radians(90), 0, 0)
    bpy.ops.object.transform_apply(rotation=True)
    link.scale = (1.0, 1.0, 1.55)
    bpy.ops.object.transform_apply(scale=True)
    link.data.materials.append(material)
    bpy.ops.object.shade_smooth()
    mesh = link.data
    bpy.data.objects.remove(link)
    return mesh


def build_swing_set(name, cx, mats, link_mesh):
    col = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(col)

    def to_col(obj):
        for c in obj.users_collection:
            c.objects.unlink(obj)
        col.objects.link(obj)
        return obj

    top = PIVOT_H + 0.06
    to_col(bc.cylinder_between(f"{name} Beam", (cx, -1.0, top), (cx, 1.0, top), 0.045, mats["steel"]))
    for sy in (-1, 1):
        for sx in (-1, 1):
            leg = bc.cylinder_between(f"{name} Leg", (cx, sy * 0.98, top + 0.02),
                                      (cx + sx * 1.22, sy * 1.08, 0.0), 0.038, mats["steel"])
            to_col(leg)
        # cross brace of the A-frame
        to_col(bc.cylinder_between(f"{name} Brace", (cx - 0.62, sy * 1.03, 1.18),
                                   (cx + 0.62, sy * 1.03, 1.18), 0.026, mats["steel"]))
    # hangers
    for y in (-CHAIN_Y, CHAIN_Y):
        bpy.ops.mesh.primitive_cylinder_add(radius=0.03, depth=0.07, location=(cx, y, PIVOT_H + 0.02))
        h = bpy.context.object
        h.rotation_euler = (math.radians(90), 0, 0)
        h.data.materials.append(mats["steel"])
        bpy.ops.object.shade_smooth()
        to_col(h)

    pivot = bpy.data.objects.new(f"{name} Pivot", None)
    pivot.empty_display_type = "ARROWS"
    pivot.location = (cx, 0.0, PIVOT_H)
    col.objects.link(pivot)

    # chains: instanced links, alternating 90 degrees
    pitch = 0.0305
    n = int((CHAIN_L - 0.05) / pitch)
    for y in (-CHAIN_Y, CHAIN_Y):
        for i in range(n):
            ob = bpy.data.objects.new(f"{name} Link", link_mesh)
            ob.location = (0.0, y, -0.02 - i * pitch)
            ob.rotation_euler = (0.0, 0.0, 0.0 if i % 2 == 0 else math.radians(90))
            ob.parent = pivot
            col.objects.link(ob)

    # seat: a rounded rubber seat, slightly curved like a belt swing
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, 0))
    seat = bpy.context.object
    seat.name = f"{name} Seat"
    seat.scale = (0.17, 0.50, 0.032)
    bpy.ops.object.transform_apply(scale=True)
    bc.bevel(seat, 0.013, 4)
    seat.data.materials.append(mats["rubber"])
    bpy.ops.object.shade_smooth()
    seat.parent = pivot
    seat.location = (0.0, 0.0, -CHAIN_L)
    to_col(seat)
    # small steel shackles where the chains meet the seat
    for y in (-CHAIN_Y, CHAIN_Y):
        bpy.ops.mesh.primitive_cylinder_add(radius=0.012, depth=0.05, location=(0, 0, 0))
        s = bpy.context.object
        s.data.materials.append(mats["steel"])
        s.parent = pivot
        s.location = (0.0, y, -CHAIN_L + 0.03)
        bpy.ops.object.shade_smooth()
        to_col(s)
    return pivot


def build_scene():
    scene = bc.reset_scene()
    bc.render_settings(scene, samples=8, fps=FPS)
    bc.world(scene, strength=1.0)
    mats = make_materials()
    link_mesh = chain_link_mesh(mats["chain"])

    bc.cove("Studio Cove", mats["floor"], flat_to=6.0, radius=6.0)

    pivots = {k: build_swing_set(f"Swing {k}", x, mats, link_mesh) for k, x in SET_X.items()}

    # lighting: a soft pool of light under each swing, cool rim lights behind, a gentle front fill
    for k, x in SET_X.items():
        bc.spot_light(f"Pool {k}", (x, 0.3, 7.0), (x, 0.0, 0.0), 520.0, spot_size_deg=50,
                      blend=0.95, radius=1.0, color=(1.0, 0.95, 0.88))
        bc.area_light(f"Rim {k}", (x + 0.6, 5.5, 4.0), (x, 0.0, 1.5), 3.0, 450.0,
                      color=(0.78, 0.88, 1.0))
    bc.area_light("Front Fill", (0.0, -11.0, 3.2), (0.0, 0.0, 1.3), 10.0, 90.0, color=(0.9, 0.95, 1.0))
    bc.area_light("Backdrop Glow", (0.0, 2.0, 6.5), (0.0, 12.0, 4.0), 12.0, 900.0, color=(0.55, 0.65, 0.8))
    return scene, pivots


def swing_angles(shot):
    d = physics.swing_data(os.path.join(BUILD, "data"))
    if shot == "hook":
        return d["t"], {"rhythm": d["rhythm_theta"], "random": d["random_theta"]}
    p = physics.pull_data(os.path.join(BUILD, "data"))
    return p["t"], {"rhythm": p["theta"], "random": np.zeros_like(p["t"])}


def ease(u):
    u = min(max(u, 0.0), 1.0)
    return u * u * (3 - 2 * u)


def setup_camera(shot, n_frames):
    if shot == "hook":
        cam = bc.camera("Camera Hook", (0.0, -13.3, 1.8), (0.0, 0.0, 1.02), lens=50.0)
        for f in range(n_frames):
            u = ease(f / max(1, n_frames - 1))
            cam.location = (0.0, -13.3 + 1.0 * u, 1.8 - 0.1 * u)
            bc.aim(cam, (0.0, 0.0, 1.02 - 0.03 * u))
            cam.keyframe_insert("location", frame=f)
            cam.keyframe_insert("rotation_euler", frame=f)
    else:
        x0 = SET_X["rhythm"]
        cam = bc.camera("Camera Rhythm", (x0 + 0.7, -9.4, 1.5), (x0, 0.0, 1.2), lens=50.0,
                        dof_distance=9.4, fstop=4.0)
        for f in range(n_frames):
            u = ease(f / max(1, n_frames - 1))
            cam.location = (x0 + 0.7 - 0.4 * u, -9.4 + 1.0 * u, 1.5 - 0.05 * u)
            bc.aim(cam, (x0 + 0.05 * u, 0.0, 1.2))
            cam.data.dof.focus_distance = (Vector(cam.location) - Vector((x0, 0.0, 1.2))).length
            cam.keyframe_insert("location", frame=f)
            cam.keyframe_insert("rotation_euler", frame=f)
            cam.data.dof.keyframe_insert("focus_distance", frame=f)
    return cam


def keyframe_swings(pivots, t_sim, angles, n_frames):
    for f in range(n_frames):
        t = f / FPS
        for k, pivot in pivots.items():
            th = float(np.interp(t, t_sim, angles[k]))
            pivot.rotation_euler = (0.0, -th, 0.0)      # positive angle = forward (+x)
            pivot.keyframe_insert("rotation_euler", index=1, frame=f)


def overlay_points(pivots):
    """Points the 2D layer needs: pivots, seats, and a point ahead of each seat (push direction)."""
    def fn(frame):
        pts = {}
        for k, pivot in pivots.items():
            m = pivot.matrix_world
            pts[f"{k}_pivot"] = tuple(m.translation)
            pts[f"{k}_seat"] = tuple(m @ Vector((0.0, 0.0, -CHAIN_L)))
            pts[f"{k}_seat_ahead"] = tuple(m @ Vector((0.35, 0.0, -CHAIN_L)))
            pts[f"{k}_seat_top"] = tuple(m @ Vector((0.0, 0.0, -CHAIN_L + 0.25)))
            pts[f"{k}_chain_front_top"] = tuple(m @ Vector((0.0, -CHAIN_Y, 0.0)))
            pts[f"{k}_chain_front_bottom"] = tuple(m @ Vector((0.0, -CHAIN_Y, -CHAIN_L)))
            pts[f"{k}_ground"] = (SET_X[k], 0.0, 0.0)
        return pts
    return fn


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shot", default="hook", choices=["hook", "rhythm"])
    ap.add_argument("--frames", type=int, default=None)
    ap.add_argument("--render", action="store_true")
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--end", type=int, default=None)
    ap.add_argument("--step", type=int, default=1)
    ap.add_argument("--samples", type=int, default=None, help="default: 8 for the hook, 6 for the single swing")
    ap.add_argument("--save-blend", default=None)
    args = ap.parse_args([a for a in sys.argv[1:] if a != "--"])

    n_frames = args.frames or (640 if args.shot == "hook" else 400)
    scene, pivots = build_scene()
    scene.cycles.samples = args.samples or (8 if args.shot == "hook" else 6)
    scene.frame_start, scene.frame_end = 0, n_frames - 1
    t_sim, angles = swing_angles(args.shot)
    keyframe_swings(pivots, t_sim, angles, n_frames)
    cam = setup_camera(args.shot, n_frames)

    if args.shot == "rhythm":
        # only the left swing set is in view: hide the other one to save render time
        for ob in bpy.data.collections["Swing random"].objects:
            ob.hide_render = True

    out_dir = os.path.join(BUILD, "frames", args.shot)
    os.makedirs(out_dir, exist_ok=True)
    bc.export_projection(scene, cam, overlay_points(pivots), range(n_frames),
                         os.path.join(out_dir, f"{args.shot}_points.json"))
    if args.save_blend:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(args.save_blend))
    if args.render:
        end = args.end if args.end is not None else n_frames - 1
        bc.render_frames(scene, out_dir, args.shot, args.start, end, args.step)


if __name__ == "__main__":
    main()
