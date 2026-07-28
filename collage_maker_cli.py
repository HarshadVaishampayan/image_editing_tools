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
        
        processed_images.append(processed_img)
    
    # Create white canvas
    canvas = Image.new('RGB', (canvas_width, canvas_height), 'white')
    
    # Divide canvas into zones to ensure distribution
    n_images = len(processed_images)
    zones_per_row = math.ceil(math.sqrt(n_images))
    zone_width = canvas_width // zones_per_row
    zone_height = canvas_height // zones_per_row
    
    # Shuffle images for random placement
    image_zone_pairs = list(enumerate(processed_images))
    random.shuffle(image_zone_pairs)
    
    placed_images = []
    
    for idx, img in image_zone_pairs:
        # Calculate zone
        zone_idx = idx
        zone_row = zone_idx // zones_per_row
        zone_col = zone_idx % zones_per_row
        
        # Random position within zone
        zone_x = zone_col * zone_width
        zone_y = zone_row * zone_height
        
        max_x = min(zone_x + zone_width - img.size[0], canvas_width - img.size[0])
        max_y = min(zone_y + zone_height - img.size[1], canvas_height - img.size[1])
        
        x = random.randint(max(0, zone_x), max(0, max_x))
        y = random.randint(max(0, zone_y), max(0, max_y))
        
        # Random rotation (-15 to +15 degrees)
        rotation = random.uniform(-15, 15)
        rotated_img = img.rotate(rotation, expand=True, resample=Image.BICUBIC)
        
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
                
                # Ensure within bounds
                x = max(0, min(x, canvas_width - rotated_img.size[0]))
                y = max(0, min(y, canvas_height - rotated_img.size[1]))
        
        # Paste image
        if rotated_img.mode == 'RGBA':
            canvas.paste(rotated_img, (x, y), rotated_img)
        else:
            canvas.paste(rotated_img, (x, y))
        
        placed_images.append((x, y, rotated_img))
    
    return canvas


def create_collage(image_paths, output_path, layout='grid', resize=False, overlap=False, dpi=300):
    """
    Create a collage from multiple images.
    
    Args:
        image_paths: List of paths to input images
        output_path: Path for output file
        layout: 'grid' or 'random'
        resize: Whether to resize images
        overlap: Whether to enable overlap
        dpi: Dots per inch for output
    """
    # Canvas dimensions
    canvas_width_inches = 8
    canvas_height_inches = 11
    canvas_width_px = int(canvas_width_inches * dpi)
    canvas_height_px = int(canvas_height_inches * dpi)
    
    # Load images
    images = []
    for path in image_paths:
        try:
            img = Image.open(path)
            # Convert to RGB if necessary
            if img.mode != 'RGB':
                img = img.convert('RGB')
            images.append(img)
        except Exception as e:
            print(f"Error loading {path}: {e}")
            sys.exit(1)
    
    if not images:
        print("No valid images to process")
        sys.exit(1)
    
    # Create collage based on layout type
    if layout == 'grid':
        canvas = create_grid_collage(images, canvas_width_px, canvas_height_px, resize, overlap)
    else:  # random
        canvas = create_random_collage(images, canvas_width_px, canvas_height_px, resize, overlap)
    
    # Save with high quality
    canvas.save(output_path, 'JPEG', quality=95, dpi=(dpi, dpi))
    
    print(f"Successfully created collage: {output_path}")
    print(f"Canvas size: {canvas_width_inches}\" x {canvas_height_inches}\" at {dpi} DPI")
    print(f"Images processed: {len(images)}")
    print(f"Layout: {layout}, Resize: {resize}, Overlap: {overlap}")


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
    
    create_collage(
        args.images,
        args.output,
        layout=args.layout,
        resize=args.resize,
        overlap=args.overlap,
        dpi=args.dpi
    )


if __name__ == '__main__':
    main()
