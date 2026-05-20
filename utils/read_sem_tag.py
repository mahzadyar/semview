"""Utility to read and decode FEI/SEM custom TIFF tag (FEI_HELIOS, code 34682).

Usage:
    python utils/read_sem_tag.py sample/sample2.tif

Functions:
    read_fei_helios_tag(path) -> decoded value or None
    print_fei_helios(path) -> prints decoded value
"""
from typing import Any, Optional
import json

try:
    import tifffile
except Exception as e:
    raise ImportError("tifffile is required: pip install tifffile") from e


TAG_CODE = 34682
TAG_NAME = "FEI_HELIOS"


def _find_tag(page) -> Optional[object]:
    tag = page.tags.get(TAG_CODE)
    if tag is not None:
        return tag
    # fallback: search by name
    for t in page.tags.values():
        if getattr(t, "name", None) == TAG_NAME:
            return t
    return None


def _decode_value(value: Any) -> Any:
    # handle numpy scalars/arrays (converted to Python types by tifffile often)
    try:
        import numpy as _np
    except Exception:
        _np = None

    if _np is not None and isinstance(value, _np.generic):
        try:
            return value.item()
        except Exception:
            pass

    # bytes -> try decode UTF-8 and JSON
    if isinstance(value, (bytes, bytearray)):
        s = value.decode("utf-8", errors="replace").rstrip("\x00")
        try:
            return json.loads(s)
        except Exception:
            return s

    # str -> maybe JSON
    if isinstance(value, str):
        value = value.rstrip("\x00")
        try:
            return json.loads(value)
        except Exception:
            return value

    return value


def read_fei_helios_tag(tif_path: str) -> Optional[Any]:
    """Return decoded FEI_HELIOS tag value or None if absent."""
    with tifffile.TiffFile(tif_path) as tif:
        page = tif.pages[0]
        tag = _find_tag(page)
        if tag is None:
            return None
            
        val = tag.value
        
        # If tifffile parses the string format unpredictably and returns an empty dict,
        # or if we want to ensure we get the raw string/JSON from modified files:
        if val == {}:
            # Read the raw bytes directly from the TIFF file because tifffile's
            # internal FEI_HELIOS decoder failed to parse the JSON string and returned {}.
            fh = tif.filehandle
            fh.seek(tag.valueoffset)
            raw_bytes = fh.read(tag.valuebytecount)
            return _decode_value(raw_bytes)
            
        return _decode_value(val)


def print_fei_helios(tif_path: str) -> None:
    """Print the decoded FEI_HELIOS tag for a file."""
    data = read_fei_helios_tag(tif_path)
    import pprint

    pprint.pprint(data)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python utils/read_sem_tag.py <tif_path> [more_paths...]")
        raise SystemExit(1)

    for path in sys.argv[1:]:
        print("File:", path)
        try:
            print_fei_helios(path)
        except Exception as exc:
            print("Error reading tag:", exc)
