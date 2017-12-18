import numpy as np
from funcy import chunks
from .text import lowers, normalize

def uniques(seq):
    returned = set()
    for item in seq:
        if item in returned: continue
        returned.add(item)
        yield item

class Playfair:
    '''Playfair encrypter/decrypter.

    The only required argument is the keyphrase.

    You can also specify two bigram arguments.

    `merge` indicates that the first letter should be treated as though it were
    the second letter for the purposes of the cipher; this is necessary to fit
    the alphabet in a 5x5 grid. It defaults to `"ji"`.

    `rep` specifies the padding letters to use when you need to encode a
    repeated letter. `rep[0]` will always be used for padding EXCEPT when the
    previous letter IS `rep[0]`, in which case `rep[1]` will be used.

    >>> p = Playfair("Playfair Example")
    >>> print(p.grid)
    [['p' 'l' 'a' 'y' 'f']
     ['i' 'r' 'e' 'x' 'm']
     ['b' 'c' 'd' 'g' 'h']
     ['k' 'n' 'o' 'q' 's']
     ['t' 'u' 'v' 'w' 'z']]
    >>> p.encode("In the face of ambiguity, refuse the temptation to guess")
    'rk zb ma ld dv py ih xb tr wp ex lz om zb iv xi ip pv ek ku qd vr qm qm'
    >>> p.decode('rk zb ma ld dv py ih xb tr wp ex lz om zb iv xi ip pv ek ku qd vr qm qm')
    'inthefaceofambiguityrefusethetemptationtoguesxsx'
    '''
    def __init__(self, keyphrase, merge='ji', rep='xq'):
        self.m1, self.m2 = merge
        self.rep = rep
        self.keyphrase = keyphrase
        fullkey = (normalize(keyphrase)+lowers).replace(self.m1, self.m2)
        self.key = ''.join(uniques(fullkey))
        self.grid = np.array(list(self.key)).reshape((5,5))
        self.inv = {}
        for i in range(5):
            for j in range(5):
                self.inv[self.grid[i,j]] = (i,j)
        self.inv[self.m1] = self.inv[self.m2]

    def decode(self, text):
        plaintext = normalize(text)
        return ''.join(self.decode_plain(plaintext))

    def encode(self, text):
        plaintext = normalize(text)
        return ' '.join(self.encode_plain(plaintext))

    def _code_pair(self, a, b, dir):
        if a == b:
            raise ValueError("Cannot encode duplicate letter!")
        r1, c1 = self.inv[a]
        r2, c2 = self.inv[b]
        if r1 == r2:
            return self.grid[r1, (c1+dir)%5]+self.grid[r1, (c2+dir)%5]
        elif c1 == c2:
            return self.grid[(r1+dir)%5, c1]+self.grid[(r2+dir)%5, c2]
        else:
            return self.grid[r1, c2] + self.grid[r2, c1]

    def encode_plain(self, text):
        i = 0
        while i < len(text):
            if len(text) == i+1 or text[i] == text[i+1]:
                a, b = text[i], self.rep[0]
                i += 1
            else:
                a,b = text[i:i+2]
                i += 2
            if a == b: # only possible if b is self.rep[0]
                b = self.rep[1]
            yield self._code_pair(a,b,1)

    def decode_plain(self, text):
        if len(text)%2:
            raise ValueError("Text is not playfair-encoded: Length is odd")
        for a,b in chunks(2, text):
            if a == b:
                raise ValueError("Text is not playfair-encoded:"+
                    " Invalid bigram {}".format(a+b))
            yield self._code_pair(a,b,-1)
