
import typing as t
import attr

'''
Basic idea:

A Result is a pair of (value, provenance), where provenance is a list of
ProvEntry objects indicating where this value came from.



'''

Provenance = t.Tuple["ProvEntry", ...]
_Proviter = t.Iterable["ProvEntry"]


class ProvEntry:
    '''Base class for provenances.'''
    @classmethod
    def find(cls, res: 'Result') -> Provenance:
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
    def make(cls, value: T, *provenance: t.Iterable[t.Any]) -> "Result[T]":
        def ensure(p: t.Any) -> ProvEntry:
            if isinstance(p, ProvEntry):
                return p
            if isinstance(p, str):
                return Label(p)
            return FromValue(p)
        provenance = tuple(ensure(p) for p in provenance)
        return cls(value, provenance)

    @classmethod
    def ensure(cls, value: t.Union[T, "Result[T]"]) -> "Result[T]":
        if isinstance(value, Result):
            return value
        return Result(value)

    @classmethod
    def unpack(cls, value: t.Union[T, "Result[T]"]) -> t.Tuple[t.Any, ...]:
        x = cls.ensure(value)
        return (x.val,) + x.provenance

    def extend(self, new_val: t.Any, *new_prov: _Proviter) -> "Result[T]":
        if not new_prov:
            new_prov = (FromValue(self.val),)
        return Result(new_val, self.provenance + new_prov)

    def __repr__(self) -> str:
        return f'<{self}>'

    def __str__(self) -> str:
        return f'{self}'

    def __format__(self, fmt: str) -> str:
        return f'{self.val:{fmt}}'


ResultStream = t.Iterable[Result]


def val(item):
    '''Unwrap an item that may or may not be a Result.'''
    if isinstance(item, Result):
        return item.val
    return item
