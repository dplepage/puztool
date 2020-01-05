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

def read(fname, format=None):
    if format == 'png' or (format is None and fname.endswith("png")):
        return read_png(fname)
    return np.array(Image.open(fname))

def toimg(data, norm=False, zoom=1):
    if data.dtype == bool:
        img = (data*255).astype('uint8')
    else:
        if norm:
            data = (data-data.min())*1.0/data.max()
        if data.max() < 1:
            img = (data*255).astype('uint8')
        elif data.max() < 256:
            img = data.astype('uint8')
        else:
            img = (data*255.0/data.max()).astype('uint8')
    im = Image.fromarray(img)
    if zoom != 1:
        im = im.resize((int(im.width*zoom), int(im.height*zoom)))
    return im

def show(data, norm=False):
    return toimg(data, norm).show()

def subrect(data, mask=None, pad=0):
    '''Return a sub-rectangle of data containing everywhere mask is True.'''
    if mask is None:
        mask = data
    rows, cols, *rest = np.where(mask)
    if rest:
        raise ValueError("Mask must be 2D")
    rm, rM = rows.min(), rows.max()
    cm, cM = cols.min(), cols.max()
    return data[rm-pad:rM+1+pad,cm-pad:cM+1+pad]
