#!/usr/bin/env python3
"""
Image Collage Maker
Creates an 8"x11" collage from multiple images with various layout options.
"""

import argparse
import math
import random
from PIL import Image
import sys
from pathlib import Path


def calculate_grid_dimensions(n_images):
    """Calculate optimal grid dimensions for n images."""
    if n_images == 1:
        return 1, 1
    
    # Try to make grid as square as possible
    cols = math.ceil(math.sqrt(n_images))
    rows = math.ceil(n_images / cols)
    
    return rows, cols


def resize_image_to_fit(img, target_width, target_height):
    """Resize image to fit within target dimensions while maintaining aspect ratio."""
    img_width, img_height = img.size
    
    # Calculate scaling factor to fit within target
    width_ratio = target_width / img_width
    height_ratio = target_height / img_height
    scale_factor = min(width_ratio, height_ratio)
    
    new_width = int(img_width * scale_factor)
    new_height = int(img_height * scale_factor)
    
    return img.resize((new_width, new_height), Image.LANCZOS)


def resize_to_height(img, target_height):
    """Resize image to specific height while maintaining aspect ratio."""
    img_width, img_height = img.size
    scale_factor = target_height / img_height
    new_width = int(img_width * scale_factor)
    
    return img.resize((new_width, target_height), Image.LANCZOS)


def random_position(zone_start, zone_extent, image_extent, canvas_extent):
    """
    Pick a random coordinate for an image inside its zone.

    Both bounds are clamped to the canvas, and the upper bound is never allowed
    below the lower bound -- an image larger than its zone would otherwise
    produce an empty range.
    """
    highest_legal = max(0, canvas_extent - image_extent)
    low = min(max(0, zone_start), highest_legal)
    high = min(zone_start + zone_extent - image_extent, highest_legal)

    if high < low:
        high = low

    return random.randint(low, high)


def create_grid_collage(images, canvas_width, canvas_height, resize_images, overlap_enabled):
    """Create a grid-based collage."""
    n_images = len(images)
    rows, cols = calculate_grid_dimensions(n_images)
    
    # Calculate cell dimensions
    cell_width = canvas_width // cols
    cell_height = canvas_height // rows
    
    # Create white canvas
    canvas = Image.new('RGB', (canvas_width, canvas_height), 'white')
    
    # Process and place images
    for idx, img in enumerate(images):
        row = idx // cols
        col = idx % cols
        
        if resize_images:
            # Resize to fit cell
            processed_img = resize_image_to_fit(img, cell_width, cell_height)
        else:
            # Keep original size but ensure it fits
            if img.size[0] > cell_width or img.size[1] > cell_height:
                processed_img = resize_image_to_fit(img, cell_width, cell_height)
            else:
                processed_img = img.copy()
        
        # Calculate position (center in cell)
        base_x = col * cell_width + (cell_width - processed_img.size[0]) // 2
        base_y = row * cell_height + (cell_height - processed_img.size[1]) // 2
        
        # Apply overlap if enabled
        if overlap_enabled:
            # Random corner overlap up to 5%
            overlap_x = random.randint(0, int(processed_img.size[0] * 0.05))
            overlap_y = random.randint(0, int(processed_img.size[1] * 0.05))
            
            # Randomly choose direction for each axis
            if random.choice([True, False]):
                base_x -= overlap_x
            else:
                base_x += overlap_x
                
            if random.choice([True, False]):
                base_y -= overlap_y
            else:
                base_y += overlap_y
        
        # Ensure image stays within canvas
        base_x = max(0, min(base_x, canvas_width - processed_img.size[0]))
        base_y = max(0, min(base_y, canvas_height - processed_img.size[1]))
        
        canvas.paste(processed_img, (base_x, base_y))
    
    return canvas


def create_random_collage(images, canvas_width, canvas_height, resize_images, overlap_enabled):
    """Create a random-layout collage with organized randomness."""
    # Calculate median height
    heights = [img.size[1] for img in images]
    heights.sort()
    median_height = heights[len(heights) // 2]
    
    # Process images
    processed_images = []
    for img in images:
        if resize_images:
            # Resize to median height
            processed_img = resize_to_height(img, median_height)
        else:
            # Keep original but cap at median height if larger
            if img.size[1] > median_height:
                processed_img = resize_to_height(img, median_height)
            else:
                processed_img = img.copy()
        
        # Never let an image exceed the canvas -- otherwise there is no legal
        # placement for it and the position maths below has an empty range.
        if processed_img.size[0] > canvas_width or processed_img.size[1] > canvas_height:
            processed_img = resize_image_to_fit(processed_img, canvas_width, canvas_height)

        processed_images.append(processed_img)

    # Create white canvas
    canvas = Image.new('RGB', (canvas_width, canvas_height), 'white')

    # Divide canvas into zones to ensure distribution
    n_images = len(processed_images)
    zones_per_row = math.ceil(math.sqrt(n_images))
    zone_width = canvas_width // zones_per_row
    zone_height = canvas_height // zones_per_row

    # Shuffle images so that zone assignment is actually randomised: the zone
    # comes from the position in the shuffled list, not the original index.
    shuffled_images = list(processed_images)
    random.shuffle(shuffled_images)

    placed_images = []

    for slot, img in enumerate(shuffled_images):
        # Calculate zone from the shuffled slot
        zone_row = slot // zones_per_row
        zone_col = slot % zones_per_row

        # Random position within zone, clamped to the canvas. An image wider
        # than its zone has a range that would otherwise run backwards.
        zone_x = zone_col * zone_width
        zone_y = zone_row * zone_height

        x = random_position(zone_x, zone_width, img.size[0], canvas_width)
        y = random_position(zone_y, zone_height, img.size[1], canvas_height)

        # Random rotation (-15 to +15 degrees). Rotate through RGBA with a
        # transparent fill so the corners the rotation introduces stay clear
        # instead of coming out black on the white canvas.
        rotation = random.uniform(-15, 15)
        rotated_img = img.convert('RGBA').rotate(
            rotation, expand=True, resample=Image.BICUBIC, fillcolor=(255, 255, 255, 0)
        )

        # Apply corner overlap if enabled
        if overlap_enabled and placed_images:
            # Randomly try to overlap with a previously placed image
            if random.random() < 0.7:  # 70% chance to overlap
                target_img_data = random.choice(placed_images)
                target_x, target_y, target_img = target_img_data
                
                # Calculate overlap position (corner overlap up to 5%)
                overlap_amount = 0.05
                
                # Randomly choose which corner to overlap
                corner = random.choice(['tl', 'tr', 'bl', 'br'])
                
                if corner == 'tl':  # Top-left
                    x = target_x - int(rotated_img.size[0] * (1 - overlap_amount))
                    y = target_y - int(rotated_img.size[1] * (1 - overlap_amount))
                elif corner == 'tr':  # Top-right
                    x = target_x + target_img.size[0] - int(rotated_img.size[0] * overlap_amount)
                    y = target_y - int(rotated_img.size[1] * (1 - overlap_amount))
                elif corner == 'bl':  # Bottom-left
                    x = target_x - int(rotated_img.size[0] * (1 - overlap_amount))
                    y = target_y + target_img.size[1] - int(rotated_img.size[1] * overlap_amount)
                else:  # Bottom-right
                    x = target_x + target_img.size[0] - int(rotated_img.size[0] * overlap_amount)
                    y = target_y + target_img.size[1] - int(rotated_img.size[1] * overlap_amount)

        # Ensure within bounds. Rotation with expand=True grows the bounding
        # box, so this has to be applied to the rotated size on every path --
        # not only when an overlap was applied.
        x = max(0, min(x, canvas_width - rotated_img.size[0]))
        y = max(0, min(y, canvas_height - rotated_img.size[1]))

        # Paste image, using its own alpha so the rotation corners stay clear
        canvas.paste(rotated_img, (x, y), rotated_img)

        placed_images.append((x, y, rotated_img))
    
    return canvas


def build_collage(sources, layout='grid', resize=False, overlap=False, dpi=300,
                  canvas_width_inches=8, canvas_height_inches=11):
    """
    Build a collage canvas from paths and/or already-open PIL Images.

    Returns (canvas, info). Pure: no printing, no disk writes, no process exit.
    Raises ValueError on unreadable input or an unknown layout.
    """
    if layout not in ('grid', 'random'):
        raise ValueError(f"unknown layout {layout!r}; expected 'grid' or 'random'")

    canvas_width_px = int(canvas_width_inches * dpi)
    canvas_height_px = int(canvas_height_inches * dpi)

    images = []
    for source in sources:
        if isinstance(source, Image.Image):
            images.append(source if source.mode == 'RGB' else source.convert('RGB'))
            continue
        try:
            img = Image.open(source)
            img.load()
        except FileNotFoundError:
            raise ValueError(f"image not found: {source}")
        except Exception as e:
            raise ValueError(f"could not read image {source}: {e}")
        images.append(img if img.mode == 'RGB' else img.convert('RGB'))

    if not images:
        raise ValueError("no images supplied")

    if layout == 'grid':
        canvas = create_grid_collage(images, canvas_width_px, canvas_height_px, resize, overlap)
        rows, cols = calculate_grid_dimensions(len(images))
    else:
        canvas = create_random_collage(images, canvas_width_px, canvas_height_px, resize, overlap)
        rows = cols = None

    info = {
        'canvas_px': (canvas_width_px, canvas_height_px),
        'canvas_inches': (canvas_width_inches, canvas_height_inches),
        'dpi': dpi,
        'layout': layout,
        'resize': resize,
        'overlap': overlap,
        'image_count': len(images),
        'grid_rows': rows,
        'grid_cols': cols,
    }
    return canvas, info


def create_collage(image_paths, output_path, layout='grid', resize=False, overlap=False, dpi=300):
    """
    Create a collage from multiple images and save it as JPEG.

    Returns the info dict, with 'output_path' added. Raises ValueError on bad
    input rather than exiting.
    """
    canvas, info = build_collage(
        image_paths, layout=layout, resize=resize, overlap=overlap, dpi=dpi
    )

    canvas.save(output_path, 'JPEG', quality=95, dpi=(dpi, dpi))

    info['output_path'] = output_path
    return info


def format_collage_report(info):
    """Render the info dict from create_collage as human-readable lines."""
    return "\n".join([
        f"Successfully created collage: {info['output_path']}",
        f"Canvas size: {info['canvas_inches'][0]}\" x {info['canvas_inches'][1]}\" "
        f"at {info['dpi']} DPI",
        f"Images processed: {info['image_count']}",
        f"Layout: {info['layout']}, Resize: {info['resize']}, Overlap: {info['overlap']}",
    ])


def main():
    parser = argparse.ArgumentParser(
        description='Create an 8"x11" collage from multiple images.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage:
  %(prog)s img1.jpg img2.jpg img3.jpg
  %(prog)s *.jpg --output my_collage.jpg
  %(prog)s img*.png --layout random --resize --overlap
  %(prog)s photo1.jpg photo2.jpg --layout grid --resize
        """
    )
    
    parser.add_argument(
        'images',
        nargs='+',
        help='Paths to input image files'
    )
    
    parser.add_argument(
        '--output', '-o',
        default='collage.jpg',
        help='Output file path (default: collage.jpg)'
    )
    
    parser.add_argument(
        '--layout', '-l',
        choices=['grid', 'random'],
        default='grid',
        help='Layout pattern: grid or random (default: grid)'
    )
    
    parser.add_argument(
        '--resize', '-r',
        action='store_true',
        help='Resize images (default: keep original size)'
    )
    
    parser.add_argument(
        '--overlap',
        action='store_true',
        help='Enable image overlap at corners (default: no overlap)'
    )
    
    parser.add_argument(
        '--dpi',
        type=int,
        default=300,
        help='Output resolution in DPI (default: 300)'
    )
    
    args = parser.parse_args()
    
    try:
        info = create_collage(
            args.images,
            args.output,
            layout=args.layout,
            resize=args.resize,
            overlap=args.overlap,
            dpi=args.dpi
        )
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(format_collage_report(info))


if __name__ == '__main__':
    main()
