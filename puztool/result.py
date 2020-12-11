import itertools
import time
import typing as t
import attr
import funcy
import pandas as pd

# from .text import shifts, lowers

Provenance = t.Tuple["ProvEntry", ...]

class ProvEntry:
    '''Base class for provenances.'''
    @classmethod
    def find(cls, res:'Result')->Provenance:
        return tuple(p for p in res.provenance if isinstance(p, cls))


@attr.s(auto_attribs=True)
class FromValue(ProvEntry):
    val: t.Any


@attr.s(auto_attribs=True)
class Label(ProvEntry):
    text: str

T = t.TypeVar("T")

@attr.s()
class Result(t.Generic[T]):
    '''A string plus some indication of where it came from.

    This is useful for e.g. a function to find words in a grid - it can return
    the words but also tell you where in the grid it found each word.
    '''
    val: T = attr.ib(default=None)
    provenance: t.Tuple[ProvEntry, ...] = attr.ib(factory=tuple)

    @classmethod
    def make(cls, value:T, *provenance:t.Iterable[t.Union[str, ProvEntry]]) -> "Result[T]":
        ensure = lambda p: p if isinstance(p, ProvEntry) else Label(p)
        provenance = tuple(ensure(p) for p in provenance)
        return cls(value, provenance)

    @classmethod
    def ensure(cls, value:t.Union[T, "Result[T]"]) -> "Result[T]":
        if isinstance(value, Result):
            return value
        return Result(value)

    def extend(self, new_val: t.Any, *new_provenance: t.Iterable[ProvEntry]) -> "Result[T]":
        if not new_provenance:
            new_provenance = (FromValue(self.val),)
        return Result(new_val, self.provenance + new_provenance)

    def __repr__(self) -> str:
        return f'<{self}>'

    def __str__(self) -> str:
        return f'{self}'

    def __format__(self, fmt:str) -> str:
        return f'{self.val:{fmt}}'

ResultStream = t.Iterable[Result]


def val(item):
    '''Unwrap an item that may or may not be a Result.'''
    if isinstance(item, Result):
        return item.val
    return item
