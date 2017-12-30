from itertools import combinations as combos
import funcy as fn
import numpy as np
try:
    import Numberjack as nj
except ImportError:
    nj = None
import pandas as pd

from .text import lowers


class Grid:
    '''A logic grid.

    The input is a data frame where each column is a set of possible values for
    one category; the order within each column is irrelevant.

    The Grid then creates a bunch of numpy object arrays, such that
    g.grids[key1][key2][x,y] indicates whether the row with value x for key1 has
    value y for key2.

    Grid also assumes all possible values have unique names - internally
    everything is indexed by numbers, but all the helper functions take names
    and infer which category is being discussed.

    For example, suppose your data is three names, favorite colors, and signs:

    >>> from puztool.parse import parse_table
    >>> frame = parse_table("""
    Brita     Blue    Ares
    Galal     Green   Scorpio
    Parvaneh  Red     Virgo
    """, names=['name', 'color', 'sign'])
    >>> g = Grid(frame)

    g now has grids mapping names to colors, colors to signs, and names to
    signs, though at the moment they're all filled with Nones:
    >>> g.grids['color']['name']
    array([[None, None, None],
           [None, None, None],
           [None, None, None]], dtype=object)

    '''
    def __init__(self, frame):
        self.frame = frame
        self.fields = fields = list(frame.columns)
        self.pairs = list(combos(self.fields, 2))
        self.nc = len(self.fields)
        self.ni = len(frame)
        self.grids = {n:{} for n in fields}
        for f1, f2 in self.pairs:
            g = np.zeros((self.ni,self.ni), dtype='object')
            g[:,:] = None
            self.grids[f1][f2] = g
            self.grids[f2][f1] = g.T
        self.domain_map = {}
        for key in fields:
            for i, val in enumerate(self.frame[key]):
                assert val not in self.domain_map
                self.domain_map[val] = (key, i)

    def exclude(self, *vals):
        # none of vals can be the same row
        for v1, v2 in combos(vals, 2):
            d1, k1 = self.domain_map[v1]
            d2, k2 = self.domain_map[v2]
            if d1 == d2: continue
            self.grids[d1][d2][k1,k2] = False

    def include(self, *vals):
        for v1, v2 in combos(vals, 2):
            d1, k1 = self.domain_map[v1]
            d2, k2 = self.domain_map[v2]
            if d1 == d2: continue
            self.grids[d1][d2][k1,k2] = True

    def requireOne(self, first, options):
        d1, k1 = self.domain_map[first]
        d2, _ = self.domain_map[options[0]]
        for opt in options[1:]:
            assert self.domain_map[opt][0] == d2
        g = self.grids[d1][d2]
        old = list(g[k1, :])
        g[k1, :] = False
        for opt in options:
            _, k2 = self.domain_map[opt]
            g[k1,k2] = old[k2] or None

    def _get_encoded_grid(self, val):
        letters = dict(zip(self.fields, lowers))
        for f1,f2 in combos(self.fields, 2):
            a = letters[f1]
            b = letters[f2]
            for i in range(self.ni):
                for j in range(self.ni):
                    if self.grids[f1][f2][i,j] == val:
                        yield '{}{}{}{}'.format(a,i,b,j)

    def _encl(self, list):
        return '!({})'.format(','.join(str(e) for e in list))


    def _get_params(self):
        d = dict(at='s', ms='s', nc=self.nc, ni=self.ni, v=0)
        encl = self._encl
        d['items'] = encl([encl(self.frame[c]) for c in self.frame])
        d['n'] = encl(self._get_encoded_grid(False))
        d['p'] = encl(self._get_encoded_grid(True))
        return ','.join('{}:{}'.format(k,v) for (k,v) in d.items())

    def get_link(self):
        # Useful tool for viewing these grids.
        base = 'http://www.jsingler.de/apps/logikloeser/?language=en#({})'
        return base.format(self._get_params())


class Solver:
    def __init__(self, grid):
        if nj is None:
            raise ValueError("Numberjack not installed, cannot use Solver.")
        self.grid = grid
        for key in ['fields', 'ni', 'nc', 'pairs']:
            setattr(self, key, getattr(grid,key))
        self.vgrids = {n:{} for n in self.fields}
        self.all_grids = []
        for f1, f2 in self.pairs:
            mat = nj.Matrix(self.ni, self.ni, '{}_{}.'.format(f1,f2))
            self.vgrids[f1][f2] = mat
            self.vgrids[f2][f1] = mat.col
            self.all_grids.append(mat)
        self.vars = VarLookup(self)
        self.constraints = (
            self.cons_rowcal() + self.cons_sanity() + self.cons_logic()
        )
        self.model = self.solver = None
        self.soln = None
        self.soln_grid = None

    def add(self, *cons):
        self.constraints.extend(cons)

    def _make_soln_grid(self):
        self.soln_grid = Grid(self.grid.frame)
        for f1, f2 in self.pairs:
            self.soln_grid.grids[f1][f2][:,:]=[
                [v.get_value() for v in row] for row in self.vgrids[f1][f2]]

    def _make_soln_df(self):
        g = self.soln_grid
        frame = g.frame
        f1 = self.fields[0]
        self.soln = pd.DataFrame(frame[f1])
        for f2 in self.fields[1:]:
            labels = frame[f2]
            self.soln[f2] = [labels[row.argmax()] for row in g.grids[f1][f2]]


    def solve(self, solvername='MiniSat'):
        if self.model:
            raise ValueError("Already solved!")
        self.model = nj.Model(*self.constraints)
        self.solver = self.model.load(solvername)
        assert self.solver.solve()
        self._make_soln_grid()
        self._make_soln_df()


    @fn.collecting
    def cons_rowcal(self):
        '''Return basic structural nj constraints.

        The returned list of constraints will require every row and column of
        every grid to have exactly one 1.
        '''
        for grid in self.all_grids:
            for i in range(self.ni):
                yield nj.Gcc(grid.row[i], {1:(1,1)})
                yield nj.Gcc(grid.col[i], {1:(1,1)})

    @fn.collecting
    def cons_sanity(self):
        '''Return sanity-check nj constraints.

        The returned list of constraints will require that for every three
        categories A, B, and C, AB[i,j] & BC[j,k] -> AC[i,k].

        For example, if your categories are first name, last name, and hair
        color, this will emit constraints ensuring that if the first name
        'Alice' goes with the last name 'Svetlana' and the last name 'Svetlana'
        goes with the hair color 'Teal', then the first name 'Alice' must go
        with the hair color 'Teal'.
        '''
        for f1, f2, f3 in combos(self.fields, 3):
            a2b = self.vgrids[f1][f2]
            b2c = self.vgrids[f2][f3]
            a2c = self.vgrids[f1][f3]
            for i in range(self.ni):
                for j in range(self.ni):
                    for k in range(self.ni):
                        yield (a2b[i,j] & b2c[j,k])<=a2c[i,k]
    @fn.collecting
    def cons_logic(self):
        '''Return nj constraints for all entered information.

        This encodes everything added via include, exclude, etc.
        '''
        for f1, f2 in self.pairs:
            bgrid = self.grid.grids[f1][f2]
            vgrid = self.vgrids[f1][f2]
            for i in range(self.ni):
                for j in range(self.ni):
                    if bgrid[i,j] is not None:
                        yield vgrid[i,j] == bgrid[i,j]

class VarLookup:
    '''Helper for indexing'''
    def __init__(self, solver):
        self.g = solver

    def __getitem__(self, tup):
        a,b = tup
        d1, k1 = self.g.grid.domain_map[a]
        d2, k2 = self.g.grid.domain_map[b]
        return self.g.vgrids[d1][d2][k1,k2]

