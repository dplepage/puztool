import re
import funcy as fn

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
from_morse = {code:letter for (letter,code) in to_morse.items()}

def encode(s):
    return ' '.join(to_morse[x] for x in s.lower() if x in to_morse)

def decode(s):
    return ''.join(from_morse[x] for x in s.split() if x in from_morse)

@fn.collecting
def extract_it(s, dotdashspace='it '):
    '''Decode morse encoded as i's and t's for dots and dashes'''
    dot, dash, space = dotdashspace
    letters = s.lower().split(space)
    for letter in letters:
        letter = re.sub('[^{}{}]'.format(dot,dash), '', letter)
        letter = letter.replace(dot, '.').replace(dash, '-')
        yield letter

if __name__ == '__main__':
    import sys
    msg = sys.argv[1]
    if set(msg) - set('.-/ '):
        print(encode(msg))
    else:
        print(decode(msg))
