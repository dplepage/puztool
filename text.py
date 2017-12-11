'''
Manipulate text in various modes.

This module recognizes three modes, each with a one-letter identifier:
a - alphabet mode; it's just a string
o - ordinal mode; it's an array of character ordinals
i - index mode; it's an array of 1-indexed alphabet indices

In index mode, a=1, b=2, etc. and all nonalphabetic characters are 0s.

Note that converting between a and o is basically just vectorized ord/char, and
therefore is lossless, but index mode can't represent nonalphabetic characters
or capitalization. Thus

>>> as_a(as_i("Foo-12*bar"))
"foo....bar"

'''
import re
import operator
from math import ceil
import string
import numpy as np
from collections import Counter

# Monkeypatch Counter to support flattening

def uncount(counter):
    return ''.join(x*y for (x,y) in counter.items())

Counter.uncount = uncount

# alias letter collections
lowers = string.ascii_lowercase
uppers = string.ascii_uppercase
letters = lowers+uppers

is_letter = np.vectorize(lambda s: s in letters)

def normalize(s):
    '''Lowercase s and remove all non-alphabetic characters.'''
    return ''.join([c for c in s.lower() if c in lowers])

def as_np(arr):
    '''Coerce a string, number, or list to a numpy array'''
    if np.isscalar(arr):
        if np.isreal(arr):
            return np.array([arr])
        return np.array(list(arr))
    elif isinstance(arr, str):
        return np.array(list(arr))
    else:
        return np.array(arr)

def ident(arr):
    '''Guess which mode an object is in.'''
    arr = as_np(arr)
    if not np.issubdtype(arr.dtype, np.number):
        # Assume it's a string or object type of some sort
        return 'a'
    if arr.max() < 27:
        return 'i'
    # Assume it's a bunch of actual ordinals
    return 'o'

def as_(arr, which):
    if which == 'a':
        return as_a(arr)
    if which == 'i':
        return as_i(arr)
    if which == 'o':
        return as_o(arr)
    raise ValueError("Unrecognized type: {}".format(which))

def as_a(arr):
    t = ident(arr)
    arr = as_np(arr)
    if t == 'a':
        return ''.join(arr)
    if t == 'i':
        ords = arr - 1 + ord('a')
        ords[ords==ord('a')-1] = ord('.')
        return ''.join(map(chr, ords))
    if t == 'o':
        return ''.join(map(chr, arr))
    raise ValueError("Unidentifiable array?")

def as_i(arr):
    a = as_a(arr)
    nums = np.array(list(map(ord, a.lower()))) - ord('a')+1
    nums[(nums > 25) | (nums < 0)] = 0
    return nums

def as_o(arr):
    a = as_a(arr)
    return np.array(list(map(ord, a)))

def shift(arr, i):
    '''Ceasar shift some data.

    Nonalphabetic characters will be left as is.

    The result will be coerced back to the detected type of the input:

    >>> # Shift text
    >>> shift("Hello, world!", 1)
    'Ifmmp, xpsme!'
    >>> # Shift alphabetic indices
    >>> shift([ 8,  5, 25,  0], 2)
    array([10,  7,  1,  0])
    >>> # Shift ordinals
    >>> shift([72, 101, 108, 108, 111, 33], 3)
    array([ 75, 104, 111, 111, 114,  33])
    '''
    t = ident(arr)
    ords = as_o(arr)
    caps = ords == ords.clip(ord('A'), ord('Z'))
    lows = ords == ords.clip(ord('a'), ord('z'))
    ords[caps] = (ords[caps]-ord('A')+i)%26+ord('A')
    ords[lows] = (ords[lows]-ord('a')+i)%26+ord('a')
    return as_(ords, t)

def shifts(s):
    '''Yield all possible shifts of s'''
    for i in range(26):
        yield (i, shift(s, i))

def show_shifts(s):
    '''Show all possible shifts of s'''
    for (i, s2) in shifts(s):
        print('{:2} - {}'.format(i, s2))

def unshift(c1, c2):
    '''Compute how much you'd need to shift c1 to get c2'''
    return (ord(c2)-ord(c1))%26
