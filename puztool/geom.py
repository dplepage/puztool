import math
import typing as t
import numpy as np
import operator


class Indexable:
    shape: tuple[int, int]

    def __getitem__(self, p: any) -> any:
        pass


Shapeable = t.Union[int, tuple[int, int], Indexable]


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

    @staticmethod
    def as_point(other) -> "Point":
        if isinstance(other, Point):
            return other
        if isinstance(other, (np.ndarray, list, tuple)):
            return Point(*other)
        if isinstance(other, int):
            return Point(other, other)
        raise NotImplementedError()

    def __repr__(self) -> str:
        return f"Point({self.r}, {self.c})"

    def __neg__(self) -> "Point":
        return self * -1

    def __pos__(self) -> "Point":
        return self

    def __abs__(self) -> "Point":
        return Point(abs(self.r), abs(self.c))

    def sqrt(self) -> "Point":
        '''Returns a point whose r and c are the square root of ours.

        Raises a ValueError if this would make a non-integer point.
        '''
        r2 = self.r ** .5
        c2 = self.c ** .5
        if r2 != int(r2) or c2 != int(c2):
            raise ValueError(f"{self!r}.sqrt() is non-integral")
        return type(self)(int(r2), int(c2))


class Shape(Point):
    def __str__(self):
        return f'{self.r}x{self.c}'


def as_shape(shape: Shapeable) -> Shape:
    if isinstance(shape, int):
        return Shape(shape, shape)
    elif hasattr(shape, "shape"):
        return Shape(*shape.shape)
    return Shape(*shape)


def mkapply(name, left=True):
    def leftfn(self, other):
        other = Point.as_point(other)
        op = getattr(operator, name)
        return Point(op(self.r, other.r), op(self.c, other.c))

    def rightfn(self, other):
        other = Point.as_point(other)
        op = getattr(operator, name)
        return Point(op(other.r, self.r), op(other.c, self.c))
    return leftfn if left else rightfn


for key in ['add', 'sub', 'mul', 'matmul', 'truediv', 'floordiv', 'mod',
            'pow', 'lshift', 'rshift', 'and', 'xor', 'or']:
    setattr(Point, f'__{key}__', mkapply(key))
    setattr(Point, f'__r{key}__', mkapply(key, False))


class _DIRS:
    l = left = w = west = Point(0, -1)
    r = right = e = east = Point(0, 1)
    u = up = n = north = Point(-1, 0)
    d = down = s = south = Point(1, 0)
    ul = upleft = nw = northwest = u + l
    ur = upright = ne = northeast = u + r
    dl = downleft = sw = southwest = d + l
    dr = downright = se = southeast = d + r
    h = hor = horizontals = (l, r)
    v = ver = verticals = (u, d)
    di = diagonals = (ul, ur, dl, dr)
    o = ortho = h + v
    a = all = ortho + diagonals

    def __getitem__(self, key):
        return getattr(self, key)

    def __contains__(self, key):
        return key in dir(self)


directions = DIRS = _DIRS()


def parse_dirs(dirs):
    '''
    Generate a set of directions from a string.

    dirs can be a list of tuples, or a comma-separated list of letters
    recognized by parse_dirs. For example, 'r,d' will map to left-to-right and
    top-bottom, while 'h, sw, ne', will map to left-to-right, right-to-left,
    upper-right-to-lower-left, and lower-left-to-lower-right.

    >>> parse_dirs("r, u")
    [Point(0, 1), array([-1,  0])]
    >>> np.array(parse_dirs(["diagonals", np.array([3,3])]))
    array([[-1, -1],
           [-1,  1],
           [ 1, -1],
           [ 1,  1],
           [ 3,  3]])
    '''
    if isinstance(dirs, str):
        dirs = [d.strip() for d in dirs.split(",")]
    chosen = []
    for d in dirs:
        if isinstance(d, str):
            choice = directions[d.lower()]
        else:
            choice = d
        if isinstance(choice, (list, tuple)):
            chosen.extend(choice)
        else:
            chosen.append(choice)
    return chosen


def indices(shape: Shapeable) -> t.Iterator[Point]:
    return (Point(r, c) for r, c in np.ndindex(*as_shape(shape)))


def index(data: Indexable):
    for p in indices(data):
        yield p, data[p]


def iter_blocks(grid: Indexable, n: Shapeable = None, size: Shapeable = None):
    if n is not None and size is not None:
        raise ValueError("Specify n or size, not both.")
    total = as_shape(grid)
    if n is None:
        if size is None:
            raise ValueError("Must specify n or size")
        size = as_shape(size)
        if total % size != (0, 0):
            raise ValueError(
                f"Cannot split {total} grid into {size} blocks")
        n = total // size
    n = as_shape(n)
    if total % n != (0, 0):
        raise ValueError(
            f"Cannot split {total} grid into {n} equal blocks")
    size = total // n
    for p in indices(n):
        a = p * size
        b = p * size + size
        yield p, grid[a.r:b.r, a.c:b.c]
