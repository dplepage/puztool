import abc
import attr
import funcy as fy
import z3


class Domain(abc.ABC):
    @abc.abstractmethod
    def mk(self, name: str) -> z3.ExprRef:
        '''Generate a new domain'''
        raise NotImplementedError()

    @abc.abstractmethod
    def cons(self, vs: list[z3.ExprRef]) -> list[z3.ExprRef]:
        '''Given vars from self.mk, return implied constraints on them.'''
        raise NotImplementedError()


@attr.s(auto_attribs=True)
class IntDomain(Domain):
    low: int
    high: int

    def mk(self, name: str) -> z3.ExprRef:
        return z3.Int(name)

    @fy.collecting
    def cons(self, vs: list[z3.ExprRef]) -> list[z3.ExprRef]:
        for var in vs:
            yield (var >= self.low) & (var <= self.high)


class BoolDomain(Domain):
    def mk(self, name):
        return z3.Bool(name)

    def cons(self, vs):
        return []
