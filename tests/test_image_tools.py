#!/usr/bin/env python3
"""
Regression tests for the image builders.

Run with:  python3 tests/test_image_tools.py

Plain Python, no test framework: exits non-zero if anything fails. Each block
pins a bug that shipped once, so a failure here means a real regression.
"""

import contextlib
import io
import os
import random
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image, ImageDraw  # noqa: E402

import collage_maker_cli as C  # noqa: E402
import image_grid_cli as G  # noqa: E402

FAILURES = []


def check(name, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {name}{('  -- ' + detail) if detail else ''}")
    if not ok:
        FAILURES.append(name)


def make_fixtures(root):
    """A portrait photo with a red edge frame, plus wide solid-colour images."""
    face = Image.new("RGB", (900, 1200), "white")
    draw = ImageDraw.Draw(face)
    draw.rectangle([0, 0, 899, 1199], outline=(255, 0, 0), width=12)
    draw.ellipse([250, 300, 650, 800], fill=(80, 140, 220))
    face.save(root / "face.jpg", quality=95)

    rgba = Image.new("RGBA", (600, 600), (0, 0, 0, 0))
    ImageDraw.Draw(rgba).ellipse([50, 50, 550, 550], fill=(20, 200, 120, 255))
    rgba.save(root / "alpha.png")
    rgba.convert("P", palette=Image.ADAPTIVE).save(root / "palette.png")

    for i, colour in enumerate([(200, 50, 50), (50, 200, 50), (50, 50, 200)]):
        Image.new("RGB", (1600, 900), colour).save(root / f"wide{i}.jpg", quality=95)


def test_grid_geometry():
    """Six 2x2in photos fill 4x6in exactly, so edging must shrink the photo."""
    worst = None
    for dpi in (150, 300, 600):
        for edging in (0.0, 0.5, 1.0, 2.0, 5.0):
            geom = G.compute_grid_geometry(edging_mm=edging, dpi=dpi)
            if geom["clipped"]:
                worst = (dpi, edging, geom["clipped"][0])
    check("grid geometry never clips across 15 dpi/edging combos", worst is None, str(worst or ""))

    exact = G.compute_grid_geometry(edging_mm=0.0, dpi=300)
    check("edging 0 yields exactly 2in photos",
          abs(exact["photo_inches"] - 2.0) < 1e-9, f"{exact['photo_inches']:.4f}in")

    spaced = G.compute_grid_geometry(edging_mm=0.5, dpi=300)
    check("edging 0.5mm fits by shrinking and flags it",
          spaced["downsized"] and not spaced["clipped"], f"{spaced['photo_inches']:.4f}in")

    try:
        G.compute_grid_geometry(edging_mm=60, dpi=300)
        check("impossible edging raises", False, "no exception")
    except ValueError:
        check("impossible edging raises ValueError", True)


def test_grid_copies_intact(root):
    """Every copy must land fully inside the canvas, frame visible on all sides."""
    canvas, info = G.build_photo_grid(str(root / "face.jpg"), edging_mm=0.5, dpi=300)
    px = canvas.load()

    def is_red(p):
        return p[0] > 150 and p[1] < 100 and p[2] < 100

    intact = 0
    for left, top, right, bottom in info["boxes"]:
        edges = [
            any(is_red(px[x, top + 3]) for x in range(left + 3, right - 3)),
            any(is_red(px[x, bottom - 4]) for x in range(left + 3, right - 3)),
            any(is_red(px[left + 3, y]) for y in range(top + 3, bottom - 3)),
            any(is_red(px[right - 4, y]) for y in range(top + 3, bottom - 3)),
        ]
        if all(edges):
            intact += 1

    check("all 6 copies fully inside the canvas", intact == 6, f"{intact}/6")
    check("sheet is exactly 1200x1800 at 300 DPI", canvas.size == (1200, 1800), str(canvas.size))


def test_transparency_inputs(root):
    for name in ("alpha.png", "palette.png"):
        try:
            canvas, _ = G.build_photo_grid(str(root / name), edging_mm=0.5, dpi=150)
            ok = canvas.mode == "RGB"
            detail = ""
        except Exception as e:
            ok, detail = False, f"{type(e).__name__}: {e}"
        check(f"{name} flattens to RGB", ok, detail)


def test_random_collage_no_crash(root):
    """Wide images with resize=False used to hit an empty randrange."""
    images = [Image.open(root / f"wide{i}.jpg").convert("RGB") for i in range(3)]
    try:
        canvas, _ = C.build_collage(images, layout="random", resize=False, dpi=300)
        ok, detail = True, ""
    except Exception as e:
        canvas, ok, detail = None, False, f"{type(e).__name__}: {e}"
    check("random layout survives wide images with resize=False", ok, detail)

    if canvas is not None:
        colours = canvas.getcolors(maxcolors=2_000_000) or []
        black = sum(n for n, col in colours if col == (0, 0, 0))
        check("rotation introduces no black corners", black == 0, f"{black} px")


def test_shuffle_randomises_zones(root):
    """The zone came from the pre-shuffle index, so placement never varied."""
    def centroid(canvas, target):
        xs = ys = n = 0
        for y in range(0, canvas.size[1], 7):
            for x in range(0, canvas.size[0], 7):
                p = canvas.getpixel((x, y))
                if all(abs(p[i] - target[i]) < 40 for i in range(3)):
                    xs, ys, n = xs + x, ys + y, n + 1
        return (xs / n, ys / n) if n else None

    zones = set()
    for seed in range(6):
        random.seed(seed)
        images = [Image.open(root / f"wide{i}.jpg").convert("RGB") for i in range(3)]
        canvas, _ = C.build_collage(images, layout="random", resize=True, dpi=300)
        spot = centroid(canvas, (200, 50, 50))
        if spot:
            zones.add((round(spot[0] / 300), round(spot[1] / 300)))
    check("random layout varies placement across seeds", len(zones) > 1,
          f"{len(zones)} distinct zones over 6 seeds")


def test_builders_are_pure(root):
    """The MCP server depends on these never printing or exiting."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        canvas, info = G.build_photo_grid(str(root / "face.jpg"), 0.5, 300)
        c2, i2 = C.build_collage([str(root / "wide0.jpg")], layout="random")
    check("builders write nothing to stdout", buf.getvalue() == "", repr(buf.getvalue()[:60]))
    check("build_photo_grid returns (Image, dict)",
          isinstance(canvas, Image.Image) and isinstance(info, dict))
    check("build_collage returns (Image, dict)",
          isinstance(c2, Image.Image) and isinstance(i2, dict))
    check("builders do not write to disk", not (root / "face_grid.jpg").exists())

    try:
        G.build_photo_grid(Image.new("RGB", (800, 800), "red"), 0.5, 150)
        C.build_collage([Image.new("RGB", (400, 400), "blue")] * 3, layout="grid", dpi=72)
        ok, detail = True, ""
    except Exception as e:
        ok, detail = False, f"{type(e).__name__}: {e}"
    check("builders accept in-memory PIL Images", ok, detail)


def test_errors_are_value_errors(root):
    cases = [
        ("grid missing file", lambda: G.build_photo_grid(str(root / "ghost.jpg"))),
        ("collage missing file", lambda: C.build_collage([str(root / "ghost.jpg")])),
        ("collage empty list", lambda: C.build_collage([])),
        ("collage bad layout", lambda: C.build_collage([str(root / "wide0.jpg")], layout="spiral")),
    ]
    for name, fn in cases:
        try:
            fn()
            check(f"{name} raises", False, "no exception")
        except SystemExit:
            check(f"{name} raises ValueError not SystemExit", False, "got SystemExit")
        except ValueError as e:
            check(f"{name} -> ValueError", True, str(e)[:56])
        except Exception as e:
            check(f"{name} -> ValueError", False, f"got {type(e).__name__}: {e}")


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        make_fixtures(root)
        test_grid_geometry()
        test_grid_copies_intact(root)
        test_transparency_inputs(root)
        test_random_collage_no_crash(root)
        test_shuffle_randomises_zones(root)
        test_builders_are_pure(root)
        test_errors_are_value_errors(root)

    print()
    if FAILURES:
        print(f"FAILURES ({len(FAILURES)}): {FAILURES}")
        return 1
    print("All image tool tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
