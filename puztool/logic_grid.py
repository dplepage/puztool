from collections import namedtuple
from itertools import combinations as combos, product
import re
import funcy as fn
import numpy as np
try:
    import Numberjack as nj
except ImportError:
    nj = None
try:
    from IPython.core.display import HTML
except ImportError:
    HTML = None
try:
    import pandas as pd
except ImportError:
    pd = None

from .text import lowers


class _Conflict:
    def __init__(self, *terms):
        self.terms = []
        for term in terms:
            if isinstance(term, _Conflict):
                self.terms.extend(term.terms)
            else:
                self.terms.append(term)

    def add(self, term):
        self.terms.append(term)

class ValInfo(namedtuple("ValInfo", ['cat', 'val', 'fullname', 'idx'])):
    '''Info about a single value in a logic grid.

    cat - the string name of the category it belongs to
    val - the actual value
    fullname - a unique identifier for this value, typically "<cat>:<val>"
    idx - the index in the category list corresponding to this value
    '''
    def __str__(self):
        return self.fullname

class AmbiguityError(KeyError): pass

class CatMan:
    '''Manager for discrete categories.

    The input should be a dict or dict-like object whose keys are the names of
    the categories and whose values are ordered lists of the possible values in
    each category.

    This object allows you to get information about a value in an intelligent
    way. For example:

    >>> c = CatMan(dict(
    ... color=['red', 'green', 'blue'],
    ... size=['small', 'medium', 'large']))
    >>> c['color:red']
    >>> c['red']

    '''
    def __init__(self, cats):
        self.catmap = {}
        self.lookup = {}
        self.categories = list(cats)
        for cat, domain in cats.items():
            self.catmap[cat] = []
            for idx, val in enumerate(domain):
                info = ValInfo(cat, val, '{}:{}'.format(cat,val), idx)
                self.catmap[cat].append(info)
                self.lookup[info.fullname] = info
                old = self.lookup.get(info.val)
                if old is None:
                    self.lookup[info.val] = info
                else:
                    self.lookup[info.val] = _Conflict(old, info)

    @property
    def num_cats(self):
        return len(self.catmap)

    @property
    def num_items(self):
        return len(self.catmap[self.categories[0]])

    def domain(self, cat):
        return self.catmap[cat]

    @property
    def all_domains(self):
        return self.catmap

    def get_info(self, value, cat=None):
        '''Get info about a value.

        If the input is a ValInfo, it'll just be returned. Otherwise, we return
        the ValInfo from our internal lookup table, raising a KeyError if it's
        not there or an AmbiguityError if it's an ambiguous name.
        '''
        if isinstance(value, ValInfo):
            return value
        v = self.lookup.get(value, None)
        if v is None:
            raise KeyError(value)
        if isinstance(v, _Conflict):
            if cat is not None:
                value = '{}:{}'.format(cat, value)
                return self.get_info(value)
            msg = "{} could be any of: {}"
            terms = ', '.join(str(t) for t in v.terms)
            raise AmbiguityError(msg.format(value, terms))
        return v

    def get_cat(self, value):
        return self.get_info(value).cat

    def get_fullname(self, value):
        return self.get_info(value).fullname

    def get_index(self, value):
        return self.get_info(value).idx

    def __getitem__(self, key):
        if isinstance(key, (list, tuple)):
            name, val = key
            key = '{}:{}'.format()
        if key in self.lookup:
            return self.get_info(key)
        return self.catmap[key]


class Grid(CatMan):
    '''A logic grid.

    The input is a dictionary of categories where each key is a category name
    and each value is a list or set of possible values for one category (the
    order within each column is irrelevant).

    The input can also be a pandas DataFrame where the column names are the
    category names and the values are the category values.

    The Grid then creates a bunch of numpy object arrays, such that
    g.grids[key1][key2][x,y] indicates whether the row with value x for key1 has
    value y for key2.

    For example, suppose your data is three names, favorite colors, and signs:

    >>> from puztool.parse import parse_table
    >>> frame = parse_table("""
    name      color   sign
    Brita     Blue    Ares
    Galal     Green   Scorpio
    Parvaneh  Red     Virgo
    """, header=0)
    >>> g = Grid(frame)

    Each value gets assigned a unique name of the form <category>:<value>. In
    the above case, for example, 'name:Brita' refers to the value 'Brita' in the
    name category. However, the helper functions will also infer the category if
    the term is unambiguous - 'Brita' also refers to that value (but it would
    not if 'Brita' was also a value in another category).

    '''
    def __init__(self, categories):
        super().__init__(categories)
        self.pairs = list(combos(self.categories, 2)) # this comes up a lot
        self.grids = {n:{} for n in self.categories}
        for f1, f2 in self.pairs:
            g = np.empty((self.num_items,self.num_items), dtype='object')
            # Both entries point to different views of the same matrix
            self.grids[f1][f2] = g
            self.grids[f2][f1] = g.T

    def exclude(self, *vals):
        '''Indicate that these values are mutually exclusive.

        This marks all intersections of values in vals as False.
        '''
        infos = map(self.get_info, vals)
        for i1, i2 in combos(infos, 2):
            if i1.cat == i2.cat:
                continue
            self.grids[i1.cat][i2.cat][i1.idx, i2.idx] = False

    def require(self, *vals):
        '''Indicate that these values must go together

        This marks all intersections of values in vals as True.

        It will complain if two values are from the same category, as requiring
        both would mean there are no solutions to the grid.
        '''
        infos = map(self.get_info, vals)
        for i1, i2 in combos(infos, 2):
            if i1.cat == i2.cat:
                raise ValueError("Cannot require both {} and {}".format(i1, i2))
            self.grids[i1.cat][i2.cat][i1.idx, i2.idx] = True

    def requireOne(self, first, options):
        '''Indicate that one of options must go with first.

        All values in options should be from the same category, and first should
        be from a different one.
        '''
        i1 = self.get_info(first)
        options = [self.get_info(opt) for opt in options]
        categories = set(opt.cat for opt in options)
        if len(set(categories)) > 1:
            raise ValueError("requireOne options must be in a single category.")
        cat = list(categories)[0]
        g = self.grids[i1.cat][cat]
        old = list(g[i1.idx, :])
        g[i1.idx, :] = False
        for i2 in options:
            g[i1.idx, i2.idx] = old[i2.idx] or None

    ### Helpers for jsingler.de links

    def _get_encoded_grid(self, val):
        # Map each category to a letter and return the list of entries matching
        # val in the form e.g. a3b5
        letters = dict(zip(self.categories, lowers))
        for f1,f2 in self.pairs:
            a = letters[f1]
            b = letters[f2]
            for i in range(self.num_items):
                for j in range(self.num_items):
                    if self.grids[f1][f2][i,j] == val:
                        yield '{}{}{}{}'.format(a,i,b,j)

    def _encl(self, list):
        return '!({})'.format(','.join(str(e) for e in list))


    def _get_params(self):
        d = dict(at='s', ms='s', nc=self.num_cats, ni=self.num_items, v=0)
        encl = self._encl
        def esc(s):
            # The escaping they use seems a little weird so I didn't bother.
            # Just strip any chars that would ruin the link.
            return re.sub('\W', '', s)
        items = []
        for cat in self.categories:
            items.append(encl(esc(str(x.val)) for x in self.domain(cat)))
        d['items'] = encl(items)
        d['n'] = encl(self._get_encoded_grid(False))
        d['p'] = encl(self._get_encoded_grid(True))
        return ','.join('{}:{}'.format(k,v) for (k,v) in d.items())

    def get_link(self):
        '''Get a link that will display this grid on jsingler.de'''
        base = 'http://www.jsingler.de/apps/logikloeser/?language=en#({})'
        return base.format(self._get_params())

    def html_link(self):
        '''get_link, but returns an HTML object that will display in ipython.'''
        l = self.get_link()
        if HTML is None:
            return l
        return HTML("<a href='{0}'>{0}</a>".format(l))

class Solution:
    def __init__(self, solver, soln):
        self.rows = soln
        self.solver = solver
        self._grid = self._df = None

    @property
    def grid(self):
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
    def df(self):
        if pd is None:
            raise ImportError("pandas not installed")
        if self._df is None:
            cols = list(self.solver.categories) + list(self.solver.xcats)
            self._df = pd.DataFrame(self.rows, columns=cols)
        return self._df


class Solver(Grid):
    def __init__(self, grid_categories, extra_categories=None):
        if nj is None:
            raise ValueError("Numberjack not installed, cannot use Solver.")
        super().__init__(grid_categories)
        self.xcats = extra_categories or dict()
        # Create grids of variables for each pair of categories
        self.vgrids = {n:{} for n in self.categories}
        self.all_grids = []
        for f1, f2 in self.pairs:
            vname = '{}_{}.'.format(f1,f2)
            mat = nj.Matrix(self.num_items, self.num_items, vname)
            # Like the normal grid, these are two views of the same object
            self.vgrids[f1][f2] = mat
            self.vgrids[f2][f1] = mat.col
            self.all_grids.append(mat)
        # Create variables for each extra category
        self.vcats = {}
        for (name, domain) in self.xcats.items():
            v = self.vcats[name] = {}
            for cat in self.categories:
                vname = '{}_{}'.format(cat, name)
                v[cat] = nj.VarArray(self.num_items, domain, vname)
        self.vars = VarLookup(self)
        # Precompute sanity constraints
        self.constraints = (
            self.cons_rowcol() + self.cons_sanity()
        )
        self.model = self.solver = None
        self.soln = self._soln_df = self._soln_grid = None

    def add(self, *cons):
        self.constraints.extend(cons)

    def _make_soln(self):
        c1 = self.categories[0]
        soln = []
        for i1 in self.domain(c1):
            row = {c1:i1.val}
            for c2 in self.categories[1:]:
                for i2 in self.domain(c2):
                    is_set = self.vgrids[c1][c2][i1.idx, i2.idx].get_value()
                    if is_set:
                        row[c2] = i2.val
                        break
            for xcat in self.xcats:
                row[xcat] = self.vcats[xcat][c1][i1.idx].get_value()
            soln.append(row)
        return Solution(self, soln)

    def solve(self, fmt='dict', solvername='MiniSat'):
        if self.model is None:
            self.constraints.extend(self.cons_grid())
            self.model = nj.Model(*self.constraints)
            self.solver = self.model.load(solvername)
        assert self.solver.solve()
        return self._make_soln()


    @fn.collecting
    def cons_rowcol(self):
        '''Return basic structural nj constraints.

        The returned list of constraints will require every row and column of
        every grid to have exactly one 1.
        '''
        for grid in self.all_grids:
            for i in range(self.num_items):
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
        for f1, f2, f3 in combos(self.categories, 3):
            a2b = self.vgrids[f1][f2]
            b2c = self.vgrids[f2][f3]
            a2c = self.vgrids[f1][f3]
            for i in range(self.num_items):
                for j in range(self.num_items):
                    for k in range(self.num_items):
                        yield (a2b[i,j] & b2c[j,k])<=a2c[i,k]
        for cat in self.xcats:
            for f1, f2 in combos(self.categories, 2):
                a2b = self.vgrids[f1][f2]
                cat1 = self.vcats[cat][f1]
                cat2 = self.vcats[cat][f2]
                for i in range(self.num_items):
                    for j in range(self.num_items):
                        yield (a2b[i,j]==0) | (cat1[i] == cat2[j])

    @fn.collecting
    def cons_grid(self):
        '''Return nj constraints for all entered information.

        This encodes everything added via include, exclude, etc.
        '''
        for f1, f2 in self.pairs:
            bgrid = self.grids[f1][f2]
            vgrid = self.vgrids[f1][f2]
            for i in range(self.num_items):
                for j in range(self.num_items):
                    if bgrid[i,j] is not None:
                        yield vgrid[i,j] == bgrid[i,j]

    def add_constraint(self, *pairs):
        vars = [self.get_info(p[0]) for p in pairs]
        opts = [self.domain(p[1]) for p in pairs]
        def add_it(fn):
            for choices in product(*opts):
                if not fn(*[c.val for c in choices]):
                    vs = [self.vars[v, c] for (v, c) in zip(vars, choices)]
                    self.add(nj.Sum(vs) < len(vs))
            return fn
        return add_it

class VarLookup:
    '''Helper for indexing'''
    def __init__(self, solver):
        self.s = solver

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

