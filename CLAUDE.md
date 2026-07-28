# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python tool suite for creating passport photo layouts and image collages, exposed as CLIs, as an importable library, and as an MCP server:

- **collage_maker_cli.py**: Creates 8"x11" collages from multiple images with configurable grid or random layouts
- **image_grid_cli.py**: Creates 4"x6" photo grids with 6 copies of a single image (useful for passport photo printing)
- **mcp_server.py**: MCP server (stdio) exposing `create_photo_grid`, `create_collage`, and `inspect_image`

All generate high-quality JPEG output suitable for professional printing at configurable DPI.

## Architecture & Key Components

### Layering

The code is split into three layers, and the split matters:

1. **Pure builders** — `build_photo_grid()` and `build_collage()` return
   `(PIL.Image, info_dict)`. They never print, never write to disk, and never
   call `sys.exit`; they raise `ValueError` on bad input. Both accept either a
   path or an already-open `PIL.Image`.
2. **Save wrappers** — `process_image()` and `create_collage()` add the disk
   write and return the info dict.
3. **Adapters** — `main()` in each CLI formats the info dict for humans;
   `mcp_server.py` formats it for a model.

Keep the builders pure. The MCP server runs over stdio, where **stdout is the
JSON-RPC channel** — a stray `print()` in library code desyncs the client.
`tests/test_image_tools.py` asserts this, so breaking it fails the suite.

### Image Processing Pipeline
1. Load and validate input images
2. Convert to RGB (transparency composited onto white via `to_rgb()`)
3. Resize/crop images to target specifications while preserving aspect ratios
4. Compose final layout on a canvas
5. Save as high-quality JPEG with metadata (DPI)

### Key Modules

**collage_maker_cli.py**
- `build_collage()`: Pure entry point; validates layout, loads sources, dispatches
- `create_grid_collage()`: Arranges images in an optimal grid (rows × cols calculated from image count)
- `create_random_collage()`: Pinterest-style layout with rotations and randomized placement
- `random_position()`: Clamps placement so an image larger than its zone cannot produce an empty range
- Image resizing helpers: `resize_image_to_fit()`, `resize_to_height()`
- Supports optional corner overlapping (up to 5%) for visual cohesion

**image_grid_cli.py**
- `compute_grid_geometry()`: Derives photo size and placement boxes; the single source of layout truth
- `crop_to_square()`: Center-crops any input image to 1:1 aspect ratio
- `to_rgb()`: Flattens alpha/palette inputs onto white
- `build_photo_grid()`: Composes the 3×2 sheet with black cutting guides
- Edge spacing configurable in millimeters (converted to pixels at DPI)

**mcp_server.py**
- Async tools offloading render work via `anyio.to_thread.run_sync` — FastMCP calls sync tools directly on the event loop, so a sync tool would block the server for the duration of a render
- Parameters are flat primitives with sentinel defaults (`str = ""`, not `str | None`) and the tools carry no return annotations, because both produce JSON Schema `anyOf`, which some clients' schema subsets reject
- All paths resolve against `--base-dir` rather than the cwd, which varies unpredictably by client

### Critical Geometry Constraint

Six 2"×2" photos occupy exactly 4"×6". There is no slack on the sheet, so any
non-zero edging **must** come out of the photo size — `compute_grid_geometry()`
shrinks the photo to fit and sets `downsized`. Centring an oversized grid instead
pushes every copy off-canvas; that was a real bug, and
`tests/test_image_tools.py` pins it across 15 dpi/edging combinations.

### Measurement System
Both tools use:
- Canvas size: specified in inches (8×11 for collages, 4×6 for grids)
- Image size: specified in inches (2×2 for grid layout)
- DPI: configurable output resolution (default 300 DPI, suitable for professional printing)
- Edging/spacing: millimeters converted to pixels for pixel-perfect layouts

## Common Commands

### Running the CLI Tools

**Activate virtual environment:**
```bash
source venv/bin/activate
```

**Create a collage from multiple images (grid layout):**
```bash
python3 collage_maker_cli.py img1.jpg img2.jpg img3.jpg --output my_collage.jpg
```

**Create a random-layout collage with overlapping:**
```bash
python3 collage_maker_cli.py *.jpg --layout random --resize --overlap --dpi 600
```

**Create a 6-copy grid from a single photo:**
```bash
python3 image_grid_cli.py photo.jpg --edging 0.5 --dpi 300
```

**High-resolution variant (for professional printing):**
```bash
python3 image_grid_cli.py photo.jpg --dpi 600
```

**Run the MCP server:**
```bash
python3 mcp_server.py --base-dir ~/Pictures
```

### Testing

Two plain-Python suites, no test framework. Both exit non-zero on failure.

```bash
python3 tests/test_image_tools.py
python3 tests/test_mcp_server.py
```

`test_image_tools.py` covers layout geometry, transparency handling, builder
purity, and the error contract. `test_mcp_server.py` launches `mcp_server.py`
over stdio and drives it as a real MCP client, covering the tool contract, the
base-directory sandbox, the resource guards, and the absence of schema unions.

Most checks pin a bug that shipped once — a failure means a real regression, not
a flaky assertion. Add to these rather than testing by hand.

## Dependencies

- **Pillow (PIL)**: Image loading, manipulation, resizing, rotation
  - Used for: opening/saving JPEG, PNG; resizing with LANCZOS quality; image.paste() compositing; rotation and transparency handling
- **mcp**: Model Context Protocol SDK (FastMCP), used only by `mcp_server.py`

## Design Notes

- Both tools preserve image quality using LANCZOS resampling and high JPEG quality (95%)
- Canvas backgrounds are white by default (suitable for photo printing)
- The collage tool calculates optimal grid dimensions automatically to keep layouts square
- Random collage applies -15° to +15° rotations for aesthetic variety
- Image overlapping is constrained to prevent complete occlusion
- All coordinate calculations include boundary checks to prevent paste errors
