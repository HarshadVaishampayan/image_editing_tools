# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python-based CLI tool suite for creating passport photo layouts and image collages. It provides two main utilities:

- **collage_maker_cli.py**: Creates 8"x11" collages from multiple images with configurable grid or random layouts
- **image_grid_cli.py**: Creates 4"x6" photo grids with 6 copies of a single image (useful for passport photo printing)

Both tools generate high-quality JPEG output suitable for professional printing at configurable DPI.

## Architecture & Key Components

### Image Processing Pipeline
Both tools follow a similar pattern:
1. Load and validate input images
2. Convert to RGB if needed (handles PNG, JPEG with transparency)
3. Resize/crop images to target specifications while preserving aspect ratios
4. Compose final layout on a canvas
5. Save as high-quality JPEG with metadata (DPI)

### Key Modules

**collage_maker_cli.py**
- `create_grid_collage()`: Arranges images in an optimal grid (rows × cols calculated from image count)
- `create_random_collage()`: Creates Pinterest-style layout with rotations and randomized placement
- Image resizing helpers: `resize_image_to_fit()`, `resize_to_height()`
- Supports optional corner overlapping (up to 5%) for visual cohesion

**image_grid_cli.py**
- `crop_to_square()`: Center-crops any input image to 1:1 aspect ratio
- `process_image()`: Creates standardized 3×2 grid with black cutting guides
- Edge spacing configurable in millimeters (converted to pixels at DPI)

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

### Testing

No automated test suite exists. Manual testing:
1. Use test images with different aspect ratios and resolutions
2. Verify output dimensions: 8"×11" for collages, 4"×6" for grids at specified DPI
3. Check image quality (no excessive compression artifacts)
4. For grid layout: verify 6 images fit correctly and cutting guides align

## Dependencies

- **Pillow (PIL)**: Image loading, manipulation, resizing, rotation
  - Used for: opening/saving JPEG, PNG; resizing with LANCZOS quality; image.paste() compositing; rotation and transparency handling

## Design Notes

- Both tools preserve image quality using LANCZOS resampling and high JPEG quality (95%)
- Canvas backgrounds are white by default (suitable for photo printing)
- The collage tool calculates optimal grid dimensions automatically to keep layouts square
- Random collage applies -15° to +15° rotations for aesthetic variety
- Image overlapping is constrained to prevent complete occlusion
- All coordinate calculations include boundary checks to prevent paste errors
