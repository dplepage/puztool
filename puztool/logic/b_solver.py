import abc
from itertools import combinations as combos, product
import typing as t

import attr
import funcy as fn
import numpy as np
import pandas as pd
import z3

from .b_grid import Grid

@attr.s(auto_attribs=True)
class VarLookup:
    '''Helper for indexing'''
    s: "Solver"

    def __getitem__(self, tup):
        if isinstance(tup, str):
            return lambda s: self[tup,s]
        a,b = tup
        if a in self.s.xcats:
            # e.g. vars['size', 'yellow']
            ib = self.s.get_info(b)
            return self.s.vcats[a][ib.cat][ib.idx]
        elif b in self.s.xcats:
            # e.g. vars['size', 'yellow']
            ia = self.s.get_info(a)
            return self.s.vcats[b][ia.cat][ia.idx]
        ia = self.s.get_info(a)
        ib = self.s.get_info(b)
        return self.s.vgrids[ia.cat][ib.cat][ia.idx,ib.idx]


@attr.s(auto_attribs=True)
class Solution:
    '''Thin wrapper around a Solver and a z3 model that solves it.

    The attribute .grid is a Grid with extra categories added for any xcats in
    the solution, mainly useful for viewing via html_link; .df is a pandas
    DataFrame of all the rows in the solution.
    '''
    solver: "Solver"
    model: z3.ModelRef
    _grid: Grid = attr.ib(init=False, default=None)
    _df: pd.DataFrame = attr.ib(init=False, default=None)
    _rows: t.List[t.Dict[str, t.Any]] = attr.ib(init=False, default=None)

    @property
    def rows(self) -> t.List[t.Dict[str,t.Any]]:
        if self._rows is None:
            c1 = self.solver.categories[0]
            self._rows = []
            for i1 in self.solver.domain(c1):
                row = {c1:i1.val}
                for c2 in self.solver.categories[1:]:
                    for i2 in self.solver.domain(c2):
                        is_set = self.model.eval(self.solver.vgrids[c1][c2][i1.idx, i2.idx])
                        if is_set:
                            row[c2] = i2.val
                            break
                for xcat in self.solver.xcats:
                    row[xcat] = self.model.eval(self.solver.vcats[xcat][c1][i1.idx])
                self._rows.append(row)
        return self._rows


    @property
    def grid(self) -> Grid:
        if self._grid is None:
            altrows = [dict(r) for r in self.rows]
            cats = list(altrows[0])
            # Deduplicate non-unique rows
            for cat in cats:
                vals = set()
                for row in altrows:
                    while row[cat] in vals:
                        row[cat] = '_{}'.format(row[cat])
                    vals.add(row[cat])
            # Add xcat rows to grid, using only values that were actually used
            catmap = {cat:[i.val for i in v] for (cat, v) in self.solver.catmap.items()}
            for cat in set(cats) - set(catmap):
                catmap[cat] = [row[cat] for row in altrows]
            self._grid = Grid(catmap)
            for f1, f2 in combos(cats, 2):
                self._grid.grids[f1][f2][:,:] = False
            for row in altrows:
                for f1, f2 in combos(cats, 2):
                    ia = self._grid.get_info(row[f1], cat=f1)
                    ib = self._grid.get_info(row[f2], cat=f2)
                    self._grid.grids[f1][f2][ia.idx, ib.idx] = True
        return self._grid

    @property
    def df(self) -> pd.DataFrame:
        if self._df is None:
            cols = list(self.solver.categories) + list(self.solver.xcats)
            self._df = pd.DataFrame(self.rows, columns=cols)
        return self._df


class NoSolution(ValueError):
    pass

class MultipleSolutions(ValueError):
    def __init__(self, solns:t.List["Solution"]):
        super().__init__()
        self.solns = solns

class CustomDomain(abc.ABC):
    @abc.abstractmethod
    def mk(self, name:str) -> z3.ExprRef:
        '''Generate a new domain'''
        raise NotImplementedError()

    @abc.abstractmethod
    def cons(self, vs:t.List[z3.ExprRef]) -> t.List[z3.ExprRef]:
        '''Given vars from self.mk, return implied constraints on them.'''
        raise NotImplementedError()

@attr.s(auto_attribs=True)
class IntDomain(CustomDomain):
    low: int
    high: int

    def mk(self, name:str) -> z3.ExprRef:
        return z3.Int(name)

    @fn.collecting
    def cons(self, vs:t.List[z3.ExprRef]) -> t.List[z3.ExprRef]:
        for var in vs:
            yield (var >= self.low) & (var <= self.high)

class BoolDomain(CustomDomain):
    def mk(self, name):
        return z3.Bool(name)

    def cons(self, vs):
        return []

class Solver(Grid):
    def __init__(self, grid_categories, extra_categories=None):
        super().__init__(grid_categories)
        self.xcats = extra_categories or dict()
        # Create grids of variables for each pair of categories
        self.vgrids = {n:{} for n in self.categories}
        self.all_grids = []
        for f1, f2 in self.pairs:
            d1 = self.domain(f1)
            d2 = self.domain(f2)
            mat = np.array([[z3.Bool(f'{a.fullname}_{b.fullname}') for a in d2] for b in d1])
            # Like the normal grid, these are two views of the same object
            self.vgrids[f1][f2] = mat
            self.vgrids[f2][f1] = mat.T
            self.all_grids.append(mat)
        # Create variables for each extra category
        self.vcats = {}
        for (name, domain) in self.xcats.items():
            v = self.vcats[name] = {}
            for cat in self.categories:
                d = self.domain(cat)
                v[cat] = [domain.mk(f'{a.fullname}_{name}') for a in d]
        self.vars = VarLookup(self)
        self.constraints = []

    def add(self, *cons):
        self.constraints.extend(cons)

    def add_constraint(self, *pairs):
        vnames = [self.get_info(p[0]) for p in pairs]
        opts = [self.domain(p[1]) for p in pairs]
        def add_it(func):
            for choices in product(*opts):
                if not func(*[c.val for c in choices]):
                    vs = [self.vars[v, c] for (v, c) in zip(vnames, choices)]
                    self.add(z3.AtMost(*vs, len(vs)-1))
            return func
        return add_it

    def all_vars(self):
        '''Return a list of all z3 variables being solved for.'''
        xvars = sum(sum((tuple(x.values()) for x in self.vcats.values()), ()), [])
        gvars = sum((list(l.flat) for l in self.all_grids), [])
        return xvars + gvars

    def all_solutions(self, limit=10):
        s = z3.Solver()
        s.add(*self.cons_sanity())
        s.add(*self.cons_rowcol())
        s.add(*self.cons_grid())
        s.add(*self.cons_domains())
        s.add(*self.constraints)
        c = 0
        # Repeatedly find a solution, then add a constraint that at least one
        # value must differ from that solution.
        while c < limit and s.check() == z3.sat:
            c += 1
            soln = Solution(self, s.model())
            yield soln
            s.add(self.cons_exclude(soln))
        if c == limit:
            print(f"Warning: more than {limit} solutions found")

    def solve(self, unique=True):
        first = None
        for soln in self.all_solutions():
            if not unique:
                return soln
            if first is not None:
                raise MultipleSolutions([first, soln])
            first = soln
        if first is None:
            raise NoSolution()
        return first

    @fn.collecting
    def cons_domains(self):
        for (name, domain) in self.xcats.items():
            vlist = sum(self.vcats[name].values(), [])
            yield from domain.cons(vlist)

    @fn.collecting
    def cons_rowcol(self):
        '''Return basic structural constraints.

        The returned list of constraints will require every row and column of
        every grid to have exactly one 1.
        '''
        for grid in self.all_grids:
            for i in range(self.num_items):
                yield z3.AtMost(*grid[i, :], 1)
                yield z3.AtLeast(*grid[i, :], 1)
                yield z3.AtMost(*grid[:, i], 1)
                yield z3.AtLeast(*grid[:, i], 1)

    @fn.collecting
    def cons_sanity(self):
        '''Return sanity-check constraints.

        The returned list of constraints will require that for every three
        categories A, B, and C, AB[i,j] & BC[j,k] -> AC[i,k].

        For example, if your categories are first name, last name, and hair
        color, this will emit constraints ensuring that if the first name
        'Alice' goes with the last name 'Svetlana' and the last name 'Svetlana'
        goes with the hair color 'Teal', then the first name 'Alice' must go
        with the hair color 'Teal'.
        '''
        for f1, f2, f3 in combos(self.categories, 3):
            a2b = self.vgrids[f1][f2]
            b2c = self.vgrids[f2][f3]
            a2c = self.vgrids[f1][f3]
            for i in range(self.num_items):
                for j in range(self.num_items):
                    for k in range(self.num_items):
                        yield z3.Implies(z3.And(a2b[i,j], b2c[j,k]), a2c[i,k])
        for cat in self.xcats:
            for f1, f2 in combos(self.categories, 2):
                a2b = self.vgrids[f1][f2]
                cat1 = self.vcats[cat][f1]
                cat2 = self.vcats[cat][f2]
                for i in range(self.num_items):
                    for j in range(self.num_items):
                        yield (a2b[i,j] == False) | (cat1[i] == cat2[j])

    @fn.collecting
    def cons_grid(self):
        '''Return constraints for all entered information.

        This encodes everything added via include, exclude, etc.
        '''
        for f1, f2 in self.pairs:
            bgrid = self.grids[f1][f2]
            vgrid = self.vgrids[f1][f2]
            for i in range(self.num_items):
                for j in range(self.num_items):
                    if bgrid[i,j] is not None:
                        yield vgrid[i,j] == bgrid[i,j]

    def cons_exclude(self, soln:Solution):
        '''Return a constraint that excludes this particular solution.'''
        return [z3.Or(*(v != soln.model.eval(v) for v in self.all_vars()))]
