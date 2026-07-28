#!/usr/bin/env python3
"""
Image Grid Generator
Creates a 4"x6" canvas with 6 copies of a 2"x2" image arranged in a 3x2 grid.
"""

import argparse
from PIL import Image, ImageDraw
import sys


def mm_to_inches(mm):
    """Convert millimeters to inches."""
    return mm / 25.4


def to_rgb(img):
    """Convert any input mode to RGB, compositing transparency onto white."""
    if img.mode == 'RGB':
        return img

    if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
        rgba = img.convert('RGBA')
        background = Image.new('RGBA', rgba.size, (255, 255, 255, 255))
        return Image.alpha_composite(background, rgba).convert('RGB')

    return img.convert('RGB')


def crop_to_square(img):
    """Crop image to 1:1 aspect ratio from center."""
    width, height = img.size
    
    if width == height:
        return img
    
    # Determine the size of the square (smallest dimension)
    square_size = min(width, height)
    
    # Calculate cropping box (center crop)
    left = (width - square_size) // 2
    top = (height - square_size) // 2
    right = left + square_size
    bottom = top + square_size
    
    return img.crop((left, top, right, bottom))


def compute_grid_geometry(edging_mm=0.5, dpi=300, rows=3, cols=2,
                          canvas_width_inches=4, canvas_height_inches=6,
                          photo_size_inches=2):
    """
    Compute the placement geometry for the photo sheet.

    Six 2"x2" photos in a 3x2 arrangement consume exactly 4"x6", so any
    non-zero edging must come out of the photo size -- otherwise the grid
    overflows the canvas and every photo gets clipped. The photo is therefore
    sized to whatever fits, never larger than the requested size.

    Returns a dict describing the canvas, the photo size actually used, and
    the placement box of each copy.
    """
    edging_px = int(mm_to_inches(edging_mm) * dpi)
    canvas_width_px = int(canvas_width_inches * dpi)
    canvas_height_px = int(canvas_height_inches * dpi)

    # Each copy occupies a cell of photo + edging on all four sides.
    cell_width = canvas_width_px // cols
    cell_height = canvas_height_px // rows

    requested_px = int(photo_size_inches * dpi)
    fitted_px = min(cell_width, cell_height) - 2 * edging_px
    photo_px = min(requested_px, fitted_px)

    if photo_px <= 0:
        raise ValueError(
            f"edging of {edging_mm}mm leaves no room for photos on a "
            f"{canvas_width_inches}\"x{canvas_height_inches}\" sheet at {dpi} DPI"
        )

    grid_width = cols * (photo_px + 2 * edging_px)
    grid_height = rows * (photo_px + 2 * edging_px)
    start_x = (canvas_width_px - grid_width) // 2
    start_y = (canvas_height_px - grid_height) // 2

    boxes = []
    for row in range(rows):
        for col in range(cols):
            x = start_x + edging_px + col * (photo_px + 2 * edging_px)
            y = start_y + edging_px + row * (photo_px + 2 * edging_px)
            boxes.append((x, y, x + photo_px, y + photo_px))

    clipped = [
        b for b in boxes
        if b[0] < 0 or b[1] < 0 or b[2] > canvas_width_px or b[3] > canvas_height_px
    ]

    return {
        'canvas_px': (canvas_width_px, canvas_height_px),
        'canvas_inches': (canvas_width_inches, canvas_height_inches),
        'rows': rows,
        'cols': cols,
        'edging_mm': edging_mm,
        'edging_px': edging_px,
        'photo_px': photo_px,
        'photo_inches': photo_px / dpi,
        'requested_inches': photo_size_inches,
        'downsized': photo_px < requested_px,
        'boxes': boxes,
        'clipped': clipped,
        'dpi': dpi,
    }


def load_image(source):
    """
    Accept a path or an already-open PIL Image and return an RGB Image.

    Raises ValueError on anything unreadable so callers can report the failure;
    never exits the process.
    """
    if isinstance(source, Image.Image):
        return to_rgb(source)

    try:
        img = Image.open(source)
        img.load()
    except FileNotFoundError:
        raise ValueError(f"image not found: {source}")
    except Exception as e:
        raise ValueError(f"could not read image {source}: {e}")

    return to_rgb(img)


def build_photo_grid(source, edging_mm=0.5, dpi=300):
    """
    Build the 4"x6" sheet holding 6 copies of the source image.

    Returns (canvas, info) where info describes the geometry actually used.
    Pure: no printing, no disk writes, no process exit.
    """
    geom = compute_grid_geometry(edging_mm=edging_mm, dpi=dpi)
    canvas_width_px, canvas_height_px = geom['canvas_px']
    photo_px = geom['photo_px']

    img = load_image(source)
    original_size = img.size

    # Crop to square (1:1 aspect ratio), then resize to the fitted photo size
    img = crop_to_square(img)
    img = img.resize((photo_px, photo_px), Image.LANCZOS)

    canvas = Image.new('RGB', (canvas_width_px, canvas_height_px), 'white')
    draw = ImageDraw.Draw(canvas)

    for left, top, right, bottom in geom['boxes']:
        canvas.paste(img, (left, top))

        # Draw black cutting guide just outside the photo, clamped to canvas
        draw.rectangle(
            [max(0, left - 1), max(0, top - 1),
             min(canvas_width_px - 1, right), min(canvas_height_px - 1, bottom)],
            outline='black',
            width=1
        )

    info = dict(geom)
    info['source_size'] = original_size
    info['copies'] = len(geom['boxes'])
    return canvas, info


def process_image(image_path, edging_mm=0.5, dpi=300, output_path=None):
    """
    Build the sheet for image_path and save it as JPEG.

    Returns the info dict, with 'output_path' added. Raises ValueError on bad
    input rather than exiting.
    """
    canvas, info = build_photo_grid(image_path, edging_mm=edging_mm, dpi=dpi)

    if output_path is None:
        output_path = image_path.rsplit('.', 1)[0] + '_grid.jpg'

    canvas.save(output_path, 'JPEG', quality=95, dpi=(dpi, dpi))

    info['output_path'] = output_path
    return info


def format_grid_report(info):
    """Render the info dict from process_image as human-readable lines."""
    lines = [
        f"Successfully created grid image: {info['output_path']}",
        f"Canvas size: {info['canvas_inches'][0]}\" x {info['canvas_inches'][1]}\" "
        f"at {info['dpi']} DPI",
        f"Each image: {info['photo_inches']:.3f}\" x {info['photo_inches']:.3f}\" "
        f"({info['photo_px']}px)",
        f"Edge spacing: {info['edging_mm']}mm ({info['edging_px']} pixels)",
    ]
    if info['downsized']:
        lines.append(
            f"Note: photos shrunk from {info['requested_inches']}\" to fit the "
            f"{info['edging_mm']}mm edging. Use --edging 0 for exact "
            f"{info['requested_inches']}\"x{info['requested_inches']}\" photos."
        )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description='Create a 4"x6" canvas with 6 copies of an image in a 3x2 grid.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage:
  %(prog)s photo.jpg
  %(prog)s photo.jpg --edging 1.0
  %(prog)s photo.png --edging 0.3 --dpi 600
        """
    )
    
    parser.add_argument(
        'image',
        help='Path to the input image file'
    )
    
    parser.add_argument(
        '--edging',
        type=float,
        default=0.5,
        help='Edge spacing in millimeters (default: 0.5mm)'
    )
    
    parser.add_argument(
        '--dpi',
        type=int,
        default=300,
        help='Output resolution in DPI (default: 300)'
    )
    
    args = parser.parse_args()

    try:
        info = process_image(args.image, args.edging, args.dpi)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(format_grid_report(info))


if __name__ == '__main__':
    main()
