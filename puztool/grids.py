import attr
import numpy as np
import funcy as fn

from .result import Result, ProvEntry
from .pipeline import source
from .geom import directions, parse_dirs, Point


def Fail(*a, **kw):
    raise NotImplementedError()


def mkrot(*rots):
    '''Make a rotation function for characters.

    The inputs should be length-four strings indicating four rotations of a
    character.

    For example:
    >>> rot = mkrot("EM3W", "UCN]", "OOOO", "HIHI")
    >>> rot('E', 1)
    'M'
    >>> rot('C', 1)
    'N'
    >>> rot('O', 3)
    'O'

    Unspecified letters will map to themselves with a number indicating how
    many clockwise turns they have:
    >>> rot('S', 1)
    'S1'

    There's a lot of room for improvement here...
    '''
    rmap = {}
    for a, b, c, d in rots:
        rmap[a] = b
        rmap[b] = c
        rmap[c] = d
        rmap[d] = a

    def rot(c, n=0):
        if len(c) > 1:
            n += int(c[1:])
            c = c[0]
        r = 0
        for i in range(n):
            if c in rmap:
                c = rmap[c]
                r = 0
            else:
                r = (r + 1) % 4
        if r:
            return f'{c}{r}'
        return c
    return rot


'''
TODO smarter rotator/flipper design?

Ideas:

1. Should really preserve state - e.g. S0 is different from S2, even though in
many fonts they look the same. There should be a mapping stage at the end where
we resolve the rotations

2. We need a notation for flipping - e.g. "S'3" is "S" flipped backwards and
then rotated 3 times clockwise. Need to make sure it's clear what the order is
(flip-then-rotate produces different results from rotate-then-flip)

3. Do we need to encode strings of these? Probably not, we can stick to arrays
so that there's no confusion.

4. Should have a library with some common ones - common box fonts, pigpen,
maybe morse?

5. Should have an easy way to add more - if a puzzle has a new font, want to
build mapping immediately.
'''


class Rotator:
    '''Rotator that understands character-level xforms.

    Useful for ciphers (or even just fonts) where rotating one letter turns it
    into another.

    For example, a pigpen A becomes a C when rotated 90° OR flipped
    horizontally, so a grid of pigpen letters could be rotated
    programmatically, remapping the characters on the fly.

    Use mkrot() to produce a simple rotator function whatever font or cipher
    you're working with.

    '''

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


def subrect(data, mask=None, pad=0, dirs='udlr'):
    '''Return a sub-rectangle of data containing everywhere mask is True.

    If mask is None, data will be used, but must then be 2D. If pad is True,
    some extra space will be left in. This will NOT add new rows if there isn't
    enough padding in a given direction.

    dirs lets you limit which dirs we chop off - by default, it's all four

    '''
    dirs = set(dirs)
    nrows, ncols, *_ = data.shape
    if mask is None:
        mask = data
    rows, cols, *rest = np.where(mask)
    if rest:
        raise ValueError("Mask must be 2D")
    rm, rM = max(rows.min() - pad, 0), rows.max() + pad + 1
    cm, cM = max(cols.min() - pad, 0), cols.max() + pad + 1
    if dirs & set('un'):
        rm = 0
    if dirs & set('ds'):
        rM = nrows
    if dirs & set('lw'):
        cm = 0
    if dirs & set('re'):
        cM = ncols
    return data[rm:rM, cm:cM]


@attr.s(auto_attribs=True)
class FromGrid(ProvEntry):
    '''Represents a range of points on a grid'''
    start: Point
    end: Point

    def __str__(self):
        return f"{self.start}->{self.end}"

    def __iter__(self):
        yield from (self.start, self.end)

    def __getitem__(self, i):
        return self.indices()[i]

    @fn.collecting
    def indices(self):
        s = self.start
        e = self.end
        d = max(abs(e - s)).max()
        delta = (e - s) // d
        for i in range(d + 1):
            yield s + i * delta

    def idx(self):
        return np.array(self.indices()).T.tolist()


@source
def iter_seqs(grid, len=(3, None), dirs=directions.all, wrap=False):
    '''Emit all sequences of letters in grid.

    dirs can be a list of tuples, or a comma-separated list of letters
    recognized by parse_dirs. For example, 'r,d' will return only words
    running left-to-right or top-bottom, while 'h, sw, ne', will return all
    words running horizontally (left-to-right or right-to-left) as well as
    any running from upper-right to lower-left or lower-left to lower-right

    dirs defaults to 'a', meaning all orthogonal and diagonal directions.

    If len is a number, only sequences of that length will be returned. If it
    is a tuple of (min, max), only sequences with lengths in [min, max] will be
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
        max_len = max(w, h)

    for row, col in np.ndindex(h, w):
        start = np.array([[row], [col]])
        for d in dirs:
            # shaping it to (2,1) means we can do d*arange(i) to get a 2xi
            # array of indices
            d = np.array(d).reshape(2, 1)
            for i in range(min_len, max_len + 1):
                points = start + d * np.arange(i)
                if wrap:
                    points[0] = points[0] % h
                    points[1] = points[1] % w
                else:
                    # bounds check - stop if we've gone off the end
                    if (points[0].clip(0, h - 1) != points[0]).any():
                        break
                    if (points[1].clip(0, w - 1) != points[1]).any():
                        break
                dr, dc = d.flat
                items = list(grid[tuple(points)])
                prov = (FromGrid(
                    start=(row, col),
                    end=(row + (i - 1) * dr, col + (i - 1) * dc)),)
                yield Result(items, prov)


def _join_val(item):
    return attr.evolve(item, val=''.join(item.val))


def iter_strings(grid, len=(3, None), dirs=directions.all, wrap=False):
    '''iter_seqs but ''.join()'s the resulting values'''
    return iter_seqs(grid, len, dirs, wrap) | _join_val
