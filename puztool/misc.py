'''Some functions that don't seem to belong anywhere else.'''

import numpy as np

def smoosh(data, join='', axis=-1):
    '''Merge the values in an array along an axis.

    The default is to merge with ''.join, so it consolidates arrays of strings.
    '''
    if isinstance(join, str):
        join = join.join
    return np.apply_along_axis(join, axis, data)

def show(data):
    '''Represent a higher-dimensional text array in a more readable(?) way.

    TODO I'm sure there are better ways to do this.
    '''
    data = np.array(data)
    dims = data.shape
    for i in range(len(dims)):
        if i == 0:
            data = smoosh(data)
        elif i == len(dims)-1:
            data = smoosh(data, '\n')
        else:
            data = smoosh(data, ' ')
    print(data)
