from .base import MapEnc, CharEnc

lowers = ' abcdefghijklmnopqrstuvwxyz'
index = MapEnc(0, {k: i for i, k in enumerate(lowers)}, int)


def grays(n):
    '''Recursively generate standard length-n gray codes.'''
    if n == 0:
        return ['']
    s = list(grays(n - 1))
    return [('0' + c) for c in s] + [('1' + c) for c in s[::-1]]


gray = MapEnc('', dict(zip(lowers[1:], grays(5)[1:])))

natos = ("alpha bravo charlie delta echo foxtrot golf"
         " hotel india juliet kilo lima mike november"
         " oscar papa quebec romeo sierra tango uniform"
         " victor whiskey xray yankee zulu")

nato = MapEnc(' ', {a[0]: a for a in natos.split()})

bord = ord

class Ord(CharEnc):
    dtype = int

    @staticmethod
    def enc1(c):
        return bord(c)

    @staticmethod
    def dec1(o):
        return chr(o)


ord = Ord()


def bin5(i: int) -> str:
    return f'{i:05b}'


def unbin(b: str) -> int:
    return int(b, 2)


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

morse = MapEnc('', to_morse)

def bflip(c):
    return c.replace('0', '·').replace('1', '0').replace('·', '1')
