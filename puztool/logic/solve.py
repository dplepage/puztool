import typing as t
import attr
import pandas as pd
import z3
from funcy import cached_property

def negate(model):
    return z3.Or(*[v()!=model.eval(v()) for v in model.decls()])

class NoSolution(ValueError):
    pass

class MultipleSolutions(ValueError):
    def __init__(self, solns:t.List["Solution"]):
        super().__init__()
        self.solns = solns

@attr.s(auto_attribs=True)
class Solution:
    model: z3.ModelRef

    @cached_property
    def df(self) -> pd.DataFrame:
        return pd.DataFrame(self.dict.items())

    @cached_property
    def dict(self):
        decs = self.model.decls()
        names = [str(x) for x in decs]
        vals = [self.model.eval(x()) for x in decs]
        vals = [v.as_long() if hasattr(v, 'as_long') else v.is_true() for v in vals]
        return dict(sorted(zip(names, vals)))


def all_solns(constraints, limit=10):
    s = z3.Solver()
    s.add(*constraints)
    for _ in range(limit):
        if s.check() != z3.sat:
            return
        soln = s.model()
        yield Solution(soln)
        s.add(negate(soln))
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
