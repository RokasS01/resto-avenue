"""Génère les 5 mini-villes low-poly de Resto Avenue (cities.blend + cities.glb + aperçus).

Usage : blender --background --python build_cities.py [-- --no-render] [-- --only nimes]
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Vector
from mathutils.geometry import tessellate_polygon

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
BLEND_PATH = os.path.join(HERE, "cities.blend")
GLB_PATH = os.path.join(ROOT, "public", "models", "cities.glb")
PREVIEW_DIR = os.path.join(HERE, "previews")

G = 0.06
HALF = 1.6
SPACING = 5.0
AZIMUTH = float(os.environ.get("CITIES_AZ", "-22"))
SUFFIX = os.environ.get("CITIES_SUFFIX", "34")

PALETTE = {
    "creme": "#f6efe4",
    "encre": "#1d1a1a",
    "gris_chaud": "#8b8178",
    "pierre_claire": "#e6d9c2",
    "pierre_doree": "#d9bf8f",
    "brique_rose": "#d98a6a",
    "brique_rouge": "#b5553f",
    "terracotta": "#c9714a",
    "ocre": "#ecd3a8",
    "olive": "#7c8f5a",
    "vert_fonce": "#4f6b4a",
    "eau": "#5fb0bd",
    "jaune": "#f2b84b",
}

Z = Vector((0, 0, 1))


def srgb_to_linear(hex_color):
    """Convertit une couleur hexadécimale sRGB en triplet linéaire."""
    out = []
    for i in (1, 3, 5):
        c = int(hex_color[i:i + 2], 16) / 255.0
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return tuple(out)


def make_materials():
    """Crée les matériaux Principled unis partagés par toutes les villes."""
    mats = {}
    for name, hex_color in PALETTE.items():
        mat = bpy.data.materials.new("mat_" + name)
        if mat.node_tree is None:
            mat.use_nodes = True
        rgba = srgb_to_linear(hex_color) + (1.0,)
        bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        bsdf.inputs["Base Color"].default_value = rgba
        bsdf.inputs["Roughness"].default_value = 0.8
        bsdf.inputs["Metallic"].default_value = 0.0
        mat.diffuse_color = rgba
        # Culling actif => doubleSided=false dans le glTF (moins coûteux, et révèle les faces inversées).
        mat.use_backface_culling = True
        mats[name] = mat
    return mats


def poly_normal(pts):
    """Normale d'un polygone (méthode de Newell)."""
    n = Vector((0, 0, 0))
    for i, p in enumerate(pts):
        q = pts[(i + 1) % len(pts)]
        n.x += (p.y - q.y) * (p.z + q.z)
        n.y += (p.z - q.z) * (p.x + q.x)
        n.z += (p.x - q.x) * (p.y + q.y)
    return n


def ring(cx, cy, z, rx, ry, n, a0=0.0, jit=None):
    """Anneau de n points (sens trigo vu de dessus) sur une ellipse, avec gigue radiale optionnelle."""
    pts = []
    for i in range(n):
        t = a0 + 2 * math.pi * i / n
        k = jit[i % len(jit)] if jit else 1.0
        pts.append(Vector((cx + rx * k * math.cos(t), cy + ry * k * math.sin(t), z)))
    return pts


def rect_pts(cx, z0, w, h):
    """Rectangle (u, v) pour un décalque mural."""
    return [(cx - w / 2, z0), (cx + w / 2, z0), (cx + w / 2, z0 + h), (cx - w / 2, z0 + h)]


def arch_pts(cx, z0, w, h, segs=4):
    """Baie en plein cintre (u, v) pour un décalque mural."""
    r = w / 2
    pts = [(cx - r, z0), (cx + r, z0)]
    for i in range(segs + 1):
        t = math.pi * i / segs
        pts.append((cx + r * math.cos(t), z0 + h - r + r * math.sin(t)))
    return pts


def disc_pts(cx, cz, r, n=8):
    """Disque polygonal (u, v) pour un décalque mural."""
    return [(cx + r * math.cos(2 * math.pi * i / n + math.pi / n),
             cz + r * math.sin(2 * math.pi * i / n + math.pi / n)) for i in range(n)]


def arch_profile(w, h, ow, oh, segs=8):
    """Profil (u, z) d'un mur percé d'une arche centrée en plein cintre."""
    r = ow / 2
    pts = [(-w / 2, 0), (-r, 0)]
    for i in range(segs + 1):
        t = math.pi - math.pi * i / segs
        pts.append((r * math.cos(t), oh - r + r * math.sin(t)))
    pts += [(r, 0), (w / 2, 0), (w / 2, h), (-w / 2, h)]
    return pts


def bridge_profile(n, span, pier, h, spring, hump=0.04, segs=5):
    """Profil (u, z) d'un pont à n arches, centré en u."""
    length = n * span + (n + 1) * pier
    x = -length / 2
    pts = [(x, 0)]
    r = span / 2
    for _ in range(n):
        x += pier
        pts.append((x, 0))
        for i in range(segs + 1):
            t = math.pi - math.pi * i / segs
            pts.append((x + r + r * math.cos(t), spring + r * math.sin(t)))
        x += span
        pts.append((x, 0))
    pts += [(length / 2, 0), (length / 2, h), (0, h + hump), (-length / 2, h)]
    return pts


def chaikin(pts, iterations):
    """Lisse une polyligne 2D ouverte (coupe des coins de Chaikin) en conservant ses extrémités."""
    for _ in range(iterations):
        out = [pts[0]]
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            out.append((0.75 * x0 + 0.25 * x1, 0.75 * y0 + 0.25 * y1))
            out.append((0.25 * x0 + 0.75 * x1, 0.25 * y0 + 0.75 * y1))
        out.append(pts[-1])
        pts = out
    return pts


def frame(x, y, z, rot, dist):
    """Repère mural (origine, vecteur droite) de la face tournée vers -Y local à `dist` du centre."""
    r = Vector((math.cos(rot), math.sin(rot), 0))
    n = r.cross(Z)
    return Vector((x, y, z)) + n * dist, r


class Builder:
    """Accumule la géométrie d'une ville dans un seul bmesh, sans sommets partagés (shading plat)."""

    def __init__(self):
        """Initialise un bmesh vide."""
        self.bm = bmesh.new()
        self.mats = []
        self.z0 = 0.0

    def mi(self, name):
        """Retourne l'index de slot du matériau, en l'ajoutant au besoin."""
        if name not in self.mats:
            self.mats.append(name)
        return self.mats.index(name)

    def face(self, pts, mat, hint=None):
        """Ajoute un polygone ; `hint` donne le côté vers lequel la normale doit pointer."""
        pts = [Vector(p) for p in pts]
        if hint is not None and poly_normal(pts).dot(Vector(hint)) < 0:
            pts.reverse()
        verts = [self.bm.verts.new((p.x, p.y, p.z + self.z0)) for p in pts]
        f = self.bm.faces.new(verts)
        f.material_index = self.mi(mat)

    def solid(self, faces, mat):
        """Ajoute un solide convexe : chaque face est orientée à l'opposé du barycentre."""
        allp = [Vector(p) for f in faces for p in f]
        c = sum(allp, Vector((0, 0, 0))) / len(allp)
        for i, f in enumerate(faces):
            fp = [Vector(p) for p in f]
            fc = sum(fp, Vector((0, 0, 0))) / len(fp)
            self.face(fp, mat if isinstance(mat, str) else mat[i], fc - c)

    def box(self, x, y, z, sx, sy, sz, mat, rot=0.0, top=True, bottom=False):
        """Pavé centré en (x, y), base à z, tourné de `rot` autour de Z."""
        c, s = math.cos(rot), math.sin(rot)
        hx, hy = sx / 2, sy / 2
        p = [(x + lx * c - ly * s, y + lx * s + ly * c, z + lz)
             for lz in (0, sz) for lx, ly in ((-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy))]
        idx = [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        if top:
            idx.append((4, 5, 6, 7))
        if bottom:
            idx.append((3, 2, 1, 0))
        self.solid([[p[i] for i in f] for f in idx], mat)

    def frustum(self, x, y, z0, z1, r0, r1, n, mat, rot=0.0, sy=1.0, top=True, bottom=False, mat_top=None):
        """Tronc de prisme régulier à n côtés (cône si r1 == 0), un pan tourné vers -Y."""
        a0 = -math.pi / 2 + math.pi / n + rot
        lo = ring(x, y, z0, r0, r0 * sy, n, a0)
        faces, mats = [], []
        if r1 <= 1e-6:
            apex = Vector((x, y, z1))
            for i in range(n):
                faces.append([lo[i], lo[(i + 1) % n], apex])
                mats.append(mat)
        else:
            hi = ring(x, y, z1, r1, r1 * sy, n, a0)
            for i in range(n):
                faces.append([lo[i], lo[(i + 1) % n], hi[(i + 1) % n], hi[i]])
                mats.append(mat)
            if top:
                faces.append(hi)
                mats.append(mat_top or mat)
        if bottom:
            faces.append(lo)
            mats.append(mat)
        self.solid(faces, mats)

    def band(self, lo, hi, mat, mode, centre=(0, 0)):
        """Bande de quads entre deux anneaux ; mode = 'out', 'in' ou 'up' pour l'orientation."""
        n = len(lo)
        for i in range(n):
            j = (i + 1) % n
            quad = [lo[i], lo[j], hi[j], hi[i]]
            if mode == "up":
                hint = Z
            else:
                mid = (lo[i] + lo[j]) / 2
                hint = Vector((mid.x - centre[0], mid.y - centre[1], 0))
                if mode == "in":
                    hint = -hint
            self.face(quad, mat, hint)

    def extrude(self, profile, mat, x, y, z, rot, depth):
        """Extrude un profil (u, z) possiblement concave, centré en (x, y), sur `depth` ; sans dessous."""
        area = sum(p[0] * q[1] - q[0] * p[1] for p, q in zip(profile, profile[1:] + profile[:1]))
        if area < 0:
            profile = profile[::-1]
        o, r = frame(x, y, z, rot, depth / 2)
        n = r.cross(Z)
        front = [o + r * u + Z * v for u, v in profile]
        back = [p - n * depth for p in front]
        for tri in tessellate_polygon([[Vector((u, v, 0)) for u, v in profile]]):
            self.face([front[i] for i in tri], mat, n)
            self.face([back[i] for i in tri], mat, -n)
        cnt = len(profile)
        for i in range(cnt):
            j = (i + 1) % cnt
            (u0, v0), (u1, v1) = profile[i], profile[j]
            if v0 <= 1e-6 and v1 <= 1e-6:
                continue
            self.face([front[i], front[j], back[j], back[i]], mat, r * (v1 - v0) - Z * (u1 - u0))

    def decal(self, o, r, pts, mat, off=0.008):
        """Polygone plaqué sur un mur (repère o, r), décollé de `off` pour éviter le z-fighting."""
        n = r.cross(Z)
        self.face([o + r * u + Z * v + n * off for u, v in pts], mat, n)

    def gable_roof(self, x, y, z, w, d, rh, mat, rot=0.0, wall=None, o=0.035, t=0.03):
        """Toit à deux pans (faîtage selon X local) ; `wall` ajoute les pignons triangulaires."""
        c, s = math.cos(rot), math.sin(rot)

        def P(lx, ly, lz):
            """Passe du repère local de la maison au repère de la ville."""
            return Vector((x + lx * c - ly * s, y + lx * s + ly * c, z + lz))

        if wall:
            for sx in (-1, 1):
                self.face([P(sx * w / 2, -d / 2, 0), P(sx * w / 2, d / 2, 0), P(sx * w / 2, 0, rh)],
                          wall, P(sx, 0, 0) - P(0, 0, 0))
        hw = w / 2 + o
        ez = -o * rh / (d / 2)
        for sy in (-1, 1):
            ye = sy * (d / 2 + o)
            top = [P(-hw, 0, rh + t), P(hw, 0, rh + t), P(hw, ye, ez + t), P(-hw, ye, ez + t)]
            bot = [p - Z * t for p in top]
            faces = [top, [top[2], top[3], bot[3], bot[2]],
                     [top[0], top[3], bot[3], bot[0]], [top[1], top[2], bot[2], bot[1]]]
            self.solid(faces + [bot], mat)
            # Le dessous sert uniquement à orienter : on le retire pour économiser des triangles.
            self.bm.faces.ensure_lookup_table()
            bmesh.ops.delete(self.bm, geom=[self.bm.faces[-1]], context="FACES")

    def hip_roof(self, x, y, z, w, d, rh, mat, rot=0.0, o=0.03):
        """Toit à quatre pans (faîtage selon X local, pyramide si w == d)."""
        c, s = math.cos(rot), math.sin(rot)

        def P(lx, ly, lz):
            """Passe du repère local au repère de la ville."""
            return Vector((x + lx * c - ly * s, y + lx * s + ly * c, z + lz))

        hw, hd = w / 2 + o, d / 2 + o
        base = [P(-hw, -hd, 0), P(hw, -hd, 0), P(hw, hd, 0), P(-hw, hd, 0)]
        rl = max(hw - hd, 0.0)
        if rl < 1e-6:
            apex = P(0, 0, rh)
            faces = [[base[i], base[(i + 1) % 4], apex] for i in range(4)]
        else:
            a, b2 = P(-rl, 0, rh), P(rl, 0, rh)
            faces = [[base[0], base[1], b2, a], [base[1], base[2], b2],
                     [base[2], base[3], a, b2], [base[3], base[0], a]]
        self.solid(faces, mat)

    def house(self, x, y, w, d, h, wall, rot=0.0, rh=None, roof="terracotta", hip=False):
        """Maisonnette : murs, toit terracotta, porte et fenêtres en décalques."""
        rh = rh if rh is not None else d * 0.42
        self.box(x, y, 0, w, d, h, wall, rot, top=False)
        if hip:
            self.hip_roof(x, y, h, w, d, rh, roof, rot)
        else:
            self.gable_roof(x, y, h, w, d, rh, roof, rot, wall=wall)
        o, r = frame(x, y, 0, rot, d / 2)
        self.decal(o, r, rect_pts(-w * 0.22, 0, 0.065, min(0.12, h * 0.5)), "encre")
        nb = 2 if h > 0.3 else 1
        for k in range(nb):
            zw = h * (0.5 if nb == 1 else 0.3 + 0.36 * k)
            self.decal(o, r, rect_pts(w * 0.2, zw, 0.055, 0.065), "encre")
            if nb == 2 and k == 1:
                self.decal(o, r, rect_pts(-w * 0.22, zw, 0.055, 0.065), "encre")
        for side in (1, -1):
            o, r = frame(x, y, 0, rot + side * math.pi / 2, w / 2)
            self.decal(o, r, rect_pts(0, h * 0.55, 0.055, 0.065), "encre")

    def crenels(self, x, y, z, sx, sy, nx, ny, mat, m=(0.07, 0.05, 0.07), rot=0.0):
        """Rangée de merlons sur le pourtour d'un rectangle (nx en façade, ny sur les côtés, coins inclus)."""
        c, s = math.cos(rot), math.sin(rot)
        mw, md, mh = m
        hx, hy = sx / 2 - md / 2, sy / 2 - md / 2
        spots = []
        for i in range(nx):
            lx = -(sx / 2 - mw / 2) + (sx - mw) * i / (nx - 1)
            spots += [(lx, -hy, 0.0), (lx, hy, 0.0)]
        for i in range(1, ny - 1):
            ly = -(sy / 2 - mw / 2) + (sy - mw) * i / (ny - 1)
            spots += [(-hx, ly, math.pi / 2), (hx, ly, math.pi / 2)]
        for lx, ly, r in spots:
            self.box(x + lx * c - ly * s, y + lx * s + ly * c, z, mw, md, mh, mat, rot + r)

    def crenels_round(self, x, y, z, r, n, mat, m=(0.07, 0.05, 0.07), a0=0.0):
        """Couronne de n merlons sur une tour ronde."""
        for i in range(n):
            t = a0 + 2 * math.pi * i / n
            self.box(x + r * math.cos(t), y + r * math.sin(t), z, m[0], m[1], m[2], mat, t + math.pi / 2)

    def cypress(self, x, y, h=0.62, r=0.085):
        """Cyprès conique."""
        self.frustum(x, y, 0, 0.07, 0.02, 0.02, 5, "gris_chaud", top=False)
        self.frustum(x, y, 0.05, 0.05 + h * 0.3, r * 0.55, r, 6, "vert_fonce", top=False, bottom=True)
        self.frustum(x, y, 0.05 + h * 0.3, 0.05 + h, r, 0, 6, "vert_fonce")

    def pine(self, x, y, h=0.75, r=0.27, lean=0.05, rot=0.0):
        """Pin parasol : tronc fin incliné, houppier aplati."""
        lo = ring(x, y, 0, 0.032, 0.032, 5)
        hi = ring(x + lean, y, h * 0.74, 0.02, 0.02, 5)
        self.band(lo, hi, "gris_chaud", "out", (x, y))
        cx = x + lean
        self.frustum(cx, y, h * 0.7, h * 0.8, r * 0.55, r, 7, "vert_fonce", rot, top=False, bottom=True)
        self.frustum(cx, y, h * 0.8, h * 0.9, r, r * 0.92, 7, "vert_fonce", rot, top=False)
        self.frustum(cx, y, h * 0.9, h, r * 0.92, r * 0.45, 7, "vert_fonce", rot)

    def plane_tree(self, x, y, h=0.5, r=0.19, rot=0.0):
        """Platane boule."""
        self.frustum(x, y, 0, h * 0.45, 0.03, 0.022, 5, "gris_chaud", top=False)
        z0 = h * 0.36
        zs = [z0, z0 + r * 0.55, z0 + r * 1.2, z0 + r * 1.75]
        rs = [r * 0.5, r, r * 0.9, r * 0.38]
        for i in range(3):
            self.frustum(x, y, zs[i], zs[i + 1], rs[i], rs[i + 1], 7, "olive", rot, top=(i == 2), bottom=(i == 0))

    def palm(self, x, y, h=0.7, lean=0.07, rot=0.0):
        """Palmier : stipe légèrement courbe et couronne de palmes retombantes."""
        a = ring(x, y, 0, 0.04, 0.04, 5)
        m = ring(x + lean * 0.7, y, h * 0.55, 0.03, 0.03, 5)
        t = ring(x + lean, y, h, 0.026, 0.026, 5)
        self.band(a, m, "gris_chaud", "out", (x, y))
        self.band(m, t, "gris_chaud", "out", (x + lean * 0.7, y))
        c = Vector((x + lean, y, h))
        length, wd = 0.3, 0.055
        for k in range(7):
            th = rot + 2 * math.pi * k / 7
            d = Vector((math.cos(th), math.sin(th), 0))
            p = Vector((-d.y, d.x, 0))
            root = c + Z * 0.02
            spine = c + d * length * 0.5 + Z * 0.085
            lp = c + d * length * 0.5 + p * wd + Z * 0.03
            rp = c + d * length * 0.5 - p * wd + Z * 0.03
            tip = c + d * length - Z * 0.1
            self.solid([[root, lp, spine], [root, spine, rp], [spine, lp, tip],
                        [spine, tip, rp], [root, rp, lp], [rp, tip, lp]], "olive")

    def socle(self):
        """Îlot plat arrondi en pierre claire matérialisant l'emprise de la ville."""
        def outline(half, rad, z, seg=5):
            """Contour d'un carré à coins arrondis."""
            pts = []
            for q, (sx, sy) in enumerate(((1, 1), (-1, 1), (-1, -1), (1, -1))):
                for i in range(seg + 1):
                    t = math.pi / 2 * (q + i / seg)
                    pts.append(Vector((sx * (half - rad) + rad * math.cos(t),
                                       sy * (half - rad) + rad * math.sin(t), z)))
            return pts

        lo = outline(HALF, 0.5, 0.0)
        hi = outline(HALF - 0.025, 0.48, G)
        self.band(lo, hi, "pierre_claire", "out")
        self.face(hi, "pierre_claire", Z)
        self.z0 = G

    def to_object(self, name, mats):
        """Convertit le bmesh en objet Blender avec ses slots de matériaux."""
        mesh = bpy.data.meshes.new(name)
        self.bm.to_mesh(mesh)
        self.bm.free()
        for m in self.mats:
            mesh.materials.append(mats[m])
        obj = bpy.data.objects.new(name, mesh)
        bpy.context.scene.collection.objects.link(obj)
        return obj


def city_nimes(b):
    """Nîmes : les Arènes, amphithéâtre elliptique à deux niveaux d'arcades."""
    cx, cy, a, bb, n = 0.0, -0.18, 1.0, 0.74, 36
    c = (cx, cy)
    h1, hc, h2, h = 0.33, 0.365, 0.68, 0.74

    def E(da, z):
        """Anneau de l'ellipse des Arènes, décalé de `da`."""
        return ring(cx, cy, z, a + da, bb + da, n)

    b.band(E(0, 0), E(0, h2), "pierre_doree", "out", c)
    b.band(E(0.022, h1), E(0.022, hc), "pierre_claire", "out", c)
    b.band(E(0.022, hc), E(0, hc), "pierre_claire", "up")
    b.band(E(0.028, h2), E(0.028, h), "pierre_claire", "out", c)
    b.band(E(0.028, h), E(-0.085, h), "pierre_claire", "up")
    b.band(E(0, h2), E(0.028, h2), "pierre_doree", "up")
    base = E(0, 0)
    for i in range(n):
        p0, p1 = base[i], base[(i + 1) % n]
        r = (p1 - p0).normalized()
        o = (p0 + p1) / 2
        w = (p1 - p0).length * 0.58
        b.decal(o, r, arch_pts(0, 0.04, w, 0.245, 3), "encre")
        b.decal(o, r, arch_pts(0, hc + 0.035, w, 0.235, 3), "encre")

    steps, ain, bin_, zb = 5, 0.5, 0.3, 0.12
    for i in range(steps):
        t0, t1 = i / steps, (i + 1) / steps
        ra, rb = a - 0.085 + (ain - a + 0.085) * t0, bb - 0.085 + (bin_ - bb + 0.085) * t0
        ra1, rb1 = a - 0.085 + (ain - a + 0.085) * t1, bb - 0.085 + (bin_ - bb + 0.085) * t1
        z0, z1 = h + (zb - h) * t0, h + (zb - h) * t1
        b.band(ring(cx, cy, z1, ra, rb, n), ring(cx, cy, z0, ra, rb, n), "pierre_doree", "in", c)
        b.band(ring(cx, cy, z1, ra, rb, n), ring(cx, cy, z1, ra1, rb1, n), "pierre_claire", "up")
    b.band(ring(cx, cy, 0.03, ain, bin_, n), ring(cx, cy, zb, ain, bin_, n), "pierre_doree", "in", c)
    b.face(ring(cx, cy, 0.03, ain, bin_, n), "ocre", Z)

    q = math.pi / 2
    b.house(-1.08, 1.2, 0.44, 0.3, 0.26, "ocre")
    b.house(-0.55, 1.12, 0.34, 0.3, 0.36, "pierre_claire", q)
    b.house(-0.02, 1.22, 0.5, 0.3, 0.28, "ocre")
    b.house(0.55, 1.12, 0.36, 0.3, 0.38, "ocre", q)
    b.house(1.08, 1.2, 0.42, 0.3, 0.26, "pierre_claire")
    b.house(-1.33, 0.6, 0.36, 0.26, 0.24, "pierre_claire", q)
    b.house(1.33, 0.6, 0.36, 0.26, 0.24, "ocre", q)
    b.cypress(-1.36, -0.05, 0.6)
    b.cypress(-1.27, -1.2, 0.68)
    b.cypress(-1.08, -1.32, 0.5)
    b.pine(1.28, -1.05, 0.78, 0.27, 0.05, 0.3)
    b.plane_tree(1.37, 0.05, 0.46, 0.17)


def city_montpellier(b):
    """Montpellier : arc de triomphe du Peyrou et château d'eau hexagonal."""
    ax, ay = -0.42, -0.45
    b.extrude(arch_profile(1.2, 0.86, 0.5, 0.72), "pierre_doree", ax, ay, 0, 0, 0.42)
    for sx in (-1, 1):
        px = ax + sx * 0.435
        b.box(px, ay, 0, 0.38, 0.46, 0.07, "pierre_claire")
        b.box(px, ay, 0.44, 0.37, 0.45, 0.03, "pierre_claire")
        for sy in (-1, 1):
            b.box(px, ay + sy * 0.215, 0.52, 0.22, 0.02, 0.22, "pierre_claire")
            b.box(px, ay + sy * 0.215, 0.14, 0.22, 0.02, 0.24, "pierre_claire")
    b.box(ax, ay, 0.86, 1.3, 0.52, 0.05, "pierre_claire")
    b.box(ax, ay, 0.91, 1.16, 0.4, 0.2, "pierre_doree")
    b.box(ax, ay, 1.11, 1.24, 0.46, 0.04, "pierre_claire")
    o, r = frame(ax, ay, 0, 0, 0.2)
    b.decal(o, r, rect_pts(0, 0.95, 0.7, 0.11), "pierre_claire")

    tx, ty, th = 0.95, 0.72, 0.24
    b.box(tx, ty, 0, 1.06, 1.06, th, "pierre_claire")
    b.box(tx, ty, th, 1.1, 1.1, 0.03, "pierre_doree")
    th += 0.03
    b.box(tx, ty - 0.58, 0, 0.4, 0.12, th * 0.66, "pierre_doree")
    b.box(tx, ty - 0.68, 0, 0.4, 0.1, th * 0.33, "pierre_doree")
    b.frustum(tx, ty, th, th + 0.06, 0.4, 0.4, 6, "pierre_doree")
    b.frustum(tx, ty, th + 0.06, th + 0.46, 0.2, 0.2, 6, "pierre_doree", top=False)
    for i in range(6):
        t = -math.pi / 2 + math.pi / 6 + 2 * math.pi * i / 6
        b.frustum(tx + 0.33 * math.cos(t), ty + 0.33 * math.sin(t), th + 0.06, th + 0.46, 0.04, 0.035, 6,
                  "pierre_claire", top=False)
        o, r = frame(tx, ty, th + 0.06, 2 * math.pi * i / 6, 0.2 * math.cos(math.pi / 6))
        b.decal(o, r, arch_pts(0, 0.02, 0.11, 0.3, 3), "encre")
    b.frustum(tx, ty, th + 0.46, th + 0.54, 0.4, 0.4, 6, "pierre_doree")
    b.frustum(tx, ty, th + 0.54, th + 0.57, 0.44, 0.44, 6, "pierre_claire")
    b.frustum(tx, ty, th + 0.57, th + 0.72, 0.36, 0.16, 6, "pierre_claire")
    b.frustum(tx, ty, th + 0.72, th + 0.8, 0.08, 0.0, 6, "pierre_doree")
    b.frustum(ax, 0.22, 0, 0.035, 0.25, 0.25, 8, "pierre_doree")
    b.frustum(ax, 0.22, 0.035, 0.04, 0.2, 0.2, 8, "eau", mat_top="eau")

    q = math.pi / 2
    b.house(-1.25, 1.2, 0.42, 0.3, 0.3, "pierre_claire")
    b.house(-0.72, 1.22, 0.4, 0.3, 0.4, "ocre")
    b.house(-0.2, 1.2, 0.4, 0.3, 0.3, "pierre_claire")
    b.house(-1.32, 0.62, 0.38, 0.28, 0.36, "ocre", q)
    b.house(-0.82, 0.7, 0.36, 0.28, 0.26, "pierre_claire")
    b.house(-1.34, 0.05, 0.34, 0.26, 0.26, "pierre_claire", q)
    b.pine(1.2, -0.62, 0.85, 0.3, 0.06, 0.2)
    b.pine(-1.3, -1.1, 0.7, 0.25, -0.05, 0.9)
    b.cypress(0.5, -1.0, 0.5)
    b.cypress(0.3, 0.9, 0.55)
    b.plane_tree(-0.3, 0.72, 0.42, 0.16)


def city_beziers(b):
    """Béziers : cathédrale Saint-Nazaire sur sa butte, Pont Vieux et ruban de l'Orb."""
    hx, hy = 0.5, 0.55
    jit = [1.0, 0.93, 1.05, 0.97, 1.04, 0.92, 1.0, 1.06, 0.95]
    a0 = 0.3
    r0 = ring(hx, hy, 0, 1.02, 0.86, 9, a0, jit)
    r1 = ring(hx, hy, 0.3, 0.84, 0.66, 9, a0, jit)
    r2 = ring(hx, hy, 0.5, 0.68, 0.5, 9, a0, jit)
    b.band(r0, r1, "olive", "out", (hx, hy))
    b.band(r1, r2, "olive", "out", (hx, hy))
    b.face(r2, "pierre_claire", Z)

    zt = 0.5
    nx, ny = 0.38, 0.68
    b.box(nx, ny, zt, 0.4, 0.62, 0.46, "pierre_doree", top=False)
    b.gable_roof(nx, ny, zt + 0.46, 0.62, 0.4, 0.16, "terracotta", math.pi / 2, wall="pierre_doree")
    o, r = frame(nx, ny, zt, -math.pi / 2, 0.2)
    for k in range(3):
        b.decal(o, r, arch_pts(-0.18 + 0.18 * k, 0.14, 0.07, 0.24, 3), "encre")
    fy = 0.31
    b.box(nx, fy, zt, 0.5, 0.14, 0.72, "pierre_doree")
    b.box(nx, fy, zt + 0.66, 0.54, 0.18, 0.05, "pierre_claire", top=False)
    b.crenels(nx, fy, zt + 0.72, 0.5, 0.14, 4, 2, "pierre_doree", (0.07, 0.05, 0.06))
    for sx in (-1, 1):
        b.box(nx + sx * 0.27, fy, zt, 0.12, 0.16, 0.86, "pierre_doree")
        b.hip_roof(nx + sx * 0.27, fy, zt + 0.86, 0.12, 0.12, 0.1, "terracotta", o=0.015)
    o, r = frame(nx, fy, zt, 0, 0.07)
    b.decal(o, r, disc_pts(0, 0.44, 0.135, 10), "pierre_claire", 0.006)
    b.decal(o, r, disc_pts(0, 0.44, 0.1, 10), "encre", 0.012)
    b.decal(o, r, arch_pts(0, 0, 0.13, 0.2, 4), "encre")

    tx, ty, tw, thh = 0.82, 0.62, 0.3, 1.18
    b.box(tx, ty, zt, tw, tw, thh, "pierre_doree")
    b.box(tx, ty, zt + thh - 0.1, tw + 0.05, tw + 0.05, 0.05, "pierre_claire", top=False)
    b.crenels(tx, ty, zt + thh, tw, tw, 3, 3, "pierre_doree", (0.075, 0.05, 0.07))
    for k in range(4):
        o, r = frame(tx, ty, zt, k * math.pi / 2, tw / 2)
        for u in (-0.065, 0.065):
            b.decal(o, r, arch_pts(u, 0.78, 0.065, 0.22, 3), "encre")
        b.decal(o, r, rect_pts(0, 0.4, 0.035, 0.14), "encre")
    b.frustum(tx + 0.08, ty + 0.08, zt + thh, zt + thh + 0.16, 0.05, 0.05, 6, "pierre_doree")
    b.frustum(tx + 0.08, ty + 0.08, zt + thh + 0.16, zt + thh + 0.26, 0.065, 0, 6, "terracotta")

    left = [(-1.57, 0.95), (-1.2, 0.5), (-0.95, -0.2), (-0.86, -0.85), (-0.9, -1.57)]
    right = [(-1.57, 0.3), (-0.95, 0.05), (-0.48, -0.4), (-0.36, -0.85), (-0.3, -1.57)]
    left, right = chaikin(left, 2), chaikin(right, 2)
    for i in range(len(left) - 1):
        b.face([(*left[i], 0.012), (*right[i], 0.012), (*right[i + 1], 0.012), (*left[i + 1], 0.012)], "eau", Z)

    by, bh = -0.85, 0.25
    b.extrude(bridge_profile(6, 0.25, 0.07, bh, 0.06), "pierre_doree", -0.45, by, 0, 0, 0.2)
    for sy in (-1, 1):
        b.box(-0.45, by + sy * 0.09, bh, 1.99, 0.02, 0.05, "pierre_claire")

    q = math.pi / 2
    b.house(0.25, -0.5, 0.36, 0.26, 0.26, "ocre")
    b.house(0.72, -0.48, 0.34, 0.26, 0.34, "pierre_claire", q)
    b.house(1.2, -0.42, 0.38, 0.28, 0.26, "ocre")
    b.house(1.25, -1.0, 0.36, 0.26, 0.24, "pierre_claire")
    b.house(-1.2, 1.25, 0.36, 0.26, 0.26, "ocre")
    b.house(-0.75, 1.15, 0.34, 0.26, 0.3, "pierre_claire", q)
    b.house(-1.34, -0.2, 0.32, 0.26, 0.24, "ocre", q)
    b.cypress(-0.28, 0.28, 0.5)
    b.cypress(1.32, 0.72, 0.5)
    b.cypress(-0.02, 0.92, 0.55)
    b.plane_tree(0.75, -1.15, 0.42, 0.16)
    b.pine(-1.28, -1.25, 0.6, 0.22, 0.04)


def city_perpignan(b):
    """Perpignan : le Castillet, porte fortifiée en brique rouge et son lanterneau à dôme."""
    br = "brique_rouge"
    mx, my, mw, md, mh = -0.2, 0.0, 0.84, 0.62, 1.0
    b.box(mx, my, 0, mw, md, mh, br)
    b.box(mx, my, mh - 0.1, mw + 0.08, md + 0.08, 0.1, br)
    b.crenels(mx, my, mh, mw + 0.08, md + 0.08, 6, 4, br)
    o, r = frame(mx, my, 0, 0, md / 2 + 0.04)
    for k in range(5):
        b.decal(o, r, rect_pts(-0.2 + 0.1 * k, mh - 0.085, 0.045, 0.05), "encre")
    o, r = frame(mx, my, 0, 0, md / 2)
    for u in (-0.12, 0.12):
        b.decal(o, r, arch_pts(u, 0.5, 0.07, 0.17, 3), "encre")
        b.decal(o, r, rect_pts(u, 0.2, 0.035, 0.13), "encre")
    b.decal(o, r, rect_pts(0, 0.05, 0.58, 0.035), "pierre_claire")

    for tx, ty, tr, thh in ((mx - mw / 2, my - md / 2, 0.21, 1.06), (mx + mw / 2, my - md / 2, 0.21, 1.06),
                            (mx - mw / 2, my + md / 2, 0.17, 1.0), (mx + mw / 2, my + md / 2, 0.17, 1.0)):
        b.frustum(tx, ty, 0, 0.1, tr + 0.03, tr, 10, br, top=False)
        b.frustum(tx, ty, 0.1, thh - 0.14, tr, tr, 10, br, top=False)
        b.frustum(tx, ty, thh - 0.14, thh - 0.1, tr, tr + 0.04, 10, br, top=False)
        b.frustum(tx, ty, thh - 0.1, thh, tr + 0.04, tr + 0.04, 10, br)
        b.crenels_round(tx, ty, thh, tr + 0.012, 6, br, (0.075, 0.05, 0.07), math.pi / 6)
        for k in (-1, 0, 1):
            o, r = frame(tx, ty, 0, k * 0.63, tr * math.cos(math.pi / 10))
            b.decal(o, r, rect_pts(0, 0.55 - 0.2 * abs(k), 0.03, 0.13), "encre")

    gx, gy, gw, gd, gh = 0.63, 0.02, 0.62, 0.5, 0.7
    b.extrude(arch_profile(gw, gh, 0.27, 0.44), br, gx, gy, 0, 0, gd)
    b.box(gx, gy, gh - 0.08, gw + 0.06, gd + 0.06, 0.08, br)
    b.crenels(gx, gy, gh, gw + 0.06, gd + 0.06, 4, 3, br)
    o, r = frame(gx, gy, 0, 0, gd / 2 + 0.03)
    for k in range(4):
        b.decal(o, r, rect_pts(-0.15 + 0.1 * k, gh - 0.068, 0.045, 0.045), "encre")
    o, r = frame(gx, gy, 0, 0, gd / 2)
    b.decal(o, r, rect_pts(0, 0.5, 0.06, 0.07), "pierre_claire")

    lx, ly, z = mx, my + 0.04, mh
    b.frustum(lx, ly, z, z + 0.32, 0.17, 0.16, 8, br, top=False)
    b.frustum(lx, ly, z + 0.32, z + 0.38, 0.2, 0.2, 8, br, bottom=True)
    b.crenels_round(lx, ly, z + 0.38, 0.165, 8, br, (0.06, 0.04, 0.05), math.pi / 8)
    b.frustum(lx, ly, z + 0.38, z + 0.56, 0.105, 0.105, 8, "pierre_claire", top=False)
    for k in range(8):
        o, r = frame(lx, ly, z + 0.38, k * math.pi / 4, 0.105 * math.cos(math.pi / 8))
        b.decal(o, r, arch_pts(0, 0.03, 0.045, 0.12, 3), "encre", 0.005)
    b.frustum(lx, ly, z + 0.56, z + 0.59, 0.125, 0.125, 8, br, bottom=True)
    b.frustum(lx, ly, z + 0.59, z + 0.66, 0.115, 0.09, 8, "brique_rose", top=False)
    b.frustum(lx, ly, z + 0.66, z + 0.72, 0.09, 0.045, 8, "brique_rose", top=False)
    b.frustum(lx, ly, z + 0.72, z + 0.76, 0.045, 0, 8, "brique_rose")
    zp = z + 0.74
    b.box(lx, ly, zp, 0.014, 0.014, 0.36, "gris_chaud")
    b.box(lx + 0.115, ly, zp + 0.2, 0.22, 0.012, 0.14, "jaune", bottom=True)
    for k in range(3):
        b.box(lx + 0.115, ly, zp + 0.222 + 0.037 * k, 0.222, 0.018, 0.02, br, bottom=True)

    q = math.pi / 2
    b.house(-1.22, 1.2, 0.42, 0.3, 0.28, "ocre")
    b.house(-0.68, 1.22, 0.38, 0.3, 0.38, "pierre_claire", q)
    b.house(-0.15, 1.2, 0.44, 0.3, 0.28, "ocre")
    b.house(0.42, 1.18, 0.36, 0.3, 0.36, "brique_rose", q)
    b.house(1.0, 1.2, 0.46, 0.3, 0.28, "ocre")
    b.house(-1.33, 0.55, 0.36, 0.26, 0.26, "pierre_claire", q)
    b.house(1.35, 0.55, 0.34, 0.26, 0.3, "ocre", q)
    b.palm(-1.2, -0.85, 0.72, 0.07, 0.3)
    b.palm(1.25, -1.0, 0.6, -0.06, 1.0)
    b.palm(-0.95, -1.25, 0.5, 0.04, 2.0)
    b.cypress(1.38, -0.2, 0.5)


def city_toulouse(b):
    """Toulouse : façade du Capitole sur sa place, clocher octogonal de Saint-Sernin en arrière-plan."""
    rose, cr = "brique_rose", "creme"
    cy, cw, cd, ch = 0.12, 2.36, 0.46, 0.56
    fy = cy - cd / 2
    b.box(0, -0.72, 0, 2.5, 1.1, 0.012, "ocre")
    b.box(0, cy, 0, cw, cd, ch, rose, top=False)
    b.box(0, cy, ch, cw + 0.06, cd + 0.06, 0.04, cr)
    b.box(0, cy, ch + 0.04, cw - 0.02, cd - 0.02, 0.05, cr)
    b.hip_roof(0, cy, ch + 0.09, cw - 0.16, cd - 0.14, 0.1, "terracotta", o=0.0)
    b.box(0, fy - 0.01, 0.2, cw + 0.02, 0.02, 0.025, cr)
    b.box(0, fy - 0.01, 0, cw + 0.02, 0.02, 0.03, cr)

    aw = 0.8
    b.box(0, fy - 0.05, 0, aw, 0.1, ch + 0.04, rose)
    b.box(0, fy - 0.06, ch, aw + 0.05, 0.14, 0.04, cr)
    b.box(0, fy - 0.06, 0.19, aw + 0.03, 0.14, 0.03, cr)
    pf = [(-aw / 2 - 0.03, 0), (aw / 2 + 0.03, 0), (0, 0.17)]
    b.extrude(pf, cr, 0, fy - 0.045, ch + 0.04, 0, 0.13)
    o, r = frame(0, fy - 0.045, ch + 0.04, 0, 0.065)
    b.decal(o, r, [(-aw / 2 + 0.09, 0.025), (aw / 2 - 0.09, 0.025), (0, 0.125)], rose)
    for k in range(8):
        u = -0.35 + 0.1 * k
        b.frustum(u, fy - 0.115, 0.22, ch, 0.02, 0.018, 6, cr, top=False)
    o, r = frame(0, fy - 0.05, 0, 0, 0.05)
    for k in range(7):
        u = -0.3 + 0.1 * k
        b.decal(o, r, arch_pts(u, 0.26, 0.05, 0.2, 3), "encre")
        b.decal(o, r, arch_pts(u, 0.035, 0.06, 0.13, 3), "encre")

    pw = 0.36
    for sx in (-1, 1):
        px = sx * (cw / 2 - pw / 2)
        b.box(px, fy - 0.04, 0, pw, 0.08, ch + 0.04, rose)
        b.box(px, fy - 0.05, ch, pw + 0.04, 0.12, 0.04, cr)
        b.extrude([(-pw / 2 - 0.02, 0), (pw / 2 + 0.02, 0), (0, 0.09)], cr, px, fy - 0.045, ch + 0.04, 0, 0.11)
        o, r = frame(px, fy - 0.04, 0, 0, 0.04)
        for u in (-0.09, 0.09):
            b.decal(o, r, arch_pts(u, 0.26, 0.055, 0.2, 3), "encre")
            b.decal(o, r, arch_pts(u, 0.035, 0.065, 0.13, 3), "encre")
        for u in (-0.165, 0, 0.165):
            b.box(px + u, fy - 0.09, 0.22, 0.026, 0.02, ch - 0.22, cr, top=False)
        x0, x1 = aw / 2, cw / 2 - pw
        o, r = frame(0, fy, 0, 0, 0)
        nb = 3
        step = (x1 - x0) / nb
        for k in range(nb):
            u = sx * (x0 + step * (k + 0.5))
            b.decal(o, r, rect_pts(u, 0.27, 0.055, 0.17), "encre")
            b.decal(o, r, arch_pts(u, 0.035, 0.065, 0.13, 3), "encre")
        for k in range(1, nb):
            b.box(sx * (x0 + step * k), fy - 0.01, 0.22, 0.026, 0.02, ch - 0.22, cr, top=False)

    sx_, sy_ = 0.62, 1.05
    b.box(sx_ - 0.42, sy_, 0, 1.2, 0.36, 0.4, rose, top=False)
    b.gable_roof(sx_ - 0.42, sy_, 0.4, 1.2, 0.36, 0.15, "terracotta", wall=rose)
    b.box(sx_, sy_, 0, 0.34, 0.74, 0.4, rose, top=False)
    b.gable_roof(sx_, sy_, 0.4, 0.74, 0.34, 0.15, "terracotta", math.pi / 2, wall=rose)
    b.frustum(sx_ + 0.3, sy_, 0, 0.34, 0.2, 0.2, 8, rose, top=False)
    b.frustum(sx_ + 0.3, sy_, 0.34, 0.46, 0.215, 0.05, 8, "terracotta", top=False)
    o, r = frame(sx_ - 0.42, sy_, 0, 0, 0.18)
    for k in range(5):
        b.decal(o, r, arch_pts(-0.48 + 0.17 * k, 0.14, 0.06, 0.18, 3), "encre")
    b.frustum(sx_, sy_, 0.4, 0.62, 0.25, 0.25, 8, rose, top=False)
    z = 0.62
    for i, tr in enumerate((0.23, 0.205, 0.18, 0.155, 0.13)):
        th = 0.2
        b.frustum(sx_, sy_, z, z + th, tr, tr, 8, rose, top=False)
        b.frustum(sx_, sy_, z + th - 0.025, z + th, tr + 0.02, tr + 0.02, 8, cr, bottom=True)
        fw = 2 * tr * math.sin(math.pi / 8)
        for k in range(8):
            o, r = frame(sx_, sy_, z, k * math.pi / 4, tr * math.cos(math.pi / 8))
            for u in (-fw * 0.22, fw * 0.22):
                b.decal(o, r, arch_pts(u, 0.035, fw * 0.3, 0.12, 2) if i < 3
                        else [(u - fw * 0.15, 0.035), (u + fw * 0.15, 0.035), (u, 0.15)], "encre", 0.005)
        z += th
    b.frustum(sx_, sy_, z, z + 0.05, 0.125, 0.11, 8, cr, top=False)
    b.frustum(sx_, sy_, z + 0.05, z + 0.52, 0.1, 0, 8, cr)

    q = math.pi / 2
    b.house(-1.25, 1.22, 0.4, 0.3, 0.28, rose)
    b.house(-0.75, 1.2, 0.36, 0.3, 0.38, "ocre", q)
    b.house(-1.3, 0.72, 0.38, 0.28, 0.3, rose, q)
    b.house(-0.78, 0.68, 0.34, 0.26, 0.26, rose)
    b.house(1.32, 0.62, 0.34, 0.26, 0.3, rose, q)
    b.house(1.3, 1.2, 0.36, 0.28, 0.26, "ocre")
    b.house(-1.38, -0.35, 0.3, 0.24, 0.26, rose, q)
    b.house(1.38, -0.35, 0.3, 0.24, 0.26, "ocre", q)
    for sx in (-1, 1):
        b.plane_tree(sx * 1.3, -0.82, 0.44, 0.16, 0.4 * sx)
        b.plane_tree(sx * 1.28, -1.22, 0.4, 0.15, 0.9 * sx)
    b.cypress(1.28, 0.2, 0.42, 0.07)


CITIES = [
    ("city_nimes", city_nimes),
    ("city_montpellier", city_montpellier),
    ("city_beziers", city_beziers),
    ("city_perpignan", city_perpignan),
    ("city_toulouse", city_toulouse),
]


def build_scene():
    """Repart d'une scène vide et construit les 5 villes, espacées le long de X."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    mats = make_materials()
    roots = []
    for i, (name, fn) in enumerate(CITIES):
        b = Builder()
        b.socle()
        fn(b)
        obj = b.to_object(name + "_mesh", mats)
        root = bpy.data.objects.new(name, None)
        root.empty_display_size = 0.5
        bpy.context.scene.collection.objects.link(root)
        obj.parent = root
        root.location = (i * SPACING, 0, 0)
        obj.data.calc_loop_triangles()
        used = [m.name for m in obj.data.materials]
        print(f"[cities] {name}: {len(obj.data.loop_triangles)} triangles, {len(used)} matériaux {used}")
        roots.append(root)
    return roots


def export_glb(roots):
    """Exporte les 5 racines ramenées en (0,0,0), puis restaure leur espacement de travail."""
    saved = [r.location.copy() for r in roots]
    for o in bpy.context.scene.objects:
        o.select_set(False)
    for r in roots:
        r.location = (0, 0, 0)
        r.select_set(True)
        for ch in r.children:
            ch.select_set(True)
    bpy.context.view_layer.update()
    os.makedirs(os.path.dirname(GLB_PATH), exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=GLB_PATH, export_format="GLB", use_selection=True, export_yup=True,
        export_apply=False, export_animations=False, export_cameras=False, export_lights=False,
        export_normals=True, export_texcoords=False, export_materials="EXPORT", export_extras=False,
    )
    for r, loc in zip(roots, saved):
        r.location = loc
    bpy.context.view_layer.update()
    print(f"[cities] GLB : {GLB_PATH} ({os.path.getsize(GLB_PATH)} octets)")


def setup_render():
    """Prépare caméra, soleil, ambiance crème et moteur de rendu pour les aperçus."""
    scene = bpy.context.scene
    world = bpy.data.worlds.new("preview_world")
    if world.node_tree is None:
        world.use_nodes = True
    nt = world.node_tree
    bg = next(n for n in nt.nodes if n.type == "BACKGROUND")
    out = next(n for n in nt.nodes if n.type == "OUTPUT_WORLD")
    cream = srgb_to_linear(PALETTE["creme"]) + (1.0,)
    bg.inputs["Color"].default_value = cream
    bg.inputs["Strength"].default_value = 0.55
    backdrop = nt.nodes.new("ShaderNodeBackground")
    backdrop.inputs["Color"].default_value = cream
    path = nt.nodes.new("ShaderNodeLightPath")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(path.outputs["Is Camera Ray"], mix.inputs[0])
    nt.links.new(bg.outputs[0], mix.inputs[1])
    nt.links.new(backdrop.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    scene.world = world
    sun_data = bpy.data.lights.new("preview_sun", "SUN")
    sun_data.energy = 1.9
    sun_data.angle = math.radians(3)
    sun = bpy.data.objects.new("preview_sun", sun_data)
    sun.rotation_euler = (math.radians(52), 0, math.radians(-38))
    scene.collection.objects.link(sun)
    cam = bpy.data.objects.new("preview_cam", bpy.data.cameras.new("preview_cam"))
    scene.collection.objects.link(cam)
    scene.camera = cam
    scene.render.resolution_x = 900
    scene.render.resolution_y = 900
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "Standard"
    return cam


def render_still(path):
    """Rend l'image courante, EEVEE d'abord puis Cycles CPU en repli."""
    scene = bpy.context.scene
    scene.render.filepath = path
    for engine in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT", "CYCLES"):
        try:
            scene.render.engine = engine
            if engine == "CYCLES":
                scene.cycles.device = "CPU"
                scene.cycles.samples = 24
            bpy.ops.render.render(write_still=True)
            if os.path.exists(path):
                return engine
        except Exception as exc:
            print(f"[cities] moteur {engine} indisponible : {exc}")
    raise RuntimeError("aucun moteur de rendu disponible")


def render_previews(roots, only=None):
    """Rend pour chaque ville une vue 3/4 en plongée depuis -Y et une vue de dessus."""
    os.makedirs(PREVIEW_DIR, exist_ok=True)
    cam = setup_render()
    for root in roots:
        short = root.name.replace("city_", "")
        if only and short not in only:
            continue
        for other in roots:
            for ch in other.children:
                ch.hide_render = other is not root
        target = root.location + Vector((0, 0, 0.45))
        az, el, dist = math.radians(AZIMUTH), math.radians(35), 10.0
        cam.data.type = "PERSP"
        cam.data.lens = 85
        cam.location = target + dist * Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)))
        cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
        engine = render_still(os.path.join(PREVIEW_DIR, f"{short}_{SUFFIX}.png"))
        cam.data.type = "ORTHO"
        cam.data.ortho_scale = 3.5
        cam.location = root.location + Vector((0, 0, 10))
        cam.rotation_euler = (0, 0, 0)
        render_still(os.path.join(PREVIEW_DIR, f"{short}_top.png"))
        print(f"[cities] aperçus {short} rendus ({engine})")
    for root in roots:
        for ch in root.children:
            ch.hide_render = False


def main():
    """Point d'entrée : construction, export GLB, aperçus, sauvegarde du .blend."""
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    only = argv[argv.index("--only") + 1].split(",") if "--only" in argv else None
    roots = build_scene()
    export_glb(roots)
    if "--no-render" not in argv:
        render_previews(roots, only)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)


main()
