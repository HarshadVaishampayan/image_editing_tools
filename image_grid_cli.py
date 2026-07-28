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


def process_image(image_path, edging_mm=0.5, dpi=300):
    """
    Process an image and create a 4"x6" canvas with 6 copies.
    
    Args:
        image_path: Path to input image
        edging_mm: Edge spacing in millimeters (default 0.5mm)
        dpi: Dots per inch for output (default 300)
    """
    
    # Convert measurements to pixels
    edging_inches = mm_to_inches(edging_mm)
    edging_px = int(edging_inches * dpi)
    
    # Image dimensions
    image_size_inches = 2
    image_size_px = int(image_size_inches * dpi)
    
    # Canvas dimensions
    canvas_width_inches = 4
    canvas_height_inches = 6
    canvas_width_px = int(canvas_width_inches * dpi)
    canvas_height_px = int(canvas_height_inches * dpi)
    
    # Load and process the input image
    try:
        img = Image.open(image_path)
    except Exception as e:
        print(f"Error loading image: {e}")
        sys.exit(1)
    
    # Crop to square (1:1 aspect ratio)
    img = crop_to_square(img)
    
    # Resize to 2"x2" while maintaining quality
    img = img.resize((image_size_px, image_size_px), Image.LANCZOS)
    
    # Create white canvas
    canvas = Image.new('RGB', (canvas_width_px, canvas_height_px), 'white')
    draw = ImageDraw.Draw(canvas)
    
    # Grid layout: 3 rows x 2 columns
    rows = 3
    cols = 2
    
    # Calculate total spacing
    # Spacing on sides: 1 unit each side
    # Spacing between copies: 2 units
    total_width_spacing = (2 * edging_px) + ((cols - 1) * 2 * edging_px)
    total_height_spacing = (2 * edging_px) + ((rows - 1) * 2 * edging_px)
    
    # Calculate starting position to center the grid
    grid_width = (cols * image_size_px) + total_width_spacing
    grid_height = (rows * image_size_px) + total_height_spacing
    
    start_x = (canvas_width_px - grid_width) // 2
    start_y = (canvas_height_px - grid_height) // 2
    
    # Place images and draw cutting guides
    for row in range(rows):
        for col in range(cols):
            # Calculate position with edging
            x = start_x + edging_px + col * (image_size_px + 2 * edging_px)
            y = start_y + edging_px + row * (image_size_px + 2 * edging_px)
            
            # Paste image
            canvas.paste(img, (x, y))
            
            # Draw black cutting guide rectangle around the image
            draw.rectangle(
                [x - 1, y - 1, x + image_size_px, y + image_size_px],
                outline='black',
                width=1
            )
    
    # Generate output filename
    output_path = image_path.rsplit('.', 1)[0] + '_grid.jpg'
    
    # Save with high quality
    canvas.save(output_path, 'JPEG', quality=95, dpi=(dpi, dpi))
    
    print(f"Successfully created grid image: {output_path}")
    print(f"Canvas size: {canvas_width_inches}\" x {canvas_height_inches}\" at {dpi} DPI")
    print(f"Each image: {image_size_inches}\" x {image_size_inches}\"")
    print(f"Edge spacing: {edging_mm}mm ({edging_px} pixels)")


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
    
    process_image(args.image, args.edging, args.dpi)


if __name__ == '__main__':
    main()
