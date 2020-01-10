from itertools import combinations as combos
import re
import typing as t
import numpy as np

try:
    from IPython.core.display import HTML
except ImportError:
    HTML = None

from ..text import lowers

class _Conflict:
    def __init__(self, *terms:t.Tuple[t.Union["_Conflict", str]]):
        self.terms = []
        for term in terms:
            if isinstance(term, _Conflict):
                self.terms.extend(term.terms)
            else:
                self.terms.append(term)

    def add(self, term:str):
        self.terms.append(term)

class ValInfo(t.NamedTuple):
    '''Info about a single possible value in a logic grid.

    cat - the string name of the category it belongs to
    val - the actual value
    fullname - a unique identifier for this value, typically "<cat>:<val>"
    idx - the index in the category list corresponding to this value
    '''
    cat: str
    val: str
    idx: int

    @property
    def fullname(self) -> str:
        return '{}:{}'.format(self.cat, self.val)

    def __str__(self) -> str:
        return self.fullname

class AmbiguityError(KeyError):
    pass

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
    ValInfo(cat='color', val='red', idx=0)
    >>> c['red']
    ValInfo(cat='color', val='red', idx=0)
    '''
    def __init__(self, cats):
        self.catmap = {}
        self.lookup = {}
        self.categories = list(cats)
        for cat, domain in cats.items():
            self.catmap[cat] = []
            for idx, val in enumerate(domain):
                info = ValInfo(cat, val, idx)
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
            key = f'{name}:{val}'
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

    def _encl(self, items):
        return '!({})'.format(','.join(str(e) for e in items))

    def _get_params(self):
        d = dict(at='s', ms='s', nc=self.num_cats, ni=self.num_items, v=0)
        encl = self._encl
        def esc(s):
            # The escaping they use seems a little weird so I didn't bother.
            # Just strip any chars that would ruin the link.
            return re.sub(r'\W', '', s)
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
