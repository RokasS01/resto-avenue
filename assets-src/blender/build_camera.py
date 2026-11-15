"""Appareil photo hybride stylisé : `blender --background --python build_camera.py`."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402
from common import Builder  # noqa: E402

FRONT_Y = -0.16
BACK_Y = 0.16
TOP_Z = 0.36
LENS_ORIGIN = (0.04, FRONT_Y, -0.03)
SHUTTER_ORIGIN = (-0.36, -0.06, TOP_Z + 0.02)
FLASH_BOX = (-0.105, 0.105, -0.105, -0.09, 0.625, 0.735)


def build_body():
    """Construit le boîtier : coque, poignée, capot, viseur, griffe, molette et dos."""
    body = Builder("cam_body")
    body.bb(-0.5, 0.5, FRONT_Y, BACK_Y, -0.30, 0.30, "ink", bevel=0.04)
    body.bb(-0.5, 0.5, FRONT_Y, BACK_Y, 0.27, TOP_Z, "grey", bevel=0.025)
    body.bb(-0.215, 0.5, FRONT_Y - 0.012, FRONT_Y + 0.02, -0.25, 0.22, "grey", bevel=0.01)

    body.lathe(
        [(0, -0.30), (0.12, -0.30), (0.135, -0.27), (0.135, 0.20), (0.11, 0.25), (0, 0.25)],
        (-0.355, FRONT_Y - 0.005, 0), "ink", segs=10,
    )

    hump = [(-0.21, FRONT_Y - 0.01, TOP_Z - 0.02), (0.21, FRONT_Y - 0.01, TOP_Z - 0.02),
            (0.13, FRONT_Y + 0.02, 0.52), (-0.13, FRONT_Y + 0.02, 0.52)]
    body.prism(hump, (0, BACK_Y - FRONT_Y + 0.02, 0), "ink")
    body.bb(-0.10, 0.10, BACK_Y, BACK_Y + 0.05, 0.37, 0.49, "ink", bevel=0.015)
    body.poly([(-0.065, BACK_Y + 0.051, 0.395), (0.065, BACK_Y + 0.051, 0.395),
               (0.065, BACK_Y + 0.051, 0.465), (-0.065, BACK_Y + 0.051, 0.465)], "glass", facing=(0, 1, 0))

    body.bb(-0.075, 0.075, -0.07, 0.09, 0.52, 0.545, "grey")
    body.bb(-0.05, 0.05, -0.05, 0.07, 0.545, 0.61, "ink")
    body.bb(-0.135, 0.135, -0.09, 0.08, 0.60, 0.76, "ink", bevel=0.02)

    body.cyl(0.08, 0.02, (SHUTTER_ORIGIN[0], SHUTTER_ORIGIN[1], TOP_Z), "ink", segs=12)
    body.lathe([(0, 0), (0.105, 0), (0.105, 0.065), (0.09, 0.08), (0, 0.08)], (0.33, 0.0, TOP_Z), "ink", segs=12, smooth=False)
    body.bb(0.32, 0.34, -0.085, -0.035, TOP_Z + 0.08, TOP_Z + 0.087, "cream")
    body.cyl(0.05, 0.04, (-0.20, 0.07, TOP_Z), "ink", segs=10, smooth=False)

    body.cyl(0.032, 0.015, (0.40, FRONT_Y - 0.012, 0.13), "light", axis="-Y", segs=8)
    body.cyl(0.04, 0.02, (0.41, FRONT_Y - 0.012, -0.14), "ink", axis="-Y", segs=8)
    for side in (-1, 1):
        body.bb(side * 0.49, side * 0.535, -0.03, 0.03, 0.17, 0.24, "grey", bevel=0.008)

    body.bb(-0.34, 0.20, BACK_Y, BACK_Y + 0.015, -0.23, 0.17, "ink")
    body.poly([(-0.31, BACK_Y + 0.016, -0.20), (0.17, BACK_Y + 0.016, -0.20),
               (0.17, BACK_Y + 0.016, 0.14), (-0.31, BACK_Y + 0.016, 0.14)], "glass", facing=(0, 1, 0))
    for x, z, mat in ((0.33, 0.10, "grey"), (0.33, -0.02, "grey"), (0.40, -0.14, "red"), (0.27, -0.14, "grey")):
        body.cyl(0.035, 0.015, (x, BACK_Y, z), mat, axis="Y", segs=8)
    return body.to_object()


def build_lens():
    """Construit l'objectif (bague rouge, lentille bombée, reflet) ; origine à sa base, axe -Y."""
    lens = Builder("cam_lens")
    profile = [
        (0.30, 0.0), (0.30, 0.045), (0.27, 0.045), (0.27, 0.15), (0.288, 0.15), (0.288, 0.20),
        (0.27, 0.20), (0.27, 0.30), (0.295, 0.33), (0.295, 0.38), (0.255, 0.38), (0.225, 0.33),
        (0.12, 0.352), (0, 0.36),
    ]
    mats = ["grey", "grey", "ink", "ink", "red", "red", "ink", "ink", "ink", "ink", "ink", "glass", "glass"]
    smooth = [True] * 11 + [False, False]
    lens.lathe(profile, LENS_ORIGIN, "ink", axis="-Y", segs=24, mats=mats, smooth=smooth)
    lens.lathe([(0.062, 0.0), (0, 0.0)], (LENS_ORIGIN[0] - 0.085, LENS_ORIGIN[1] - 0.356, LENS_ORIGIN[2] + 0.085),
               "cream", axis="-Y", segs=8)
    lens.lathe([(0.028, 0.0), (0, 0.0)], (LENS_ORIGIN[0] + 0.02, LENS_ORIGIN[1] - 0.36, LENS_ORIGIN[2] + 0.005),
               "cream", axis="-Y", segs=6)
    return lens.to_object(origin=LENS_ORIGIN)


def build_flash():
    """Construit la face lumineuse du flash, seul porteur du matériau `mat_flash`."""
    flash = Builder("cam_flash")
    flash.bb(*FLASH_BOX, "flash")
    x0, x1, y0, y1, z0, z1 = FLASH_BOX
    return flash.to_object(origin=((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))


def build_shutter():
    """Construit le bouton déclencheur ; origine à sa base pour l'enfoncer en code."""
    shutter = Builder("cam_shutter")
    shutter.lathe([(0, 0), (0.058, 0), (0.058, 0.035), (0.045, 0.05), (0, 0.05)], SHUTTER_ORIGIN, "red", segs=12)
    return shutter.to_object(origin=SHUTTER_ORIGIN)


def main():
    """Assemble l'appareil photo, exporte `camera.glb` et rend les aperçus."""
    common.reset_scene()
    objects = [build_body(), build_lens(), build_flash(), build_shutter()]
    common.finish("camera", objects, {
        "front34": (-0.9, -1.25, 0.6),
        "front": (0.0, -1.0, 0.08),
        "back34": (-1.0, 1.2, 0.7),
    })


main()
