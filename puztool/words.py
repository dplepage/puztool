from functools import lru_cache
from itertools import product
from pathlib import Path
import os
import re

from .pipeline import Modifier
from .result import val
from .text import swappable

here = Path(__file__).parent

data_path = os.environ.get("PUZTOOL_DATA_DIR", "data/wordlists")

default_data_dir = here/data_path

def make_tree(wordlist, reversed=False):
    '''Build a prefix tree from a wordlist.

    The returned structure is a dict mapping characters to subdicts; a dict will
    have the key '' if it is a word. For example:

    >>> make_tree(['bat', 'bath', 'bats', 'baths']) == {
    ... 'b': {
    ...     'a': {
    ...         't': {
    ...             '': 'bat',
    ...         'h': {
    ...             '': 'bath',
    ...             's': {
    ...                 '': 'baths'}},
    ...             's': {
    ...                 '': 'bats'}}}}}
    True
    '''
    tree = dict()
    for word in wordlist:
        top = tree
        for char in word[::-1] if reversed else word:
            top = top.setdefault(char, {})
        top[''] = word
    return tree

def find_words(tree):
    for c, v in tree.items():
        if c == '':
            yield v
        else:
            yield from find_words(v)

class WordTree(object):
    def __init__(self, list=None, tree=None, reversed=False):
        if tree is None:
            tree = make_tree(list, reversed)
        self.reversed = reversed
        self.tree = tree

    def __getitem__(self, word):
        top = self.tree
        for c in word[::-1] if self.reversed else word:
            if c not in top:
                return WordTree(tree={}, reversed=self.reversed)
            top = top[c]
        return WordTree(tree=top, reversed=self.reversed)

    def __contains__(self, word):
        top = self.tree
        for c in word[::-1] if self.reversed else word:
            if c not in top:
                return False
            top = top[c]
        if '' in top and top[''] == word:
            return True
        return False

    def has(self, prefix):
        top = self.tree
        for c in prefix[::-1] if self.reversed else prefix:
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
                yield from self[letter].search(rest)

# Lazy loading wordlists and trees
class WordList(Modifier):
    def __init__(self, words=None, path=None):
        self._path = path
        self._words = words

    def _process(self, seq):
        return (x for x in seq if val(x) in self.set)

    def open(self):
        return self.path.open()

    @property
    @lru_cache()
    def list(self):
        if self._words is not None:
            return self._words
        with self._path.open() as f:
            return f.read().splitlines()

    @property
    @lru_cache()
    def set(self):
        return set(self.list)

    @property
    @lru_cache()
    def prefix_tree(self):
        return WordTree(self.list)

    @property
    @lru_cache()
    def suffix_tree(self):
        return WordTree(self.list, reversed=True)

    def search(self, sets):
        for chars in product(*sets):
            word = ''.join(chars)
            if word in self.set:
                yield word

    def matches(self, regex):
        if isinstance(regex, str):
            regex = re.compile(regex)
        for word in self:
            if regex.match(word):
                yield word

    def patmatch(self, pattern):
        for word in self:
            if len(word) != len(pattern):
                continue
            if swappable(word, pattern):
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

    def __len__(self):
        return len(self.set)

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
                self._cache[attr] = WordList(path=path)
            elif attr == 'default':
                # No default -> fall back on OSPD
                # because it's the only one checked in to github
                self._cache[attr] = self.ospd
        return self._cache[attr]

    def __getattr__(self, attr):
        return self.get(attr)

    def __contains__(self, name):
        if name in self._cache: return True
        return (self.data_dir/f'{name}.txt').exists()

lists = Lists()
