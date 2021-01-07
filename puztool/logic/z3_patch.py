def apply():
    try:
        import z3
    except ImportError:
        z3 = None
    else:
        # Monekypatch z3 types for ease of use - a & b now means z3.And(a,b),
        # etc.
        z3.BoolRef.__and__ = z3.And
        z3.BoolRef.__or__ = z3.Or
        z3.BoolRef.__invert__ = z3.Not
        z3.BoolRef.__xor__ = z3.Xor
        z3.BoolRef.__rshift__ = z3.Implies
        z3.ArithRef.__abs__ = lambda self: z3.If(self > 0, self, -self)
        # Fix so that various z3 functions will work with numpy integer types.
        # We have to use importlib because the module is hidden in the z3
        # namespace by z3 itself (z3.z3 is z3, stupidly). Ideally we'd fix
        # floats, too, but that's more invasive and at some point this changes
        # from 'patching z3py' to 'forking z3py' and I have no intention of
        # doing that.
        import importlib as ilib
        import numpy as np
        z3_lib = ilib.import_module("z3.z3")

        def _is_int(val):
            return np.issubdtype(type(val), np.integer)

        z3_lib._is_int = _is_int
