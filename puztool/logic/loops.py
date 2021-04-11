import funcy as fy
from .grids import as_shape, _mk_grid
from .base import Solvable
from .domain import IntDomain, BoolDomain
from puztool.grids import DIRS
import typing as t
import numpy as np
import z3


class Point(t.NamedTuple):
    r: int
    c: int

    def is_in(self, shape):
        rows, cols = as_shape(shape)
        return 0 <= self.r < rows and 0 <= self.c < cols

    def __getitem__(self, ds):
        if not isinstance(ds, tuple):
            ds = (ds,)
        new = Point(*self)
        for d in ds:
            new += DIRS[d]
        return new

    def __getattr__(self, attr):
        if attr in DIRS:
            return self + DIRS[attr]

    @staticmethod
    def as_point(other):
        if isinstance(other, Point):
            return other
        if isinstance(other, (np.ndarray, list, tuple)):
            return Point(*other)
        if isinstance(other, int):
            return Point(other, other)
        raise NotImplementedError()

    def __add__(self, other):
        other = self.as_point(other)
        return Point(self.r + other.r, self.c + other.c)

    def __sub__(self, other):
        other = self.as_point(other)
        return Point(self.r - other.r, self.c - other.c)

    def __mul__(self, other):
        other = self.as_point(other)
        return Point(self.r * other.r, self.c * other.c)


class Edge(t.NamedTuple):
    start: Point
    end: Point
    left: Point
    right: Point
    val: z3.ArithRef

    def sym(self):
        return Edge(
            start=self.end,
            end=self.start,
            left=self.right,
            right=self.left,
            val=self.val)


class EdgeIterator:
    def __init__(self, v, h):
        self.v = v
        self.h = h
        rows, cols = self.h.shape
        self.shape = (rows-1, cols)

    def __getitem__(self, coords):
        r, c = coords
        return dict(n=self.h[r, c], s=self.h[r + 1, c],
                    w=self.v[r, c], e=self.v[r, c + 1])

    def corner(self, coords: Point):
        p = Point.as_point(coords)

        def get(m, p: Point):
            return m[p] if p.is_in(m) else None
        edges = dict(n=get(self.v, p - (1, 0)),
                     s=get(self.v, p),
                     w=get(self.h, p - (0, 1)),
                     e=get(self.h, p))
        return {k: v for (k, v) in edges.items() if v is not None}

    def iter_corners(self):
        rows, cols = self.h.shape
        cols += 1
        for r, c in np.ndindex(rows, cols):
            yield Point(r, c), self.corner((r, c))

    def iter_edges(self, ext=True, sym=False):
        rows, cols = self.shape
        # horizontal edges
        for r, c in np.ndindex(rows + 1, cols):
            if c not in (0, cols - 1) or ext:
                e = Edge(start=Point(r, c),
                         end=Point(r, c + 1),
                         left=Point(r - 1, c),
                         right=Point(r, c),
                         val=self.h[r, c])
                yield e
                if sym:
                    yield e.sym()
        # vertical edges
        for r, c in np.ndindex(rows, cols + 1):
            if r not in (0, rows - 1) or ext:
                e = Edge(start=Point(r, c),
                         end=Point(r + 1, c),
                         left=Point(r, c),
                         right=Point(r, c - 1),
                         val=self.v[r, c])
                yield e
                if sym:
                    yield e.sym()


class EdgeSet(EdgeIterator, Solvable):
    _next_id = 0

    @classmethod
    def get_id(cls):
        cls._next_id += 1
        return cls._next_id - 1

    def __init__(self, shape, domain=None, loop=True, single_loop=True,
                 idstr=None):
        if domain is None:
            domain = BoolDomain()
        if idstr is None:
            idstr = f"edgset{self.get_id()}"
        rows, cols = as_shape(shape)
        v = _mk_grid((rows, cols + 1), domain, idstr + "_v")
        h = _mk_grid((rows + 1, cols), domain, idstr + "_h")
        super().__init__(v, h)
        self.domain = domain
        self.shape = (rows, cols)
        self.loop = loop
        self.single_loop = single_loop
        self.loop_index = None
        if single_loop:
            num_corners = (rows + 1) * (cols + 1)
            self.loop_index = _mk_grid((rows + 1, cols + 1),
                                       IntDomain(-num_corners, num_corners),
                                       idstr + "_li")

    def uniques(self):
        # don't include loop_index even if we have one - it's not unique.
        return list(self.v.flat) + list(self.h.flat)

    @fy.collecting
    def constraints(self):
        yield from self.domain.cons(self.v.flat)
        yield from self.domain.cons(self.h.flat)
        if self.loop:
            yield from self._loop_cons()
        if self.single_loop:
            yield from self._single_loop_cons()

    @fy.collecting
    def _loop_cons(self):
        # Every corner must have either no edges or exactly two edges
        for point, c in self.iter_corners():
            vars = tuple([(v, 1) for v in c.values()])
            yield z3.PbEq(vars, 0) | z3.PbEq(vars, 2)

    @fy.collecting
    def _single_loop_cons(self):
        # Single loop constraint: assign an index to each corner of the loop.
        # These must all be unique, and satisfy A) that any corner the loop
        # doesn't visit has a negative index, and B) the values on either side
        # of an edge are positive and differ by exactly 1 unless one of them is
        # zero. A loop can't satisfy this constraint unless it has 0 on it, and
        # there can only be one 0 because of distinctness, so there must be
        # exactly one loop.
        yield z3.Distinct(*self.loop_index.flat)
        for e in self.iter_edges():
            sv = self.loop_index[e.start]
            ev = self.loop_index[e.end]
            oneoff = z3.Or(ev == sv + 1, sv == ev + 1, sv == 0, ev == 0)
            yield z3.Implies(e.val, oneoff)
        for point, c in self.iter_corners():
            empty = z3.And(*(~var for var in c.values()))
            yield z3.Implies(empty, self.loop_index[point] < 0)

    def reify(self, soln):
        return EdgeIterator(soln(self.v), soln(self.h))
