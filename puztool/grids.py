from typing import Tuple
import attr
import numpy as np
import funcy as fn

from .result import Result, ProvEntry
from .pipeline import source


def Fail(*a, **kw):
    raise NotImplementedError()

class Rotator:
    def __init__(self, vflip_char=None, hflip_char=None, cw_char=None):
        self.vflip_char = np.vectorize(vflip_char) if vflip_char else Fail
        self.hflip_char = np.vectorize(hflip_char) if hflip_char else Fail
        self.cw_char = np.vectorize(cw_char) if cw_char else Fail

    def hflip(self, mat):
        return self.hflip_char(hflip(mat))

    def vflip(self, mat):
        return self.vflip_char(vflip(mat))

    def cw(self, mat, n=1):
        n = n % 4
        for _ in range(n):
            mat = self.cw_char(mat)
        return cw(mat, n)

    def ccw(self, mat, n=1):
        return self.cw(mat, n * 3)

    def r180(self, mat):
        return self.cw(mat, 2)


def hflip(mat):
    '''Flip a matrix horizontally.

    The returned value is a view of the original.
    '''
    return np.flip(mat, 1)


def vflip(mat):
    '''Flip a matrix vertically.

    The returned value is a view of the original.
    '''
    return np.flip(mat, 0)


def cw(mat, n=1):
    '''Rotate a matrix 90 degrees clockwise n times.'''
    return np.rot90(mat, 3 * n)


def ccw(mat, n=1):
    '''Rotate a matrix 90 degrees counter-clockwise n times.'''
    return np.rot90(mat, n)


def r180(mat):
    return np.rot90(mat, 2)


def asdir(mat, edge):
    '''Returns a view of mat as though the specified edge were on the left.

    * If edge is 'l' or 'w', the matrix is unchanged.
    * If edge is 'r' or 'e', the matrix is flipped horizontally
    * If edge is 'd' or 's', the matrix is rotated clockwise (so the leftmost
      item from the bottom edge is now the topmost item on the left edge)
    * If edge is 'u' or 'n', the matrix is flipped and rotated so that the top
      row (left to right) moves to the left row (top to bottom)
    '''
    edge = edge.lower()
    if edge in 'lw':
        return mat
    if edge in 're':
        return hflip(mat)
    if edge in 'ds':
        return cw(mat)
    if edge in 'un':
        return hflip(cw(mat))
    raise ValueError(f"Edge {edge} not in LRDU/WESN")


def fall(mat, row, d='l', empty=''):
    target = asdir(mat, d)
    w = target.shape[1]
    items = [item for item in target[row, :] if item != empty]
    target[row, :] = items + [empty] * (w - len(items))



def subrect(data, mask=None, pad=0):
    '''Return a sub-rectangle of data containing everywhere mask is True.

    If mask is None, data will be used, but must then be 2D.
    If pad is True
    '''
    if mask is None:
        mask = data
    rows, cols, *rest = np.where(mask)
    if rest:
        raise ValueError("Mask must be 2D")
    rm, rM = max(rows.min()-pad, 0), rows.max()+pad+1
    cm, cM = max(cols.min()-pad, 0), cols.max()+pad+1
    return data[rm:rM, cm:cM]


@attr.s(auto_attribs=True)
class FromGrid(ProvEntry):
    '''Represents a range of points on a grid'''
    start: Tuple[int, int]
    end: Tuple[int, int]

    def __str__(self):
        return f"{self.start}->{self.end}"

    def __iter__(self):
        yield from (self.start, self.end)

    @fn.collecting
    def indices(self):
        s = np.array(self.start)
        e = np.array(self.end)
        d = abs(e-s).max()
        delta = (e-s)//d
        for i in range(d+1):
            yield tuple(s+i*delta)


class _DIRS:
    l = left = w = west = np.array([0,-1])
    r = right = e = east = np.array([0, 1])
    u = up = n = north = np.array([-1, 0])
    d = down = s = south = np.array([1, 0])
    ul = upleft = nw = northwest = u+l
    ur = upright = ne = northeast = u+r
    dl = downleft = sw = southwest = d+l
    dr = downright = se = southeast = d+r
    h = hor = horizontals = (l, r)
    v = ver = verticals = (u, d)
    di = diagonals = (ul, ur, dl, dr)
    o = ortho = h+v
    a = all = ortho + diagonals

    def __getitem__(self, key):
        return getattr(self, key)

directions = DIRS = _DIRS()

def parse_dirs(dirs):
    '''
    Generate a set of directions from a string.

    dirs can be a list of tuples, or a comma-separated list of letters
    recognized by parse_dirs. For example, 'r,d' will map to left-to-right and
    top-bottom, while 'h, sw, ne', will map to left-to-right, right-to-left,
    upper-right-to-lower-left, and lower-left-to-lower-right.

    >>> parse_dirs("r, u")
    [array([0, 1]), array([-1,  0])]
    >>> parse_dirs(["diagonals", np.array([3,3])])
    [(array([-1, -1]), array([-1,  1]), array([ 1, -1]), array([1, 1])), array([3, 3])]
    '''
    if isinstance(dirs, str):
        dirs = [d.strip() for d in dirs.split(",")]
    chosen = []
    for d in dirs:
        if isinstance(d, str):
            choice = directions[d.lower()]
        else:
            choice = d
        if isinstance(choice, list):
            chosen.extend(choice)
        else:
            chosen.append(choice)
    return chosen

@source
def iter_seqs(grid, len=(3,None), dirs=directions.all, wrap=False):
    '''Emit all sequences of letters in grid.

    dirs can be a list of tuples, or a comma-separated list of letters
    recognized by parse_dirs. For example, 'r,d' will return only words
    running left-to-right or top-bottom, while 'h, sw, ne', will return all
    words running horizontally (left-to-right or right-to-left) as well as
    any running from upper-right to lower-left or lower-left to lower-right

    dirs defaults ot 'a', meaning all orthogonal and diagonal directions.

    If len is a number, only sequences of that length will be returned. If it is
    a tuple of (min, max), only sequences with lengths in [min, max] will be
    returned. If len is None, or if len is a tuple and min or max is None, that
    bound will be ignored, e.g. len=(3,None) returns all sequences of 3 or more
    cells.

    Note that while this function does return strings, "len" here refers to the
    number of *cells* per word. If the input grid has cells containing multiple
    letters, len=3 will return all strings made by combining three adjacent
    cells, regardless of how long the actual strings are.

    The results are Result objects where .val is the sequence in question
    and .provenance is a tuple of (start, end) indicating where in the grid
    the word was found.
    '''
    dirs = parse_dirs(dirs)
    h, w = grid.shape[:2]
    if not isinstance(len, (list, tuple)):
        min_len = max_len = len
    else:
        min_len, max_len = len
    if min_len is None:
        min_len = 3
    if max_len is None:
        max_len = max(w,h)

    for row, col in np.ndindex(h, w):
        start = np.array([[row], [col]])
        for d in dirs:
            # shaping it to (2,1) means we can do d*arange(i) to get a 2xi
            # array of indices
            d = np.array(d).reshape(2,1)
            for i in range(min_len, max_len+1):
                points = start + d*np.arange(i)
                if wrap:
                    points[0] = points[0]%h
                    points[1] = points[1]%w
                else:
                    # bounds check - stop if we've gone off the end
                    if (points[0].clip(0,h-1) != points[0]).any():
                        break
                    if (points[1].clip(0,w-1) != points[1]).any():
                        break
                dr, dc = d.flat
                items = list(grid[tuple(points)])
                prov = (FromGrid(
                    start = (row, col),
                    end = (row+(i-1)*dr, col+(i-1)*dc)),)
                yield Result(items, prov)

def _join_val(item):
    return attr.evolve(item, val=''.join(item.val))

def iter_strings(grid, size=(3,None), dirs=directions.all, wrap=False):
    '''iter_seqs but ''.join()'s the resulting values'''
    return iter_seqs(grid, size, dirs, wrap) | _join_val
