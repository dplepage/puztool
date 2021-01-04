import typing as t
import numpy as np
from ..pipeline import Modifier, modifier, terminal


class Reverse(Modifier):
    """Turns an encoder into a decoder."""
    def __init__(self, coder):
        self.coder = coder

    def _process(self, seq):
        yield from self.coder.decode(seq)

    def __call__(self, *data):
        if len(data) == 1 and isinstance(data[0], t.Iterable):
            data = data[0]
        return self.coder.decode(data)


class Coder(Modifier):
    """Coder is a Modifier that can encode/decode in some way."""
    def encode(self, text: str) -> np.ndarray:
        pass

    def decode(self, data: np.ndarray) -> str:
        pass

    def stringify(self, data: np.ndarray) -> str:
        pass

    def unstringify(self, text: str) -> np.ndarray:
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
    """Characterwise encoding"""
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
    """Characterwise encoding backed by a simple mapping"""
    def __init__(self, default, mapping, dtype=None, lower=True):
        self.default = default
        self.mapping = mapping
        self.lower = lower
        self.rmap = {v: k for (k, v) in self.mapping.items()}
        self.dtype = dtype or str

    def enc1(self, c):
        if self.lower:
            c = c.lower()
        return self.mapping.get(c, self.default)

    def dec1(self, c):
        return self.rmap.get(c, ' ')

