import numpy as np

from .modifier import Result

class DIRS:
    l = left = w = west = np.array([0,-1])
    r = right = e = east = np.array([0, 1])
    u = up = n = north = np.array([-1, 0])
    d = down = s = south = np.array([1, 0])
    ul = upleft = nw = northwest = u+l
    ur = upright = ne = northeast = u+r
    dl = downleft = sw = southwest = d+l
    dr = downright = se = southeast = d+r
    h = hor = horizontals = [l, r]
    v = ver = verticals = [u, d]
    di = diagonals = [ul, ur, dl, dr]
    o = ortho = h+v
    a = all = ortho + diagonals

    def __getitem__(self, key):
        return getattr(self, key)

directions = DIRS()

def parse_dirs(s):
    '''
    dirs can be a list of tuples, or a comma-separated list of letters
    recognized by parse_dirs. For example, 'r,d' will return only words
    running left-to-right or top-bottom, while 'h, sw, ne', will return all
    words running horizontally (left-to-right or right-to-left) as well as
    any running from upper-right to lower-left or lower-left to lower-right

    dirs defaults to 'a', meaning all orthogonal and diagonal directions.
    '''
    if isinstance(s, str):
        chosen = []
        for key in s.split(','):
            choice = directions[key.strip()]
            if isinstance(choice, list):
                chosen.extend(choice)
            else:
                chosen.append(choice)
        return chosen
    return s

def iter_strings(grid, len=(3,None), dirs=directions.all):
    '''Emit all sequences of letters in grid.

    dirs can be a list of tuples, or a comma-separated list of letters
    recognized by parse_dirs. For example, 'r,d' will return only words
    running left-to-right or top-bottom, while 'h, sw, ne', will return all
    words running horizontally (left-to-right or right-to-left) as well as
    any running from upper-right to lower-left or lower-left to lower-right

    dirs defaults ot 'a', meaning all orthogonal and diagonal directions.

    If len is a number, only sequences of that length will be returned. If it is
    a tuple of (min, max), only sequences with lengths in [min, max] will be
    returned. If len is None, or if len is a tuple and min or max is None, that
    bound will be ignored, e.g. len=(3,None) returns all sequences of 3 or more
    cells.

    Note that while this function does return strings, "len" here refers to the
    number of *cells* per word. If the input grid has cells containing multiple
    letters, len=3 will return all strings made by combining three adjacent
    cells, regardless of how long the actual strings are.

    The results are Result objects where .val is the string in question
    and .provenance is a tuple of (start, end) indicating where in the grid
    the word was found.
    '''
    dirs = parse_dirs(dirs)
    h, w = grid.shape[:2]
    if not isinstance(len, (list, tuple)):
        min_len = max_len = len
    else:
        min_len, max_len = len
    if min_len is None:
        min_len = 3
    if max_len is None:
        max_len = max(w,h)

    for row in range(h):
        for col in range(w):
            start = np.array([[row], [col]])
            for dir in dirs:
                # shaping it to (2,1) means we can do dir*arange(i) to get a 2xi
                # array of indices
                dir = np.array(dir).reshape(2,1)
                for i in range(min_len, max_len+1):
                    points = start + dir*np.arange(i)
                    # bounds check - stop if we've gone off the end
                    if (points[0].clip(0,h-1) != points[0]).any():
                        break
                    if (points[1].clip(0,w-1) != points[1]).any():
                        break
                    dr, dc = dir.flat
                    yield Result(''.join(grid[list(points)]),
                        ((row, col), (row+(i-1)*dr, col+(i-1)*dc)))
