import abc
import typing as t

import attr
import funcy as fy
import numpy as np
import pandas as pd
import z3
from z3.z3util import get_vars


class NoSolution(ValueError):
    '''Indicates a problem has no solution.'''
    pass


class MultipleSolutions(ValueError):
    '''Indicates we found multiple solutions when we didn't expect to.'''

    def __init__(self, solns: t.List["Solution"]):
        super().__init__(solns)
        self.solns = solns


@attr.s(auto_attribs=True)
class Solution:
    model: z3.ModelRef

    @fy.cached_property
    def df(self) -> pd.DataFrame:
        return pd.DataFrame(self.dict.items())

    @fy.cached_property
    def dict(self):
        decls = self.model.decls()
        names = [str(x) for x in decls]
        vals = [self.val(x()) for x in decls]
        return dict(sorted(zip(names, vals)))

    def val(self, exp):
        v = self.model.eval(exp)
        if hasattr(v, 'as_long'):
            return v.as_long()
        return z3.is_true(v)

    def vals(self, vars):
        if isinstance(vars, z3.AstRef):
            return self._val1(vars)
        return np.vectorize(self._val1)(vars)


class Solvable(abc.ABC):
    @abc.abstractmethod
    def constraints(self):
        raise NotImplementedError()

    @abc.abstractmethod
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
    subprobs_: t.List[Solvable] = attr.ib(factory=list)

    def constraints(self):
        l = []
        l.extend(self.constraints_)
        for p in self.subprobs_:
            l.extend(p.constraints())
        return l

    def uniques(self):
        l = []
        l.extend(self.uniques_)
        for p in self.subprobs_:
            l.extend(p.uniques())
        return l

    def add(self, *constraints):
        self.constraints_.extend(constraints)

    def add_uniques(self, *uniques):
        self.uniques_.extend(uniques)

    def include(self, item):
        self.subprobs_.append(item)
        return item


def negate(problem, model):
    '''Make a constraint that model isn't the solution to problem.'''
    return z3.Or(*[v != model.eval(v) for v in problem.uniques()])


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


def solve(problem, unique=True):
    '''Solve a problem.

    If unique is set (the default), this will check for a second solution and
    raise MultipleSolutions() if it finds one.

    '''
    first = None
    for soln in all_solns(problem, 2):
        if not unique:
            return soln
        if first is not None:
            raise MultipleSolutions([first, soln])
        first = soln
    if first is None:
        raise NoSolution()
    return first
