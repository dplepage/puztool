import z3
import numpy as np
import funcy as fn
from ..grids import asdir
from ..geom import iter_blocks, Shapeable, Indexable, as_shape, index, Point

from .base import Solvable
from .domain import Domain, IntDomain


def _mk_grid(shape: Shapeable, domain: Domain, id: str):
    rows, cols = as_shape(shape)
    return np.array([
        [domain.mk(f"{id}_{r}_{c}") for c in range(cols)]
        for r in range(rows)])


class Z3Matrix(Solvable):
    '''A rectangular matrix of z3 variables.'''
    _next_id = 0

    @property
    def shape(self):
        return as_shape(self.M.shape)

    @classmethod
    def get_id(cls):
        cls._next_id += 1
        return cls._next_id - 1

    def __init__(self, shape: Shapeable, domain: Domain, id: str = None):
        if id is None:
            id = f"vars{self.get_id()}"
        self.domain = domain
        self.M = _mk_grid(shape, domain, id)

    @fn.collecting
    def constraints(self):
        yield from self.domain.cons(self.M.flat)

    def uniques(self):
        return list(self.M.flat)

    def reify(self, soln):
        return soln.vals(self.M)


class IntMatrix(Z3Matrix):
    '''A rectangular matrix of z3 ints, constrained to a range.

    If shape is an int, it's treated as (shape, shape).

    Bounds should be a tuple of (low, high); if high is None, it defaults to
    low + max(shape).

    If unique is true, this object also generates constraints that no row or
    column can contain the same value twice.

    Thus, for example, IntMatrix(9, unique=True) would be a suitable base for a
    sudoku - a 9x9 grid of ints from 1 to 9 inclusive, constrained so that each
    digit appears exactly once in each row and column.
    '''

    def __init__(self, shape: Shapeable, bounds: tuple[int, int] = (1, None),
                 unique: bool = False, id: str = None):
        shape = as_shape(shape)
        low, high = bounds
        if high is None:
            high = max(shape) - 1 + low
        super().__init__(shape, IntDomain(low, high), id)
        self.low = low
        self.high = high
        self.unique = unique

    @fn.collecting
    def constraints(self):
        yield from super().constraints()
        if self.unique:
            yield from unique_rowcols(self.M)


class Sudoku(IntMatrix):
    '''IntMatrix subclass with sudoku constraints.'''

    def __init__(self, shape: Shapeable = 9, id: str = None,
                 clues: Indexable = None):
        super().__init__(shape, unique=True, id=id)
        self.clues = clues

    @fn.collecting
    def constraints(self):
        yield from super().constraints()
        for _, subgrid in iter_blocks(self.M, self.shape.sqrt()):
            yield z3.Distinct(*subgrid.flat)
        if self.clues is not None:
            for p, v in index(self.clues):
                if v is not None:
                    yield self.M[p] == v


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
