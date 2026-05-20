import numpy as np
from PIL import Image

def rgb_to_grayscale(rgb_image):
    if rgb_image.ndim == 2:
        return rgb_image

    if rgb_image.ndim == 3 and rgb_image.shape[2] in (3, 4):
        if np.array_equal(rgb_image[..., 0], rgb_image[..., 1]) and np.array_equal(rgb_image[..., 0], rgb_image[..., 2]):
            return rgb_image[..., 0].copy()
    
    original_dtype = rgb_image.dtype
    gray = (
        rgb_image[..., 0].astype(np.float64) * 0.2989 + 
        rgb_image[..., 1].astype(np.float64) * 0.5870 + 
        rgb_image[..., 2].astype(np.float64) * 0.1140
    )
    
    if np.issubdtype(original_dtype, np.integer):
        info = np.iinfo(original_dtype)
        gray = np.clip(gray, info.min, info.max)
    
    return gray.astype(original_dtype)

def has_identical_rgb_channels(image):
    if not (image.ndim == 3 and image.shape[2] in (3, 4)):
        return False
    red = image[..., 0]
    green = image[..., 1]
    blue = image[..., 2]
    return np.array_equal(red, green) and np.array_equal(red, blue)

def normalize_image(image_array: np.ndarray) -> np.ndarray:
    arr = image_array.astype(np.float32)
    if arr.ndim == 2:
        pass
    elif arr.ndim == 3 and arr.shape[2] in (3, 4):
        if arr.shape[2] == 4:
            arr = arr[:, :, :3]
        arr = 0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]
    else:
        arr = arr.reshape(arr.shape[0], -1)
    
    arr_min = arr.min()
    arr_max = arr.max()
    if arr_max > arr_min:
        arr = (arr - arr_min) / (arr_max - arr_min) * 255
    return arr.astype(np.uint8)

def downscale_image(image_array: np.ndarray, max_width: int, max_height: int) -> np.ndarray:
    h, w = image_array.shape[:2]
    scale = min(max_width / w, max_height / h, 1.0)
    if scale < 1.0:
        new_h = int(h * scale)
        new_w = int(w * scale)
        resized = Image.fromarray(image_array).resize((new_w, new_h), Image.Resampling.NEAREST)
        image_array = np.array(resized)
    return image_array
