try:
    import z3
except ImportError:
    z3 = None
else:
    # IMO z3 should provide this :-/
    z3.BoolRef.__and__ = z3.And
    z3.BoolRef.__or__ = z3.Or
    z3.BoolRef.__invert__ = z3.Not
