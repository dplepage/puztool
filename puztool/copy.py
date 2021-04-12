import pandas as pd
from pandas.io import clipboard as cb
import numpy as np


def cp(data, headers=False, index=False):
    if isinstance(data, np.ndarray):
        data = pd.DataFrame(data)
    if isinstance(data, pd.DataFrame):
        data.to_clipboard(header=False, index=False)
    else:
        cb.copy(data)
