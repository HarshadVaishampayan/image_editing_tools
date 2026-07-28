# Passport Photos & Photo Collages

Professional Python CLI tools for creating photo layouts and collages ready for printing.

## Features

### 🖼️ Photo Grid Generator (`image_grid_cli.py`)
Creates a **4"×6" sheet** containing **6 identical copies** of a single photo arranged in a 3×2 grid — ideal for passport photo printing or photo booth strips.

- Automatically crops any image to square (1:1 aspect ratio)
- Includes cutting guides (black lines) for easy trimming
- Configurable edge spacing
- Professional-quality output at adjustable DPI
- White background

**Perfect for:** Passport photos, ID photos, small gift prints

### 📸 Collage Maker (`collage_maker_cli.py`)
Creates an **8"×11" collage** from multiple images with two layout styles.

**Grid Layout** — Organized arrangement (automatically calculated optimal rows/columns)
- Distributes images evenly across the page
- Centers images in each cell
- Optional corner overlapping for visual interest

**Random Layout** — Artistic Pinterest-style arrangement
- Randomly rotates each image (-15° to +15°)
- Places images in distributed zones for balanced composition
- Optional corner overlapping for layered effect
- Resizes all images to a consistent height for cohesion

Both layouts support:
- Optional image resizing
- Optional corner overlapping effects
- Customizable output resolution (DPI)

**Perfect for:** Memory boards, photo albums, gift prints, event posters

---

## Installation

### Prerequisites
- Python 3.7 or higher
- Pillow (PIL) library

### Setup

1. **Clone or download this repository**

2. **Create and activate virtual environment** (recommended):
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install Pillow
   ```

---

## Usage

### Photo Grid Generator

Basic usage:
```bash
python3 image_grid_cli.py photo.jpg
```

This creates `photo_grid.jpg` with 6 copies of your photo.

#### Options:
- `--edging MILLIMETERS` — Space between images (default: 0.5mm)
- `--dpi DPI` — Output resolution (default: 300 DPI for professional printing; use 600 for higher quality)

#### Examples:
```bash
# Standard passport photo grid
python3 image_grid_cli.py my_photo.jpg

# With more spacing between copies
python3 image_grid_cli.py my_photo.jpg --edging 1.0

# High resolution for premium printing
python3 image_grid_cli.py my_photo.jpg --dpi 600

# Minimal spacing
python3 image_grid_cli.py my_photo.jpg --edging 0.3
```

---

### Collage Maker

Basic usage (grid layout):
```bash
python3 collage_maker_cli.py image1.jpg image2.jpg image3.jpg
```

This creates `collage.jpg` with images in a grid.

#### Options:
- `--output FILE` or `-o FILE` — Custom output filename (default: `collage.jpg`)
- `--layout STYLE` or `-l STYLE` — Choose `grid` or `random` (default: `grid`)
- `--resize` or `-r` — Resize images to fit cells perfectly
- `--overlap` — Enable corner overlapping for artistic effect
- `--dpi DPI` — Output resolution (default: 300)

#### Examples:

**Simple 3×3 grid from 9 photos:**
```bash
python3 collage_maker_cli.py photo1.jpg photo2.jpg photo3.jpg photo4.jpg photo5.jpg photo6.jpg photo7.jpg photo8.jpg photo9.jpg
```

**Random artistic layout with overlapping:**
```bash
python3 collage_maker_cli.py *.jpg --layout random --overlap
```

**Grid with resizing and custom output:**
```bash
python3 collage_maker_cli.py img*.jpg --layout grid --resize --output my_collage.jpg
```

**High-resolution random collage:**
```bash
python3 collage_maker_cli.py vacation_*.jpg --layout random --resize --overlap --dpi 600
```

**All options combined:**
```bash
python3 collage_maker_cli.py *.jpg --output memory_board.jpg --layout random --resize --overlap --dpi 600
```

---

## Output Specifications

### Photo Grid Output
- **Size:** 4" × 6" (standard photo print size)
- **Default Resolution:** 300 DPI (professional quality)
- **Content:** 6 copies of input image + cutting guides
- **Format:** JPEG (quality 95)
- **Background:** White
- **Filename:** `{original_filename}_grid.jpg`

### Collage Output
- **Size:** 8" × 11" (US letter dimensions)
- **Default Resolution:** 300 DPI (professional quality)
- **Format:** JPEG (quality 95)
- **Background:** White
- **Filename:** `collage.jpg` (or custom via `--output`)

**Print recommendations:**
- 300 DPI: Standard photo printing
- 600 DPI: Premium/gallery quality printing (larger file size)

---

## Tips & Best Practices

### For Photo Grids
- **Face alignment:** Make sure the subject is centered in the frame for best crop results
- **Cutting guides:** The black lines mark where to cut for 2"×2" photos
- **Photo quality:** Use high-resolution source images (at least 2000×2000px recommended)
- **Printing:** Use photo paper for best results; specify 4"×6" size when sending to printer

### For Collages
- **Grid vs. Random:** Grid is cleaner/more formal; Random is more playful/artistic
- **Resizing images:** Use `--resize` if your images have very different sizes
- **Image count:** Any number works (layout automatically calculates optimal grid)
- **Odd counts:** With 7-8 images, you might get 2×4 or 2×3+1 layouts
- **Overlapping:** Use `--overlap` for visual interest but be aware it may hide parts of images
- **Memory boards:** Use `--layout random --overlap --dpi 600` for scrapbook-style results

### Image Quality
- Use high-resolution source images (at least 1500px width/height)
- JPEG, PNG, and other common formats supported
- Images with transparency (PNG) will be converted to RGB on white background

---

## Examples

### Example 1: Simple Passport Photos
```bash
# Create a sheet of 6 passport photos
python3 image_grid_cli.py passport_photo.jpg --dpi 600

# Print at 4"×6" size
```

### Example 2: Vacation Memory Board
```bash
# Create artistic collage from trip photos
python3 collage_maker_cli.py vacation_day1_*.jpg vacation_day2_*.jpg --layout random --overlap --output vacation_memories.jpg --dpi 600
```

### Example 3: Event Photo Album
```bash
# Grid layout for wedding or party photos
python3 collage_maker_cli.py event_photo_*.jpg --layout grid --resize --output event_collage.jpg
```

### Example 4: Scrapbooking
```bash
# Artistic layout with rotation and overlapping
python3 collage_maker_cli.py *.jpg --layout random --resize --overlap --dpi 300
```

---

## Troubleshooting

**"No valid images to process"**
- Check that image files exist and paths are correct
- Try using absolute paths: `/full/path/to/image.jpg`
- Supported formats: JPEG, PNG, BMP, GIF, and most common image formats

**Images look pixelated or low quality**
- Increase DPI: use `--dpi 600` for higher resolution
- Use higher-resolution source images
- Note: Higher DPI = larger file size

**Collage looks distorted**
- Try using `--resize` to normalize image sizes
- All images should ideally have similar aspect ratios for grid layout
- Random layout handles mixed aspect ratios better

**Output file not found**
- Check current directory for `collage.jpg` or `{filename}_grid.jpg`
- Use `--output` to specify full path: `--output /full/path/output.jpg`

---

## File Format Support

**Input:** JPEG, PNG, BMP, GIF, TIFF, and most common image formats
**Output:** JPEG (quality 95, optimized for printing)

---

## License & Attribution

This project creates professional photo layouts using Python and the Pillow imaging library.

---

## Questions or Issues?

Check that:
1. Python 3.7+ is installed: `python3 --version`
2. Pillow is installed: `python3 -c "from PIL import Image; print('OK')"`
3. Image files exist and are readable
4. You have write permission in the output directory
