import os
from pathlib import Path
from .parse import parse_grid, parse_lists, parse_table, pg, pt, pl
from .words import lists
from .text import shift, unshift, normalize, lowers
from .misc import smoosh, show
from .dropquote import DropQuote
from .pipeline import P
from .service import qat, nutr
from . import pipes
from . import gridsearch
from . import logic

here = Path(__file__).parent

def edit():
    os.system(f"subl {here}")

__all__ = [
    'parse_grid',
    'parse_lists',
    'parse_table',
    'pg',
    'pt',
    'pl',
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
    'gridsearch',
    'logic',
]
