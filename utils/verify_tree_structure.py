"""Verify tree structure for GUI display."""

import sys
import os
# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.metadata import decode_value
import tifffile


def print_tree(data, indent=0, max_items=5):
    """Print tree structure (simulating the GUI tree view)."""
    prefix = '  ' * indent
    if isinstance(data, dict):
        items = list(data.items())
        for key, value in items[:max_items]:
            if isinstance(value, dict):
                print(f'{prefix}[+] {key}/')
                print_tree(value, indent + 1, max_items=3)
            elif isinstance(value, (list, tuple)):
                print(f'{prefix}    {key}: [{len(value)} items]')
            else:
                display_val = str(value)
                if len(display_val) > 50:
                    display_val = display_val[:47] + "..."
                print(f'{prefix}    {key}: {display_val}')
        if len(items) > max_items:
            print(f'{prefix}    ... and {len(items)-max_items} more items')


# Load and decode FEI_HELIOS
with tifffile.TiffFile('sample/sample2.tif') as tif:
    page = tif.pages[0]
    tag = page.tags[34682]
    fh = tif.filehandle
    fh.seek(tag.valueoffset)
    raw_bytes = fh.read(tag.valuebytecount)
    decoded = decode_value(raw_bytes)

print('\nGUI Extra Tags Tree View:')
print('=' * 70)
print('[+] FEI_HELIOS/')
if isinstance(decoded, dict):
    print_tree(decoded)
else:
    print(f"ERROR: Not a dict, got {type(decoded).__name__}")
print('=' * 70)
