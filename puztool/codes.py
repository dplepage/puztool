import typing as t
import numpy as np
from .pipeline import Modifier, modifier, terminal

def grays(n):
    if n == 0:
        return ['']
    s = list(grays(n-1))
    return [('0'+c) for c in s] + [('1'+c) for c in s[::-1]]


class Reverse(Modifier):
    def __init__(self, coder):
        self.coder = coder
    def _process(self, seq):
        yield from self.coder.decode(seq)

    def __call__(self, *data):
        if len(data) == 1 and isinstance(data[0], t.Iterable):
            data = data[0]
        return self.coder.decode(data)

class Coder(Modifier):
    def encode(self, text:str)->np.ndarray:
        pass
    def decode(self, data:np.ndarray)->str:
        pass
    def stringify(self, data:np.ndarray)->str:
        pass
    def unstringify(self, text:str)->np.ndarray:
        pass

    def _process(self, seq):
        for c in seq:
            yield from self.encode(c)

    @property
    def un(self):
        return Reverse(self)

    def __invert__(self):
        return self.un

    def __call__(self, val):
        return self.encode(val)


class CharEnc(Coder):
    sep = ' '
    dtype = str
    def encode(self, text):
        enc = [self.enc1(c) for c in text]
        return np.array([e for e in enc if e is not None])

    def decode(self, data):
        return ''.join([self.dec1(c) for c in data])

    def stringify(self, data):
        return self.sep.join(str(d) for d in data)

    def unstringify(self, text):
        if self.sep:
            t = text.split(self.sep)
        else:
            t = list(text)
        return np.array(t, dtype=self.dtype)

class MapEnc(CharEnc):
    def __init__(self, default, mapping, dtype=None, lower=True):
        self.default = default
        self.mapping = mapping
        self.lower = lower
        self.rmap = {v:k for (k,v) in self.mapping.items()}
        self.dtype = dtype or str

    def enc1(self, c):
        if self.lower:
            c = c.lower()
        return self.mapping.get(c, self.default)

    def dec1(self, c):
        return self.rmap.get(c, ' ')

@terminal
def join(c='', seq=''):
    return c.join(seq)

lowers = ' abcdefghijklmnopqrstuvwxyz'

Index = MapEnc(0, {k:i for i,k in enumerate(lowers)}, int)
Gray = MapEnc('', dict(zip(lowers[1:], grays(5)[1:])))
natos = "alpha bravo charlie delta echo foxtrot golf hotel india juliet kilo lima mike november oscar papa quebec romeo sierra tango uniform victor whiskey xray yankee zulu"
Nato = MapEnc(' ', {a[0]:a for a in natos.split()})

to_morse = {
    ' ': '/',
    'a': '.-',
    'b': '-...',
    'c': '-.-.',
    'd': '-..',
    'e': '.',
    'f': '..-.',
    'g': '--.',
    'h': '....',
    'i': '..',
    'j': '.---',
    'k': '-.-',
    'l': '.-..',
    'm': '--',
    'n': '-.',
    'o': '---',
    'p': '.--.',
    'q': '--.-',
    'r': '.-.',
    's': '...',
    't': '-',
    'u': '..-',
    'v': '...-',
    'w': '.--',
    'x': '-..-',
    'y': '-.--',
    'z': '--..',
    '1': '.----',
    '2': '..---',
    '3': '...--',
    '4': '....-',
    '5': '.....',
    '6': '-....',
    '7': '--...',
    '8': '---..',
    '9': '----.',
    '0': '-----',
    '.': '.-.-.-',
    ',': '--..--',
    '?': '..--..',
    '/': '-..-.',
    '+': '.-.-.',
    '*': '...-.-',
    '=': '-...-',
    ';': '-.-.-.',
    ':': '---...',
    "'": '.----.',
    '"': '.-..-.',
    '-': '-....-',
    '_': '..--.-',
    '$': '...-..-',
    '(': '-.--.',
    ')': '-.--.-',
    '&': '.-...',
    '!': '...-.',
    '%': '-.-.-',
    '@': '........',
    '#': '.-.-..'
}

Morse = MapEnc('', to_morse)
braille_map = " a1b'k2l@cif/msp\"e3h9o6r^djg>ntq,*5<-u8v.%[$+x!&;:4\\0z7(_?w]#y)="
Braille = MapEnc('', {c:chr(0x2800+i) for i,c in enumerate(braille_map)})


class Ord(CharEnc):
    dtype=int
    def enc1(self, c):
        return ord(c)
    def dec1(self, o):
        return chr(o)

def bin5(i):
    return f'{i:05b}'

def unbin(b):
    return int(b, 2)

def bflip(c):
    return c.replace('0', '·').replace('1', '0').replace('·', '1')

@modifier
def split_up(seq, sep=' '):
    if isinstance(seq, str):
        yield from seq.split(sep)
    else:
        for item in seq:
            yield from item.split(sep)
