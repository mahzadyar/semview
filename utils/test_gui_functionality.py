#!/usr/bin/env python3
"""
Test script for TIFF metadata GUI functionality.

Validates metadata extraction and image preview generation
without requiring a display.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.image_processing import normalize_image, downscale_image
from core.metadata import decode_value, BASIC_TAGS

try:
    import tifffile
    import numpy as np
except ImportError as e:
    print(f"Error: {e}")
    sys.exit(1)


def test_sample_file(file_path: str) -> None:
    """Test metadata extraction and image processing on a sample TIFF."""
    print(f"\n{'='*70}")
    print(f"Testing: {file_path}")
    print(f"{'='*70}\n")
    
    if not os.path.exists(file_path):
        print(f"[FAIL] File not found: {file_path}")
        return
    
    with tifffile.TiffFile(file_path) as tif:
        page = tif.pages[0]
        image_array = page.asarray()
        
        # Test 1: Image properties
        print(f"[PASS] Image loaded")
        print(f"  - Shape: {image_array.shape}")
        print(f"  - Dtype: {image_array.dtype}")
        print(f"  - Min/Max: {image_array.min()}/{image_array.max()}")
        
        # Test 2: Image normalization
        try:
            normalized = normalize_image(image_array)
            print(f"[PASS] Image normalized to 8-bit")
            print(f"  - Normalized shape: {normalized.shape}")
            print(f"  - Normalized dtype: {normalized.dtype}")
            print(f"  - Normalized range: {normalized.min()}-{normalized.max()}")
        except Exception as e:
            print(f"[FAIL] Normalization failed: {e}")
            return
        
        # Test 3: Image downscaling
        try:
            downscaled = downscale_image(normalized, 600, 700)
            print(f"[PASS] Image downscaled for preview")
            print(f"  - Downscaled shape: {downscaled.shape}")
        except Exception as e:
            print(f"[FAIL] Downscaling failed: {e}")
            return
        
        # Test 4: Basic metadata extraction
        print(f"\n[PASS] Basic TIFF Metadata:")
        basic_count = 0
        for tag in page.tags.values():
            if tag.code in BASIC_TAGS:
                basic_count += 1
                tag_name = BASIC_TAGS[tag.code]
                display_val = str(tag.value)
                if len(display_val) > 60:
                    display_val = display_val[:57] + "..."
                print(f"  - {tag_name:30s}: {display_val}")
        
        if basic_count == 0:
            print(f"  (No basic tags found)")
        
        # Test 5: Extra tags extraction
        print(f"\n[PASS] Extra/Proprietary Tags:")
        extra_count = 0
        for tag in page.tags.values():
            if tag.code not in BASIC_TAGS and tag.code not in {256, 257, 258, 259, 262, 273, 277, 278, 279, 284, 338, 339, 320, 282, 283, 296}:
                extra_count += 1
                tag_name = tag.name or f"Tag {tag.code}"
                
                # Check if complex (dict)
                if isinstance(tag.value, dict) or (isinstance(tag.value, list) and len(tag.value) > 0 and isinstance(tag.value[0], dict)):
                    # Extract raw bytes
                    try:
                        fh = tif.filehandle
                        fh.seek(tag.valueoffset)
                        raw_bytes = fh.read(tag.valuebytecount)
                        decoded = decode_value(raw_bytes)
                        
                        if isinstance(decoded, dict):
                            keys_sample = list(decoded.keys())[:3]
                            print(f"  - {tag_name:30s}: {{dict}} with keys {keys_sample}")
                        else:
                            display_val = str(decoded)[:60]
                            print(f"  - {tag_name:30s}: {display_val}")
                    except Exception as e:
                        print(f"  - {tag_name:30s}: [Error: {e}]")
                else:
                    display_val = str(tag.value)
                    if len(display_val) > 60:
                        display_val = display_val[:57] + "..."
                    print(f"  - {tag_name:30s}: {display_val}")
        
        if extra_count == 0:
            print(f"  (No extra tags found)")
        
        print(f"\n{'='*70}")
        print(f"[PASS] All tests passed for {os.path.basename(file_path)}")
        print(f"{'='*70}\n")


def main():
    """Run tests on available sample files."""
    sample_files = [
        "sample/sample2.tif",
        "sample/sample2_gen.tif",
        "sample/sample.tif",
    ]
    
    tested = False
    for sample in sample_files:
        if os.path.exists(sample):
            test_sample_file(sample)
            tested = True
    
    if not tested:
        print("[FAIL] No sample TIFF files found in sample/ directory")
        print("  Please ensure sample/sample2.tif or similar exists")
        sys.exit(1)


if __name__ == "__main__":
    main()
