to_nato = {}
from_nato = {}

for i in "alpha bravo charlie delta echo foxtrot golf hotel india juliet kilo lima mike november oscar papa quebec romeo sierra tango uniform victor whiskey xray yankee zulu".split():
    to_nato[i[0]] = i
    from_nato[i] = i[0]

def encode(s):
    return ' '.join([to_nato[c] for c in s.lower() if c in to_nato])

def decode(s):
    return ''.join([from_nato[word] for word in s.lower().split() if word in from_nato])

if __name__ == '__main__':
    import sys
    msg = sys.argv[1]
    if set(msg.lower().split()) - set(x.lower() for x in from_nato):
        print(encode(msg))
    else:
        print(decode(msg))
