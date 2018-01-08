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
'foo....bar'

'''
import string
from collections import Counter

import numpy as np
import pandas as pd

# Monkeypatch Counter to support flattening

def uncount(counter):
    '''Flatten this counter.

    >>> c = Counter("foofoobarbar") - Counter("foobar")
    >>> c.uncount()
    'foobar'
    '''
    return ''.join(x*y for (x,y) in counter.items())

Counter.uncount = uncount

# alias letter collections
lowers = string.ascii_lowercase
uppers = string.ascii_uppercase
letters = lowers+uppers

# make some vectorized helpers you can do them to arrays
is_letter = np.vectorize(lambda s: s in letters)
is_lower = np.vectorize(lambda s: s == s.lower())
is_upper = np.vectorize(lambda s: s == s.upper())

def normalize(s):
    '''Lowercase s and remove all non-alphabetic characters.'''
    return ''.join([c for c in s.lower() if c in lowers])

norm_all = np.vectorize(normalize)

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

def imod(arr):
    r'''Mod an array of alphabet indices to stay within the alphabet.

    >>> imod([0,1,25,26,27,109])
    array([26,  1, 25, 26,  1,  5])

    This is particularly useful because as_a looks for numbers outside [1,26]
    to guess whether an array is alphabet indices or character ordinals:

    >>> as_a([21, 29, 1, 12, 5, 7, 15, 14])
    '\x15\x1d\x01\x0c\x05\x07\x0f\x0e'
    >>> as_a(imod([21, 29, 1, 12, 5, 7, 15, 14]))
    'ucalegon'

    '''
    return (np.array(arr)-1)%26 + 1

def as_(arr, which):
    '''Convert an object to alphabet, index, or ordinal mode.'''
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
    nums[(nums > 26) | (nums < 1)] = 0
    return nums

def as_o(arr):
    a = as_a(arr)
    return np.array(list(map(ord, a)))

def lmasks(ords):
    '''Find which items in an ordinal array are letters.

    The return value is a tuple of (lettermask, uppermask, lowermask), such that
    ords[uppermask] selects all uppercase characters in ords, ords[lowermask]
    selects all lowercase characters in ords, and lettermask is
    uppermask+lowermask.
    '''
    uppermask = ords == ords.clip(ord('A'), ord('Z'))
    lowermask = ords == ords.clip(ord('a'), ord('z'))
    return (uppermask | lowermask, uppermask, lowermask)

def omod(ords, uppermask, lowermask):
    r'''Wrap uppercase/lowercase values to stay in their ordinal ranges.

    This is useful when you've just applied some mathematical operation to a
    string containing both upper and lowercase letters, and you want to make
    sure that values that have moved beyond a or z get wrapped back to stay
    within their alphabet.

    >>> s = "Hello, world!"
    >>> ords = as_o(s)
    >>> lmask, upmask, lowmask = lmasks(ords)
    >>> ords[lmask] += 20
    >>> as_a(ords) # Most chars have been shifted out of the alphabet
    '\\y\x80\x80\x83, \x8b\x83\x86\x80x!'
    >>> as_a(omod(ords, upmask, lowmask)) # chars stay in alphabet
    'Byffi, qilfx!'
    '''
    ords[uppermask] = (ords[uppermask]-ord('A'))%26+ord('A')
    ords[lowermask] = (ords[lowermask]-ord('a'))%26+ord('a')
    return ords

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
    lmask, uppermask, lowermask = lmasks(ords)
    ords[lmask] += i
    ords = omod(ords, uppermask, lowermask)
    return as_(ords, t)

def shiftdf(*words, in_=None):
    '''Given a set of words, return a dataframe of all caesar shifts of them.

    If in_ is not None, values that aren't in in_ will be left blank. This is
    useful when, for example, you want to know all the shifts of a set of words
    that are valid words.
    '''
    if in_:
        def mod(s, i):
            x = shift(s, i)
            if x not in in_:
                return ''
            return x
    else:
        mod = shift
    return pd.DataFrame([[mod(word,i) for word in words] for i in range(26)])

def shifts(s):
    '''Yield all possible caesar shifts of s.'''
    for i in range(26):
        yield (i, shift(s, i))

def show_shifts(s):
    '''Print all possible shifts of s.

    Note that if you're using jupyter lab/notebook, shiftdf will be easier to
    read because jupyter formats dataframes nicely. If you're not using jupyter,
    you probably should be.
    '''
    for (i, s2) in shifts(s):
        print('{:2} - {}'.format(i, s2))

def unshift(c1, c2):
    '''Compute how much you'd need to shift c1 to get c2.

    If x == shift(y, 3), then unshift(x,y) will be 3.

    If you pass in multicharacter strings, this'll just compute the unshift for
    the first one.
    '''
    return (ord(c2[0])-ord(c1[0]))%26


def vigenere(arr, keyword):
    '''Vigenere shift some data.

    Nonalphabetic characters will be left as is.

    The result will be coerced back to the detected type of the input:

    >>> # text
    >>> vigenere("Hello, world!", 'potato')
    'Wselh, kdfed!'
    >>> # alphabetic indices
    >>> vigenere([ 8,  5, 25,  3, 7, 0], 'abc')
    array([8, 6, 1, 3, 8, 0])
    >>> # ordinals
    >>> vigenere([72, 101, 108, 108, 111, 33], 'abc')
    array([ 72, 102, 110, 108, 112,  33])
    '''
    t = ident(arr)
    ords = as_o(arr)
    lets, caps, lows = lmasks(ords)
    n = len(ords[lets])
    # repeat keyword as many times as needed to match lengths
    cipher = as_i(keyword*(1+n//len(keyword)))[:n]-1
    ords[lets] += cipher
    ords = omod(ords, caps, lows)
    return as_(ords, t)

def unvigenere(arr, keyword):
    '''Inverse of vigenere.

    >>> vigenere("Hello, world!", 'potato')
    'Wselh, kdfed!'
    >>> unvigenere("Wselh, kdfed!", 'potato')
    'Hello, world!'

    '''
    t = ident(arr)
    ords = as_o(arr)
    lets, caps, lows = lmasks(ords)
    n = len(ords[lets])
    # repeat keyword as many times as needed to match lengths
    cipher = 27-as_i(keyword*(1+n//len(keyword)))[:n]
    ords[lets] += cipher
    ords = omod(ords, caps, lows)
    return as_(ords, t)


class UnswappableError(ValueError): pass

def swap(a, b, c, alphabet=lowers):
    '''Exchange all occurences of characters in b with characters in c.

    >>> swap("bagel", "ba", "an")
    'angel'
    >>> swap("proton", "rot", "iem")
    'piemen'
    >>> swap("abcdefg", "abc", "efg")
    'efgdabc'

    Nonsensical swaps will raise UnswappableErrors:

    >>> swap("abbdefg", "abc", "ggg")
    Traceback (most recent call last):
        ...
    puztool.text.UnswappableError: Conflict - b or a->g?
    '''
    shift = getswap(b,c, alphabet=alphabet)
    return a.translate(str.maketrans(alphabet, shift))

def _swap1(a, b, c):
    return a.translate(str.maketrans(b, c))

def getswap(first, second, alphabet=lowers):
    '''Compute a substitution cipher that maps a to b.

    The return value will be a string subst satisfying
    a.translate(str.maketrans(alphabet, subst)) == b

    This will raise an UnswappableError if no such string exists.

    >>> getswap("werewolf", "monomial")
    'fbcdolghejkawripqnstuvmxyz'
    >>> swap("werewolf", lowers, "fbcdolghejkawripqnstuvmxyz")
    'monomial'

    >>> getswap("werewolf", "dividend")
    Traceback (most recent call last):
      ...
    puztool.text.UnswappableError: Conflict - f or w->d?

    >>> getswap("werewolf", "apoplexy")
    Traceback (most recent call last):
      ...
    puztool.text.UnswappableError: Conflict - w->l or a?

    >>> getswap("werewolf", "foo")
    Traceback (most recent call last):
      ...
    puztool.text.UnswappableError: Length mismatch (8 vs 3)
    '''
    if len(first) != len(second):
        msg = "Length mismatch ({} vs {})"
        raise UnswappableError(msg.format(len(first), len(second)))
    # sanity check
    fwd = {}
    back = {}
    for a,b in zip(first, second):
        if fwd.get(a,b) != b:
            raise UnswappableError(
                "Conflict - {}->{} or {}?".format(a,b,fwd[a]))
        if back.get(b,a) != a:
            raise UnswappableError(
                "Conflict - {} or {}->{}?".format(a,back[b],b))
        fwd[a] = b
        back[b] = a
    # Actually compute it
    record = alphabet
    for a,b in zip(first, second):
        a = _swap1(a, alphabet, record)
        record = _swap1(record, a+b, b+a)
    return record

def swappable(first, second):
    '''Returns True iff a substitution cipher could map first to second.

    >>> swappable("werewolf", 'monomial')
    True
    >>> swappable("werewolf", 'dividend')
    False

    Use `getswap` if you want an error message that tells you why they can't be
    swapped.
    '''
    try:
        getswap(first, second)
    except UnswappableError:
        return False
    return True

class Swapper:
    '''Helper for when you're manually trying to solve a substitution cipher.

    >>> s = Swapper('c xch, c ltch, c echct: lchcxc')

    s.swap exchanges two strings; if you only pass in one, it must be two
    letters and will swap those two letters. s.end returns the current result:

    >>> s.swap('ca')
    >>> s.end
    'a xah, a ltah, a eahat: lahaxa'

    s.sp, short for "swap and print", is just like swap except it prints s.end
    afterwards. This makes it easy to use repeatedly from a shell:

    >>> s.sp('ltah', 'plan')
    a xan, a plan, a eanal: panaxa
    >>> s.sp('xe','mc')
    a man, a plan, a canal: panama

    s.subst shows the substitution cipher that maps start to end:

    >>> s.subst
    'ebadcfgnijkpxhotqrsluvwmyz'

    '''
    def __init__(self, start, alphabet=lowers):
        self.start = start
        self.alphabet = alphabet
        self.subst = alphabet

    @property
    def end(self):
        return swap(self.start, self.alphabet, self.subst)

    def swap(self, first, second=None):
        if second is None:
            first, second = first
        sw = getswap(first, second, alphabet=self.alphabet)
        self.subst = swap(self.subst, self.alphabet, sw)

    def sp(self, first, second=None):
        self.swap(first, second)
        print(self.end)
