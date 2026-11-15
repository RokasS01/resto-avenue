"""Devanture de restaurant méridionale en diorama : `blender --background --python build_storefront.py`."""

import math
import os
import sys

from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402
from common import Builder  # noqa: E402

GROUND = 0.15
HALF_W = 4.0
DEPTH = 3.0
EAVE_Z, RIDGE_Z = 6.3, 6.95
DOOR_X0, DOOR_X1 = 1.30, 2.40
DOOR_TOP, TRANSOM_TOP = 2.38, 2.85
SHOP_X0, SHOP_X1 = -3.6, 2.7
WINDOWS = [(-2.6, 4.50, 5.80, 0.5), (0.0, 4.50, 5.80, 0.5), (2.6, 4.20, 5.85, 0.55)]
RECESS = 0.14
SIGN_BOX = (-1.6, 1.6, -0.12, -0.06, 3.245, 3.795)
DOOR_HINGE = (2.33, 0.035, GROUND)


def build_walls():
    """Construit le volume ocre, creusé de l'entrée et des baies de l'étage."""
    walls = Builder("walls")
    profile = [(-HALF_W, 0, 0), (-HALF_W, DEPTH, 0), (-HALF_W, DEPTH, RIDGE_Z), (-HALF_W, 0, EAVE_Z)]
    walls.prism(profile, (2 * HALF_W, 0, 0), "ochre")
    cutter = Builder("cutter")
    cutter.bb(DOOR_X0, DOOR_X1, -0.2, 1.0, GROUND, TRANSOM_TOP, "ochre")
    for center, z0, z1, half in WINDOWS:
        cutter.bb(center - half, center + half, -0.2, RECESS, z0, z1, "ochre")
    return common.boolean_cut(walls.to_object(), cutter.to_object())


def add_roof(b):
    """Ajoute la toiture à faible pente : dalle, rangs de tuiles canal et cheminée."""
    slope = (RIDGE_Z + 0.05 - EAVE_Z) / (DEPTH + 0.05)
    y0, y1 = -0.38, DEPTH + 0.06
    z_at = lambda y: EAVE_Z + 0.04 + slope * y  # noqa: E731
    profile = [(-4.2, y0, z_at(y0)), (-4.2, y1, z_at(y1)), (-4.2, y1, z_at(y1) + 0.08), (-4.2, y0, z_at(y0) + 0.08)]
    b.prism(profile, (8.4, 0, 0), "terracotta")

    start = Vector((0, y0 - 0.04, z_at(y0 - 0.04) + 0.08))
    along = Vector((0, 1, slope)).normalized()
    up = Vector((0, -slope, 1)).normalized()
    side = Vector((1, 0, 0))
    length = (y1 - y0 + 0.04) / along.y
    rows = 3
    for i in range(21):
        x = -4.0 + i * 0.4
        for row in range(rows):
            s0 = length * row / rows
            s1 = min(length, length * (row + 1) / rows + 0.06)
            rings = []
            for s, radius in ((s0, 0.135), (s1, 0.085)):
                center = start + along * s + side * x
                rings.append([
                    center + side * (radius * math.cos(t)) + up * (radius * math.sin(t))
                    for t in (math.pi * k / 4 for k in range(5))
                ])
            for k in range(4):
                mid = math.pi * (k + 0.5) / 4
                b.poly([rings[0][k], rings[0][k + 1], rings[1][k + 1], rings[1][k]], "terracotta",
                       facing=side * math.cos(mid) + up * math.sin(mid))
            b.poly(rings[0], "terracotta", facing=-along)
            if row == rows - 1:
                b.poly(rings[1], "terracotta", facing=along)

    b.bb(2.3, 3.0, 1.6, 2.2, 6.6, 7.45, "ochre")
    b.bb(2.24, 3.06, 1.54, 2.26, 7.45, 7.53, "cream")
    b.bb(2.4, 2.9, 1.7, 2.1, 7.53, 7.68, "terracotta")


def add_facade_trim(b):
    """Ajoute corniches, soubassement et plan lumineux de l'intérieur derrière la porte."""
    b.bb(-HALF_W - 0.04, HALF_W + 0.04, -0.07, 0.0, 3.95, 4.06, "cream")
    b.bb(-HALF_W - 0.06, HALF_W + 0.06, -0.12, 0.0, EAVE_Z - 0.20, EAVE_Z + 0.02, "cream")
    b.bb(-HALF_W - 0.03, SHOP_X0, -0.04, 0.0, GROUND, 0.70, "grey")
    b.bb(SHOP_X1, HALF_W + 0.03, -0.04, 0.0, GROUND, 0.70, "grey")
    b.poly([(DOOR_X0, 0.97, GROUND), (DOOR_X1, 0.97, GROUND), (DOOR_X1, 0.97, TRANSOM_TOP), (DOOR_X0, 0.97, TRANSOM_TOP)],
           "light", facing=(0, -1, 0))


def add_shopfront(b):
    """Ajoute la devanture en applique : boiserie rouge foncé, vitrine, rideau bistrot, bâti de porte."""
    glass_x0, glass_x1 = SHOP_X0 + 0.25, DOOR_X0 - 0.25
    b.bb(SHOP_X0, DOOR_X0, -0.09, 0.0, GROUND, 0.85, "red_dark")
    for k in range(3):
        x0 = glass_x0 + 0.08 + k * (glass_x1 - glass_x0) / 3
        b.bb(x0, x0 + (glass_x1 - glass_x0) / 3 - 0.16, -0.115, -0.09, GROUND + 0.12, 0.74, "red")
    for x0, x1 in ((SHOP_X0, glass_x0), (glass_x1, DOOR_X0), (DOOR_X1, SHOP_X1)):
        b.bb(x0, x1, -0.11, 0.0, GROUND, 3.05, "red_dark")
    b.bb(SHOP_X0 - 0.04, SHOP_X1 + 0.04, -0.13, 0.0, 2.85, 3.05, "red_dark")
    b.bb(glass_x0, glass_x1, -0.14, 0.0, 0.83, 0.89, "cream")

    b.poly([(glass_x0, -0.02, 0.85), (glass_x1, -0.02, 0.85), (glass_x1, -0.02, 2.85), (glass_x0, -0.02, 2.85)],
           "glass", facing=(0, -1, 0))
    third = (glass_x1 - glass_x0) / 3
    for k in (1, 2):
        x = glass_x0 + k * third
        b.bb(x - 0.03, x + 0.03, -0.07, 0.0, 0.89, 2.85, "red_dark")
    b.bb(glass_x0, glass_x1, -0.06, 0.0, 2.33, 2.39, "red_dark")
    b.bb(glass_x0, glass_x1, -0.035, -0.02, 0.89, 1.42, "cream")
    b.bb(glass_x0, glass_x1, -0.05, -0.02, 1.42, 1.45, "light")

    for x0, x1 in ((DOOR_X0, DOOR_X0 + 0.06), (DOOR_X1 - 0.06, DOOR_X1)):
        b.bb(x0, x1, -0.03, 0.10, GROUND, TRANSOM_TOP, "wood")
    b.bb(DOOR_X0, DOOR_X1, -0.03, 0.10, TRANSOM_TOP - 0.06, TRANSOM_TOP, "wood")
    b.bb(DOOR_X0, DOOR_X1, -0.03, 0.10, DOOR_TOP, DOOR_TOP + 0.07, "wood")
    b.poly([(DOOR_X0, 0.04, DOOR_TOP), (DOOR_X1, 0.04, DOOR_TOP), (DOOR_X1, 0.04, TRANSOM_TOP), (DOOR_X0, 0.04, TRANSOM_TOP)],
           "glass", facing=(0, -1, 0))
    b.bb(DOOR_X0 - 0.1, DOOR_X1 + 0.1, -0.30, 0.0, GROUND, GROUND + 0.03, "grey")


def add_awning(b):
    """Ajoute le store banne à rayures rouge / crème avec lambrequin et bras."""
    profile = [(-0.12, 3.14), (-1.75, 2.62), (-1.75, 2.38), (-1.71, 2.38), (-1.71, 2.585), (-0.12, 3.10)]
    x_start, stripe, count = -3.75, 0.5, 13
    for s in range(count):
        x0, x1 = x_start + s * stripe, x_start + (s + 1) * stripe
        mat = "red" if s % 2 == 0 else "cream"
        for k in range(len(profile)):
            (ya, za), (yb, zb) = profile[k], profile[(k + 1) % len(profile)]
            b.add([(x1, ya, za), (x0, ya, za), (x0, yb, zb), (x1, yb, zb)], [(0, 1, 2, 3)], mat, fix_normals=False)
    x_end = x_start + count * stripe
    b.poly([(x_start, y, z) for y, z in profile], "red", facing=(-1, 0, 0))
    b.poly([(x_end, y, z) for y, z in profile], "red", facing=(1, 0, 0))
    for x in (x_start + 0.2, x_end - 0.2):
        b.tube((x, -0.11, 2.50), (x, -1.70, 2.56), 0.022, "grey", segs=4)


def add_sign_backing_and_lamps(b):
    """Ajoute le fond d'enseigne et les deux appliques col-de-cygne qui l'éclairent."""
    b.bb(-1.78, 1.78, -0.06, 0.0, 3.16, 3.88, "red_dark")
    for side in (-1, 1):
        x = side * 2.25
        b.bb(x - 0.06, x + 0.06, -0.03, 0.0, 3.74, 3.90, "ink")
        b.tube((x, -0.02, 3.84), (x, -0.30, 3.90), 0.018, "ink", segs=4)
        b.tube((x, -0.30, 3.90), (x, -0.40, 3.78), 0.018, "ink", segs=4)
        b.lathe([(0.04, 0.12), (0.17, 0.0), (0.15, 0.0), (0.03, 0.10)], (x, -0.40, 3.64), "ink", segs=10)
        b.sphere(0.075, (x, -0.40, 3.66), "light")


def add_flower_pot(b, loc, radius=0.11, flowers=("red", "red", "light")):
    """Ajoute un pot en terre cuite garni de feuillage et de quelques fleurs."""
    b.lathe([(0, 0), (radius * 0.7, 0), (radius, radius * 1.4), (radius * 1.12, radius * 1.4),
             (radius * 1.12, radius * 1.7), (0, radius * 1.7)], loc, "terracotta", segs=8)
    top = (loc[0], loc[1], loc[2] + radius * 2.4)
    b.sphere(radius * 1.35, top, "green_dark", scale=(1.15, 1.0, 0.85))
    for k, mat in enumerate(flowers):
        angle = 2.1 * k + loc[0] * 3
        b.sphere(radius * 0.42, (top[0] + radius * 1.05 * math.cos(angle), top[1] - radius * 0.75 * abs(math.sin(angle)) - 0.02,
                                 top[2] + radius * 0.5), mat, subdiv=0)


def add_window(b, center, z0, z1, half):
    """Ajoute une croisée crème en retrait, son appui et ses volets bleus ouverts."""
    x0, x1 = center - half, center + half
    b.poly([(x0, RECESS - 0.03, z0), (x1, RECESS - 0.03, z0), (x1, RECESS - 0.03, z1), (x0, RECESS - 0.03, z1)],
           "glass", facing=(0, -1, 0))
    frame = 0.06
    y0, y1 = 0.04, RECESS - 0.03
    # Léger retrait : évite les faces coplanaires (z-fighting) avec les tableaux de la baie.
    x0, x1, z0, z1 = x0 + 0.004, x1 - 0.004, z0 + 0.004, z1 - 0.004
    b.bb(x0, x0 + frame, y0, y1, z0, z1, "cream")
    b.bb(x1 - frame, x1, y0, y1, z0, z1, "cream")
    b.bb(x0, x1, y0, y1, z1 - frame, z1, "cream")
    b.bb(x0, x1, y0, y1, z0, z0 + frame, "cream")
    b.bb(center - 0.025, center + 0.025, y0, y1, z0, z1, "cream")
    for frac in (0.36, 0.68):
        z = z0 + (z1 - z0) * frac
        b.bb(x0, x1, y0 + 0.01, y1, z - 0.02, z + 0.02, "cream")
    for side in (-1, 1):
        sx0 = center + side * (half + 0.03)
        sx1 = center + side * (half + 0.49)
        b.bb(min(sx0, sx1), max(sx0, sx1), -0.05, 0.0, z0, z1, "blue")
        for z in (z0 + 0.22, (z0 + z1) / 2, z1 - 0.22):
            b.bb(min(sx0, sx1) + 0.03, max(sx0, sx1) - 0.03, -0.075, -0.05, z - 0.045, z + 0.045, "blue")


def add_upper_floor(b):
    """Ajoute les fenêtres de l'étage, les appuis fleuris et le balcon en fer forgé."""
    for center, z0, z1, half in WINDOWS:
        add_window(b, center, z0, z1, half)
    for center, z0, _z1, half in WINDOWS[:2]:
        b.bb(center - half - 0.07, center + half + 0.07, -0.13, 0.03, z0 - 0.09, z0, "cream")
        add_flower_pot(b, (center - 0.2, -0.06, z0), radius=0.085)
        add_flower_pot(b, (center + 0.22, -0.06, z0), radius=0.075, flowers=("light", "red"))

    bx0, bx1, by = 1.72, 3.48, -0.62
    b.bb(bx0, bx1, by, 0.0, 4.08, 4.20, "stone")
    for x in (bx0 + 0.2, bx1 - 0.2):
        b.prism([(x - 0.06, 0, 3.80), (x - 0.06, 0, 4.08), (x - 0.06, -0.45, 4.08)], (0.12, 0, 0), "stone")
    rail_top, rail_low = 5.12, 4.30
    corners = [(bx0 + 0.03, -0.01), (bx0 + 0.03, by + 0.03), (bx1 - 0.03, by + 0.03), (bx1 - 0.03, -0.01)]
    for (xa, ya), (xb, yb) in zip(corners, corners[1:]):
        for z, radius in ((rail_top, 0.025), (rail_low, 0.018)):
            b.tube((xa, ya, z), (xb, yb, z), radius, "ink", segs=4)
        count = 11 if abs(xb - xa) > 0.5 else 3
        for k in range(count + 1):
            t = k / count
            x, y = xa + (xb - xa) * t, ya + (yb - ya) * t
            b.tube((x, y, 4.20), (x, y, rail_top), 0.012, "ink", segs=3, caps=False)
    for k, x in enumerate((2.05, 2.6, 3.15)):
        add_flower_pot(b, (x, by - 0.10, 4.78), radius=0.10, flowers=("red", "light", "red") if k % 2 == 0 else ("light", "red", "red"))
        b.bb(x - 0.13, x + 0.13, by - 0.11, by + 0.05, 4.75, 4.78, "ink")


def add_ground(b):
    """Ajoute le trottoir (dalle 11 × 5 m) et sa bordure côté rue."""
    b.bb(-5.5, 5.5, -4.78, 0.0, 0.0, GROUND, "stone")
    b.bb(-5.5, 5.5, -5.0, -4.78, 0.0, GROUND - 0.02, "grey")


def add_chair(b, loc, yaw):
    """Ajoute une chaise bistrot ; le dossier est du côté +Y du repère local."""
    with b.at(loc, (0, 0, yaw)):
        b.lathe([(0, 0.43), (0.17, 0.43), (0.19, 0.45), (0.19, 0.47), (0, 0.47)], (0, 0, 0), "red", segs=8, phase=math.pi / 8)
        for sx in (-1, 1):
            for sy in (-1, 1):
                b.tube((sx * 0.12, sy * 0.12, 0.44), (sx * 0.17, sy * 0.17, 0.0), 0.016, "ink", segs=4, caps=False)
            b.tube((sx * 0.14, 0.13, 0.44), (sx * 0.16, 0.20, 0.88), 0.016, "ink", segs=4)
        b.box((0.38, 0.03, 0.13), (0, 0.195, 0.80), "red", rot=(-9, 0, 0))
        b.box((0.32, 0.02, 0.04), (0, 0.17, 0.62), "ink", rot=(-9, 0, 0))


def add_table_set(b, loc, yaw):
    """Ajoute une table bistrot dressée (assiettes, verres, carafe) et ses deux chaises."""
    top = 0.74
    with b.at(loc, (0, 0, yaw)):
        b.lathe([(0, 0), (0.22, 0), (0.22, 0.025), (0.05, 0.05), (0.03, 0.08), (0.03, top - 0.04),
                 (0.40, top - 0.04), (0.40, top), (0, top)], (0, 0, 0), "ink", segs=12,
                mats=["ink"] * 6 + ["red", "cream"])
        for side in (-1, 1):
            b.lathe([(0.07, 0), (0.115, 0.018), (0.095, 0.018), (0.06, 0.008), (0, 0.008)],
                    (side * 0.19, 0, top), "cream", segs=8)
            b.sphere(0.05, (side * 0.19, 0, top + 0.02), "terracotta" if side > 0 else "olive", subdiv=0, scale=(1, 1, 0.6))
            b.lathe([(0, 0), (0.024, 0), (0.034, 0.10), (0, 0.075)], (side * 0.12, 0.2 * side, top), "glass", segs=6,
                    mats=["glass", "glass", "red_dark"])
        b.lathe([(0, 0), (0.045, 0), (0.045, 0.13), (0.016, 0.19), (0.016, 0.25), (0, 0.25)], (0.0, -0.17, top), "green_dark", segs=6)
        for side in (-1, 1):
            add_chair(b, (side * 0.68, 0, 0), -side * 90)


def add_chalkboard(b, loc, yaw):
    """Ajoute l'ardoise-chevalet avec quelques lignes de menu à la craie."""
    with b.at(loc, (0, 0, yaw)):
        for side in (-1, 1):
            with b.at((0, side * 0.21, 0), (side * 13, 0, 0)):
                b.box((0.62, 0.035, 1.0), (0, 0, 0.5), "wood")
                b.box((0.50, 0.012, 0.78), (0, side * 0.022, 0.55), "ink")
                if side < 0:
                    b.box((0.26, 0.006, 0.05), (0, -0.03, 0.85), "light")
                    for k, width in enumerate((0.36, 0.30, 0.38, 0.24)):
                        b.box((width, 0.006, 0.028), (-0.19 + width / 2, -0.03, 0.72 - k * 0.11), "cream")
        b.box((0.62, 0.10, 0.03), (0, 0, 0.99), "wood")


def add_tree_planter(b, loc, variant):
    """Ajoute une jardinière en bois plantée d'un olivier au feuillage facetté."""
    x, y, z = loc
    b.bb(x - 0.38, x + 0.38, y - 0.38, y + 0.38, z, z + 0.58, "wood", bevel=0.02)
    b.bb(x - 0.41, x + 0.41, y - 0.41, y + 0.41, z + 0.50, z + 0.60, "red_dark")
    b.bb(x - 0.33, x + 0.33, y - 0.33, y + 0.33, z + 0.60, z + 0.62, "ink")
    lean = 0.10 if variant == 0 else -0.08
    b.tube((x, y, z + 0.6), (x + lean, y + 0.03, z + 1.25), 0.06, "wood", segs=5, r_end=0.045)
    b.tube((x + lean, y + 0.03, z + 1.25), (x - lean * 0.6, y - 0.02, z + 1.75), 0.045, "wood", segs=5, r_end=0.03)
    blobs = [
        ((0.0, 0.0, 1.95), 0.52, "olive"), ((0.36, 0.10, 1.75), 0.36, "green_dark"),
        ((-0.34, -0.12, 1.78), 0.38, "olive"), ((0.08, -0.05, 2.38), 0.34, "olive"),
    ]
    for (dx, dy, dz), radius, mat in blobs:
        sign = 1 if variant == 0 else -1
        b.sphere(radius, (x + sign * dx, y + sign * dy, z + dz), mat, subdiv=2 if radius > 0.5 else 1,
                 scale=(1.0, 1.0, 0.8), rot=(0, 0, 37 * (dx + 1) * (variant + 1)))
    for k in range(3):
        angle = 2.1 * k + variant
        b.sphere(0.13, (x + 0.2 * math.cos(angle), y + 0.2 * math.sin(angle), z + 0.66), "green_dark", subdiv=0)


def add_shrub_pot(b, loc):
    """Ajoute un gros pot en terre cuite garni d'un arbuste en boule."""
    b.lathe([(0, 0), (0.18, 0), (0.26, 0.38), (0.29, 0.38), (0.29, 0.45), (0, 0.45)], loc, "terracotta", segs=10)
    b.sphere(0.34, (loc[0], loc[1], loc[2] + 0.72), "green_dark", scale=(1, 1, 0.95))
    b.sphere(0.2, (loc[0] + 0.14, loc[1] - 0.1, loc[2] + 0.98), "olive")


def add_string_lights(b):
    """Ajoute la guirlande : deux mâts, un câble en chaînette et ses ampoules `mat_light`."""
    poles = [(-5.2, -4.5), (5.2, -4.5)]
    pole_top = GROUND + 3.45
    for x, y in poles:
        b.lathe([(0, 0), (0.20, 0), (0.20, 0.06), (0.07, 0.14), (0, 0.14)], (x, y, GROUND), "grey", segs=8)
        b.tube((x, y, GROUND + 0.1), (x, y, pole_top + 0.05), 0.035, "ink", segs=5)
    anchors = [
        (Vector((-3.85, -0.03, 4.30)), Vector((poles[0][0], poles[0][1], pole_top)), 0.45, 9),
        (Vector((poles[0][0], poles[0][1], pole_top)), Vector((poles[1][0], poles[1][1], pole_top)), 0.75, 19),
        (Vector((poles[1][0], poles[1][1], pole_top)), Vector((3.85, -0.03, 4.30)), 0.45, 9),
    ]
    for start, end, sag, bulbs in anchors:
        points = []
        for k in range(bulbs + 2):
            t = k / (bulbs + 1)
            point = start.lerp(end, t)
            point.z -= sag * 4 * t * (1 - t)
            points.append(point)
        for a, c in zip(points, points[1:]):
            b.tube(a, c, 0.012, "ink", segs=3, caps=False)
        for point in points[1:-1]:
            b.sphere(0.07, (point.x, point.y, point.z - 0.07), "light", subdiv=1)


def build_static():
    """Assemble tout le décor fixe dans `storefront_static`."""
    b = Builder("storefront_static")
    b.absorb(build_walls())
    add_roof(b)
    add_facade_trim(b)
    add_shopfront(b)
    add_awning(b)
    add_sign_backing_and_lamps(b)
    add_upper_floor(b)
    add_ground(b)
    add_table_set(b, (-3.0, -2.5, GROUND), 18)
    add_table_set(b, (-0.5, -3.3, GROUND), -24)
    add_chalkboard(b, (3.3, -1.7, GROUND), -28)
    add_tree_planter(b, (-4.75, -4.0, GROUND), 0)
    add_tree_planter(b, (4.75, -4.0, GROUND), 1)
    add_shrub_pot(b, (-3.95, -0.5, GROUND))
    add_shrub_pot(b, (3.25, -0.5, GROUND))
    add_string_lights(b)
    return b.to_object()


def build_sign():
    """Construit le bandeau d'enseigne vide (3,2 × 0,55 m) ; origine en son centre."""
    sign = Builder("sign")
    sign.bb(*SIGN_BOX, "cream")
    x0, x1, y0, y1, z0, z1 = SIGN_BOX
    return sign.to_object(origin=((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))


def build_door():
    """Construit le vantail vitré en bois ; origine sur la charnière, au niveau du seuil."""
    door = Builder("door")
    x0, x1 = DOOR_X0 + 0.07, DOOR_HINGE[0]
    y0, y1 = DOOR_HINGE[1] - 0.025, DOOR_HINGE[1] + 0.025
    z0, z1 = GROUND + 0.015, DOOR_TOP - 0.01
    door.bb(x0, x0 + 0.11, y0, y1, z0, z1, "wood")
    door.bb(x1 - 0.11, x1, y0, y1, z0, z1, "wood")
    door.bb(x0 + 0.11, x1 - 0.11, y0, y1, z1 - 0.12, z1, "wood")
    door.bb(x0 + 0.11, x1 - 0.11, y0, y1, z0, z0 + 0.42, "wood")
    door.bb(x0 + 0.11, x1 - 0.11, y0, y1, z0 + 1.02, z0 + 1.08, "wood")
    door.bb(x0 + 0.11, x1 - 0.11, y0 + 0.015, y1 - 0.015, z0 + 0.42, z1 - 0.12, "glass")
    for y in (y0 - 0.035, y1 + 0.035):
        door.tube((x0 + 0.055, y, z0 + 0.92), (x0 + 0.055, y, z0 + 1.32), 0.016, "grey", segs=5)
    return door.to_object(origin=DOOR_HINGE)


def main():
    """Assemble la devanture, exporte `storefront.glb` et rend les aperçus."""
    common.reset_scene()
    objects = [build_static(), build_sign(), build_door()]
    common.finish("storefront", objects, {
        "front34": (0.85, -1.3, 0.6),
        "front": (0.0, -1.0, 0.1),
        "top34": (-0.6, -1.0, 1.1),
        "back34": (-1.0, 1.2, 0.7),
    })


main()
