"""Intérieur de bistrot en maison de poupée (page contact) : `blender --background --python build_interior.py`.

Les cotes sont en repère Blender : X identique au glTF, Y = -Z glTF (mur du fond à Y = +5), Z = Y glTF.
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402
from common import Builder  # noqa: E402

HALF_W = 3.5
BACK = 5.0
WALL_H = 3.6
FLOOR_X, FLOOR_Y, TILE = 6.0, 5.0, 0.5
DADO = 1.0
BAR_X0, BAR_X1, BAR_Y0, BAR_Y1, BAR_TOP = -3.5, -0.55, 2.1, 2.7, 1.10
TABLE_TOP = 0.76

PHONE_ORIGIN = (-1.15, 2.4, 1.35)
MAIL_ORIGIN = (1.2, 1.6, 1.15)
INSTA_ORIGIN = (1.15, 4.9, 2.35)
MAP_ORIGIN = (-1.15, 4.9, 2.4)

# Repères muraux : (u le long du mur, d = saillie vers la salle, z) -> coordonnées monde.
WALLS = {
    "back": lambda u, d, z: (u, BACK - d, z),
    "left": lambda u, d, z: (-HALF_W + d, u, z),
    "right": lambda u, d, z: (HALF_W - d, u, z),
}


def wbox(b, wall, u0, u1, z0, z1, d0, d1, mat):
    """Ajoute un pavé plaqué au mur, sans les faces invisibles (dos contre le mur, dessous au sol)."""
    to_world = WALLS[wall]
    center = Vector(to_world((u0 + u1) / 2, (d0 + d1) / 2, (z0 + z1) / 2))
    quads = [
        [(u0, d1, z0), (u1, d1, z0), (u1, d1, z1), (u0, d1, z1)],
        [(u0, d0, z0), (u0, d1, z0), (u0, d1, z1), (u0, d0, z1)],
        [(u1, d0, z0), (u1, d1, z0), (u1, d1, z1), (u1, d0, z1)],
        [(u0, d0, z1), (u1, d0, z1), (u1, d1, z1), (u0, d1, z1)],
    ]
    if z0 > common.EPS:
        quads.append([(u0, d0, z0), (u1, d0, z0), (u1, d1, z0), (u0, d1, z0)])
    if d0 > common.EPS:
        quads.append([(u0, d0, z0), (u1, d0, z0), (u1, d0, z1), (u0, d0, z1)])
    for quad in quads:
        points = [Vector(to_world(*p)) for p in quad]
        b.poly(points, mat, facing=sum(points, Vector()) / 4 - center)


def rounded_square(half, radius, y, steps=3):
    """Retourne le contour d'un carré à coins arrondis dans le plan XZ, à la profondeur `y`."""
    points = []
    for corner, (sx, sz) in enumerate(((1, 1), (-1, 1), (-1, -1), (1, -1))):
        cx, cz = sx * (half - radius), sz * (half - radius)
        for k in range(steps + 1):
            angle = math.pi / 2 * (corner + k / steps)
            points.append((cx + radius * math.cos(angle), y, cz + radius * math.sin(angle)))
    return points


def add_floor(b):
    """Ajoute le sol en damier crème / terracotta, prolongé devant et sur les côtés de la salle."""
    verts, faces, mats = [], [], []
    nx, ny = round(2 * FLOOR_X / TILE), round(2 * FLOOR_Y / TILE)
    for i in range(nx):
        for j in range(ny):
            x0, y0 = -FLOOR_X + i * TILE, -FLOOR_Y + j * TILE
            start = len(verts)
            verts += [(x0, y0, 0), (x0 + TILE, y0, 0), (x0 + TILE, y0 + TILE, 0), (x0, y0 + TILE, 0)]
            faces.append((start, start + 1, start + 2, start + 3))
            mats.append("terracotta" if (i + j) % 2 else "cream")
    b.add(verts, faces, face_mats=mats, fix_normals=False)


def add_walls(b):
    """Ajoute les trois murs ocre (faces vers la salle), le soubassement, la cimaise et la frise."""
    b.poly([(-HALF_W, BACK, 0), (HALF_W, BACK, 0), (HALF_W, BACK, WALL_H), (-HALF_W, BACK, WALL_H)], "ochre", facing=(0, -1, 0))
    for side in (-1, 1):
        x = side * HALF_W
        b.poly([(x, 0, 0), (x, BACK, 0), (x, BACK, WALL_H), (x, 0, WALL_H)], "ochre", facing=(-side, 0, 0))
    spans = {"back": (-HALF_W, HALF_W), "left": (0, BACK - 0.05), "right": (0, BACK - 0.05)}
    for wall, (u0, u1) in spans.items():
        wbox(b, wall, u0, u1, 0, DADO, 0, 0.05, "red_dark")
        wbox(b, wall, u0, u1, DADO, DADO + 0.07, 0, 0.08, "wood")
        wbox(b, wall, u0, u1, WALL_H - 0.16, WALL_H, 0, 0.04, "cream")


def add_kitchen_door(b):
    """Ajoute la porte battante bleue de la cuisine (hublot) et l'horloge au-dessus."""
    wbox(b, "back", -0.58, 0.58, 0, 2.32, 0, 0.09, "wood")
    wbox(b, "back", -0.47, 0.47, 0, 2.21, 0.09, 0.11, "blue")
    wbox(b, "back", -0.47, 0.47, 0, 0.28, 0.11, 0.125, "grey")
    wbox(b, "back", 0.30, 0.38, 1.0, 1.3, 0.11, 0.13, "grey")
    b.lathe([(0.24, 0), (0.24, 0.035), (0.17, 0.035), (0.17, 0.015), (0, 0.015)], (0, BACK - 0.11, 1.62), "cream",
            axis="-Y", segs=12, mats=["cream", "cream", "cream", "glass"])
    b.lathe([(0.25, 0), (0.25, 0.05), (0.2, 0.05), (0.2, 0.03), (0, 0.03)], (0, BACK, 2.84), "ink",
            axis="-Y", segs=12, mats=["ink", "ink", "ink", "cream"])
    b.box((0.03, 0.01, 0.15), (0, BACK - 0.035, 2.90), "ink")
    b.box((0.11, 0.01, 0.03), (0.045, BACK - 0.035, 2.84), "ink")


def add_bar(b):
    """Ajoute le comptoir en bois à dessus crème, son repose-pieds et deux tabourets."""
    b.bb(BAR_X0, BAR_X1, BAR_Y0, BAR_Y1, 0.10, BAR_TOP - 0.07, "wood")
    b.bb(BAR_X0, BAR_X1 - 0.03, BAR_Y0 + 0.04, BAR_Y1, 0, 0.10, "ink")
    b.bb(BAR_X0, BAR_X1 + 0.08, BAR_Y0 - 0.10, BAR_Y1 + 0.06, BAR_TOP - 0.07, BAR_TOP, "cream")
    count = 4
    width = (BAR_X1 - BAR_X0 - 0.1) / count
    for k in range(count):
        x0 = BAR_X0 + 0.1 + k * width
        b.bb(x0, x0 + width - 0.1, BAR_Y0 - 0.025, BAR_Y0, 0.22, 0.90, "red_dark")
    b.tube((BAR_X0, BAR_Y0 - 0.10, 0.20), (BAR_X1, BAR_Y0 - 0.10, 0.20), 0.022, "grey", segs=5)
    for x in (BAR_X0 + 0.75, BAR_X0 + 1.5, BAR_X0 + 2.25, BAR_X1 - 0.02):
        b.tube((x, BAR_Y0, 0.20), (x, BAR_Y0 - 0.10, 0.20), 0.016, "grey", segs=4, caps=False)
    for x in (-2.75, -2.0):
        b.lathe([(0, 0), (0.19, 0), (0.19, 0.03), (0.03, 0.06), (0.03, 0.70), (0.17, 0.70), (0.19, 0.74), (0.17, 0.79), (0, 0.79)],
                (x, 1.62, 0), "ink", segs=10, mats=["ink"] * 5 + ["red"] * 3)
        b.lathe([(0.03, 0), (0.12, 0), (0.12, 0.02), (0.03, 0.02)], (x, 1.62, 0.26), "grey", segs=8)


def add_coffee_machine(b, loc):
    """Ajoute la machine à café simplifiée : caisson gris, groupes, bac et tasses sur le dessus."""
    with b.at(loc):
        b.bb(-0.36, 0.36, -0.20, 0.20, 0.03, 0.50, "grey", bevel=0.03)
        b.bb(-0.37, 0.37, -0.215, -0.16, 0.36, 0.47, "red")
        b.bb(-0.30, 0.30, -0.205, -0.17, 0.10, 0.33, "ink")
        b.bb(-0.33, 0.33, -0.30, -0.19, 0.0, 0.06, "ink")
        for x in (-0.15, 0.15):
            b.cyl(0.055, 0.08, (x, -0.25, 0.25), "cream", segs=8)
            b.tube((x, -0.25, 0.25), (x + 0.12, -0.33, 0.23), 0.016, "ink", segs=4)
            b.lathe([(0, 0), (0.035, 0), (0.045, 0.06), (0.035, 0.06), (0, 0.03)], (x, -0.25, 0.06), "cream", segs=6)
        b.sphere(0.028, (0.28, -0.22, 0.415), "light", subdiv=0)
        b.tube((-0.30, -0.19, 0.30), (-0.34, -0.30, 0.16), 0.014, "cream", segs=4)
        for x, y in ((-0.2, 0.02), (-0.05, 0.02), (0.1, 0.02), (-0.12, -0.1)):
            b.lathe([(0, 0), (0.04, 0), (0.055, 0.07), (0.042, 0.07), (0, 0.035)], (x, y, 0.50), "cream", segs=6)


def add_bottle(b, loc, mat, height=0.34, radius=0.055):
    """Ajoute une bouteille de révolution à col étroit."""
    b.lathe([(0, 0), (radius, 0), (radius, height * 0.55), (radius * 0.35, height * 0.75),
             (radius * 0.35, height), (0, height)], loc, mat, segs=6)


def add_glass(b, loc, wine="red_dark"):
    """Ajoute un petit verre évasé rempli."""
    b.lathe([(0, 0), (0.028, 0), (0.04, 0.11), (0, 0.085)], loc, "glass", segs=6, mats=["glass", "glass", wine])


def add_shelves(b):
    """Ajoute les étagères à bouteilles derrière le comptoir (mur du fond gauche et mur gauche)."""
    palette = ["green_dark", "red_dark", "olive", "blue", "terracotta", "glass", "green_dark", "red"]
    for level, z in enumerate((1.50, 2.10)):
        wbox(b, "back", -3.38, -1.90, z - 0.05, z, 0, 0.22, "wood")
        for k in range(7):
            x = -3.24 + k * 0.205
            height = 0.30 + 0.07 * ((k * 3 + level) % 3)
            add_bottle(b, (x, BACK - 0.12, z), palette[(k * 3 + level * 5) % len(palette)], height=height)
        wbox(b, "left", 2.95, 4.72, z - 0.05, z, 0, 0.22, "wood")
        for k in range(6):
            y = 3.12 + k * 0.29
            if (k + level) % 3 == 2:
                for dy in (-0.06, 0.06):
                    add_glass(b, (-HALF_W + 0.12, y + dy, z), wine="glass")
            else:
                add_bottle(b, (-HALF_W + 0.12, y, z), palette[(k * 5 + level * 3 + 1) % len(palette)],
                           height=0.30 + 0.06 * ((k + level) % 3))
    for x in (-3.2, -2.05):
        b.prism([(x, BACK, 1.45), (x, BACK - 0.18, 1.45), (x, BACK, 1.28)], (0.04, 0, 0), "wood")
        b.prism([(x, BACK, 2.05), (x, BACK - 0.18, 2.05), (x, BACK, 1.88)], (0.04, 0, 0), "wood")


def add_chair(b, loc, yaw):
    """Ajoute une chaise bistrot rouge ; le dossier est du côté +Y du repère local."""
    with b.at(loc, (0, 0, yaw)):
        b.lathe([(0, 0.43), (0.18, 0.43), (0.20, 0.45), (0.20, 0.47), (0, 0.47)], (0, 0, 0), "red", segs=8, phase=math.pi / 8)
        for sx in (-1, 1):
            for sy in (-1, 1):
                b.tube((sx * 0.12, sy * 0.12, 0.44), (sx * 0.17, sy * 0.17, 0.004), 0.018, "ink", segs=4)
            b.tube((sx * 0.14, 0.13, 0.44), (sx * 0.16, 0.20, 0.90), 0.018, "ink", segs=4)
        b.box((0.40, 0.035, 0.15), (0, 0.195, 0.82), "red", rot=(-9, 0, 0))
        b.box((0.34, 0.02, 0.05), (0, 0.17, 0.62), "red", rot=(-9, 0, 0))


def add_place_setting(b, loc, food):
    """Ajoute une assiette crème garnie."""
    b.lathe([(0.065, 0), (0.105, 0.018), (0.085, 0.018), (0.055, 0.008), (0, 0.008)], loc, "cream", segs=8,
            mats=["ochre", "cream", "cream", "cream"])
    b.sphere(0.045, (loc[0], loc[1], loc[2] + 0.02), food, subdiv=0, scale=(1, 1, 0.6))


def add_table(b, loc, yaw, chairs=(0, 180), mail=False):
    """Ajoute une table bistrot ronde nappée et dressée, avec ses chaises (angles autour de la table)."""
    with b.at(loc, (0, 0, yaw)):
        b.lathe([(0, 0), (0.24, 0), (0.24, 0.03), (0.05, 0.06), (0.035, 0.09), (0.035, 0.60), (0.47, 0.60),
                 (0.455, TABLE_TOP), (0, TABLE_TOP)], (0, 0, 0), "ink", segs=12, mats=["ink"] * 5 + ["red", "red", "cream"])
        if mail:
            for side in (-1, 1):
                add_place_setting(b, (side * 0.30, -0.15, TABLE_TOP), "olive" if side < 0 else "terracotta")
                add_glass(b, (side * 0.12, -0.33, TABLE_TOP))
        else:
            for side in (-1, 1):
                add_place_setting(b, (side * 0.24, 0.0, TABLE_TOP), "olive" if side < 0 else "terracotta")
                add_glass(b, (side * 0.13, 0.22 * side, TABLE_TOP))
            add_bottle(b, (0.0, -0.20, TABLE_TOP), "green_dark", height=0.30, radius=0.05)
            b.lathe([(0, 0), (0.045, 0), (0.06, 0.07), (0, 0.07)], (0.02, 0.2, TABLE_TOP), "terracotta", segs=6,
                    mats=["terracotta", "terracotta", "light"])
        for angle in chairs:
            rad = math.radians(angle)
            add_chair(b, (0.72 * math.cos(rad), 0.72 * math.sin(rad), 0), angle - 90)


def add_window(b):
    """Ajoute la fenêtre du mur droit : vitrage, croisée crème, appui, brise-bise et pot fleuri."""
    u0, u1, z0, z1 = 2.3, 4.1, 1.28, 2.78
    wbox(b, "right", u0, u1, z0, z1, 0, 0.02, "glass")
    for a, c in ((u0 - 0.08, u0), (u1, u1 + 0.08)):
        wbox(b, "right", a, c, z0 - 0.08, z1 + 0.08, 0, 0.08, "cream")
    wbox(b, "right", (u0 + u1) / 2 - 0.035, (u0 + u1) / 2 + 0.035, z0, z1, 0.02, 0.075, "cream")
    for a, c in ((z0 - 0.08, z0), (z1, z1 + 0.08)):
        wbox(b, "right", u0, u1, a, c, 0, 0.08, "cream")
    wbox(b, "right", u0, u1, 2.22, 2.27, 0.02, 0.06, "cream")
    wbox(b, "right", u0 - 0.14, u1 + 0.14, z0 - 0.14, z0 - 0.08, 0, 0.2, "wood")
    wbox(b, "right", u0, u1, z0, z0 + 0.52, 0.02, 0.045, "red")
    wbox(b, "right", u0, u1, z0 + 0.52, z0 + 0.55, 0.02, 0.06, "wood")
    add_plant(b, (HALF_W - 0.11, 2.75, z0 - 0.08), 0.085, flowers=("red", "light", "red"))


def add_entrance_door(b):
    """Ajoute la porte vitrée d'entrée sur le mur gauche, côté salle."""
    u0, u1 = 0.25, 1.40
    wbox(b, "left", u0 - 0.09, u1 + 0.09, 0, 2.42, 0, 0.09, "wood")
    wbox(b, "left", u0, u1, 0, 2.33, 0.09, 0.10, "red_dark")
    wbox(b, "left", u0 + 0.13, u1 - 0.13, 0.95, 2.20, 0.10, 0.11, "glass")
    wbox(b, "left", u0 + 0.13, u1 - 0.13, 0.16, 0.80, 0.10, 0.115, "red")
    wbox(b, "left", u1 - 0.11, u1 - 0.05, 0.98, 1.28, 0.11, 0.15, "grey")


def add_chalkboard(b):
    """Ajoute l'ardoise « menu » murale : titre jaune et lignes de craie."""
    u0, u1, z0, z1 = 2.02, 2.98, 1.32, 2.68
    wbox(b, "back", u0, u1, z0, z1, 0, 0.05, "wood")
    wbox(b, "back", u0 + 0.07, u1 - 0.07, z0 + 0.07, z1 - 0.07, 0.05, 0.058, "ink")
    wbox(b, "back", u0 + 0.26, u1 - 0.26, z1 - 0.30, z1 - 0.20, 0.058, 0.064, "light")
    for k, width in enumerate((0.52, 0.40, 0.56, 0.36, 0.48)):
        z = z1 - 0.48 - k * 0.15
        wbox(b, "back", u0 + 0.16, u0 + 0.16 + width, z, z + 0.045, 0.058, 0.064, "cream")
        wbox(b, "back", u1 - 0.24, u1 - 0.15, z, z + 0.045, 0.058, 0.064, "terracotta")


def add_pictures(b):
    """Ajoute deux petits cadres décoratifs sur le mur droit, côté salle."""
    for u0, u1, z0, z1, inner in ((0.75, 1.25, 1.75, 2.45, "blue"), (1.42, 1.98, 1.95, 2.40, "olive")):
        wbox(b, "right", u0, u1, z0, z1, 0, 0.04, "wood")
        wbox(b, "right", u0 + 0.06, u1 - 0.06, z0 + 0.06, z1 - 0.06, 0.04, 0.046, "cream")
        wbox(b, "right", u0 + 0.12, u1 - 0.12, z0 + 0.12, (z0 + z1) / 2, 0.046, 0.05, inner)


def add_pendant(b, x, y, bottom=2.72):
    """Ajoute une suspension : fil fin depuis le haut des murs, abat-jour rouge et ampoule lumineuse."""
    b.tube((x, y, bottom + 0.30), (x, y, WALL_H), 0.012, "ink", segs=4, caps=False)
    b.lathe([(0, 0.25), (0.045, 0.25), (0.31, 0.0), (0.34, 0.0), (0.06, 0.27), (0.05, 0.34), (0, 0.34)], (x, y, bottom), "red",
            segs=12, mats=["cream", "cream", "red", "red", "ink", "ink"])
    b.sphere(0.10, (x, y, bottom + 0.07), "light", subdiv=1)


def add_plant(b, loc, radius, flowers=()):
    """Ajoute un pot en terre cuite garni d'un feuillage en boules facettées, éventuellement fleuri."""
    x, y, z = loc
    b.lathe([(0, 0), (radius * 0.7, 0), (radius, radius * 1.5), (radius * 1.12, radius * 1.5),
             (radius * 1.12, radius * 1.8), (0, radius * 1.8)], loc, "terracotta", segs=8)
    b.sphere(radius * 1.35, (x, y, z + radius * 2.9), "green_dark", scale=(1.1, 1.1, 1.0))
    b.sphere(radius * 0.85, (x + radius * 0.5, y - radius * 0.4, z + radius * 4.0), "olive", subdiv=1)
    for k, mat in enumerate(flowers):
        angle = 2.1 * k + 0.5
        b.sphere(radius * 0.4, (x - radius * 1.0, y + radius * 1.1 * math.cos(angle), z + radius * (3.0 + 0.9 * math.sin(angle))),
                 mat, subdiv=0)


def add_coat_rack(b, loc):
    """Ajoute un portemanteau sur pied avec un chapeau et une veste."""
    with b.at(loc):
        b.lathe([(0, 0), (0.22, 0), (0.22, 0.03), (0.03, 0.07), (0.03, 1.85), (0, 1.88)], (0, 0, 0), "ink", segs=8)
        for k in range(4):
            angle = math.pi / 4 + k * math.pi / 2
            b.tube((0, 0, 1.68), (0.2 * math.cos(angle), 0.2 * math.sin(angle), 1.80), 0.018, "ink", segs=4)
        b.lathe([(0.21, 0), (0.12, 0.02), (0.10, 0.13), (0, 0.15)], (0, 0, 1.87), "olive", segs=8,
                mats=["olive", "red_dark", "olive"])
        b.prism([(0.05, -0.20, 1.72), (0.30, -0.24, 1.60), (0.36, -0.22, 0.95), (0.06, -0.18, 0.95)], (0, 0.14, 0), "blue")


def build_static():
    """Assemble tout le décor fixe dans `interior_static`."""
    b = Builder("interior_static")
    add_floor(b)
    add_walls(b)
    add_kitchen_door(b)
    add_bar(b)
    add_coffee_machine(b, (-2.75, 2.42, BAR_TOP))
    add_glass(b, (-2.0, 2.3, BAR_TOP))
    add_glass(b, (-1.88, 2.42, BAR_TOP), wine="terracotta")
    add_shelves(b)
    add_table(b, MAIL_ORIGIN[:2] + (0,), 0, chairs=(8, 172), mail=True)
    add_table(b, (-2.45, 0.35, 0), 20)
    add_table(b, (2.45, 0.0, 0), 65)
    add_table(b, (2.55, 3.65, 0), -15)
    add_window(b)
    add_entrance_door(b)
    add_chalkboard(b)
    add_pictures(b)
    add_pendant(b, -2.0, 2.4)
    add_pendant(b, 0.0, 0.5)
    add_pendant(b, 2.0, 1.6)
    add_plant(b, (3.08, 4.58, 0), 0.26)
    add_plant(b, (-3.12, 1.6, 0), 0.22)
    add_plant(b, (-3.1, -0.25, 0), 0.24)
    add_coat_rack(b, (3.12, 1.95, 0))
    return b.to_object()


def build_phone():
    """Construit le téléphone rétro à cadran posé sur le comptoir ; origine au centre visuel."""
    b = Builder("spot_phone")
    with b.at((PHONE_ORIGIN[0], PHONE_ORIGIN[1], BAR_TOP)):
        slope = math.degrees(math.atan2(0.19, 0.31))
        b.prism([(-0.33, -0.27, 0), (-0.33, 0.20, 0), (-0.33, 0.20, 0.27), (-0.33, 0.04, 0.27), (-0.33, -0.27, 0.08)],
                (0.66, 0, 0), "red")
        b.bb(-0.35, 0.35, -0.29, 0.22, 0.0, 0.035, "red_dark")
        with b.at((0, -0.115, 0.175), (slope, 0, 0)):
            b.lathe([(0.165, 0), (0.165, 0.03), (0.062, 0.03), (0.062, 0.045), (0, 0.045)], (0, 0, 0), "cream", segs=14,
                    mats=["cream", "cream", "red_dark", "red_dark"])
            for k in range(8):
                angle = math.radians(-60 + k * 300 / 7)
                b.lathe([(0.027, 0), (0.027, 0.006), (0, 0.006)], (0.113 * math.cos(angle), 0.113 * math.sin(angle), 0.03),
                        "ink", segs=6)
        for side in (-1, 1):
            b.bb(side * 0.15 - 0.055, side * 0.15 + 0.055, 0.05, 0.19, 0.27, 0.40, "red_dark")
            b.lathe([(0, 0), (0.085, 0), (0.105, 0.03), (0.105, 0.10), (0.085, 0.14), (0, 0.14)],
                    (side * 0.32, 0.12, 0.335), "red", segs=10)
        b.bb(-0.30, 0.30, 0.065, 0.175, 0.385, 0.475, "red", bevel=0.02)
        start, end = Vector((-0.40, 0.12, 0.34)), Vector((-0.36, -0.12, 0.03))
        points = []
        for k in range(15):
            t = k / 14
            point = start.lerp(end, t)
            point.x -= 0.03 + 0.045 * math.sin(math.pi * t) + 0.03 * math.sin(2 * math.pi * 4.5 * t)
            point.z -= 0.05 * math.sin(math.pi * t)
            points.append(point)
        for a, c in zip(points, points[1:]):
            b.tube(a, c, 0.014, "ink", segs=4)
    return b.to_object(origin=PHONE_ORIGIN)


def build_mail():
    """Construit l'enveloppe crème à cachet de cire, dressée sur son présentoir ; origine au centre visuel."""
    b = Builder("spot_mail")
    x, y, z = MAIL_ORIGIN
    b.prism([(x - 0.19, y - 0.07, TABLE_TOP), (x - 0.19, y + 0.13, TABLE_TOP), (x - 0.19, y + 0.10, TABLE_TOP + 0.16),
             (x - 0.19, y + 0.045, TABLE_TOP + 0.16), (x - 0.19, y - 0.01, TABLE_TOP + 0.10), (x - 0.19, y - 0.07, TABLE_TOP + 0.10)],
            (0.38, 0, 0), "wood")
    with b.at(MAIL_ORIGIN, (-12, 0, 0)):
        b.box((0.80, 0.045, 0.54), (0, 0, 0), "cream")
        b.prism([(-0.40, -0.0225, 0.27), (0.40, -0.0225, 0.27), (0, -0.0225, -0.075)], (0, -0.008, 0), "grey")
        b.prism([(-0.365, -0.0305, 0.27), (0.365, -0.0305, 0.27), (0, -0.0305, -0.045)], (0, -0.012, 0), "cream")
        for side in (-1, 1):
            b.box((0.36, 0.006, 0.022), (side * 0.23, -0.0255, -0.165), "grey", rot=(0, side * 36, 0))
        b.lathe([(0.105, 0), (0.105, 0.02), (0.085, 0.035), (0.055, 0.035), (0.045, 0.025), (0, 0.025)], (0, -0.036, -0.03), "red",
                axis="-Y", segs=10, mats=["red", "red", "red", "red_dark", "red_dark"])
    return b.to_object(origin=MAIL_ORIGIN)


def build_insta():
    """Construit le cadre photo mural en forme d'appareil photo stylisé ; origine au centre visuel."""
    b = Builder("spot_insta")
    back = BACK - 0.005 - INSTA_ORIGIN[1]
    with b.at(INSTA_ORIGIN):
        b.prism(rounded_square(0.41, 0.13, back), (0, -back - 0.01, 0), "red")
        b.prism(rounded_square(0.335, 0.085, -0.01), (0, -0.03, 0), "cream")
        b.lathe([(0.235, 0), (0.235, 0.07), (0.165, 0.07), (0.165, 0.03), (0.075, 0.03), (0.075, 0.045), (0, 0.045)],
                (0, -0.04, -0.03), "red", axis="-Y", segs=16, mats=["red", "red", "red_dark", "light", "ink", "ink"])
        b.cyl(0.055, 0.035, (0.215, -0.04, 0.225), "light", axis="-Y", segs=8)
        b.bb(-0.27, -0.09, -0.065, -0.04, 0.20, 0.265, "red")
        b.tube((0, back - 0.014, 0.40), (0, back - 0.014, 0.50), 0.012, "ink", segs=4)
    return b.to_object(origin=INSTA_ORIGIN)


def build_map():
    """Construit le plan encadré et sa grosse épingle rouge en relief ; origine au centre visuel."""
    b = Builder("spot_map")
    back = BACK - 0.005 - MAP_ORIGIN[1]
    half_w, half_h, bar = 0.46, 0.40, 0.065
    with b.at(MAP_ORIGIN):
        b.bb(-half_w + bar, half_w - bar, 0.045, back, -half_h + bar, half_h - bar, "cream")
        for x0, x1 in ((-half_w, -half_w + bar), (half_w - bar, half_w)):
            b.bb(x0, x1, 0.0, back, -half_h, half_h, "wood")
        for z0, z1 in ((-half_h, -half_h + bar), (half_h - bar, half_h)):
            b.bb(-half_w + bar, half_w - bar, 0.0, back, z0, z1, "wood")
        b.prism([(-0.395, 0.045, -0.335), (-0.02, 0.045, -0.335), (-0.08, 0.045, -0.22), (-0.19, 0.045, -0.17),
                 (-0.25, 0.045, -0.05), (-0.395, 0.045, 0.0)], (0, -0.008, 0), "blue")
        b.prism([(-0.36, 0.045, 0.17), (-0.20, 0.045, 0.19), (-0.21, 0.045, 0.31), (-0.35, 0.045, 0.30)], (0, -0.008, 0), "olive")
        streets = [((0.02, 0.03), 0.74, 16), ((0.05, -0.02), 0.56, -62), ((-0.12, 0.17), 0.30, -72),
                   ((0.14, -0.21), 0.44, 8), ((0.10, 0.25), 0.50, 4), ((0.30, 0.0), 0.60, 88)]
        # Épaisseurs décalées : évite les faces coplanaires aux croisements de rues.
        for k, ((sx, sz), length, angle) in enumerate(streets):
            b.box((length, 0.006 + 0.002 * k, 0.04), (sx, 0.040, sz), "grey", rot=(0, angle, 0))
        tip = Vector((0.13, 0.04, -0.10))
        axis = Vector((0.0, -0.5, 0.87)).normalized()
        matrix = Matrix.Translation(tip) @ axis.to_track_quat("Z", "Y").to_matrix().to_4x4()
        b.lathe([(0, 0), (0.03, 0.08), (0.095, 0.19), (0.115, 0.255), (0.095, 0.32), (0.04, 0.35), (0, 0.35)], None, "red",
                segs=10, matrix=matrix)
        b.lathe([(0.09, 0), (0.09, 0.017), (0, 0.017)], None, "red_dark", segs=8,
                matrix=Matrix.Translation(tip + Vector((0, 0.005, 0))) @ Vector((0, -1, 0)).to_track_quat("Z", "Y").to_matrix().to_4x4())
    return b.to_object(origin=MAP_ORIGIN)


def main():
    """Assemble l'intérieur, exporte `interior.glb` et rend les aperçus paysage, portrait et plongée."""
    common.reset_scene()
    objects = [build_static(), build_phone(), build_mail(), build_insta(), build_map()]
    # Export simple face : le culling des faces arrière est porté par les matériaux (doubleSided = false).
    for material in bpy.data.materials:
        material.use_backface_culling = True
    common.finish("interior", objects, {}, shots={
        "landscape": ((0, -6, 1.9), (0, 3, 1.6), 32, 900, 562),
        "portrait": ((0, -8.5, 2.0), (0, 3, 1.7), 44, 450, 950),
        "top34": ((5.0, -8.5, 8.0), (0, 2.2, 0.8), 38, 900, 700),
    })


main()
