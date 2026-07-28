#!/usr/bin/env python3
"""
MCP server exposing the photo-grid and collage tools.

Deliberately conservative so it works across MCP clients (Claude, Codex,
Gemini CLI, opencode, ...):

* stdio transport, which every client implements
* tools only -- no resources, prompts, sampling or elicitation
* flat primitive parameters with sentinel defaults. `str | None` renders as
  a JSON Schema `anyOf`, which several clients' schema subsets reject, so
  optional strings default to "" instead of None.
* text results by default. Image content blocks are opt-in via
  `return_preview`, because client support for them is uneven.

Nothing here writes to stdout -- that is the JSON-RPC channel, and a stray
print would desync the client. The underlying library functions return data
instead of printing, which is what keeps that true.
"""

import argparse
import base64
import binascii
import io
import os
from pathlib import Path

import anyio
from PIL import Image
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.utilities.types import Image as MCPImage

import collage_maker_cli
import image_grid_cli

# Resource guards. An 8x11 sheet at 600 DPI is already a 4800x6600 canvas
# (~95MB uncompressed); anything beyond that is a denial-of-service by typo.
MAX_DPI = 600
MAX_SOURCE_PIXELS = 80_000_000
MAX_IMAGES = 60
PREVIEW_MAX_PX = 512

mcp = FastMCP("image-editing-tools")

_base_dir = Path.home()


def set_base_dir(path):
    """Set the directory that all relative paths resolve against."""
    global _base_dir
    _base_dir = Path(path).expanduser().resolve()
    return _base_dir


def _resolve(path_str):
    """
    Resolve a user-supplied path against the base directory.

    Clients launch servers from unpredictable working directories, so relative
    paths are interpreted against an explicit base rather than the cwd. Paths
    that escape the base directory are rejected.
    """
    candidate = Path(path_str).expanduser()
    if not candidate.is_absolute():
        candidate = _base_dir / candidate

    resolved = candidate.resolve()
    if resolved != _base_dir and _base_dir not in resolved.parents:
        raise ValueError(
            f"path {path_str!r} resolves outside the allowed base directory "
            f"{_base_dir}. Pass a path inside it, or restart the server with "
            f"--base-dir."
        )
    return resolved


def _resolve_input(path_str):
    resolved = _resolve(path_str)
    if not resolved.exists():
        raise ValueError(f"image not found: {resolved}")
    if not resolved.is_file():
        raise ValueError(f"not a file: {resolved}")
    return resolved


def _resolve_output(path_str, default_name, overwrite):
    resolved = _resolve(path_str) if path_str else (_base_dir / default_name)
    if resolved.is_dir():
        resolved = resolved / default_name

    if not resolved.parent.exists():
        raise ValueError(f"output directory does not exist: {resolved.parent}")
    if resolved.exists() and not overwrite:
        raise ValueError(
            f"{resolved} already exists. Choose a different output_path, or "
            f"pass overwrite=true to replace it."
        )
    return resolved


def _check_dpi(dpi):
    if dpi < 30 or dpi > MAX_DPI:
        raise ValueError(f"dpi must be between 30 and {MAX_DPI}, got {dpi}")


def _decode_base64(data, label="image_base64"):
    try:
        raw = base64.b64decode(data, validate=True)
    except (binascii.Error, ValueError) as e:
        raise ValueError(f"{label} is not valid base64: {e}")

    try:
        img = Image.open(io.BytesIO(raw))
        img.load()
    except Exception as e:
        raise ValueError(f"{label} did not decode to a readable image: {e}")

    if img.size[0] * img.size[1] > MAX_SOURCE_PIXELS:
        raise ValueError(f"{label} exceeds the {MAX_SOURCE_PIXELS:,} pixel limit")
    return img


def _load_sources(paths, base64_items, label):
    """Turn path strings and/or base64 blobs into a list of loadable sources."""
    sources = []
    for p in paths:
        resolved = _resolve_input(p)
        with Image.open(resolved) as probe:
            if probe.size[0] * probe.size[1] > MAX_SOURCE_PIXELS:
                raise ValueError(
                    f"{resolved} exceeds the {MAX_SOURCE_PIXELS:,} pixel limit"
                )
        sources.append(str(resolved))

    for i, blob in enumerate(base64_items):
        sources.append(_decode_base64(blob, f"{label}[{i}]"))

    if not sources:
        raise ValueError(f"supply at least one image via {label} or a path")
    if len(sources) > MAX_IMAGES:
        raise ValueError(f"at most {MAX_IMAGES} images per call, got {len(sources)}")
    return sources


def _preview(canvas):
    """Downscale a canvas into a small JPEG for optional visual verification."""
    thumb = canvas.copy()
    thumb.thumbnail((PREVIEW_MAX_PX, PREVIEW_MAX_PX), Image.LANCZOS)
    buf = io.BytesIO()
    thumb.save(buf, "JPEG", quality=70)
    return MCPImage(data=buf.getvalue(), format="jpeg")


def _result(text, canvas, return_preview):
    return [text, _preview(canvas)] if return_preview else text


@mcp.tool()
async def create_photo_grid(
    image_path: str = "",
    image_base64: str = "",
    output_path: str = "",
    edging_mm: float = 0.5,
    dpi: int = 300,
    overwrite: bool = False,
    return_preview: bool = False,
):
    """Create a printable 4x6 inch sheet holding 6 copies of one photo in a 3x2 grid, with black cutting guides. Intended for passport and ID photos.

    Supply the photo either as image_path (a file path) or image_base64 (raw
    base64 image bytes) -- exactly one of the two.

    The photo is centre-cropped to a square first, which trims the longer
    dimension: a portrait photo loses its top and bottom (head and shoulders), a
    landscape photo loses its left and right. Call inspect_image first to see
    exactly how much would be removed.

    Six 2x2 inch photos fill a 4x6 inch sheet exactly, so any non-zero edging_mm
    makes each photo slightly smaller than 2x2. Pass edging_mm=0 when the output
    must be exactly 2x2 inches, as US passport photos require. The reply states
    the physical size actually used.

    Args:
        image_path: Path to the source photo. Relative paths resolve against the server base directory.
        image_base64: Base64-encoded source photo, as an alternative to image_path.
        output_path: Where to write the JPEG. Defaults to <input>_grid.jpg, or photo_grid.jpg for base64 input.
        edging_mm: White gutter around each photo in millimetres. 0 gives exact 2x2 inch photos.
        dpi: Output resolution, 30-600. 300 is standard for printing.
        overwrite: Allow replacing an existing output file.
        return_preview: Also return a small preview image of the finished sheet.
    """
    if bool(image_path) == bool(image_base64):
        raise ValueError("supply exactly one of image_path or image_base64")
    _check_dpi(dpi)
    if edging_mm < 0:
        raise ValueError(f"edging_mm must be >= 0, got {edging_mm}")

    if image_path:
        source = str(_resolve_input(image_path))
        default_name = Path(source).stem + "_grid.jpg"
    else:
        source = _decode_base64(image_base64)
        default_name = "photo_grid.jpg"

    destination = _resolve_output(output_path, default_name, overwrite)

    def render():
        canvas, info = image_grid_cli.build_photo_grid(
            source, edging_mm=edging_mm, dpi=dpi
        )
        canvas.save(destination, "JPEG", quality=95, dpi=(dpi, dpi))
        return canvas, info

    canvas, info = await anyio.to_thread.run_sync(render)

    w, h = info["canvas_px"]
    lines = [
        f"Wrote {destination}",
        f"Sheet: {info['canvas_inches'][0]}x{info['canvas_inches'][1]} inches "
        f"({w}x{h} px) at {dpi} DPI",
        f"Copies: {info['copies']} in a {info['rows']}x{info['cols']} grid",
        f"Photo size: {info['photo_inches']:.3f}x{info['photo_inches']:.3f} inches "
        f"({info['photo_px']}px square)",
        f"Edging: {edging_mm}mm ({info['edging_px']} px)",
        f"Clipped copies: {len(info['clipped'])}",
    ]
    if info["downsized"]:
        lines.append(
            f"Note: photos are {info['photo_inches']:.3f} inches, not the "
            f"requested {info['requested_inches']}, because the {edging_mm}mm "
            f"edging has to come out of the photo. Use edging_mm=0 for exact "
            f"{info['requested_inches']}x{info['requested_inches']} inch photos."
        )
    return _result("\n".join(lines), canvas, return_preview)


@mcp.tool()
async def create_collage(
    image_paths: list[str] = [],
    images_base64: list[str] = [],
    output_path: str = "",
    layout: str = "grid",
    resize: bool = False,
    overlap: bool = False,
    dpi: int = 300,
    overwrite: bool = False,
    return_preview: bool = False,
):
    """Combine several images into one printable 8x11 inch collage.

    Supply images as image_paths (file paths), images_base64 (base64 image
    bytes), or a mix of both.

    layout="grid" tiles the images in even rows and columns, keeping every image
    upright and fully visible. layout="random" scatters them with small random
    rotations for a scrapbook look, which crops and overlaps more aggressively.

    resize=true scales images to fill their space and generally looks better;
    resize=false keeps original sizes and only shrinks what does not fit.

    Args:
        image_paths: Paths to the source images. Relative paths resolve against the server base directory.
        images_base64: Base64-encoded source images, usable instead of or alongside image_paths.
        output_path: Where to write the JPEG. Defaults to collage.jpg in the base directory.
        layout: Either "grid" or "random".
        resize: Scale images to fit their allotted space.
        overlap: Let images overlap slightly at the corners.
        dpi: Output resolution, 30-600. 300 is standard for printing.
        overwrite: Allow replacing an existing output file.
        return_preview: Also return a small preview image of the finished collage.
    """
    if layout not in ("grid", "random"):
        raise ValueError(f"layout must be 'grid' or 'random', got {layout!r}")
    _check_dpi(dpi)

    sources = _load_sources(image_paths, images_base64, "images_base64")
    destination = _resolve_output(output_path, "collage.jpg", overwrite)

    def render():
        canvas, info = collage_maker_cli.build_collage(
            sources, layout=layout, resize=resize, overlap=overlap, dpi=dpi
        )
        canvas.save(destination, "JPEG", quality=95, dpi=(dpi, dpi))
        return canvas, info

    canvas, info = await anyio.to_thread.run_sync(render)

    w, h = info["canvas_px"]
    lines = [
        f"Wrote {destination}",
        f"Canvas: {info['canvas_inches'][0]}x{info['canvas_inches'][1]} inches "
        f"({w}x{h} px) at {dpi} DPI",
        f"Images placed: {info['image_count']}",
        f"Layout: {layout} (resize={resize}, overlap={overlap})",
    ]
    if info["grid_rows"]:
        lines.append(f"Grid: {info['grid_rows']} rows x {info['grid_cols']} columns")
    return _result("\n".join(lines), canvas, return_preview)


@mcp.tool()
async def inspect_image(image_path: str):
    """Report an image's dimensions, mode and orientation, and what a square centre-crop would remove.

    Use this before create_photo_grid to check whether the subject survives the
    square crop that the photo sheet applies.

    Args:
        image_path: Path to the image. Relative paths resolve against the server base directory.
    """
    resolved = _resolve_input(image_path)

    def probe():
        with Image.open(resolved) as img:
            return img.size, img.mode, img.format

    (width, height), mode, fmt = await anyio.to_thread.run_sync(probe)

    square = min(width, height)
    trimmed = abs(width - height)
    orientation = (
        "square" if width == height
        else "landscape" if width > height
        else "portrait"
    )

    lines = [
        f"{resolved}",
        f"Format: {fmt}, mode: {mode}",
        f"Dimensions: {width}x{height} px ({orientation}, "
        f"aspect {width / height:.3f})",
        f"Square centre-crop would be {square}x{square} px",
    ]
    if trimmed:
        edge = "left and right" if width > height else "top and bottom"
        lines.append(
            f"Crop removes {trimmed} px total from the {edge} "
            f"({trimmed / 2:.0f} px from each side, "
            f"{100 * trimmed / max(width, height):.1f}% of the long edge)"
        )
    else:
        lines.append("Already square; the centre-crop removes nothing.")

    max_print = min(width, height)
    lines.append(
        f"At 300 DPI the cropped square prints at "
        f"{max_print / 300:.2f}x{max_print / 300:.2f} inches before resampling."
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="MCP server for passport photo sheets and print collages."
    )
    parser.add_argument(
        "--base-dir",
        default=os.environ.get("IMAGE_TOOLS_BASE_DIR"),
        help="Directory that relative paths resolve against and that reads and "
             "writes are confined to (default: $IMAGE_TOOLS_BASE_DIR or $HOME).",
    )
    parser.add_argument(
        "--transport",
        default="stdio",
        choices=["stdio", "streamable-http"],
        help="MCP transport (default: stdio, which every client supports).",
    )
    args = parser.parse_args()

    set_base_dir(args.base_dir or Path.home())
    mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
