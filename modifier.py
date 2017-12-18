import itertools
from .text import shifts

class Result:
    '''A string plus some indication of where it came from.

    This is useful for e.g. a function to find words in a grid - it can  return
    the words but also tell you where in the grid it found each word.

    '''
    def __init__(self, val, provenance=()):
        self.val = val
        self.provenance = provenance

    def extend(self, new_val, provenance=None):
        if provenance is None:
            provenance = self.val
        return Result(new_val, self.provenance + (provenance,))

    def __repr__(self):
        return '<{}>'.format(self.val)

    def __str__(self):
        return self.val


class TextModifier:
    '''Chainable function for manipulating strings.

    In a statically-typed language, this would probably be implemented as a
    monad, but we're not in a statically typed language.

    Basically, this wraps any function that takes a Result and returns an
    iterable of new Results, and turns that function into a more flexible object
    that can be composed with other modifiers, run on iterables, and so forth.

    The Result type is just a string plus a "provenance" tuple indicating where
    this string came from.

    So, for example, you might define a function that yields all single-letter
    deletions of a string:

    >>> def deletions(result):
    ...     s = result.val
    ...     for i in range(len(s)):
    ...         yield result.extend(s[:i]+s[i+1:])
    >>> for item in deletions(Result("foo")):
    ...     print('{0.val} ({0.provenance})'.format(item))
    oo (('foo',))
    fo (('foo',))
    fo (('foo',))

    When wrapped in a TextModifier, this function will also work on strings and
    lists:

    >>> deletions = TextModifier(deletions)
    >>> list(deletions("foo"))
    [<oo>, <fo>, <fo>]
    >>> list(deletions(["foo", "bar"]))
    [<oo>, <fo>, <fo>, <ar>, <br>, <ba>]

    It can also now be chained with other modifiers:

    >>> from puztool import lists
    >>> chain = deletions | Unique() | In(lists.ospd)
    >>> list(chain(["fooe", "barrk"]))
    [<foe>, <bark>]


    The provenance can be any object. This is useful if you want to define a
    "spout" that returns a list of strings plus some information about where
    they came from.

    For a great example of this, see gridsearch.py - the iter_strings() function
    extracts all strings in any direction from a grid of letters, and includes
    the start and end coordinates of each string in the provenance. If you want
    to find all strings in a grid that are words with one extra letter, you
    might use the above chain to run `chain(iter_strings(the_grid))`. The
    results will tell you what the actual words are that are in the grid with
    one extra letter each, but the provenance for each will tell you what the
    word was before a letter was deleted and where in the grid the original
    string was.
    '''

    def __init__(self, fn):
        self.fn = fn

    def __call__(self, val):
        if isinstance(val, (str, Result)):
            yield from self._onval(val)
        else:
            for item in val:
                yield from self._onval(item)

    def _onval(self, val):
        if isinstance(val, str):
            val = Result(val)
        yield from self.fn(val)

    def __or__(self, other):
        return TextModifier(lambda val: other(self(val)))



@TextModifier
def deletions(result):
    '''Return all strings generated from the input by removing one letter.'''
    s = result.val
    for i in range(len(s)):
        yield result.extend(''.join(s[:i])+''.join(s[i+1:]))


@TextModifier
def perms(result):
    '''Return all strings generated from the input by transposition.'''
    for p in itertools.permutations(result.val):
        yield result.extend(''.join(p))


@TextModifier
def caesars(result):
    '''Return all strings generated from the input by caesar shifting.'''
    for (i, s) in shifts(result.val):
        yield result.extend(s, 'shift-{}'.format(i))

class In(TextModifier):
    '''Modifier that filters out words not in a set.

    Useful with word lists.
    '''
    def __init__(self, set):
        self.set = set
        super().__init__(lambda s:[s] if s.val in set else [])


class Unique(TextModifier):
    '''Modifier that filters duplicate words.

    Note that this ignores provenance - if a source generates the same word from
    several different provenances, only the first one generated will make it
    through Unique
    '''
    def __init__(self):
        self.set = set()
        super().__init__(self._uniquify)

    def _uniquify(self, result):
        if result.val in self.set:
            return
        self.set.add(result.val)
        yield result

