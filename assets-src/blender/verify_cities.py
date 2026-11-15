"""Réimporte cities.glb dans une scène vide et contrôle le contrat d'export.

Usage : blender --background --python verify_cities.py
"""

import json
import os
import struct

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
GLB_PATH = os.path.join(os.path.dirname(os.path.dirname(HERE)), "public", "models", "cities.glb")
EXPECTED = ["city_nimes", "city_montpellier", "city_beziers", "city_perpignan", "city_toulouse"]


def read_gltf_json(path):
    """Extrait le bloc JSON d'un fichier GLB."""
    with open(path, "rb") as fh:
        fh.read(12)
        length, _ = struct.unpack("<I4s", fh.read(8))
        return json.loads(fh.read(length))


def check_json(gltf):
    """Contrôle la structure brute du glTF : racines, enfants, TRS, absence d'animation/caméra/lampe."""
    nodes = gltf["nodes"]
    roots = [nodes[i] for i in gltf["scenes"][0]["nodes"]]
    print("racines :", [n["name"] for n in roots])
    assert sorted(n["name"] for n in roots) == sorted(EXPECTED)
    for n in roots:
        assert not any(k in n for k in ("translation", "rotation", "scale", "matrix", "mesh")), n
        kids = [nodes[i] for i in n["children"]]
        assert len(kids) == 1 and "mesh" in kids[0], kids
        assert not any(k in kids[0] for k in ("translation", "rotation", "scale", "matrix")), kids[0]
        mesh = gltf["meshes"][kids[0]["mesh"]]
        tris = 0
        for prim in mesh["primitives"]:
            assert "NORMAL" in prim["attributes"]
            tris += gltf["accessors"][prim["indices"]]["count"] // 3
        lo = [min(gltf["accessors"][p["attributes"]["POSITION"]]["min"][k] for p in mesh["primitives"]) for k in range(3)]
        hi = [max(gltf["accessors"][p["attributes"]["POSITION"]]["max"][k] for p in mesh["primitives"]) for k in range(3)]
        print(f"{n['name']} > {kids[0]['name']} : {tris} triangles, {len(mesh['primitives'])} primitives, "
              f"bbox glTF min={[round(v, 3) for v in lo]} max={[round(v, 3) for v in hi]}")
        assert tris <= 4500
    for key in ("animations", "cameras", "images", "textures", "skins"):
        assert key not in gltf, key
    assert "KHR_lights_punctual" not in gltf.get("extensionsUsed", [])
    print("matériaux :", [(m["name"], m.get("doubleSided", False)) for m in gltf["materials"]])


def check_import():
    """Réimporte le GLB dans Blender et contrôle noms, positions et total de triangles."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=GLB_PATH)
    total = 0
    for name in EXPECTED:
        root = bpy.data.objects[name]
        assert root.type == "EMPTY" and root.parent is None
        assert root.location.length < 1e-6 and all(abs(s - 1) < 1e-6 for s in root.scale)
        child = root.children[0]
        child.data.calc_loop_triangles()
        total += len(child.data.loop_triangles)
    print("types d'objets :", sorted({o.type for o in bpy.data.objects}), "- total triangles :", total)
    assert total <= 20000


check_json(read_gltf_json(GLB_PATH))
check_import()
print("taille :", os.path.getsize(GLB_PATH), "octets")
print("VERIFICATION OK")
