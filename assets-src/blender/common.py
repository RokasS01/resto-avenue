"""Palette, matériaux, primitives low-poly, export GLB et aperçus partagés par les scripts d'assets."""

import math
import os
from contextlib import contextmanager

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector

SRC_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(os.path.dirname(SRC_DIR))
MODELS_DIR = os.path.join(PROJECT_DIR, "public", "models")
PREVIEW_DIR = os.path.join(SRC_DIR, "previews")

EPS = 1e-6

MATERIALS = {
    "red": {"color": "#ae3037"},
    "red_dark": {"color": "#8a2229"},
    "cream": {"color": "#f6efe4"},
    "ink": {"color": "#1d1a1a"},
    "grey": {"color": "#8b8178"},
    "stone": {"color": "#cfc6ba"},
    "terracotta": {"color": "#d98a5f"},
    "ochre": {"color": "#ecd3a8"},
    "olive": {"color": "#7c8f5a"},
    "green_dark": {"color": "#4f6b4a"},
    "blue": {"color": "#6f9aa8"},
    "glass": {"color": "#bfe0e6", "roughness": 0.35},
    "wood": {"color": "#a9744f"},
    "light": {"color": "#f2b84b", "emission": "#f2b84b"},
    "flash": {"color": "#f4f0e6"},
}

AXIS = {
    "Z": Matrix.Identity(4),
    "-Z": Matrix.Rotation(math.pi, 4, "X"),
    "Y": Matrix.Rotation(-math.pi / 2, 4, "X"),
    "-Y": Matrix.Rotation(math.pi / 2, 4, "X"),
    "X": Matrix.Rotation(math.pi / 2, 4, "Y"),
    "-X": Matrix.Rotation(-math.pi / 2, 4, "Y"),
}


def hex_to_linear(value):
    """Convertit une couleur hexadécimale sRGB en triplet RGBA linéaire."""
    value = value.lstrip("#")
    channels = [int(value[i : i + 2], 16) / 255.0 for i in (0, 2, 4)]
    linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return (*linear, 1.0)


def reset_scene():
    """Repart d'un fichier Blender vide pour rendre le script relançable."""
    bpy.ops.wm.read_factory_settings(use_empty=True)


def get_mat(name):
    """Retourne le matériau Principled `mat_<name>`, créé à la demande depuis la palette."""
    full_name = "mat_" + name
    mat = bpy.data.materials.get(full_name)
    if mat:
        return mat
    spec = MATERIALS[name]
    mat = bpy.data.materials.new(full_name)
    if mat.node_tree is None:
        mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled")
    color = hex_to_linear(spec["color"])
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = spec.get("roughness", 0.8)
    bsdf.inputs["Metallic"].default_value = 0.0
    if spec.get("emission"):
        bsdf.inputs["Emission Color"].default_value = hex_to_linear(spec["emission"])
        bsdf.inputs["Emission Strength"].default_value = 1.0
    mat.diffuse_color = color
    return mat


def xf(loc=(0, 0, 0), rot=(0, 0, 0)):
    """Construit une matrice translation + rotation (Euler XYZ en degrés)."""
    euler = Euler([math.radians(a) for a in rot], "XYZ")
    return Matrix.Translation(Vector(loc)) @ euler.to_matrix().to_4x4()


class Builder:
    """Accumule des primitives low-poly dans un seul maillage multi-matériaux."""

    def __init__(self, name):
        """Initialise un maillage vide nommé `name`."""
        self.name = name
        self.bm = bmesh.new()
        self.slots = []
        self.base = Matrix.Identity(4)

    @contextmanager
    def at(self, loc=(0, 0, 0), rot=(0, 0, 0), matrix=None):
        """Empile un repère local (imbriquable) appliqué aux primitives créées dans le bloc."""
        previous = self.base
        self.base = previous @ (matrix if matrix is not None else xf(loc, rot))
        try:
            yield self
        finally:
            self.base = previous

    def slot(self, mat_name):
        """Retourne l'index de slot du matériau, en l'ajoutant au besoin."""
        if mat_name not in self.slots:
            self.slots.append(mat_name)
        return self.slots.index(mat_name)

    def add(self, verts, faces, mat=None, smooth=False, matrix=None, fix_normals=True, face_mats=None):
        """Ajoute une géométrie brute (sommets + faces indexées) et retourne les faces créées."""
        full = self.base @ matrix if matrix is not None else self.base
        bverts = [self.bm.verts.new(full @ Vector(v)) for v in verts]
        created = []
        for index, face in enumerate(faces):
            bface = self.bm.faces.new([bverts[i] for i in face])
            bface.material_index = self.slot(face_mats[index] if face_mats else mat)
            bface.smooth = smooth
            created.append(bface)
        if fix_normals:
            bmesh.ops.recalc_face_normals(self.bm, faces=created)
        return created

    def poly(self, points, mat, facing=None):
        """Ajoute une face plane ; `facing` impose le côté vers lequel pointe la normale."""
        pts = [Vector(p) for p in points]
        if facing is not None:
            normal = Vector((0, 0, 0))
            for i in range(len(pts)):
                normal += pts[i].cross(pts[(i + 1) % len(pts)])
            if normal.dot(Vector(facing)) < 0:
                pts.reverse()
        return self.add(pts, [tuple(range(len(pts)))], mat, fix_normals=False)

    def box(self, size, loc, mat, rot=(0, 0, 0), bevel=0.0):
        """Ajoute un pavé centré sur `loc`, chanfreiné si `bevel` > 0."""
        sx, sy, sz = (s / 2 for s in size)
        verts = [
            (-sx, -sy, -sz), (sx, -sy, -sz), (sx, sy, -sz), (-sx, sy, -sz),
            (-sx, -sy, sz), (sx, -sy, sz), (sx, sy, sz), (-sx, sy, sz),
        ]
        faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        created = self.add(verts, faces, mat, matrix=xf(loc, rot), fix_normals=False)
        if bevel > 0:
            edges = list({e for f in created for e in f.edges})
            bmesh.ops.bevel(
                self.bm, geom=edges, offset=bevel, offset_type="OFFSET",
                segments=1, profile=0.5, affect="EDGES",
            )
        return created

    def bb(self, x0, x1, y0, y1, z0, z1, mat, bevel=0.0):
        """Ajoute un pavé défini par ses bornes sur chaque axe."""
        size = (abs(x1 - x0), abs(y1 - y0), abs(z1 - z0))
        loc = ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)
        return self.box(size, loc, mat, bevel=bevel)

    def lathe(self, profile, loc, mat, axis="Z", segs=12, smooth=True, mats=None, matrix=None, phase=0.0):
        """Révolutionne un profil [(rayon, hauteur)...] ; matière à gauche du profil parcouru.

        Chaque bande a ses propres sommets : lissage autour de l'axe, arêtes vives le long du profil.
        """
        full = matrix if matrix is not None else xf(loc) @ AXIS[axis]
        angles = [phase + 2 * math.pi * k / segs for k in range(segs)]
        for i in range(len(profile) - 1):
            (r0, h0), (r1, h1) = profile[i], profile[i + 1]
            if r0 < EPS and r1 < EPS:
                continue
            band_mat = mats[i] if mats else mat
            band_smooth = smooth[i] if isinstance(smooth, (list, tuple)) else smooth
            ring0 = [(r0 * math.cos(a), r0 * math.sin(a), h0) for a in angles]
            ring1 = [(r1 * math.cos(a), r1 * math.sin(a), h1) for a in angles]
            if r0 < EPS:
                verts = [(0, 0, h0)] + ring1
                faces = [(0, 1 + (k + 1) % segs, 1 + k) for k in range(segs)]
            elif r1 < EPS:
                verts = ring0 + [(0, 0, h1)]
                faces = [(k, (k + 1) % segs, segs) for k in range(segs)]
            else:
                verts = ring0 + ring1
                faces = [(k, (k + 1) % segs, segs + (k + 1) % segs, segs + k) for k in range(segs)]
            flat_cap = abs(h1 - h0) < EPS
            self.add(verts, faces, band_mat, smooth=band_smooth and not flat_cap, matrix=full, fix_normals=False)

    def cyl(self, radius, height, loc, mat, axis="Z", segs=12, smooth=True, r_top=None):
        """Ajoute un cylindre (ou tronc de cône) fermé dont la base est posée sur `loc`."""
        top = radius if r_top is None else r_top
        self.lathe([(0, 0), (radius, 0), (top, height), (0, height)], loc, mat, axis=axis, segs=segs, smooth=smooth)

    def tube(self, p1, p2, radius, mat, segs=6, caps=True, smooth=False, r_end=None):
        """Ajoute un cylindre fin tendu entre deux points."""
        p1, p2 = Vector(p1), Vector(p2)
        length = (p2 - p1).length
        end = radius if r_end is None else r_end
        matrix = Matrix.Translation(p1) @ (p2 - p1).to_track_quat("Z", "Y").to_matrix().to_4x4()
        profile = [(radius, 0), (end, length)]
        if caps:
            profile = [(0, 0)] + profile + [(0, length)]
        self.lathe(profile, None, mat, segs=segs, smooth=smooth, matrix=matrix)

    def prism(self, points, vector, mat):
        """Extrude un polygone 3D fermé le long de `vector` pour former un solide."""
        vector = Vector(vector)
        base = [Vector(p) for p in points]
        count = len(base)
        verts = base + [p + vector for p in base]
        faces = [tuple(range(count)), tuple(range(2 * count - 1, count - 1, -1))]
        faces += [(k, (k + 1) % count, count + (k + 1) % count, count + k) for k in range(count)]
        return self.add(verts, faces, mat)

    def sphere(self, radius, loc, mat, subdiv=1, scale=(1, 1, 1), rot=(0, 0, 0), smooth=False):
        """Ajoute une icosphère facettée, éventuellement écrasée par `scale`."""
        matrix = self.base @ xf(loc, rot) @ Matrix.Diagonal((*scale, 1.0))
        result = bmesh.ops.create_icosphere(self.bm, subdivisions=subdiv, radius=radius, matrix=matrix)
        index = self.slot(mat)
        for face in {f for v in result["verts"] for f in v.link_faces}:
            face.material_index = index
            face.smooth = smooth

    def weld(self):
        """Fusionne les sommets confondus (nécessaire avant un booléen)."""
        bmesh.ops.remove_doubles(self.bm, verts=self.bm.verts, dist=1e-5)

    def absorb(self, obj):
        """Intègre le maillage d'un objet existant puis supprime cet objet."""
        face_start = len(self.bm.faces)
        vert_start = len(self.bm.verts)
        remap = [self.slot(m.name[4:]) for m in obj.data.materials]
        self.bm.from_mesh(obj.data)
        self.bm.verts.ensure_lookup_table()
        self.bm.faces.ensure_lookup_table()
        for vert in self.bm.verts[vert_start:]:
            vert.co = obj.matrix_world @ vert.co
        for face in self.bm.faces[face_start:]:
            face.material_index = remap[face.material_index] if remap else 0
        bpy.data.objects.remove(obj)

    def to_object(self, origin=(0, 0, 0)):
        """Crée l'objet Blender, avec son origine placée sur `origin` (repère monde)."""
        origin = Vector(origin)
        bmesh.ops.translate(self.bm, verts=self.bm.verts, vec=-origin)
        self.bm.normal_update()
        mesh = bpy.data.meshes.new(self.name)
        self.bm.to_mesh(mesh)
        self.bm.free()
        for mat_name in self.slots:
            mesh.materials.append(get_mat(mat_name))
        obj = bpy.data.objects.new(self.name, mesh)
        obj.location = origin
        bpy.context.scene.collection.objects.link(obj)
        return obj


def boolean_cut(obj, cutter):
    """Soustrait `cutter` de `obj` ; les faces creusées gardent le matériau du cutter."""
    modifier = obj.modifiers.new("cut", "BOOLEAN")
    modifier.operation = "DIFFERENCE"
    modifier.solver = "EXACT"
    modifier.material_mode = "TRANSFER"
    modifier.object = cutter
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    cut_mesh = bpy.data.meshes.new_from_object(obj.evaluated_get(depsgraph))
    obj.modifiers.clear()
    old_mesh = obj.data
    obj.data = cut_mesh
    bpy.data.meshes.remove(old_mesh)
    bpy.data.objects.remove(cutter)
    return obj


def make_root(name, children):
    """Crée l'Empty racine à l'origine et y parente tous les objets de l'asset."""
    root = bpy.data.objects.new(name, None)
    root.empty_display_size = 0.5
    bpy.context.scene.collection.objects.link(root)
    for child in children:
        child.parent = root
    return root


def triangle_count(obj):
    """Compte les triangles d'un objet maillé après triangulation des n-gones."""
    return sum(len(p.vertices) - 2 for p in obj.data.polygons)


def export_glb(name):
    """Exporte toute la scène en GLB (+Y up, sans animation, caméra ni lampe)."""
    os.makedirs(MODELS_DIR, exist_ok=True)
    path = os.path.join(MODELS_DIR, name + ".glb")
    wanted = {
        "filepath": path,
        "export_format": "GLB",
        "use_selection": False,
        "export_apply": True,
        "export_yup": True,
        "export_normals": True,
        "export_texcoords": False,
        "export_tangents": False,
        "export_materials": "EXPORT",
        "export_vertex_color": "NONE",
        "export_animations": False,
        "export_cameras": False,
        "export_lights": False,
        "export_extras": False,
        "export_skins": False,
        "export_morph": False,
    }
    supported = bpy.ops.export_scene.gltf.get_rna_type().properties.keys()
    bpy.ops.export_scene.gltf(**{k: v for k, v in wanted.items() if k in supported})
    return path


def _pick_engine(scene):
    """Sélectionne Cycles CPU si disponible, sinon EEVEE."""
    forced = os.environ.get("RA_ENGINE")
    try:
        if forced and forced != "CYCLES":
            raise RuntimeError("moteur forcé")
        bpy.ops.preferences.addon_enable(module="cycles")
        scene.render.engine = "CYCLES"
        scene.cycles.device = "CPU"
        scene.cycles.samples = 48
        scene.cycles.use_denoising = False
    except Exception:
        scene.render.engine = forced or "BLENDER_EEVEE"


def _preview_rig(resolution):
    """Installe monde, soleil, caméra et moteur de rendu des aperçus ; retourne la caméra."""
    scene = bpy.context.scene
    world = bpy.data.worlds.new("preview_world")
    if world.node_tree is None:
        world.use_nodes = True
    background = next(n for n in world.node_tree.nodes if n.bl_idname == "ShaderNodeBackground")
    background.inputs["Color"].default_value = hex_to_linear("#f6efe4")
    background.inputs["Strength"].default_value = 0.9
    scene.world = world

    sun_data = bpy.data.lights.new("preview_sun", "SUN")
    sun_data.energy = 3.0
    sun_data.angle = math.radians(4)
    sun = bpy.data.objects.new("preview_sun", sun_data)
    sun.rotation_euler = Euler((math.radians(52), 0, math.radians(-38)), "XYZ")
    scene.collection.objects.link(sun)

    cam_data = bpy.data.cameras.new("preview_cam")
    cam_data.lens = 60
    cam_data.clip_end = 500
    cam = bpy.data.objects.new("preview_cam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam

    _pick_engine(scene)
    scene.render.resolution_x = resolution
    scene.render.resolution_y = resolution
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "Standard"
    os.makedirs(PREVIEW_DIR, exist_ok=True)
    return cam


def render_previews(name, views, resolution=900):
    """Rend des aperçus PNG : `views` associe un suffixe à la direction caméra (depuis le sujet)."""
    scene = bpy.context.scene
    corners = [
        obj.matrix_world @ Vector(corner)
        for obj in scene.objects if obj.type == "MESH"
        for corner in obj.bound_box
    ]
    low = Vector([min(c[i] for c in corners) for i in range(3)])
    high = Vector([max(c[i] for c in corners) for i in range(3)])
    center = (low + high) / 2
    radius = (high - low).length / 2

    cam = _preview_rig(resolution)
    distance = radius / math.sin(cam.data.angle / 2) * 0.82
    for suffix, direction in views.items():
        direction = Vector(direction).normalized()
        cam.location = center + direction * distance
        cam.rotation_euler = direction.to_track_quat("Z", "Y").to_euler()
        scene.render.filepath = os.path.join(PREVIEW_DIR, f"{name}_{suffix}.png")
        bpy.ops.render.render(write_still=True)


def render_shots(name, shots):
    """Rend des aperçus cadrés : suffixe -> (position, cible, FOV vertical en degrés, largeur, hauteur)."""
    scene = bpy.context.scene
    cam = _preview_rig(900)
    cam.data.sensor_fit = "VERTICAL"
    for suffix, (eye, target, fov, width, height) in shots.items():
        cam.data.angle = math.radians(fov)
        cam.location = Vector(eye)
        cam.rotation_euler = (Vector(eye) - Vector(target)).to_track_quat("Z", "Y").to_euler()
        scene.render.resolution_x = width
        scene.render.resolution_y = height
        scene.render.filepath = os.path.join(PREVIEW_DIR, f"{name}_{suffix}.png")
        bpy.ops.render.render(write_still=True)


def finish(name, objects, views, shots=None):
    """Parent à la racine, exporte le GLB, sauvegarde le .blend puis rend les aperçus.

    `shots` (cadrages explicites, cf. `render_shots`) remplace `views` quand il est fourni.
    """
    make_root(name, objects)
    bpy.context.view_layer.update()
    path = export_glb(name)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(SRC_DIR, name + ".blend"), check_existing=False)
    for obj in objects:
        print(f"[{name}] {obj.name}: {triangle_count(obj)} triangles, origine {tuple(round(c, 3) for c in obj.location)}")
    print(f"[{name}] total {sum(triangle_count(o) for o in objects)} triangles, {os.path.getsize(path) / 1024:.1f} Ko -> {path}")
    if os.environ.get("RA_NO_PREVIEW") == "1":
        return
    if shots:
        render_shots(name, shots)
    else:
        render_previews(name, views)
