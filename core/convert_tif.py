import sys
import os

# Add parent directory to path so core package can be imported when running directly
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# pyrefly: ignore [missing-import]
import numpy as np
import json
from typing import Optional, Any

from core.metadata import get_databar_height_from_metadata, get_pixel_size_from_metadata
from core.image_processing import rgb_to_grayscale, has_identical_rgb_channels

try:
    import tifffile
except ImportError:
    print("Error: The 'tifffile' library is required. Install it using: pip install tifffile")
    sys.exit(1)



def convert_and_compress(
    input_path: str,
    output_path: str,
    compression: str = 'zlib',
    rgb_to_grayscale_enabled: bool = True,
    bit_depth: str = 'original',
    crop_databar: bool = False,
    databar_position: str = 'bottom',
    databar_height_mode: str = 'auto',
    databar_height_manual: int = 119,
    update_resolution: bool = True,
    x_res_tag_path: str = "FEI_HELIOS / Scan / PixelWidth",
    y_res_tag_path: str = "FEI_HELIOS / Scan / PixelHeight",
    databar_height_tag_path: str = "FEI_HELIOS / PrivateFei / DatabarHeight"
) -> dict:
    """
    Reads a TIFF, converts it to grayscale, and saves it with specified compression,
    while preserving all custom metadata tags (useful for SEM devices).
    
    Bit Depth Preservation:
    - Input: 8-bit RGB (24-bit) → Output: 8-bit grayscale
    - Input: 16-bit RGB (48-bit) → Output: 16-bit grayscale
    - Input: 32-bit RGB (96-bit) → Output: 32-bit grayscale
    - Input: float RGB → Output: float grayscale
    
    Args:
        input_path: Path to input TIFF file
        output_path: Path to output TIFF file
        compression: Compression method ('none', 'zlib', 'lzw', or None for no compression)
        rgb_to_grayscale_enabled: Skip grayscale conversion for non-identical RGB, else convert to grayscale
        bit_depth: 'original' or '8-bit'
        crop_databar: Crop off the databar from the image
        databar_position: Position of databar ('top' or 'bottom')
        databar_height_mode: Mode to determine height ('auto' or 'manual')
        databar_height_manual: Manual height of databar in pixels
        update_resolution: Compute correct XResolution/YResolution from SEM pixel size metadata
    
    Returns:
        dict: {'success': bool, 'skipped': bool, 'reason': str or None}
    """
    if not os.path.exists(input_path):
        print(f"Error: Input file '{input_path}' not found.")
        return {'success': False, 'skipped': False, 'reason': 'File not found'}

    print(f"Reading: {input_path}")
    
    with tifffile.TiffFile(input_path) as tif:
        image = tif.asarray()
        page = tif.pages[0]
        
        # Determine image type and whether grayscale conversion applies
        is_rgb = image.ndim == 3 and image.shape[2] in (3, 4)
        do_grayscale_conversion = False
        
        if is_rgb and rgb_to_grayscale_enabled:
            if not has_identical_rgb_channels(image):
                print(f"Skipping grayscale conversion: RGB channels are not identical (keeping as RGB)")
            else:
                do_grayscale_conversion = True
        elif not is_rgb:
            print(f"Already grayscale (shape={image.shape}), skipping grayscale conversion")

        # Crop databar if requested
        if crop_databar:
            H = image.shape[0]
            h_crop = None
            if databar_height_mode == 'auto':
                h_crop = get_databar_height_from_metadata(page, tif, databar_height_tag_path)
                if h_crop is None:
                    h_crop = databar_height_manual
                    print(f"Warning: Could not fetch DatabarHeight from metadata, falling back to manual height: {h_crop}px")
            else:
                h_crop = databar_height_manual
            
            if h_crop and 0 < h_crop < H:
                if databar_position == 'bottom':
                    image = image[:-h_crop, ...]
                elif databar_position == 'top':
                    image = image[h_crop:, ...]
                print(f"Cropped {h_crop}px off the {databar_position} (New shape: {image.shape})")
            else:
                print(f"Warning: Crop skipped (invalid or too large height: {h_crop}px, image height: {H}px)")

        # Apply grayscale conversion if applicable
        if do_grayscale_conversion:
            write_image = rgb_to_grayscale(image)
            photometric_interp = 'minisblack'
        elif is_rgb:
            write_image = image
            photometric_interp = 'rgb'
        else:
            # Already grayscale
            write_image = image
            photometric_interp = 'minisblack'
            
        # Apply bit depth downsampling if requested
        if bit_depth == '8-bit' and write_image.dtype != np.uint8:
            print(f"Downsampling to 8-bit from {write_image.dtype}")
            arr = write_image.astype(np.float32)
            arr_min, arr_max = arr.min(), arr.max()
            if arr_max > arr_min:
                write_image = ((arr - arr_min) / (arr_max - arr_min) * 255.0).astype(np.uint8)
            else:
                write_image = arr.astype(np.uint8)
        
        # tifffile.imwrite automatically populates layout and format tags
        # (like width, height, planar configuration, etc.) based on the numpy array.
        # If we try to manually pass these via extratags, it will cause an error.
        # We explicitly ignore these core geometric/structural tags.
        ignore_tags = {
            256,  # ImageWidth
            257,  # ImageLength
            258,  # BitsPerSample
            259,  # Compression
            262,  # PhotometricInterpretation
            273,  # StripOffsets
            277,  # SamplesPerPixel
            278,  # RowsPerStrip
            279,  # StripByteCounts
            284,  # PlanarConfiguration
            338,  # ExtraSamples
            339,  # SampleFormat
            320,  # ColorMap
        }
        
        # Extract metadata and tags to preserve
        extratags = []
        resolution = None
        resolutionunit = None
        
        for tag in page.tags.values():
            if tag.code == 282: # XResolution
                resolution = (tag.value, resolution[1]) if resolution else (tag.value, 1)
            elif tag.code == 283: # YResolution
                resolution = (resolution[0], tag.value) if resolution else (1, tag.value)
            elif tag.code == 296: # ResolutionUnit
                resolutionunit = tag.value
            elif tag.code not in ignore_tags:
                try:
                    # If tifffile parsed the tag into a complex structure (like a dict or list of dicts),
                    # it means it's a known proprietary custom tag (like FEI_HELIOS).
                    # Bypass the decoder and extract the exact original raw bytes to preserve it perfectly.
                    if isinstance(tag.value, dict) or (isinstance(tag.value, list) and len(tag.value) > 0 and isinstance(tag.value[0], dict)):
                        fh = tif.filehandle
                        fh.seek(tag.valueoffset)
                        raw_bytes = fh.read(tag.valuebytecount)
                        extratags.append((tag.code, 's', len(raw_bytes), raw_bytes))
                    else:
                        extratags.append((tag.code, tag.dtype, tag.count, tag.value))
                except Exception as e:
                    print(f"Warning: Could not copy tag {tag.name} (Code: {tag.code}): {e}")

        # Ensure resolution tuple is completely built if partially present
        if resolution and None in resolution:
            resolution = (resolution[0] or 1, resolution[1] or 1)
        
        # Override resolution from SEM pixel size metadata if requested
        if update_resolution:
            pixel_size = get_pixel_size_from_metadata(page, tif, x_res_tag_path, y_res_tag_path)
            if pixel_size is not None:
                pw_m, ph_m = pixel_size
                # Convert meters to pixels/cm: pixels_per_cm = 1 / (pixel_size_m * 100)
                x_res = 1.0 / (pw_m * 100.0)
                y_res = 1.0 / (ph_m * 100.0)
                old_res_str = f"{resolution}" if resolution else "(none)"
                resolution = (x_res, y_res)
                resolutionunit = 3  # centimeters
                print(f"Updated resolution from {old_res_str} to ({x_res:,.2f}, {y_res:,.2f}) pixels/cm")
                print(f"  Pixel size: {pw_m*1e9:.4f} x {ph_m*1e9:.4f} nm")
            else:
                print("Warning: Update Resolution enabled but no SEM pixel size metadata found, keeping original resolution")
            
        # Map compression type
        if compression == 'none':
            compression_value = None
            comp_str = "uncompressed"
        elif compression == 'lzw':
            compression_value = 'lzw'
            comp_str = "LZW compressed"
        elif compression == 'zlib':
            compression_value = 'zlib'
            comp_str = "ZIP compressed"
        else:
            compression_value = 'zlib'
            comp_str = "ZIP compressed"
        
        color_str = 'Grayscale' if do_grayscale_conversion else ('RGB' if is_rgb else 'Grayscale (unchanged)')
        print(f"Writing: {output_path} ({color_str}, {comp_str})")
        # Sanitize extratags: convert numpy types and strings
        sanitized_extratags = []
        for code, dtype, count, value in extratags:
            v = value
            # Convert numpy scalars/arrays to native Python types when possible
            try:
                import numpy as _np
                if isinstance(v, _np.generic):
                    v = v.item()
                elif isinstance(v, _np.ndarray):
                    v = v.tolist()
            except Exception:
                pass

            # If the tag value is a Python str, convert to bytes (TIFF expects str/bytes)
            if isinstance(v, str):
                v = v.encode('utf-8')
                dtype = 's'
                count = len(v)

            sanitized_extratags.append((code, dtype, count, v))
        # Write with specified compression method
        tifffile.imwrite(
            output_path,
            write_image,
            photometric=photometric_interp,
            compression=compression_value,
            resolution=resolution,
            resolutionunit=resolutionunit,
            extratags=sanitized_extratags
        )
        
    print("Done!")
    return {'success': True, 'skipped': False, 'reason': None}

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python core/convert_tif.py <input.tif> <output.tif>")
        print("Example: python core/convert_tif.py sem_image_uncompressed.tif sem_image_compressed.tif")
        sys.exit(1)
        
    in_file = sys.argv[1]
    out_file = sys.argv[2]
    
    result = convert_and_compress(in_file, out_file)
    sys.exit(0 if result['success'] else 1)
