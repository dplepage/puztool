import itertools
import time
import typing as t

from .pipeline import modifier, item_mod
from .result import val, Result
from .text import lowers, shifts


class _Auto:
    pass


@modifier
def vals(seq):
    return (val(x) for x in seq)


@modifier
def res(seq):
    return (Result(x) for x in seq)


@modifier
def printing(seq, prov=False):
    for item in seq:
        if prov:
            print(repr(item))
        else:
            print(val(item))
        yield item


@modifier
def info(seq, progress=True):
    start = time.process_time()
    c = 0
    for item in seq:
        c += 1
        if progress:
            if c == 1:
                print("\r1 item... ", end='')
            else:
                print(f"\r{c} items... ", end='')
        yield item
    end = time.process_time()
    print(f"\r{c} items in {end-start:.2}s".format(c, end - start))


@item_mod
def deletions(result):
    '''Return all strings generated from the input by removing one letter.'''
    s = result.val
    for i in range(len(s)):
        yield result.extend(''.join(s[:i]) + ''.join(s[i + 1:]))


@item_mod
def additions(result):
    '''Return all strings generated from the input by adding one letter.'''
    result = Result.ensure(result)
    s = result.val
    for i in range(len(s) + 1):
        for c in lowers:
            yield result.extend(''.join(s[:i]) + c + ''.join(s[i:]))


@item_mod
def perms(result):
    '''Return all strings generated from the input by transposition.'''
    for p in itertools.permutations(result.val):
        yield result.extend(''.join(p))


@item_mod
def substrings(result):
    '''Return all strings generated from the input by transposition.'''
    for i in range(len(result.val)):
        for j in range(i + 1, len(result.val) + 1):
            yield result.extend(result.val[i:j])


@item_mod
def of_length(result, low=1, high=None):
    if len(result.val) < low:
        return
    if high is not None and len(result.val) > high:
        return
    yield result


@item_mod
def caesars(result):
    '''Return all strings generated from the input by caesar shifting.'''
    for (i, s) in shifts(result.val):
        yield result.extend(s, 'shift-{}'.format(i))


@modifier
def in_(items, seq):
    '''Modifier that filters out words not in a set.

    Useful with word lists.
    '''
    return (item for item in seq if val(item) in items)


@modifier
def filter(predicate, seq):
    return (item for item in seq if predicate(val(item)))


@modifier
def unique(seq):
    items = set()
    for x in seq:
        if val(x) in items:
            continue
        items.add(val(x))
        yield x


def apply(fn, *a, item_arg=None, **kw):
    def mod(seq):
        for item in seq:
            if item_arg is not None:
                kw[item_arg] = item
                r = fn(*a, **kw)
            else:
                r = fn(item, *a, **kw)
            if isinstance(r, t.Generator):
                yield from r
            else:
                yield r
    return modifier(mod)()
