'''Tools for parsing free text.

parse_grid, aliased to pg, tries to parse grids sensibly. It will look for
comma-separated or tab-separated lines, then fall back on whitespace-separated
(unless you explicitly provide a `sep` regex); it will reject any guessed
separator that results in a non-rectangular grid. It will also convert strings
to numbers if every cell has a numberable string, and will truncate lines at '#'
unless you set comment=None (or some other comment-start character)

parse_table, aliased to pt, tries to parse tabular data via pandas.read_table.

'''
from textwrap import dedent
import io
import re
import numpy as np
import pandas as pd
from pandas.io.clipboard import clipboard_get

def guess_splitter(lines):
    if all('\t' in line for line in lines):
        return r'\t'
    elif all(',' in line for line in lines):
        return r', *'
    elif all(re.search("\W", line) for line in lines):
        return r'\W+'
    return None


def parse_grid(data=None, sep=None, nostrip=False, comment='#', jagged=False):
    if data is None:
        data = clipboard_get()
    if not nostrip:
        data = dedent(data.rstrip()).strip()
    lines = data.splitlines()
    if comment:
        lines = [re.sub(comment+'.*$', '', line).strip() for line in lines]
        lines = [line for line in lines if line]
    if sep is None:
        sep = guess_splitter(lines)
    if sep is not None and sep != '':
        lines = [re.split(sep, line) for line in lines]
    else:
        lines = [list(line) for line in lines]
    all_items = sum(lines, [])
    mode = str
    if all(re.match('^\d+$', d) for d in all_items):
        mode = int
    elif all(re.match('^\d+\.?\d*$', d) for d in all_items):
        mode = float
    is_rect = all(len(line) == len(lines[0]) for line in lines)
    if is_rect:
        jagged = False
    if jagged:
        return np.array([
            np.array([mode(val) for val in line]) for line in lines])
    data = np.array([mode(val) for val in all_items])
    if is_rect:
        data = data.reshape(len(lines), -1)
    return data


def parse_lists(data=None, sep=None, nostrip=False, comment='#'):
    return parse_grid(data, sep, nostrip, comment, jagged=True)


def parse_table(table=None, sep='\s+', header=None, conv=None, **kw):
    if table is None:
        table = clipboard_get()
    if isinstance(table, str):
        table = io.StringIO(table)
    if conv is not None:
        kw['converters'] = dict(enumerate(conv))
    kw.setdefault("comment", '#')
    return pd.read_table(table, sep=sep, header=header, **kw)



pt = parse_table
pl = parse_lists
pg = parse_grid


if __name__ == '__main__':
    # TODO proper tests
    def check(a, b):
        correct = False
        try:
            correct = (pg(a) == b).all()
        except:
            pass
        if not correct:
            print("MISMATCH parsing:")
            print(a)
            print("EXPECTED:")
            print(b)
            print("GOT:")
            print(pg(a))
            import sys; sys.exit(1)

    check("1 2 3 4 5", np.array([1,2,3,4,5]))
    check("1 2 3 4 5a", np.array(['1','2','3','4','5a']))
    check('''
    1 2 3 4 5 6
    7 8 9 10 11 12
    13 14 15 16 17 18
    ''', np.arange(18).reshape(3,6)+1)
    check('''
    0 1 2 3 4 5 6
    7 8 9 10 11 12
    13 14 15 16 17 18
    ''', np.arange(19))
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
    ''', np.array(['a', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j']))
    check('''
    1 2 3, 4 5 6
    7 8 9, 10 11 12
    ''', np.array([['1 2 3', '4 5 6'],['7 8 9', '10 11 12']]))
