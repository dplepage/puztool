from .text import letters

class DropQuote:
    def __init__(self, columns, wordlist):
        self.columns = [list(c) for c in columns]
        self.wordlist = wordlist
        self.update_sets()

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
