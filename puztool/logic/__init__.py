from .z3_patch import apply as _apply_patch
from . import grids
from .cat_grid import CatGrid
from .cat_prob import CatProblem, Unique
from .base import (
    NoSolution, MultipleSolutions, Solution, all_solns, solve, Problem)
from .domain import Domain, IntDomain, BoolDomain
from .grids import IntMatrix, Z3Matrix, Sudoku

_apply_patch()

__all__ = [
    'CatGrid',
    'CatProblem',
    'Domain',
    'IntDomain',
    'BoolDomain',
    'NoSolution',
    'MultipleSolutions',
    'Solution',
    'Problem',
    'all_solns',
    'solve',
    'grids',
    'IntMatrix',
    'Z3Matrix',
    'Sudoku',
    'Unique',
]
