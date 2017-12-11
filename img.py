import os
import numpy as np
import png
from PIL import Image

# This is convenient because it means scipy.misc.imshow will work
os.environ.setdefault('SCIPY_PIL_IMAGE_VIEWER', 'open -W')

def read_png(fname):
    '''Read a PNG into a numpy array.

    PIL can't handle multichannel images with >8 bits, so Image.load(), and thus
    scipy.misc.imread or imageio.imread, silently truncate the extra bits.

    This function, on the other hand, will correctly read a 16-bit png.
    '''
    w, h, data, info = png.Reader(fname).read()
    data = np.array(list(data))
    return data.reshape(h, w, info['planes'])

def imread(fname, format=None):
    if format == 'png' or (format is None and fname.endswith("png")):
        return read_png(fname)
    return np.array(Image.open(fname))

def imshow(data, norm=False):
    if data.dtype == bool:
        img = (data*255).astype('uint8')
    else:
        if norm:
            data = data*1.0/data.max()
        if data.max() < 1:
            img = (data*255).astype('uint8')
        elif data.max() < 256:
            img = data.astype('uint8')
        else:
            img = (data*255.0/data.max()).astype('uint8')
    return Image.fromarray(img).show()

