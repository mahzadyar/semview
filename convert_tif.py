import sys
import os
# pyrefly: ignore [missing-import]
import numpy as np
import json

try:
    import tifffile
except ImportError:
    print("Error: The 'tifffile' library is required. Install it using: pip install tifffile")
    sys.exit(1)

def rgb_to_grayscale(rgb_image):
    """
    Converts an RGB image to single-channel grayscale using the 
    standard luminosity method (ITU-R 601-2). Preserves original bit depth.
    
    Bit Depth Preservation:
    - 8-bit RGB (0-255 per channel)  → 8-bit grayscale
    - 16-bit RGB (0-65535 per channel) → 16-bit grayscale
    - 32-bit RGB (0-4294967295 per channel) → 32-bit grayscale
    - float32/float64 → float32/float64 (preserved)
    """
    if rgb_image.ndim == 2:
        # Already grayscale
        return rgb_image

    # Debloating path: when RGB channels are identical, preserve exact values
    # by taking one channel directly instead of recomputing weighted luminance.
    if rgb_image.ndim == 3 and rgb_image.shape[2] in (3, 4):
        if np.array_equal(rgb_image[..., 0], rgb_image[..., 1]) and np.array_equal(rgb_image[..., 0], rgb_image[..., 2]):
            return rgb_image[..., 0].copy()
    
    # Fallback weighting for non-identical RGB inputs
    # Use float64 for intermediate calculations to avoid overflow/underflow
    original_dtype = rgb_image.dtype
    gray = (
        rgb_image[..., 0].astype(np.float64) * 0.2989 + 
        rgb_image[..., 1].astype(np.float64) * 0.5870 + 
        rgb_image[..., 2].astype(np.float64) * 0.1140
    )
    
    # Clip to valid range for the original dtype and convert back
    if np.issubdtype(original_dtype, np.integer):
        # For integer types, clip to the valid range
        info = np.iinfo(original_dtype)
        gray = np.clip(gray, info.min, info.max)
    
    return gray.astype(original_dtype)

def has_identical_rgb_channels(image):
    """
    Returns True when the first three channels are exactly identical.
    Supports RGB and RGBA arrays shaped (H, W, C) where C is 3 or 4.
    """
    if not (image.ndim == 3 and image.shape[2] in (3, 4)):
        return False

    red = image[..., 0]
    green = image[..., 1]
    blue = image[..., 2]
    return np.array_equal(red, green) and np.array_equal(red, blue)

def convert_and_compress(input_path, output_path, compression='zlib'):
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
        
        # Only process RGB images (3 or 4 channels). Skip grayscale or other formats.
        if not (image.ndim == 3 and image.shape[2] in (3, 4)):
            print(f"Skipping non-RGB TIFF: {input_path} (shape={image.shape})")
            return {'success': False, 'skipped': True, 'reason': f'Non-RGB format (shape={image.shape})'}

        # Convert only "grayscale-in-RGB" images where R, G, and B are identical.
        if not has_identical_rgb_channels(image):
            print(f"Skipping RGB TIFF with non-identical channels: {input_path}")
            return {'success': False, 'skipped': True, 'reason': 'RGB channels are not identical'}

        # Convert RGB to grayscale
        gray_image = rgb_to_grayscale(image)
        
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
                    # tag.value might be complex for some nested tags, 
                    # but standard/custom values are usually fine.
                    extratags.append((tag.code, tag.dtype, tag.count, tag.value))
                except Exception as e:
                    print(f"Warning: Could not copy tag {tag.name} (Code: {tag.code}): {e}")

        # Ensure resolution tuple is completely built if partially present
        if resolution and None in resolution:
            resolution = (resolution[0] or 1, resolution[1] or 1)
            
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
        
        print(f"Writing: {output_path} (Grayscale, {comp_str})")
        # Sanitize extratags: convert numpy types and JSON-serialize complex values
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

            # If value is a dict or a nested non-primitive sequence, JSON-serialize it
            need_json = False
            if isinstance(v, dict):
                need_json = True
            elif isinstance(v, (list, tuple)):
                def _is_primitive(x):
                    return isinstance(x, (str, bytes, bytearray, int, float))
                if not all(_is_primitive(x) for x in v):
                    need_json = True

            if need_json:
                try:
                    j = json.dumps(v, ensure_ascii=False)
                    vb = j.encode('utf-8')
                    v = vb
                    dtype = 's'
                    count = len(v)
                except Exception as e:
                    print(f"Warning: could not serialize tag {code}: {e}")
                    continue

            # If the tag value is a Python str, convert to bytes (TIFF expects str/bytes)
            if isinstance(v, str):
                v = v.encode('utf-8')
                dtype = 's'
                count = len(v)

            sanitized_extratags.append((code, dtype, count, v))
        # Write with specified compression method
        tifffile.imwrite(
            output_path,
            gray_image,
            photometric='minisblack',
            compression=compression_value,
            resolution=resolution,
            resolutionunit=resolutionunit,
            extratags=sanitized_extratags
        )
        
    print("Done!")
    return {'success': True, 'skipped': False, 'reason': None}

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python convert_tif.py <input.tif> <output.tif>")
        print("Example: python convert_tif.py sem_image_uncompressed.tif sem_image_compressed.tif")
        sys.exit(1)
        
    in_file = sys.argv[1]
    out_file = sys.argv[2]
    
    result = convert_and_compress(in_file, out_file)
    sys.exit(0 if result['success'] else 1)
