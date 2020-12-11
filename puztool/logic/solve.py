import typing as t
import attr
import pandas as pd
import z3
from z3.z3util import get_vars
import numpy as np
import funcy as fn
from ..grids import asdir

# TODO probably some of the b_solver stuff could merge with this?


def negate(problem, model):
    '''Make a constraint that model isn't the solution to problem.'''
    return z3.Or(*[v != model.eval(v) for v in problem.uniques()])


class NoSolution(ValueError):
    pass


class MultipleSolutions(ValueError):
    def __init__(self, solns: t.List["Solution"]):
        super().__init__(solns)
        self.solns = solns


@attr.s(auto_attribs=True)
class Solution:
    model: z3.ModelRef

    @fn.cached_property
    def df(self) -> pd.DataFrame:
        return pd.DataFrame(self.dict.items())

    @fn.cached_property
    def dict(self):
        decls = self.model.decls()
        names = [str(x) for x in decls]
        vals = [self.model.eval(x()) for x in decls]
        vals = [v.as_long() if hasattr(v, 'as_long') else v.is_true() for v in vals]
        return dict(sorted(zip(names, vals)))

    def _val1(self, exp):
        v = self.model.eval(exp)
        if hasattr(v, 'as_long'):
            return v.as_long()
        return z3.is_true(v)

    def vals(self, vars):
        if isinstance(vars, z3.AstRef):
            return self._val1(vars)
        return np.vectorize(self._val1)(vars)


class Solvable:
    def constraints(self):
        raise NotImplementedError()

    def uniques(self):
        raise NotImplementedError()

    def __add__(self, other):
        result = Problem()
        result.include(self)
        result.include(other)
        return result


@attr.s(auto_attribs=True)
class Problem(Solvable):
    constraints_: t.List[z3.ExprRef] = attr.ib(factory=list)
    uniques_: t.List[z3.ExprRef] = attr.ib(factory=list)
    def constraints(self):
        return self.constraints_

    def uniques(self):
        return self.uniques_

    def add(self, *constraints):
        self.constraints_.extend(constraints)

    def add_uniques(self, *uniques):
        self.uniques_.extend(uniques)

    def include(self, item):
        if isinstance(item, Solvable):
            self.add(*item.constraints())
            self.add_uniques(*item.uniques())
        elif isinstance(item, t.Iterable):
            self.add(*item)
        else:
            self.add(item)
        return item


class Auto:
    pass


def mk_grid(size, typ, idstr):
    if isinstance(size, t.Iterable):
        h, w = size
    else:
        h = w = size
    return np.array([
        [typ(f"{idstr}_{r}_{c}") for c in range(w)] for r in range(h)])


class Z3Matrix(Solvable):
    _next_id = 0

    @classmethod
    def get_id(cls):
        cls._next_id += 1
        return cls._next_id - 1

    def __init__(self, size, typ, idstr=Auto):
        if idstr is Auto:
            idstr = f"vars{self.get_id()}"
        self.M = mk_grid(size, typ, idstr)

    def constraints(self):
        return []

    def uniques(self):
        return list(self.M.flat)


class IntMatrix(Z3Matrix):
    def __init__(self, size, bounds=(1, None), unique=False, idstr=Auto):
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
    def __init__(self, size, idstr=Auto):
        super().__init__(size, z3.Bool, idstr)


def unique_rowcols(m):
    if isinstance(m, Z3Matrix):
        m = m.M
    h, w = m.shape
    for r in range(h):
        yield z3.Distinct(*m[r, :])
    for c in range(w):
        yield z3.Distinct(*m[:, c])


def visibility(heights, occlusions=None):
    '''Given a heightmap, return a same-sized array of left-occlusion exprs.

    Specifically, occ[i,j] will be "the maximum of heights[i,:j]", as a z3
    expression.

    Use visibilities(heightmap) to get a directional dict of occlusion
    heightmaps in all directions; this function is provided for the special case
    where you need to do this yourself instead of using visibilities (e.g. maybe
    your grid is weird and "rotating" it doesn't actually do what this library
    assumes it does).f
    '''
    if occlusions is None:
        occlusions = np.empty(heights.shape, dtype=object)
    occlusions[:,0] = z3.IntVal(0)
    h, w = occlusions.shape
    for r in range(h):
        for c in range(1, w):
            occ = occlusions[r, c-1]
            height = heights[r, c-1]
            occlusions[r,c] = z3.If((height > occ), height, occ)
    return occlusions

def visibilities(heightmap):
    dmap = {}
    for d in 'lurd':
        dmap[d] = np.empty(heightmap.shape, dtype=object)
        heights = asdir(heightmap, d)
        occlusions = asdir(dmap[d], d)
        visibility(heights, occlusions)
    return dmap

def all_solns(problem, limit=10):
    if not isinstance(problem, Solvable):
        problem = Problem(problem, get_vars(z3.And(*problem)))
    s = z3.Solver()
    s.add(*problem.constraints())
    for _ in range(limit):
        if s.check() != z3.sat:
            return
        soln = s.model()
        yield Solution(soln)
        s.add(negate(problem, soln))
    print(f"Warning: Terminated early after {limit} solutions.")

def solve(constraints, unique=True):
    first = None
    for soln in all_solns(constraints, 2):
        if not unique:
            return soln
        if first is not None:
            raise MultipleSolutions([first, soln])
        first = soln
    if first is None:
        raise NoSolution()
    return first
