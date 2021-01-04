import os
from pathlib import Path
from .parse import parse_grid, parse_table, pg, pt
from .words import lists
from .text import shift, unshift, normalize, lowers
from .misc import smoosh, show
from .dropquote import DropQuote
from .pipeline import P
from .service import qat, nutr
from . import pipes
from . import codes as C
from . import grids
from . import logic

here = Path(__file__).parent


def edit():
    os.system(f"subl {here}")


__all__ = [
    'parse_grid',
    'parse_table',
    'pg',
    'pt',
    'lists',
    'shift',
    'unshift',
    'normalize',
    'lowers',
    'smoosh',
    'show',
    'DropQuote',
    'qat', 'nutr',
    'pipes',
    'P',
    'C',
    'grids',
    'logic',
]
