import numpy as np

from .text import letters
from .misc import smoosh
from .words import lists

class Segment:
    def __init__(self, start, end):
        self.start = start
        self.end = end

    @property
    def len(self):
        return self.end - self.start

    def __repr__(self):
        return f'Segment({self.start!r}, {self.end!r})'

def make_segs(s):
    segs = []
    seg = None
    for i,c in enumerate(s):
        if c != '?':
            if seg is not None:
                segs.append(Segment(seg, i))
                seg = None
            continue
        if seg is None:
            seg = i
    return segs


class DropQuote:
    def __init__(self, columns, gridstr=None, wordlist=lists.default):
        self.columns = [list(c) for c in columns]
        self.wordlist = wordlist
        self.segs = None
        self.width = len(self.columns)
        self.height = max(len(c) for c in self.columns)
        if gridstr:
            self.segs = make_segs(gridstr)
            self.height = int(np.ceil(len(gridstr)/self.width))
        self.update_sets()

    def p(self):
        cols = self.columns
        x = np.empty((len(cols), max(len(c) for c in cols)), dtype=str)
        x[:] = ' '
        for i,c in enumerate(self.columns):
            x[i, :len(c)] = sorted(c)
        print('\n'.join(smoosh(x[:,::-1].T)))
        if self.segs:
            print('-'*len(self.columns))
            x = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            gstr = list(' '*self.height*self.width)
            for i, seg in enumerate(self.segs):
                gstr[seg.start:seg.end] = x[i%len(x)]*seg.len
            for i in range(0, len(gstr), len(self.columns)):
                print(''.join(gstr[i:i+len(self.columns)]))

    def update_sets(self):
        self.sets = [set(c) for c in self.columns]

    def __getitem__(self, k):
        if not isinstance(k, slice):
            return list(self.columns[k])
        if k.step not in [None, 1]:
            raise ValueError("Illegal step: {}".format(k.step))
        start, stop, _ = k.indices(len(self.columns))
        if start < stop:
            sets = self.sets[start:stop]
        else:
            sets = self.sets[start:] + self.sets[:stop]
        return list(self.wordlist.search(sets))

    def __setitem__(self, k, value):
        if not isinstance(k, slice):
            raise ValueError("Can only set ranges on DropQuote instances")
        if k.step not in [None, 1]:
            raise ValueError("Illegal step: {}".format(k.step))
        start, stop, _ = k.indices(len(self.columns))
        if start < stop:
            cols = self.columns[start:stop]
        else:
            cols = self.columns[start:] + self.columns[:stop]
        pairs = list(zip(cols, value))
        if not all((c not in letters or c in col) for (col, c) in pairs):
            s = '{}:{}:{}'.format(range.start, range.stop, range.step)
            raise ValueError("Not in {}: {}".format(s, value))
        for col, v in zip(cols, value):
            if v in letters:
                col.remove(v)
        self.update_sets()
