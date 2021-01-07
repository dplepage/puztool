import typing as t
import z3
import numpy as np
import funcy as fn
from ..grids import asdir

from .base import Solvable


def _mk_grid(size, typ, idstr):
    if isinstance(size, t.Iterable):
        h, w = size
    else:
        h = w = size
    return np.array([
        [typ(f"{idstr}_{r}_{c}") for c in range(w)] for r in range(h)])


class Z3Matrix(Solvable):
    '''A rectangular matrix of z3 variables.'''
    _next_id = 0

    @classmethod
    def get_id(cls):
        cls._next_id += 1
        return cls._next_id - 1

    def __init__(self, size, typ, idstr=None):
        if idstr is None:
            idstr = f"vars{self.get_id()}"
        self.M = _mk_grid(size, typ, idstr)

    def constraints(self):
        return []

    def uniques(self):
        return list(self.M.flat)


class IntMatrix(Z3Matrix):
    '''A rectangular matrix of z3 ints, constrained to a range.

    If size is an int, it's treated as (size, size).

    If bounds aren't specified, they default to (1, size).

    If unique is true, this object also generates constraints that no row or
    column can contain the same value twice.

    Thus, for example, IntMatrix(9, unique=True) would be a suitable base for a
    sudoku - a 9x9 grid of ints from 1 to 9 inclusive, constrained so that each
    digit appears exactly once in each row and column.
    '''

    def __init__(self, size, bounds=(1, None), unique=False, idstr=None):
        super().__init__(size, z3.Int, idstr)
        low, high = bounds
        if high is None:
            high = max(*self.M.shape) - 1 + low
        self.low = low
        self.high = high
        self.unique = unique

    @fn.collecting
    def constraints(self):
        yield from ((v >= self.low) & (v <= self.high) for v in self.M.flat)
        if self.unique:
            yield from unique_rowcols(self.M)


class BoolMatrix(Z3Matrix):
    def __init__(self, size, idstr=None):
        super().__init__(size, z3.Bool, idstr)


def unique_rowcols(m):
    '''Returns uniqueness constraints on each row and column of m.

    m can be a Z3Matrix or a numpy array of variables.
    '''
    if isinstance(m, Z3Matrix):
        m = m.M
    h, w = m.shape
    for r in range(h):
        yield z3.Distinct(*m[r, :])
    for c in range(w):
        yield z3.Distinct(*m[:, c])


def left_vis(heights: IntMatrix, occlusions=None):
    '''Given a heightmap, return a same-sized array of left-occlusion exprs.

    Specifically, occ[i,j] will be "the maximum of heights[i,:j]", as a z3
    expression.

    Use visibilities(heightmap) to get a directional dict of occlusion
    heightmaps in all directions; this function is provided for the special
    case where you need to do this yourself instead of using visibilities (e.g.
    maybe your grid is weird and "rotating" it doesn't actually do what this
    library assumes it does).
    '''
    if occlusions is None:
        occlusions = np.empty(heights.shape, dtype=object)
    occlusions[:, 0] = z3.IntVal(0)
    h, w = occlusions.shape
    for r in range(h):
        for c in range(1, w):
            occ = occlusions[r, c - 1]
            height = heights[r, c - 1]
            occlusions[r, c] = z3.If((height > occ), height, occ)
    return occlusions


def visibilities(heightmap):
    dmap = {}
    for d in 'lurd':
        dmap[d] = np.empty(heightmap.shape, dtype=object)
        heights = asdir(heightmap, d)
        occlusions = asdir(dmap[d], d)
        left_vis(heights, occlusions)
    return dmap



'''TODO

Edge map: a grid of bools or ints on edges.

EdgeMap(Bool, (9,9)) should create two underlying matrices, one 9x10 and one
10x9; m[3,4].l should be the left edge of square (3,4) (and .u, .d, .r)

Corner map: A grid of corner values.

Corners((9,9)) should be a 10x10 map where c[3,4].ul is the upper-left corner
of square 3,4, and so on.

Maybe can merge these? A single lookup wrapper could wrap all three:

foo = IntMatrix(9, unique=True)
w = GridWrapper(foo, edges=Bool, corners=None)
w[3,4].val == w.M[3,4] == foo.M[3,4]
w[3,4].l is the var for the edge


'''
