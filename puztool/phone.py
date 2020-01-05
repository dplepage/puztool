from itertools import product
from .text import lowers
from .result import Result
from .pipeline import item_mod

keypad = {
    2:'abc',
    3:'def',
    4:'ghi',
    5:'jkl',
    6:'mno',
    7:'pqrs',
    8:'tuv',
    9:'wxyz',
}
padback = dict()
for (k, letters) in keypad.items():
    for l in letters:
        padback[l] = k

def to_phone(word):
    return [padback[c.lower()]  if c.lower() in lowers else c for c in word]

def from_phone(sequence):
    strings = [keypad[i] for i in sequence]
    for combo in product(*strings):
        yield Result(''.join(combo), sequence)

@item_mod
def from_word(result):
    for r in from_phone(to_phone(result.val)):
        yield result.extend(r.val)
