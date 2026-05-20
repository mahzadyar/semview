import json
from typing import Optional, Any, Tuple

BASIC_TAGS = {
    256: "Image Width",
    257: "Image Length",
    258: "Bits Per Sample",
    259: "Compression",
    262: "Photometric Interpretation",
    273: "Strip Offsets",
    277: "Samples Per Pixel",
    278: "Rows Per Strip",
    279: "Strip Byte Counts",
    282: "X Resolution",
    283: "Y Resolution",
    284: "Planar Configuration",
    296: "Resolution Unit",
    254: "New Subfile Type",
    305: "Software",
    306: "DateTime",
    270: "Image Description",
}

def parse_ini(ini_string: str) -> dict:
    result = {}
    current_section = None
    for line in ini_string.split('\n'):
        line = line.strip()
        if not line or line.startswith(';'):
            continue
        if line.startswith('[') and line.endswith(']'):
            current_section = line[1:-1]
            result[current_section] = {}
        elif '=' in line and current_section:
            key, val = line.split('=', 1)
            result[current_section][key.strip()] = val.strip()
        elif '=' in line:
            key, val = line.split('=', 1)
            result[key.strip()] = val.strip()
    return result

def decode_value(value: Any) -> Any:
    try:
        import numpy as _np
    except ImportError:
        _np = None

    if _np is not None and isinstance(value, _np.generic):
        try:
            return value.item()
        except Exception:
            pass

    if isinstance(value, (bytes, bytearray)):
        s = value.decode("utf-8", errors="replace").rstrip("\x00")
        try:
            return json.loads(s)
        except Exception:
            pass
        if '[' in s and ']' in s:
            try:
                parsed = parse_ini(s)
                if parsed: return parsed
            except Exception:
                pass
        return s

    if isinstance(value, str):
        value = value.rstrip("\x00")
        try:
            return json.loads(value)
        except Exception:
            pass
        if '[' in value and ']' in value:
            try:
                parsed = parse_ini(value)
                if parsed: return parsed
            except Exception:
                pass
        return value

    return value

def _decode_fei_helios(page, tif) -> Optional[dict]:
    """Locate and decode the FEI_HELIOS tag (code 34682). Returns decoded dict or None."""
    tag = page.tags.get(34682)
    if tag is None:
        for t in page.tags.values():
            if getattr(t, "name", None) == "FEI_HELIOS":
                tag = t
                break
    if tag is None:
        return None
        
    val = tag.value
    if val == {}:
        try:
            fh = tif.filehandle
            fh.seek(tag.valueoffset)
            raw_bytes = fh.read(tag.valuebytecount)
            decoded = decode_value(raw_bytes)
        except Exception:
            return None
    else:
        decoded = decode_value(val)
        
    if isinstance(decoded, dict):
        return decoded
    return None

def get_databar_height_from_metadata(page, tif, databar_height_tag_path: str = "FEI_HELIOS / PrivateFei / DatabarHeight") -> Optional[int]:
    h = get_value_by_path(page, tif, databar_height_tag_path)
    if h is not None:
        try:
            return int(float(h))
        except (ValueError, TypeError):
            pass
            
    decoded = _decode_fei_helios(page, tif)
    if decoded is None:
        return None
    private_fei = decoded.get("PrivateFei")
    if isinstance(private_fei, dict):
        height = private_fei.get("DatabarHeight")
        if height is not None:
            try:
                return int(height)
            except ValueError:
                pass
    return None

def get_value_by_path(page, tif, target_path: str) -> Optional[Any]:
    if not target_path: 
        return None
    
    def _search_dict(data, current_path, target):
        if isinstance(data, dict):
            for k, v in data.items():
                k_text = str(k).replace("_", " ")
                new_path = f"{current_path} / {k_text}" if current_path else k_text
                
                if not isinstance(v, (dict, list, tuple)):
                    if new_path == target:
                        return v
                
                res = _search_dict(v, new_path, target)
                if res is not None:
                    return res
        elif isinstance(data, (list, tuple)):
            if data and all(isinstance(item, dict) for item in data):
                for i, item in enumerate(data):
                    new_path = f"{current_path}[{i}]" if current_path else f"[{i}]"
                    res = _search_dict(item, new_path, target)
                    if res is not None: return res
            else:
                for i, item in enumerate(data):
                    new_path = f"{current_path}[{i}]" if current_path else f"[{i}]"
                    if not isinstance(item, (dict, list, tuple)):
                        if new_path == target:
                            return item
                    res = _search_dict(item, new_path, target)
                    if res is not None: return res
        return None

    for tag in page.tags.values():
        if tag.code in BASIC_TAGS:
            continue
            
        tag_name = tag.name or f"Tag {tag.code}"
        val = tag.value
        try:
            if isinstance(val, dict) or (isinstance(val, list) and len(val) > 0 and isinstance(val[0], dict)):
                fh = tif.filehandle
                fh.seek(tag.valueoffset)
                raw_bytes = fh.read(tag.valuebytecount)
                decoded = decode_value(raw_bytes)
            else:
                decoded = decode_value(val)
        except Exception:
            continue
            
        if not isinstance(decoded, (dict, list, tuple)):
            if tag_name == target_path:
                return decoded
                
        res = _search_dict(decoded, tag_name, target_path)
        if res is not None:
            return res
            
    return None

def get_pixel_size_from_metadata(page, tif, x_tag_path: str = "FEI_HELIOS / Scan / PixelWidth", y_tag_path: str = "FEI_HELIOS / Scan / PixelHeight") -> Optional[Tuple[float, float]]:
    """Extract pixel dimensions from arbitrary metadata paths.
    
    Returns:
        (pixel_width_meters, pixel_height_meters) or None if not available.
    """
    pw = get_value_by_path(page, tif, x_tag_path)
    ph = get_value_by_path(page, tif, y_tag_path)
    
    if pw is None or ph is None:
        return None
        
    try:
        pw_f = float(pw)
        ph_f = float(ph)
        if pw_f > 0 and ph_f > 0:
            return (pw_f, ph_f)
    except (ValueError, TypeError):
        pass
    return None

