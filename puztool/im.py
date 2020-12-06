import io
import os
import numpy as np
from PIL import Image
import imageio

# This is convenient because it means scipy.misc.imshow will work
os.environ.setdefault('SCIPY_PIL_IMAGE_VIEWER', 'open -W')

def _read_png(fname):
    '''Read a PNG into a numpy array.

    See https://github.com/imageio/imageio/issues/352
    '''
    return imageio.imread(fname, format="PNG-FI")

def _info(data):
    h, w, *d = data.shape
    if len(d) > 1:
        raise Exception("Image has too many dimensions?")
    try:
        depth = data.dtype.itemsize*8
        if not d or d[0] == 1:
            mode = 'grayscale'
        elif d[0] == 3:
            mode = 'RGB'
        elif d[0] == 4:
            mode = 'RGBA'
        else:
            mode = f'{d[0]}-channel'
        if not d:
            shape = f'{h}x{w}'
        else:
            shape = f'{h}x{w}x{d[0]}'
        print(f"{w}x{h} {depth}-bit {mode} image (array is {shape})")
    except Exception as e:
        print(f"Failed info for image: {e}")
    return data

def read(fname, fmt=None, dtype=None):
    if fmt == 'png' or (fmt is None and fname.endswith("png")):
        data = _read_png(fname)
    else:
        data = imageio.imread(fname)
    if dtype is not None:
        dtype = np.dtype(dtype)
        if dtype.kind == 'b':
            data = (data > 0).astype(dtype)
        elif dtype.kind in 'fc' and data.dtype.kind in 'iu':
            data = normalize(data)
    return _info(data)

def normalize(data):
    '''Rescale data to [0,1].

    The result is always floating-point
    '''
    m, M = data.min(), data.max()
    if m == M:
        print("Warning: normalizing uniform data")
        return np.ones(data.shape)
    return ((data*1.0)-m)/(M-m)

norm = normalize

def parse(byts):
    if isinstance(byts, np.ndarray):
        byts = byts.tobytes()
    return _info(imageio.imread(io.BytesIO(byts)))

def paste():
    try:
        return _info(imageio.imread("<clipboard>"))
    except RuntimeError as e:
        print(f"Error: {e}")
        return None

def disp(data, norm=False, zoom='auto'):
    if data.dtype == bool:
        data = (data*255).astype('uint8')
    else:
        if norm:
            data = normalize(data)
        if data.max() <= 1:
            data = (data*255).astype('uint8')
        elif data.max() < 256:
            data = data.astype('uint8')
        else:
            data = (data*255.0/data.max()).astype('uint8')
    img = Image.fromarray(data)
    if zoom == 'auto':
        w, h = img.width, img.height
        wscale = 700/img.width
        hscale = 500/img.height
        zoom = min(wscale, hscale)
    if zoom != 1:
        neww, newh = int(img.width*zoom), int(img.height*zoom)
        print(f"Scaled {img.width}x{img.height} img to {neww}x{newh}")
        img = img.resize((neww, newh), Image.NEAREST)
    return img

# def ndisp(data, zoom=1):
# TODO: remember what this function was going to be?

def show(data, norm=False):
    return disp(data, norm).show()
