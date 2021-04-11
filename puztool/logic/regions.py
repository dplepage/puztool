import enum
from .base import Solvable
from .grids import IntMatrix, _mk_grid
from puztool.geom import as_shape, indices
from .domain import IntDomain
import funcy as fy


class Subtree(enum.IntEnum):
    O = 0
    R = 1
    N = 2
    S = 3
    E = 4
    W = 5


subtree_domain = IntDomain(0, 6)


class Regions(Solvable):
    _next_id = 0

    @classmethod
    def get_id(cls):
        cls._next_id += 1
        return cls._next_id - 1

    def __init__(self, shape, complete=True, rectangular=False, min_size=1, max_size=None, id: str = None):
        if id is None:
            id = f'region{self.get_id()}'
        self.shape = as_shape(shape)
        nrows, ncols = self.shape
        ncells = nrows * ncols
        if max_size is None:
            max_size = ncells
        self.parents = _mk_grid(self.shape, subtree_domain, f'{id}-subtree')
        self.region_id = IntMatrix(self.shape, (0, ncells)).M
        self.region_size = IntMatrix(self.shape, (min_size, max_size + 1)).M

    def uniques(self):
        return list(self.region_id.flat)

    @fy.collecting
    def cons(self):
        for p in indices(self):

        for r, c in np.ndindex(*self.shape):
            if self.complete:
                pv = self.parents[r, v]
                yield pv != Subtree.O

        if self.complete:
            yield z3.And(*[v != Subtree.O for v in self.parents.flat])
        # Propagate region id
