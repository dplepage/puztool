'''Tools for parsing free text.

parse_grid, aliased to pg, tries to parse grids sensibly. It will look for
comma-separated or tab-separated lines, then fall back on whitespace-separated
(unless you explicitly provide a `sep` regex); it will reject any guessed
separator that results in a non-rectangular grid. It will also convert strings
to numbers if every cell has a numberable string, and will truncate lines at
'#' unless you set comment=None (or some other comment-start character)

parse_table, aliased to pt, tries to parse tabular data via pandas.read_table.

'''
import io
import re
import funcy as fn
import numpy as np
import pandas as pd
from pandas.io.clipboard import clipboard_get
from .grids import subrect


def guess_splitter(lines):
    '''Make a guess for what regex will split these lines reasonably.'''
    if all('\t' in line for line in lines):
        return '\t'
    elif all(',' in line for line in lines):
        return r', *'
    elif all(re.search(r'\W', line) for line in lines):
        return r'\W+'
    return None


def parse_grid(data=None, sep=None, strip='udr', comment='#', empty='',
               ignore_blank=True, dtype=None, on_empty=None, quiet=False):
    msg = fn.identity if quiet else print
    if data is None:
        data = clipboard_get()
    lines = data.splitlines()
    # Strip leading blank line (generally from pasting something into triple
    # quotes)
    if lines and lines[0] == '':
        lines = lines[1:]
    if not lines:
        msg("No data to parse.")
        return np.empty((0, 0), dtype=dtype)
    # Strip comments and blank lines
    if comment:
        lines = [re.sub(comment + '.*$', '', line) for line in lines]
    if ignore_blank:
        lines = [line for line in lines if line]
    # Determine splitter and split lines into items
    if sep is None:
        sep = guess_splitter([line for line in lines if line])
    if sep is not None and sep != '':
        msg(f"Separating by {sep!r}")
        lines = [re.split(sep, line) for line in lines]
    else:
        msg(f"Separating by character")
        lines = [list(line) for line in lines]
    # Pad out shape to rectangular
    lens = [len(line) for line in lines]
    width = max(lens)
    for line in lines:
        if len(line) < width:
            line.extend([''] * (width - len(line)))
    grid = np.array(lines, dtype=str)
    grid[grid == empty] = ''
    if strip:
        grid = subrect(grid, dirs=strip)
    # Determine dtype
    if dtype is None:
        dtype = object
        if all(re.match(r'^\d+$', d) for d in grid.flat if d):
            dtype = int
        elif all(re.match(r'^\d+\.?\d*$', d) for d in grid.flat if d):
            dtype = float
    # xform coerces items to type
    if dtype is object:
        xform = lambda x: x if x != empty else None
    else:
        xform = fn.iffy(dtype, default=on_empty)
        dtype = object if '' in grid.flat and on_empty is None else dtype
    h, w = grid.shape
    result = np.array([[xform(val) for val in line]
                       for line in grid], dtype=dtype)
    msg(f"Array is {h} rows x {w} cols of type {result.dtype}")
    return result


def parse_table(table=None, sep=r'\s+', header=None, conv=None, **kw):
    if table is None:
        table = clipboard_get()
    if isinstance(table, str):
        table = io.StringIO(table)
    if conv is not None:
        kw['converters'] = dict(enumerate(conv))
    kw.setdefault("comment", '#')
    return pd.read_table(table, sep=sep, header=header, **kw)


pt = parse_table
pg = parse_grid

pg.dots = fn.partial(pg, sep='', empty='.')


if __name__ == '__main__':
    # TODO proper tests
    def check(a, b):
        pa = pg(a, dedent=True)
        if pa.shape != b.shape or not (pa == b).all():
            print("MISMATCH parsing:")
            print(a)
            print("EXPECTED:")
            print(b)
            print("GOT:")
            print(pa)

    check("1 2 3 4 5", np.array([[1, 2, 3, 4, 5]]))
    check("1 2 3 4 5a", np.array([['1', '2', '3', '4', '5a']]))
    check('''
    1 2 3 4 5 6
    7 8 9 10 11 12
    13 14 15 16 17 18
    ''', np.arange(18).reshape(3, 6) + 1)
    check('''
    a b c d e
    f g h i j
    ''', np.array([['a', 'b', 'c', 'd', 'e'], ['f', 'g', 'h', 'i', 'j']]))
    check('''
    aa b c d e
    f g h i j
    ''', np.array([['aa', 'b', 'c', 'd', 'e'], ['f', 'g', 'h', 'i', 'j']]))
    check('''
    a a b c d e
    f g h i j
    ''', np.array(['a', 'a', 'b', 'c', 'd', 'e'],
                  ['f', 'g', 'h', 'i', 'j', '']))
    check('''
    1 2 3, 4 5 6
    7 8 9, 10 11 12
    ''', np.array([['1 2 3', '4 5 6'], ['7 8 9', '10 11 12']]))
