'''A tool for helping with drop quotes.

This is mainly intended for use within a jupyter notebook.

'''
import numpy as np

from .text import letters
from .misc import smoosh
from .words import lists

class Segment:
    def __init__(self, start, end, key, word=None):
        self.start = start
        self.end = end
        self.key = key
        self._word = word

    @property
    def word(self):
        return self._word

    @word.setter
    def word(self, value):
        if value is not None and len(value) != len(self):
            raise ValueError(f"{value} isn't length {len(self)}")
        self._word = value

    def __len__(self):
        return self.end - self.start

    def __repr__(self):
        return f'Segment({self.start!r}, {self.end!r}, {self.key!r}, {self._word!r})'

def make_segs(s):
    keys = iter('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ')
    segs = {}
    seg = None
    for i, c in enumerate(s):
        if c != '?':
            if seg is not None:
                k = next(keys)
                segs[k]=Segment(seg, i, k)
                seg = None
            continue
        if seg is None:
            seg = i
    if seg:
        k = next(keys)
        segs[k] = Segment(seg, len(s), k)
    return segs


class DropQuoteBank:
    def __init__(self, columns, wordlist=lists.default):
        self.columns = [list(c) for c in columns]
        self.wordlist = wordlist
        self.segs = None
        self.width = len(self.columns)
        self.height = max(len(c) for c in self.columns)
        self.update_sets()

    def p(self):
        cols = self.columns
        x = np.empty((len(cols), max(len(c) for c in cols)), dtype=str)
        if x.shape[1] == 0:
            print("<bank empty>")
            return
        x[:] = ' '
        for i,c in enumerate(self.columns):
            x[i, :len(c)] = sorted(c)
        print('\n'.join(smoosh(x[:,::-1].T)))

    def update_sets(self):
        self.sets = [set(c) for c in self.columns]

    def query(self, start, end):
        start = start%self.width
        end = end%self.width
        if start < end:
            sets = self.sets[start:end]
        else:
            sets = self.sets[start:] + self.sets[:end]
        return list(self.wordlist.search(sets))

    def remove(self, start, value):
        start = start%self.width
        end = (start + len(value))%self.width
        if start < end:
            cols = self.columns[start:end]
        else:
            cols = self.columns[start:] + self.columns[:end]
        pairs = list(zip(cols, value))
        if not all((c not in letters or c in col) for (col, c) in pairs):
            s = '{}:{}'.format(start, end)
            raise ValueError("Not in {}: {}".format(s, value))
        for col, v in zip(cols, value):
            if v in letters:
                col.remove(v)
        self.update_sets()

    def add(self, start, value):
        start = start%self.width
        end = (start + len(value))%self.width
        if start < end:
            cols = self.columns[start:end]
        else:
            cols = self.columns[start:] + self.columns[:end]
        for col, c in zip(cols, value):
            col.append(c)
        self.update_sets()

    def __getitem__(self, k):
        if not isinstance(k, slice):
            return list(self.columns[k])
        if k.step not in [None, 1]:
            raise ValueError("Illegal step: {}".format(k.step))
        return self.query(k.start, k.stop)

    def __setitem__(self, k, value):
        if not isinstance(k, slice):
            raise ValueError("Can only set ranges on DropQuote instances")
        if k.step not in [None, 1]:
            raise ValueError("Illegal step: {}".format(k.step))
        self.remove(k.start, value)


class DropQuote:
    def __init__(self, columns, gridstr, wordlist=lists.default):
        self.bank = DropQuoteBank(columns, wordlist)
        self.segs = make_segs(gridstr.replace('\n', ''))
        self.width = self.bank.width
        self.height = int(np.ceil(len(gridstr)/self.width))

    def p(self):
        self.bank.p()
        print('-'*self.width)
        gstr = list(' '*self.height*self.width)
        for key, seg in self.segs.items():
            if seg.word:
                gstr[seg.start:seg.end] = seg.word
            else:
                gstr[seg.start:seg.end] = key*len(seg)
        for i in range(0, len(gstr), self.width):
            print(''.join(gstr[i:i+self.width]))

    def message(self):
        words = [seg.word or key*len(seg) for key, seg in self.segs.items()]
        return ' '.join(words)

    def get_seg(self, key):
        return self.segs[str(key)]

    def do_obvious(self):
        while True:
            progress = False
            for key, seg in self.segs.items():
                if seg.word:
                    continue
                opts = self[key]
                if len(opts) == 1:
                    print(f"{key} -> {opts[0]}")
                    self[key] = opts[0]
                    progress = True
            if not progress:
                break

    def opts(self):
        for key, seg in self.segs.items():
            if seg.word:
                continue
            options = self[key]
            n = len(options)
            if n > 6:
                options = options[:5]
            s = ', '.join(options)
            if n > 6:
                print(f'{key} -> {s} ({n-5} more)')
            else:
                print(f'{key} -> {s}')

    def __getitem__(self, key):
        seg = self.get_seg(key)
        if seg.word:
            return [seg.word]
        return self.bank[seg.start:seg.end]

    def __setitem__(self, key, word):
        seg = self.get_seg(key)
        if seg.word:
            if seg.word == word:
                return
            self.bank.add(seg.start, seg.word)
        seg.word = word
        self.bank.remove(seg.start, word)

    def __delitem__(self, key):
        seg = self.get_seg(key)
        if seg.word:
            self.bank.add(seg.start, seg.word)
            seg.word = None
