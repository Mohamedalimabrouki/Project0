"""
Resonance - Blender scene: the Taipei 101 tuned mass damper (hero shot).

Real proportions from the operator's published data: a 660 t steel sphere,
5.5 m wide, built from 41 steel plates each 125 mm thick, hung on 8 cables
(in 4 pairs) and restrained by 8 hydraulic viscous dampers underneath.
Its swing period is tuned to the tower's sway, about 6.8 s, which means an
effective pendulum length of about 11.5 m (L = g·T²/4π²).

Motion shown: a gentle swing of 0.15 m amplitude (a strong wind, not a storm;
the record is 1 m, Typhoon Soudelor, 2015).
"""

import argparse
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import blender_common as bc  # noqa: E402

BUILD = os.environ.get("EP_BUILD", os.path.join(HERE, "..", "build"))
FPS = 30

R = 2.75                      # m, sphere radius (5.5 m diameter)
PLATES = 41
PLATE_T = 0.125               # m
PERIOD = 6.8                  # s
L_EFF = 9.81 * PERIOD ** 2 / (4 * math.pi ** 2)    # 11.49 m
AMP = 0.15                    # m
CENTRE_Z = 4.2                # m, sphere centre above the floor below it
PIVOT_Z = CENTRE_Z + L_EFF


def gold_material():
    # yellow gold paint (the real ball is painted gold); metallic, slightly rough
    return bc.principled("Damper Gold", (0.95, 0.66, 0.2, 1.0), metallic=1.0, roughness=0.38)


def build_scene():
    scene = bc.reset_scene()
    bc.render_settings(scene, samples=8, fps=FPS)
    bc.world(scene, strength=1.0)
    gold = gold_material()
    steel = bc.principled("Frame Steel", (0.22, 0.24, 0.27, 1.0), metallic=0.9, roughness=0.35)
    cable_mat = bc.principled("Cable", (0.55, 0.57, 0.6, 1.0), metallic=1.0, roughness=0.3)
    damper_mat = bc.principled("Damper", (0.12, 0.13, 0.15, 1.0), metallic=0.8, roughness=0.3)
    rod_mat = bc.principled("Rod", (0.85, 0.86, 0.88, 1.0), metallic=1.0, roughness=0.1)
    floor = bc.grid_floor_material(spacing=1.0, line_strength=0.3, roughness=0.5,
                                   fade_start=10.0, fade_end=40.0, base_scale=1.2, specular=0.25)
    bc.cove("Floor 87", floor, width=160.0, front=-60.0, flat_to=14.0, radius=10.0, height=60.0)

    # the swinging assembly hangs from a pivot empty, so rotating it swings everything
    pivot = bpy.data.objects.new("TMD Pivot", None)
    scene.collection.objects.link(pivot)
    pivot.location = (0.0, 0.0, PIVOT_Z)

    # 41 plates: discs whose radius follows the sphere
    z0 = -PLATES * PLATE_T / 2
    for i in range(PLATES):
        zc = z0 + (i + 0.5) * PLATE_T
        r = math.sqrt(max(R ** 2 - (zc * R / (PLATES * PLATE_T / 2)) ** 2 * 0.985, 0.05))
        bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=r, depth=PLATE_T * 0.985,
                                            location=(0.0, 0.0, 0.0))
        disc = bpy.context.object
        disc.name = f"Plate {i + 1:02d}"
        bc.bevel(disc, 0.012, 2)
        disc.data.materials.append(gold)
        bpy.ops.object.shade_smooth()
        disc.parent = pivot
        disc.location = (0.0, 0.0, zc - L_EFF)

    # equator belt where the cables attach
    bpy.ops.mesh.primitive_torus_add(major_radius=R + 0.06, minor_radius=0.09, major_segments=96,
                                     minor_segments=12)
    belt = bpy.context.object
    belt.name = "Cradle Belt"
    belt.data.materials.append(steel)
    bpy.ops.object.shade_smooth()
    belt.parent = pivot
    belt.location = (0.0, 0.0, -L_EFF)

    # 8 cables in 4 pairs, from the belt up (they converge slightly towards the pivot frame)
    cables = []
    for k in range(4):
        a = math.radians(45 + 90 * k)
        for d in (-0.22, 0.22):
            ax, ay = math.cos(a), math.sin(a)
            px, py = -ay * d, ax * d
            bottom = Vector((ax * (R + 0.06) + px, ay * (R + 0.06) + py, -L_EFF))
            top = Vector((ax * (R + 0.9) + px, ay * (R + 0.9) + py, 0.0))
            c = bc.cylinder_between("Cable", bottom, top, 0.0445, cable_mat, vertices=16)
            # re-parent keeping the local position relative to the pivot
            c.location = (bottom + top) / 2
            c.parent = pivot
            cables.append(c)

    # bottom pin (goes into the bumper ring)
    pin = bc.cylinder_between("Pin", (0, 0, -L_EFF - R - 0.9), (0, 0, -L_EFF - R + 0.2), 0.28, steel)
    pin.parent = pivot
    pin.location = (0.0, 0.0, -L_EFF - R - 0.35)

    # bumper ring on the floor stand
    bpy.ops.mesh.primitive_torus_add(major_radius=1.5, minor_radius=0.16, location=(0, 0, CENTRE_Z - R - 1.1),
                                     major_segments=64, minor_segments=12)
    ring = bpy.context.object
    ring.name = "Bumper Ring"
    ring.data.materials.append(steel)
    bpy.ops.object.shade_smooth()
    stand = bc.cylinder_between("Ring Stand", (0, 0, 0), (0, 0, CENTRE_Z - R - 1.1), 0.9, steel, vertices=48)

    # 8 hydraulic dampers: body on the floor, rod to the lower part of the ball (updated per frame)
    dampers = []
    for k in range(8):
        a = math.radians(22.5 + 45 * k)
        anchor = Vector((math.cos(a) * 5.2, math.sin(a) * 5.2, 0.6))
        attach_local = Vector((math.cos(a) * R * 0.72, math.sin(a) * R * 0.72, -L_EFF - R * 0.62))
        body = bc.cylinder_between("Damper Body", (0, 0, 0), (0, 0, 1.6), 0.2, damper_mat, vertices=32)
        rod = bc.cylinder_between("Damper Rod", (0, 0, 0), (0, 0, 1.0), 0.07, rod_mat, vertices=16)
        base = bc.cylinder_between("Damper Mount", anchor - Vector((0, 0, 0.6)), anchor, 0.3, steel, vertices=24)
        dampers.append((anchor, attach_local, body, rod))

    # lights: dramatic top light, warm rim, cool fill
    bc.spot_light("Top", (0.0, -2.0, 24.0), (0.0, 0.0, CENTRE_Z), 26000.0, spot_size_deg=34, blend=0.8,
                  radius=1.5, color=(1.0, 0.95, 0.88))
    bc.area_light("Rim Left", (-12.0, 10.0, 9.0), (0.0, 0.0, CENTRE_Z), 12.0, 7000.0, color=(1.0, 0.85, 0.65))
    bc.area_light("Rim Right", (12.0, 9.0, 7.0), (0.0, 0.0, CENTRE_Z), 12.0, 4500.0, color=(0.7, 0.82, 1.0))
    bc.area_light("Fill", (0.0, -16.0, 5.0), (0.0, 0.0, CENTRE_Z), 10.0, 1800.0, color=(0.85, 0.9, 1.0))
    return scene, pivot, dampers


def aim_between(obj, p0, p1, base_len):
    d = p1 - p0
    obj.location = p0
    obj.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    obj.scale = (1.0, 1.0, d.length / base_len)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", type=int, default=250)
    ap.add_argument("--render", action="store_true")
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--end", type=int, default=None)
    ap.add_argument("--step", type=int, default=1)
    ap.add_argument("--samples", type=int, default=8)
    ap.add_argument("--save-blend", default=None)
    args = ap.parse_args([a for a in sys.argv[1:] if a != "--"])

    scene, pivot, dampers = build_scene()
    scene.cycles.samples = args.samples
    n = args.frames
    scene.frame_start, scene.frame_end = 0, n - 1

    # the damper bodies were created along +Z from the origin with lengths 1.6 and 1.0;
    # move their mesh origin to the base so they can be aimed and stretched
    for anchor, attach_local, body, rod in dampers:
        for obj, ln in ((body, 1.6), (rod, 1.0)):
            me = obj.data
            for v in me.vertices:
                v.co.z += ln / 2
    theta_amp = math.asin(AMP / L_EFF)
    for f in range(n):
        t = f / FPS
        th = theta_amp * math.sin(2 * math.pi * t / PERIOD + 0.6)
        pivot.rotation_euler = (0.0, th, 0.0)
        pivot.keyframe_insert("rotation_euler", index=1, frame=f)
        M = Matrix.Translation(pivot.location) @ Matrix.Rotation(th, 4, "Y")
        for anchor, attach_local, body, rod in dampers:
            attach = M @ attach_local
            direction = attach - anchor
            L = direction.length
            u = direction.normalized()
            body_end = anchor + u * 1.6
            aim_between(body, anchor, body_end, 1.6)
            aim_between(rod, body_end - u * 0.3, attach, 1.0)
            for obj in (body, rod):
                obj.keyframe_insert("location", frame=f)
                obj.keyframe_insert("rotation_euler", frame=f)
                obj.keyframe_insert("scale", frame=f)

    # camera: slow orbit, low angle, the ball fills the frame
    cam = bc.camera("Camera TMD", (0, -15, 3.2), (0, 0, CENTRE_Z + 0.4), lens=50.0, dof_distance=15.0, fstop=8.0)
    for f in range(n):
        u = f / max(1, n - 1)
        u = u * u * (3 - 2 * u)
        a = math.radians(-112 + 34 * u)
        r = 21.5 - 2.0 * u
        cam.location = (r * math.cos(a), r * math.sin(a), 2.2 + 0.8 * u)
        bc.aim(cam, (0.0, 0.0, CENTRE_Z + 0.5 - 0.2 * u))
        cam.data.dof.focus_distance = r
        cam.keyframe_insert("location", frame=f)
        cam.keyframe_insert("rotation_euler", frame=f)
        cam.data.dof.keyframe_insert("focus_distance", frame=f)

    out_dir = os.path.join(BUILD, "frames", "taipei")
    os.makedirs(out_dir, exist_ok=True)

    def pts(frame):
        scene.frame_set(frame)
        M = pivot.matrix_world
        return {
            "centre": tuple(M @ Vector((0, 0, -L_EFF))),
            "top": tuple(M @ Vector((0, 0, -L_EFF + R))),
            "bottom": tuple(M @ Vector((0, 0, -L_EFF - R))),
            "left": tuple(M @ Vector((-R, 0, -L_EFF))),
            "right": tuple(M @ Vector((R, 0, -L_EFF))),
            "cable_top": tuple(M @ Vector((math.cos(math.radians(135)) * (R + 0.35),
                                           math.sin(math.radians(135)) * (R + 0.35), -L_EFF + 2.6))),
            "damper": tuple((dampers[5][0] + (M @ dampers[5][1])) / 2),
        }
    bc.export_projection(scene, cam, pts, range(n), os.path.join(out_dir, "taipei_points.json"))
    if args.save_blend:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(args.save_blend))
    if args.render:
        end = args.end if args.end is not None else n - 1
        bc.render_frames(scene, out_dir, "taipei", args.start, end, args.step)


if __name__ == "__main__":
    main()
