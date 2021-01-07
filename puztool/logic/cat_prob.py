import abc
from itertools import combinations as combos, product
import typing as t

import attr
import funcy as fn
import numpy as np
import pandas as pd
import z3

from .cat_grid import CatGrid
from .base import Solvable, Solution, solve, all_solns


@attr.s(auto_attribs=True)
class VarLookup:
    '''Helper for indexing.

    Logic is complicated, to make quick use easier:

    The general case is that v[name1, name2] returns the variable indicating
    that name1 goes with name2. As with all variable accessors, it's smart
    enough to do the right thing if you leave off the domain as long as the
    names are unique, so e.g. v['alice', 'ferret'] is the same as
    v['name:alice', 'pet:ferret'] as long as 'alice' and 'ferret' only appear
    in those two categories.

    If either value is the name of an extra category, the variable for that
    category will be returned instead. Thus v['alice', 'hairspeed'] would
    return the int variable for alice's hairspeed.

    If the input is a single string containing a /, it's split on the /, so
    v['alice/ferret'] is the same as v['alice', 'ferret']

    If the input is a single string without a /, this curries, so v['alice'] is
    a lookup function satisfying v['alice'](foo) == v['alice', 'foo']
    '''
    prob: "CatProblem"

    def __getitem__(self, tup):
        if isinstance(tup, str) and '/' in tup:
            tup = tup.split('/')
        if isinstance(tup, str):
            return lambda s: self[tup, s]
        a, b = tup
        if a in self.prob.xcats:
            # e.g. vars['size', 'yellow']
            ib = self.prob.get_info(b)
            return self.prob.vcats[a][ib.cat][ib.idx]
        if b in self.prob.xcats:
            # e.g. vars['yellow', 'size']
            ia = self.prob.get_info(a)
            return self.prob.vcats[b][ia.cat][ia.idx]
        ia = self.prob.get_info(a)
        ib = self.prob.get_info(b)
        return self.prob.vgrids[ia.cat][ib.cat][ia.idx, ib.idx]


@attr.s(auto_attribs=True)
class CatSoln:
    '''Thin wrapper around a CatProblem and a Solution for it.

    The attribute .grid is a Grid with extra categories added for any xcats in
    the solution, mainly useful for viewing via html_link; .df is a pandas
    DataFrame of all the rows in the solution.
    '''
    catprob: "CatProblem"
    soln: Solution
    _grid: CatGrid = attr.ib(init=False, default=None)
    _df: pd.DataFrame = attr.ib(init=False, default=None)
    _rows: t.List[t.Dict[str, t.Any]] = attr.ib(init=False, default=None)

    @property
    def rows(self) -> t.List[t.Dict[str, t.Any]]:
        if self._rows is None:
            c1 = self.catprob.categories[0]
            self._rows = []
            for i1 in self.catprob.domain(c1):
                row = {c1: i1.val}
                for c2 in self.catprob.categories[1:]:
                    for i2 in self.catprob.domain(c2):
                        is_set = self.soln.val(
                            self.catprob.vgrids[c1][c2][i1.idx, i2.idx])
                        if is_set:
                            row[c2] = i2.val
                            break
                for xcat in self.catprob.xcats:
                    row[xcat] = self.soln.val(
                        self.catprob.vcats[xcat][c1][i1.idx])
                self._rows.append(row)
        return self._rows

    @property
    def grid(self) -> CatGrid:
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
            catmap = {cat: [i.val for i in v]
                      for (cat, v) in self.catprob.catmap.items()}
            for cat in set(cats) - set(catmap):
                catmap[cat] = [row[cat] for row in altrows]
            self._grid = CatGrid(catmap)
            for f1, f2 in combos(cats, 2):
                self._grid.grids[f1][f2][:, :] = False
            for row in altrows:
                for f1, f2 in combos(cats, 2):
                    ia = self._grid.get_info(row[f1], cat=f1)
                    ib = self._grid.get_info(row[f2], cat=f2)
                    self._grid.grids[f1][f2][ia.idx, ib.idx] = True
        return self._grid

    @property
    def df(self) -> pd.DataFrame:
        if self._df is None:
            cols = list(self.catprob.categories) + list(self.catprob.xcats)
            self._df = pd.DataFrame(self.rows, columns=cols)
        return self._df


class CustomDomain(abc.ABC):
    unique = False

    @abc.abstractmethod
    def mk(self, name: str) -> z3.ExprRef:
        '''Generate a new domain'''
        raise NotImplementedError()

    @abc.abstractmethod
    def cons(self, vs: t.List[z3.ExprRef]) -> t.List[z3.ExprRef]:
        '''Given vars from self.mk, return implied constraints on them.'''
        raise NotImplementedError()


@attr.s(auto_attribs=True)
class IntDomain(CustomDomain):
    low: int
    high: int
    unique: bool = False

    def mk(self, name: str) -> z3.ExprRef:
        return z3.Int(name)

    @fn.collecting
    def cons(self, vs: t.List[z3.ExprRef]) -> t.List[z3.ExprRef]:
        for var in vs:
            yield (var >= self.low) & (var <= self.high)


class BoolDomain(CustomDomain):
    def mk(self, name):
        return z3.Bool(name)

    def cons(self, vs):
        return []


class CatProblem(CatGrid, Solvable):
    '''A z3-backed category grid Solvable'''

    def __init__(self, categories):
        grid_categories = {}
        self.xcats = {}
        for k, v in categories.items():
            if isinstance(v, CustomDomain):
                self.xcats[k] = v
            else:
                grid_categories[k] = v
        super().__init__(grid_categories)
        # Create grids of variables for each pair of categories
        self.vgrids = {n: {} for n in self.categories}
        self.all_grids = []
        for f1, f2 in self.pairs:
            d1 = self.domain(f1)
            d2 = self.domain(f2)
            mat = np.array([
                [z3.Bool(f'{a.fullname}_{b.fullname}') for a in d2]
                for b in d1])
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
        # A list for adding general other constraints
        self._constraints = []

    def constraints(self):
        return (self.cons_sanity()
                + self.cons_rowcol()
                + self.cons_grid()
                + self.cons_domains()
                + self._constraints)

    def add(self, *cons):
        self._constraints.extend(cons)

    def add_constraint(self, *pairs):
        vnames = [self.get_info(p[0]) for p in pairs]
        opts = [self.domain(p[1]) for p in pairs]

        def add_it(func):
            for choices in product(*opts):
                if not func(*[c.val for c in choices]):
                    vs = [self.vars[v, c] for (v, c) in zip(vnames, choices)]
                    self.add(z3.AtMost(*vs, len(vs) - 1))
            return func
        return add_it

    def uniques(self):
        '''Return a list of all z3 variables being solved for.'''
        xvars = sum(sum((tuple(x.values())
                         for x in self.vcats.values()), ()), [])
        gvars = sum((list(grid.flat) for grid in self.all_grids), [])
        return xvars + gvars

    def all_solutions(self, limit=10):
        for soln in all_solns(self, limit=limit):
            yield CatSoln(self, soln)

    def solve(self, unique=True):
        soln = solve(self, unique=unique)
        return CatSoln(self, soln)

    @fn.collecting
    def cons_domains(self):
        '''Return domain constraints.

        The returned list of constraints constrains every variable in
        self.xcats to be in the domain it belongs to.
        '''
        for (name, domain) in self.xcats.items():
            vlist = sum(self.vcats[name].values(), [])
            yield from domain.cons(vlist)
            if domain.unique:
                vals = self.vcats[name][self.categories[0]]
                for a, b in combos(vals, 2):
                    yield a != b

    @fn.collecting
    def cons_rowcol(self):
        '''Return basic structural constraints.

        The returned list of constraints will require every row and column of
        every grid to have exactly one 1.
        '''
        for grid in self.all_grids:
            for i in range(self.num_items):
                yield z3.PbEq([(g, 1) for g in grid[i, :]], 1)
                yield z3.PbEq([(g, 1) for g in grid[:, i]], 1)

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
                        yield z3.Implies(
                            z3.And(a2b[i, j], b2c[j, k]), a2c[i, k])
        for cat in self.xcats:
            for f1, f2 in combos(self.categories, 2):
                a2b = self.vgrids[f1][f2]
                cat1 = self.vcats[cat][f1]
                cat2 = self.vcats[cat][f2]
                for i in range(self.num_items):
                    for j in range(self.num_items):
                        yield (a2b[i, j] == False) | (cat1[i] == cat2[j])

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
                    if bgrid[i, j] is not None:
                        yield vgrid[i, j] == bgrid[i, j]

    def cons_exclude(self, soln: Solution):
        '''Return a constraint that excludes this particular solution.'''
        return [z3.Or(*(v != soln.model.eval(v) for v in self.uniques()))]

    def mk_exclude(self, *vals, **cats):
        keys = [self.get_info(k) for k in vals]
        x = []
        for a, b in combos(keys, 2):
            if a.cat == b.cat:
                continue
            x.append(~self.vars[a.fullname, b.fullname])
        for xcat, vals in cats.items():
            for val in vals:
                for k in keys:
                    x.append(self.vars[k, xcat] != val)
        return z3.And(x)

    def exclude(self, *vals, **cats):
        self.add(self.mk_exclude(*vals, **cats))
