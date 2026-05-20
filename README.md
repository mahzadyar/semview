# SEMView - Scientific TIFF Explorer & Optimizer

**Release:** v2.0.0 — 2026-05-20

A cross-platform GUI application designed as an all-in-one studio for analyzing, viewing, and optimizing scientific TIFF images (specifically tailored for SEM devices). It serves as both a hierarchical metadata viewer and a powerful batch-processing optimizer, seamlessly converting oversized RGB-encoded grayscale files back to optimized single-channel TIFFs without losing structural or proprietary scientific metadata.

## What's New in v2.0.0
- **Unified Interface:** The metadata viewer and the batch converter have been fully merged into one cohesive interface.
- **Conversion Toggles:** You can now optionally bypass grayscale conversion or choose not to skip colored images.
- **Interactive File Browser:** Select a single file to view its preview and metadata, or select a folder to batch convert its entire contents.
- **8-Bit Downsampling:** Convert high bit-depth files (e.g. 16-bit) to normalized 8-bit grayscale for optimization and compatibility.
- **Customizable Pixel Sizes:** Directly map any metadata row (such as custom pixel size keys) as `PixelSizeX` or `PixelSizeY` using a context menu in the Extra Tags table.

## Features

- **Unified Studio Interface**: 
  - **File Browser**: Expandable directory tree to preview files instantly.
  - **Image Preview**: Dynamic live-scale image viewer that handles multiple bit-depths.
  - **Metadata Explorer**: Tabbed table views showing both standard tags and nested proprietary tags (e.g. FEI_HELIOS SEM metadata).
- **Core Conversion Engine**:
  - **TIFF Optimization**: Converts bloated 3-channel RGB storing purely grayscale data into single-channel grayscale TIFFs.
  - **Compression Choices**: ZIP (Deflate, recommended), LZW, or Uncompressed.
  - **Configurable Filters**: Checkboxes allowing you to skip naturally colored RGB images or force grayscale math across any image.
- **Batch Processing**:
  - Convert selected files or process entire directory trees recursively directly from the internal file browser.
  - See real-time progress bars, skip logs, and cancel ongoing intensive conversions anytime.
- **Metadata Protection**: 
  - Preserves resolution strings and actively bypasses decoding on complex proprietary tags to re-inject raw byte data, guaranteeing preservation for scientific instruments.

## Installation

### Option 1: Standalone Executable (Windows & Linux)
You can download the pre-built executables from the [Releases](../../releases) page:
- `SEMView` for Linux or `SEMView.exe` for Windows.
- Simply run the executable directly. No Python needed!

### Option 2: Python Installation

**Prerequisites**:
- Python 3.7+

**Setup**:
1. Clone or download the repository.
2. (Optional) Create a virtual environment:
   ```bash
   python -m venv .venv
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

**Launch the application:**
```bash
python gui.py
```

### GUI Workflow

1. **Browse**: Use the File Browser pane on the left to navigate your filesystem.
2. **Inspect**: Click on any `.tif` or `.tiff` file. 
   - The preview window will render the image securely irrespective of bit-depth.
   - The Metadata tabs on the right will parse standard image logic and nested INI/JSON device parameters.
3. **Configure Options**:
   - **Output Mode**: Choose to Add a Suffix, dump copies to a new Output Folder, or strictly Replace Original Files.
   - **Compression**: Select ZIP (default), LZW, or No Compression.
   - **Skip Color Images**: Keep this checked to avoid destroying RGB data if a multi-color image is accidentally fed in.
   - **Force RGB to Grayscale**: Keep this checked to convert images mathematically to a single channel.
4. **Convert**:
   - Highlighting a **file** and clicking "Convert Selected" processes that standalone file.
   - Highlighting a **folder** and clicking "Convert Selected" batch-converts all TIFFs inside that folder recursively.
5. **Logs**: Check the bottom log screen tracking skipped files, errors, and successful completions.

## Command Line Usage

For scripting, you can call the engine directly from the command line:

```bash
python core/convert_tif.py input.tif output.tif
```

Advanced batch processing scripts can be crafted by looping this base call.

## Troubleshooting

- **Module Not Found**: Ensure you installed `tifffile`, `numpy`, and `pillow` using `pip install -r requirements.txt`.
- **Files Skipped During Batch**: By default, the app skips purely 2D grayscale arrays (already optimized) and mismatching RGB colorful arrays. Check the log if you expected them to be processed (or uncheck "Skip Color Images").
- **Missing Tags**: Some basic core tags (like `ImageWidth`) inherently change when images undergo matrix processing. The tool intelligently filters them to allow `tifffile` to rebuild them safely while forcefully passing complex scientific tags untouched.
