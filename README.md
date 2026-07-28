# Passport Photos & Photo Collages

Python tools for creating photo layouts and collages ready for printing, usable
three ways: as command-line tools, as an importable library, or as an **MCP
server** that exposes the same capabilities to AI assistants.

## Features

### 🖼️ Photo Grid Generator (`image_grid_cli.py`)
Creates a **4"×6" sheet** containing **6 identical copies** of a single photo arranged in a 3×2 grid — ideal for passport photo printing or photo booth strips.

- Automatically crops any image to square (1:1 aspect ratio)
- Includes cutting guides (black lines) for easy trimming
- Configurable edge spacing
- Professional-quality output at adjustable DPI
- White background

**Perfect for:** Passport photos, ID photos, small gift prints

> **Photo size and edging.** Six 2"×2" photos fill a 4"×6" sheet *exactly*, so
> there is no spare room on the sheet. Any non-zero `--edging` therefore comes
> out of the photos, making each one slightly smaller than 2"×2" (0.5mm edging
> gives 1.967"). Use `--edging 0` when the photos must be exactly 2"×2", as US
> passport photos require. The tool always reports the size it actually used.

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

3. **Install the package** (gives you the CLIs, the library, and the MCP server):
   ```bash
   pip install -e .
   ```

   For the CLI tools alone, `pip install Pillow` is enough.

---

## MCP Server

The same capabilities are exposed over the [Model Context Protocol](https://modelcontextprotocol.io),
so AI assistants can build photo sheets and collages directly.

### Tools

| Tool | What it does |
|------|--------------|
| `create_photo_grid` | 4"×6" sheet with 6 copies of one photo, with cutting guides |
| `create_collage` | 8"×11" collage from several images, grid or random layout |
| `inspect_image` | Dimensions, mode, orientation, and what a square centre-crop would remove |

Images can be passed as file paths **or** as base64 data, so it works both with
assistants that see your filesystem and with ones where you attach an image.

### Running it

```bash
image-editing-tools-mcp --base-dir ~/Pictures
```

`--base-dir` is the directory that relative paths resolve against, and reads and
writes are confined to it. It defaults to `$IMAGE_TOOLS_BASE_DIR`, or your home
directory. Set it to the narrowest directory you actually need.

The server speaks **stdio**, which every MCP client supports.

### Client configuration

Replace `/path/to/image_editing_tools` with your checkout, and point `command` at
the `image-editing-tools-mcp` executable inside your virtualenv (`venv/bin/` on
macOS and Linux, `venv\Scripts\` on Windows).

**Claude Code** — one command:

```bash
claude mcp add image-tools -- /path/to/image_editing_tools/venv/bin/image-editing-tools-mcp --base-dir ~/Pictures
```

**Claude Desktop** — `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "image-tools": {
      "command": "/path/to/image_editing_tools/venv/bin/image-editing-tools-mcp",
      "args": ["--base-dir", "/Users/you/Pictures"]
    }
  }
}
```

**Codex CLI** — `~/.codex/config.toml`:

```toml
[mcp_servers.image_tools]
command = "/path/to/image_editing_tools/venv/bin/image-editing-tools-mcp"
args = ["--base-dir", "/Users/you/Pictures"]
```

or `codex mcp add image_tools -- /path/to/venv/bin/image-editing-tools-mcp --base-dir ~/Pictures`

**Gemini CLI** — `~/.gemini/settings.json` or `.gemini/settings.json`:

```json
{
  "mcpServers": {
    "image-tools": {
      "command": "/path/to/image_editing_tools/venv/bin/image-editing-tools-mcp",
      "args": ["--base-dir", "/Users/you/Pictures"]
    }
  }
}
```

**opencode** — `opencode.json`:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "image-tools": {
      "type": "local",
      "command": [
        "/path/to/image_editing_tools/venv/bin/image-editing-tools-mcp",
        "--base-dir",
        "/Users/you/Pictures"
      ],
      "enabled": true
    }
  }
}
```

### Limits

Guards exist so a mistaken tool call cannot exhaust memory or clobber files:
DPI is capped at 600, source images at 80 megapixels, collages at 60 images per
call, and existing files are never overwritten unless `overwrite` is set.

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
- **Face alignment:** The image is centre-cropped to a square, trimming whichever dimension is longer — a portrait photo loses its top and bottom, a landscape photo its left and right. Keep the subject centred, and leave headroom in portrait shots.
- **Exact 2"×2":** Use `--edging 0`. Any other value shrinks the photos to make room for the gutter — see the note under Features.
- **Cutting guides:** The black lines mark where to cut
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

## Testing

```bash
python3 tests/test_image_tools.py
python3 tests/test_mcp_server.py
```

The first covers layout geometry and the image builders. The second launches the
MCP server over stdio and drives it as a real client, checking the tool contract,
the sandbox, and the resource guards. Both are plain Python — no test framework
required — and exit non-zero on failure.

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
