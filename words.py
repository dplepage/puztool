from functools import lru_cache
from itertools import product
from pathlib import Path
import os

from .modifier import In

here = Path(__file__).parent

data_path = os.environ.get("PUZTOOL_DATA_DIR", "data/wordlists")

default_data_dir = here/data_path

def make_tree(wordlist):
    tree = dict()
    for word in wordlist:
        top = tree
        for char in word:
            top = top.setdefault(char, {})
        top[''] = word
    return tree

def find_words(tree):
    for c, val in tree.items():
        if c == '':
            yield val
        else:
            yield from find_words(val)

class WordTree(object):
    def __init__(self, list=None, tree=None):
        if tree is None:
            tree = make_tree(list)
        self.tree = tree

    def __getitem__(self, word):
        top = self.tree
        for c in word:
            if c not in top:
                return WordTree(tree={})
            top = top[c]
        return WordTree(tree=top)

    def __contains__(self, word):
        top = self.tree
        for c in word:
            if c not in top:
                return False
            top = top[c]
        if '' in top and top[''] == word:
            return True
        return False

    def has(self, prefix):
        top = self.tree
        for c in prefix:
            if c not in top:
                return False
            top = top[c]
        return True

    @property
    def word(self):
        return self.tree.get("", None)

    def words(self):
        return list(self.iterwords())

    def iterwords(self):
        return find_words(self.tree)

    def search(self, sets):
        if not len(sets):
            if self.word:
                yield self.word
            return
        head, *rest = sets
        for letter in head:
            if self.has(letter):
                yield from self.search(rest)


# Lazy loading wordlists and trees

# Coincidentally, the `set` property is exactly what modifiers.In uses, so we
# can just inherit from In to turn WordLists into filters!
class WordList(In):
    def __init__(self, path):
        self.path = path

    def open(self):
        return self.path.open()

    @property
    @lru_cache()
    def list(self):
        return self.open().read().splitlines()

    @property
    @lru_cache()
    def set(self):
        return set(self.list)

    @property
    @lru_cache()
    def tree(self):
        return WordTree(self.list)

    def search(self, sets):
        for chars in product(*sets):
            word = ''.join(chars)
            if word in self.set:
                yield word

    def search_phrases(self, sets):
        '''Warning: This'll probably produce a lot of junk.'''
        for chars in product(*sets):
            yield from self.find_phrases(''.join(chars))

    def find_phrase(self, text):
        return next(self.find_phrases(text))

    def find_phrases(self, text):
        return (' '.join(p) for p in self._find_phrases(text, ()))

    def _find_phrases(self, text, prefix):
        for i in range(len(text), 0, -1):
            word, rest = text[:i], text[i:]
            if word in self.set:
                if not rest:
                    yield prefix+(word,)
                else:
                    yield from (self._find_phrases(rest, prefix=prefix+(word,)))

    def __contains__(self, word):
        return word in self.set

    def __iter__(self):
        yield from self.list

class Lists:
    def __init__(self, data_dir=None):
        self._cache = {}
        self.data_dir = data_dir or default_data_dir

    def get(self, attr):
        if attr.startswith('__'):
            return object.__getattr__(self, attr)
        if attr not in self._cache:
            path = self.data_dir/'{}.txt'.format(attr)
            if path.exists():
                self._cache[attr] = WordList(path)
        return self._cache[attr]

    def __getattr__(self, attr):
        return self.get(attr)

    def __contains__(self, name):
        if name in self._cache: return True
        return (self.data_dir/f'{name}.txt').exists()

lists = Lists()
