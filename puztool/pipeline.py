'''
A collection of tools for pipelining operations on iterables

The main type is Pipeline, which represents a flow of data from a source through
any number of modifiers to a terminal.

In practice, you usually do not need to create pipelines yourself, but can
instead use the `source`, `modifier`, and `terminal` decorators:

>>> @source
... def get_words():
...     return ("gemini", "jodhpurs", "balderdash", "facetiously")
>>> @modifier
... def alph(seq):
...     for x in seq:
...         vowels = ''.join(c for c in x if c in 'aeiouy')
...         if vowels == ''.join(sorted(vowels)):
...             yield (x, vowels)
>>> @terminal
... def joinlines(seq):
...     return '\\n'.join(f'{a} {b}' for a,b in seq)
>>> print(get_words() | alph() | joinlines())
gemini eii
jodhpurs ou
facetiously aeiouy

# This module provides several useful terminals and modifiers on the helper
# object P:

>>> get_words() | P.all()
['gemini', 'jodhpurs', 'balderdash', 'facetiously']
>>> get_words() | P.first()
'gemini'
>>> get_words() | P.limit(2).all()
['gemini', 'jodhpurs']


Pipeline objects will also automatically interpret functions as item modifiers,
so you can pipe them to plain functions and get reasonable results:

>>> get_words() | (lambda s:s[:3]) | P.all()
['gem', 'jod', 'bal', 'fac']


Pipelines can be combined without all their pieces to yield segments that can be
mixed and matched:

>>> x = (lambda s:s[:3]) | alph() | P.all()
>>> ['food', 'bart'] | x
[('foo', 'oo'), ('bar', 'a')]
'''

import abc
import typing as t
import itertools
import attr
import funcy as fy
import pandas as pd

from .result import Result, val


def lift(fn):
    '''Converts a function from item->item or item->seq to seq->seq

    This is basically monadic lifting for the sequence monad, if that means
    anything to you.

    The input should be a function that takes a single argument and either
    returns a single argument or returns a generator; the returned function will
    take a sequence and will yield all results of calling the original function
    on each element of that sequence.

    For example:

    >>> def add_one(x): return x+1
    >>> def repeat(x): yield from [x, x, x]
    >>> list(lift(add_one)([1, 2, 3]))
    [2, 3, 4]
    >>> list(lift(repeat)([1, 2, 3]))
    [1, 1, 1, 2, 2, 2, 3, 3, 3]

    Note that only generators are flattened - if you return a simple iterable,
    it'll just be added as a single element:

    >>> def repeat_list(x): return [x, x, x]
    >>> list(lift(repeat_list)([1, 2, 3]))
    [[1, 1, 1], [2, 2, 2], [3, 3, 3]]
    '''
    def newfn(seq):
        for item in seq:
            result = fn(item)
            if isinstance(result, t.Generator):
                yield from result
            else:
                yield result
    return newfn


@attr.s(frozen=True)
class Pipeline:
    '''A Pipeline represents a flow of data from a source to a terminus.

    A complete pipeline has a source, which is a callable that returns an
    iterable, a series of modifiers, each of which takes an iterable and returns
    a new iterable, and a terminus, which takes an iterable and returns some
    other value.

    Executing a pipeline of (src, (mod1, mod2), term) therefore simply means
    returning term(mod2(mod1(src()))).

    However, pipelines can also be incomplete - lacking a source, terminus, or
    both - and pipelines can be joined together with the | operator. Thus, you
    can create modular components and chain them together with ease:

    >>> def addone(seq):
    ...     return (x+1 for x in seq)
    >>> p1 = Pipeline(src=lambda: range(5))
    >>> p2 = Pipeline(mods=(addone,))
    >>> p3 = Pipeline(term=list)
    >>> p1 | p3
    [0, 1, 2, 3, 4]
    >>> p1 | p2 | p3
    [1, 2, 3, 4, 5]
    >>> p1 | p2 | p2 | p3
    [2, 3, 4, 5, 6]

    The pieces can also be piped together separately and reused:

    >>> addtwo = p2 | p2
    >>> p1 | addtwo | addtwo | p3
    [4, 5, 6, 7, 8]

    Piping is semi-intelligent: if you pipe a pipeline to or from a callable,
    that callable is assumed to be a function that operates on a single item,
    and is lifted up to be a modifier that calls this function on each item:

    >>> p1 | (lambda x:x*2) | p3
    [0, 2, 4, 6, 8]

    If the callable returns a generator, it will be flattened (in the style of
    a monadic bind):

    >>> def one_and_two(x):
    ...     yield x
    ...     yield x*2
    >>> p1 | one_and_two | p3
    [0, 0, 1, 2, 2, 4, 3, 6, 4, 8]

    Finally, a noncallable piped into a Pipeline will be treated as an iterable
    source:

    >>> [1, 2] | addtwo | p3
    [3, 4]

    Note that while the smart piping can be useful, it obvious only works if at
    least one item in a given pipe pair is

    '''
    _src: t.Callable[[], t.Iterable] = attr.ib(default=None)
    _mods: t.Tuple[t.Callable[[t.Iterable], t.Iterable], ...] = attr.ib(factory=tuple)
    _term: t.Callable[[t.Iterable], t.Any] = attr.ib(default=None)

    def set_src(self, src):
        if self._src is not None:
            raise ValueError("Cannot double-source Pipeline")
        return attr.evolve(self, src=src)

    def set_term(self, terminus):
        if self._term is not None:
            raise ValueError("Cannot double-terminate Pipeline")
        return attr.evolve(self, term=terminus)

    def mod_left(self, mod):
        return attr.evolve(self, _mods=(mod,) + self._mods)

    def mod_right(self, mod):
        return attr.evolve(self, _mods=self._mods+(mod,))

    @classmethod
    def from_src(cls, src):
        if not callable(src):
            return cls(src=lambda:src)
        return cls(src=src)

    @classmethod
    def from_src_fn(cls, fn):
        def newfn(*a, **kw):
            return cls(src=fn(*a, **kw))
        return newfn

    @classmethod
    def from_mod(cls, mod):
        return cls(mods = (mod,))

    @classmethod
    def from_item_mod(cls, mod):
        return cls(mods = (lift(mod),))

    @classmethod
    def from_term(cls, term):
        return cls(term=term)

    def execute(self, debug=False):
        if not self._src:
            raise ValueError("No source")
        if not self._term:
            raise ValueError("No term")
        seq = self._src()
        if debug:
            print(f"S - {self._src} - {seq}")
        for m in self._mods:
            seq = m(seq)
            if debug:
                print("M", m, seq)
        seq = self._term(seq)
        if debug:
            print("T", self._term, seq)
        return seq

    def __iter__(self):
        if self._term:
            return self.execute()
        else:
            yield from self | as_iter()

    def __str__(self):
        return " -> ".join(str(s) for s in (self._src,)+self._mods+(self._term,))

    @property
    def complete(self) -> bool:
        return self._src is not None and self._term is not None

    @classmethod
    def as_pipeline(cls, other):
        if isinstance(other, Pipeline):
            return other
        if hasattr(other, '_as_pipeline'):
            return other._as_pipeline()
        if isinstance(other, t.Callable):
            return Pipeline.from_item_mod(other)
        return Pipeline(src=lambda:other)

    def pipe_to(self, other):
        other = Pipeline.as_pipeline(other)
        if other._src:
            raise ValueError("Can't pipe to src")
        if self._term:
            raise ValueError("Can't pipe out of term")
        return Pipeline(src=self._src, mods=self._mods+other._mods, term=other._term)

    def pipe_from(self, other):
        return Pipeline.as_pipeline(other).pipe_to(self)

    def __or__(self, other):
        result = self.pipe_to(other)
        if result._src and result._term:
            return result.execute()
        return result

    def __ror__(self, other):
        result = self.pipe_from(other)
        if result._src and result._term:
            return result.execute()
        return result

    def all(self) -> "Pipeline":
        return self | as_list()

    def df(self, unpack=None, columns=None) -> pd.DataFrame:
        return self | as_df(unpack=unpack, columns=columns)


def source(fn_or_iterable):
    if callable(fn_or_iterable):
        return lambda *a, **kw: \
            Pipeline.from_src(lambda: fn_or_iterable(*a, **kw))
    return Pipeline.from_src(lambda: fn_or_iterable)


def terminal(fn):
    return lambda *a, **kw: \
        Pipeline.from_term(lambda seq: fn(*a, **kw, seq=seq))


def modifier(fn):
    return lambda *a, **kw: \
        Pipeline.from_mod(lambda seq: fn(*a, **kw, seq=seq))


def item_mod(fn):
    return lambda *a, **kw: \
        Pipeline.from_item_mod(lambda item: fn(item, *a, **kw))



class Pipeable(abc.ABC):
    def _as_pipeline(self) -> "Pipeline":
        raise NotImplementedError()

    def __or__(self, other):
        return self._as_pipeline() | other

    def __ror__(self, other):
        return other | self._as_pipeline()


class Source(Pipeable):
    '''Abstract base class to make anything a Source'''
    @abc.abstractmethod
    def _generate(self) -> t.Iterable:
        raise NotImplementedError()

    def _as_pipeline(self) -> "Pipeline":
        return Pipeline.from_src(self._generate)


class Terminus(Pipeable):
    @abc.abstractmethod
    def _consume(self, seq: t.Iterable):
        raise NotImplementedError()

    def _as_pipeline(self) -> "Pipeline":
        return Pipeline.from_term(self._consume)


class Modifier(Pipeable):
    @abc.abstractmethod
    def _process(self, seq: t.Iterable) -> t.Iterable:
        raise NotImplementedError()

    def _as_pipeline(self) -> "Pipeline":
        return Pipeline.from_mod(self._process)


@terminal
def as_iter(seq):
    return iter(seq)


@terminal
def as_list(seq):
    return list(seq)


@terminal
def as_df(seq, unpack=None, columns=None):
    '''Unpack a sequence into a pandas DataFrame.

    The type of the first tiem '''
    try:
        fst = fy.next(seq)
    except StopIteration:
        return pd.DataFrame()
    if unpack is None:
        if isinstance(fst, Result):
            unpack = True
    if unpack is True and columns is None:
        columns = ['value'] + [f'prov{i}' for i in range(len(fst.provenance))]
    seq = itertools.chain([fst], seq)
    if unpack:
        if isinstance(fst, (list, tuple)):
            items = ((tuple(item.val) + item.provenance) for item in seq)
        else:
            items = (((item.val,) + item.provenance) for item in seq)
    else:
        items = iter(seq)
    return pd.DataFrame(items, columns=columns)


def staticmod(fn):
    return staticmethod(modifier(fn))


def as_join(join: t.Union[str, t.Callable]) -> t.Callable:
    '''Make a join function from a string or function.

    This is a convenience for functions that take a 'join' function. If the
    input is a function, it's passed through unchanged:

    >>> j1 = as_join(lambda *a: sum((list(x) for x in a), []))
    >>> j1('abc')
    ['a', 'b', 'c']

    If instead it's a string, the return value is that string's .join():

    >>> j2 = as_join(' ')
    >>> j2('abc')
    'a b c'
    '''
    if isinstance(join, str):
        return join.join
    return join

class PipelineHelper(Pipeline):
    '''Helper class for a bunch of common pipeline filters and terminals.

    >>> P = PipelineHelper()
    >>> range(3) |  P.first()
    0
    >>> range(3) | P.all()
    [0, 1, 2]
    >>> ['a', 'b', 'c'] | P.join()
    'abc'
    >>> range(3) | P.limit(2).all()
    [0, 1]
    >>> range(5) | P.filter(lambda x:x%2).all()
    [1, 3]
    >>> range(5) | P.exclude(1, 2).all()
    [0, 3, 4]
    '''
    @staticmethod
    @terminal
    def first(seq):
        return fy.first(seq)

    @staticmethod
    @terminal
    def join(join='', *, seq):
        return as_join(join)(seq)

    @staticmod
    def limit(n, seq):
        for i, v in enumerate(seq):
            if i >= n:
                break
            yield v

    filter = staticmod(fy.filter)
    flatten = staticmod(fy.flatten)

    @staticmethod
    def exclude(*args):
        return PipelineHelper.filter(lambda x: x not in args)

    @staticmod
    def chunks(n, join=None, *, seq):
        if join is None:
            yield from fy.chunks(n, seq)
        else:
            if isinstance(join, str):
                join = join.join
            for item in fy.chunks(n, seq):
                yield join(item)

    @staticmod
    def split(sep=' ', *, seq):
        for item in seq:
            r = Result.ensure(item)
            for i, piece in enumerate(val(r).split(sep)):
                yield r.extend(piece, (val(r), i))

    @staticmod
    def parallel(*mods, seq):
        iters = itertools.tee(seq, len(mods))
        yield from fy.interleave(*[(i | m) for (m, i) in zip(mods, iters)])


P = PipelineHelper()
