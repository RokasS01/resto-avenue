"""Camionnette vintage de tournage : `blender --background --python build_van.py`."""

import math
import os
import sys

import bmesh

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402
from common import Builder  # noqa: E402

HALF_WIDTH = 0.9
TOP_Z = 1.92
SILL_Z, BELT_Z, GLASS_TOP_Z = 0.90, 1.18, 1.66
# Demi-section de caisse : (fraction de demi-largeur, hauteur), du bas de caisse au pavillon.
SECTION = [
    (0.80, 0.30), (0.97, 0.42), (1.0, 0.60), (1.0, SILL_Z), (1.0, BELT_Z),
    (0.93, GLASS_TOP_Z), (0.89, 1.77), (0.74, 1.86), (0.40, 1.91),
]
BAND_MATS = ["cream", "cream", "cream", "red", "red", "red", "cream", "cream", "cream"]
GLASS_BAND = 4
# Couples le long du véhicule : (y, facteur de largeur). L'avant est en -Y.
STATIONS = [
    (-2.0, 0.84), (-1.94, 0.94), (-1.82, 1.0), (-1.62, 1.0), (-0.85, 1.0), (-0.70, 1.0),
    (0.30, 1.0), (0.45, 1.0), (1.45, 1.0), (1.82, 1.0), (1.94, 0.95), (2.0, 0.86),
]
GLASS_SPANS = (3, 5, 7)
RING = 2 * len(SECTION) + 1

WHEEL_RADIUS = 0.36
WHEEL_X = 0.70
AXLES_Y = {"f": -1.2, "r": 1.2}


def clamp01(value):
    """Borne une valeur entre 0 et 1."""
    return max(0.0, min(1.0, value))


def lean(y, z):
    """Décalage en Y qui incline le pare-brise, arrondit le pavillon et rentre le bas de caisse."""
    tuck = 0.07 * clamp01((0.60 - z) / 0.30)
    rise = clamp01((z - BELT_Z) / (GLASS_TOP_Z - BELT_Z))
    crown = clamp01((z - GLASS_TOP_Z) / (TOP_Z - GLASS_TOP_Z))
    front = tuck + 0.26 * rise + 0.30 * crown ** 0.7
    rear = tuck + 0.10 * rise + 0.20 * crown ** 0.7
    return clamp01((-1.1 - y) / 0.9) * front - clamp01((y - 1.3) / 0.7) * rear


def band_of(k):
    """Associe un segment de l'anneau de section à sa bande (None = plancher)."""
    if k < len(SECTION):
        return k
    if k < RING - 1:
        return RING - 2 - k
    return None


def build_shell():
    """Construit la coque par lofting de sections, avec vitres en retrait et passages de roues."""
    shell = Builder("shell")
    verts = []
    for y, width_factor in STATIONS:
        half = [(f * HALF_WIDTH * width_factor, z) for f, z in SECTION]
        ring = half + [(0.0, TOP_Z)] + [(-x, z) for x, z in reversed(half)]
        verts += [(x, y + lean(y, z), z) for x, z in ring]

    faces, mats, glass_ids = [], [], []
    for i in range(len(STATIONS) - 1):
        for k in range(RING):
            k2 = (k + 1) % RING
            faces.append((i * RING + k, i * RING + k2, (i + 1) * RING + k2, (i + 1) * RING + k))
            band = band_of(k)
            if band is None:
                mats.append("ink")
            elif band == GLASS_BAND and i in GLASS_SPANS:
                glass_ids.append(len(faces) - 1)
                mats.append("glass")
            else:
                mats.append(BAND_MATS[band])
    for offset in (0, (len(STATIONS) - 1) * RING):
        for band in range(len(SECTION)):
            right, left = offset + band, offset + RING - 1 - band
            if band == len(SECTION) - 1:
                faces.append((right, right + 1, left))
            else:
                faces.append((right, right + 1, left - 1, left))
            if band == GLASS_BAND:
                glass_ids.append(len(faces) - 1)
                mats.append("glass")
            else:
                mats.append(BAND_MATS[band])

    created = shell.add(verts, faces, face_mats=mats, fix_normals=False)
    bmesh.ops.recalc_face_normals(shell.bm, faces=shell.bm.faces)
    red = shell.slot("red")
    for index in glass_ids:
        result = bmesh.ops.inset_region(
            shell.bm, faces=[created[index]], thickness=0.055, depth=-0.025, use_even_offset=True
        )
        for face in result["faces"]:
            face.material_index = red
    shell_obj = shell.to_object()

    cutter = Builder("cutter")
    for y in AXLES_Y.values():
        for side in (-1, 1):
            cutter.cyl(0.45, 0.5, (side * 0.52, y, WHEEL_RADIUS), "ink", axis="X" if side > 0 else "-X", segs=16)
    cutter.weld()
    return common.boolean_cut(shell_obj, cutter.to_object())


def add_front(body):
    """Ajoute pare-chocs, phares, calandre et clignotants sur la face avant."""
    body.bb(-0.80, 0.80, -2.10, -1.96, 0.40, 0.55, "grey", bevel=0.035)
    for side in (-1, 1):
        x = side * 0.50
        body.lathe(
            [(0.17, 0.0), (0.17, 0.035), (0.13, 0.035), (0.11, 0.07), (0, 0.085)],
            (x, -1.995, 1.04), "light", axis="-Y", segs=12,
            mats=["grey", "grey", "light", "light"],
        )
        body.cyl(0.055, 0.03, (x, -1.995, 0.76), "terracotta", axis="-Y", segs=8)
    for z in (0.98, 1.04, 1.10):
        body.bb(-0.22, 0.22, -2.02, -1.99, z - 0.015, z + 0.015, "ink")
    body.tube((0, -1.975, BELT_Z + 0.03), (0, -1.975 + 0.25, GLASS_TOP_Z - 0.02), 0.022, "red", segs=4)


def add_rear(body):
    """Ajoute pare-chocs, feux et poignée de hayon sur la face arrière."""
    body.bb(-0.82, 0.82, 1.96, 2.10, 0.40, 0.55, "grey", bevel=0.035)
    for side in (-1, 1):
        body.bb(side * 0.60 - 0.05, side * 0.60 + 0.05, 1.99, 2.02, 0.94, 1.14, "light", bevel=0.01)
    body.bb(-0.008, 0.008, 1.995, 2.008, 0.62, BELT_Z - 0.03, "ink")
    body.bb(0.04, 0.16, 1.99, 2.03, 0.98, 1.02, "grey")


def add_sides(body):
    """Ajoute baguettes, joints de portes, poignées, rétroviseurs et essieux."""
    for side in (-1, 1):
        x = side * HALF_WIDTH
        body.bb(x - 0.012, x + 0.012, -1.80, 1.80, BELT_Z - 0.035, BELT_Z + 0.005, "cream")
        for y, z0 in ((-0.72, 0.52), (0.375, 0.32)):
            body.bb(x - 0.006, x + 0.006, y - 0.008, y + 0.008, z0, BELT_Z - 0.04, "ink")
        body.bb(x - 0.02, x + 0.02, -0.92, -0.80, 1.02, 1.05, "grey")
        body.bb(x - 0.02, x + 0.02, 0.44, 0.56, 1.02, 1.05, "grey")
        body.tube((x, -1.63, 1.26), (side * 1.0, -1.70, 1.36), 0.014, "ink", segs=4)
        body.box((0.04, 0.10, 0.17), (side * 1.0, -1.71, 1.42), "ink", bevel=0.012)
    for y in AXLES_Y.values():
        body.tube((-WHEEL_X, y, WHEEL_RADIUS), (WHEEL_X, y, WHEEL_RADIUS), 0.04, "ink", segs=6, caps=False)


def add_roof_rack(body):
    """Ajoute la galerie de toit et le matériel de tournage : caisses, valise, duvet, trépied."""
    rail_z = 2.0
    for side in (-1, 1):
        x = side * 0.60
        body.bb(x - 0.02, x + 0.02, -1.0, 1.4, rail_z - 0.02, rail_z + 0.02, "grey")
        for y in (-0.9, 0.2, 1.3):
            body.bb(x - 0.018, x + 0.018, y - 0.018, y + 0.018, 1.85, rail_z, "grey")
    for y in (-1.0, -0.4, 0.2, 0.8, 1.4):
        body.bb(-0.60, 0.60, y - 0.02, y + 0.02, rail_z - 0.02, rail_z + 0.02, "grey")
    deck = rail_z + 0.02

    body.bb(-0.52, 0.04, 0.55, 1.28, deck, deck + 0.25, "wood", bevel=0.015)
    for y in (0.70, 1.13):
        body.bb(-0.53, 0.05, y - 0.025, y + 0.025, deck - 0.004, deck + 0.256, "grey")

    body.bb(0.10, 0.54, 0.52, 1.22, deck, deck + 0.20, "terracotta", bevel=0.03)
    for y in (0.68, 1.06):
        body.bb(0.094, 0.546, y - 0.025, y + 0.025, deck - 0.004, deck + 0.206, "cream")
    body.bb(0.26, 0.38, 0.49, 0.52, deck + 0.08, deck + 0.12, "ink")

    body.bb(-0.50, -0.06, -0.22, 0.34, deck, deck + 0.27, "blue", bevel=0.02)
    body.bb(-0.508, -0.052, -0.228, 0.348, deck + 0.17, deck + 0.20, "grey")

    body.cyl(0.11, 0.62, (-0.54, -0.62, deck + 0.11), "olive", axis="X", segs=8)
    for x in (-0.40, -0.06):
        body.cyl(0.117, 0.04, (x, -0.62, deck + 0.11), "ink", axis="X", segs=8)

    hub = (0.33, 0.30, deck + 0.05)
    for dx in (-0.08, 0.0, 0.08):
        body.tube(hub, (0.33 + dx, -0.88, deck + 0.025), 0.02, "ink", segs=5, r_end=0.013)
    body.box((0.10, 0.12, 0.08), (0.33, 0.36, deck + 0.05), "grey", bevel=0.012)
    body.tube((0.33, 0.40, deck + 0.06), (0.47, 0.34, deck + 0.10), 0.011, "ink", segs=4)


def build_wheel(name, x, y):
    """Construit une roue (pneu, enjoliveur, écrous) dont l'origine est son centre."""
    wheel = Builder(name)
    center = (x, y, WHEEL_RADIUS)
    profile = [
        (0, -0.12), (0.30, -0.12), (0.36, -0.075), (0.36, 0.075), (0.30, 0.12), (0.215, 0.12),
        (0.215, 0.10), (0.19, 0.10), (0.17, 0.135), (0.075, 0.15), (0.06, 0.175), (0, 0.175),
    ]
    mats = ["ink"] * 6 + ["cream"] * 3 + ["grey", "grey"]
    with wheel.at(center):
        with wheel.at(matrix=common.AXIS["X" if x > 0 else "-X"]):
            wheel.lathe(profile, (0, 0, 0), "ink", segs=18, mats=mats)
            for k in range(5):
                angle = 2 * math.pi * k / 5
                wheel.box(
                    (0.04, 0.04, 0.03), (0.125 * math.cos(angle), 0.125 * math.sin(angle), 0.145),
                    "ink", rot=(0, 0, math.degrees(angle)),
                )
    return wheel.to_object(origin=center)


def main():
    """Assemble la camionnette, exporte `van.glb` et rend les aperçus."""
    common.reset_scene()
    body = Builder("van_body")
    body.absorb(build_shell())
    add_front(body)
    add_rear(body)
    add_sides(body)
    add_roof_rack(body)
    objects = [body.to_object()]
    for axle, y in AXLES_Y.items():
        for side, x in (("l", -WHEEL_X), ("r", WHEEL_X)):
            objects.append(build_wheel(f"wheel_{axle}{side}", x, y))
    common.finish("van", objects, {
        "front34": (1.0, -1.25, 0.55),
        "front": (0.0, -1.0, 0.12),
        "back34": (-1.0, 1.2, 0.65),
    })


main()
