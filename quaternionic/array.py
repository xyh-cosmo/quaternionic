import numpy as np

from .properties import QuaternionPropertiesMixin
from .converters import QuaternionConvertersMixin


class array(QuaternionPropertiesMixin, QuaternionConvertersMixin, np.ndarray):
    """Subclass of numpy arrays interpreted as quaternions

    This class encapsulates quaternion algebra, with numpy's "ufunc"s
    overridden by quaternionic methods.  Standard algebraic operations can be
    performed naturally — as in `q1+q2`, `q1*q2`, etc.  Numpy functions can
    also be used as expected — as in `np.exp(q)`, `np.log(q)`, etc.

    Because this is a subclass of numpy's ndarray object, its constructor takes
    anything the ndarray constructor takes, or just an ndarray to be considered
    as a quaternion array:

        q1 = quaternionic.array([1, 2, 3, 4])  # explicit array
        q2 = quaternionic.array(np.random.rand(10, 4))  # re-interpret ndarray

    In addition to the basic numpy array features, we also have a number of
    extra properties that are particularly useful for quaternions, including

      * Methods to extract and/or set components
        * w, x, y, z
        * i, j, k (equivalent to x, y, z)
        * scalar, vector (equivalent to w, [x, y, z])
        * real, imag (equivalent to scalar, vector)
      * Methods related to norms
        * abs (square-root of sum of squares of components)
        * norm (sum of squares of components)
        * modulus, magnitude (equal to abs)
        * absolute_square, abs2, mag2, squared_norm (equal to norm)
        * normalized
        * conjugate, conj
        * inverse
      * Methods related to array infrastructure
        * ndarray
        * flattened
        * iterator

    There are also several converters to and from other representations of
    rotations, including

       * to/from_rotation_matrix
       * to_transformation_matrix
       * to/from_axis_angle
       * to/from_euler_angles
       * to/from_spherical_coordinates

    """

    # https://numpy.org/doc/1.18/user/basics.subclassing.html
    def __new__(cls, input_array, *args, **kwargs):
        if isinstance(input_array, int) and len(args) == 3:
            input_array = [input_array, *args]
        input_array = np.asanyarray(input_array, dtype=float)
        if input_array.shape[-1] != 4:
            raise ValueError(
                f"\nInput array has shape {input_array.shape} when viewed as a float array.\n"
                "Its last dimension should have size 4, representing the components of a quaternion."
            )
        obj = input_array.view(cls)
        return obj

    def __getitem__(self, i):
        # Note that this simply assumes that if the returned array has last
        # dimension of size 4, it is a quaternionic array.  Obviously, this may
        # not always be true, but there's no simple way to decide more
        # correctly.
        r = super().__getitem__(i)
        if hasattr(r, 'shape') and len(r.shape)>0 and r.shape[-1] == 4:
            return type(self)(r)
        else:
            return r

    def __array_finalize__(self, obj):
        if self.shape[-1] != 4:
            raise ValueError(
                f"\nArray to finalize has shape {self.shape}; "
                "last dimension should have size 4 to represent a quaternion.\n"
                "If you are trying to slice the quaternions, you should append `.ndarray` before slicing.\n"
                "For example, instead of `q[..., 2:]`, you must use `q.ndarray[..., 2:]` to return a\n"
                "general (non-quaternion) numpy array.  This is a limitation of numpy.\n\n"
                "Also note that quaternions have attributes like `q.w`, `q.x`, `q.y`, and `q.z` to return\n"
                "arrays of individual components, and `q.vector` to return the \"vector\" part."
            )

    def __array_ufunc__(self, ufunc, method, *args, out=None, **kwargs):
        from . import algebra

        # We will not be supporting any more ufunc keywords beyond `out`
        if kwargs:
            raise NotImplementedError(f"Unrecognized arguments to {type(self).__name__}.__array_ufunc__: {kwargs}")

        this_type = lambda o: isinstance(o, type(self))

        if ufunc in [
            np.add, np.subtract, np.multiply, np.divide, np.true_divide,
            np.bitwise_or, np.bitwise_xor, np.right_shift, np.left_shift,
        ]:
            # float64[4](float64[4], float64[4])
            if this_type(args[0]) and this_type(args[1]):
                a1, a2 = args[:2]
                b1 = a1.ndarray[..., 0]
                b2 = a2.ndarray[..., 0]
                shape = np.broadcast(b1, b2).shape + (4,)
                result = out or np.zeros(shape)
                if isinstance(result, tuple):
                    result = result[0]
                if isinstance(result, type(self)):
                    result = result.view(np.ndarray)
                getattr(algebra, ufunc.__name__)(a1.ndarray, a2.ndarray, result)
                result = type(self)(result)

            # float64[4](float64, float64[4])
            elif not this_type(args[0]) and this_type(args[1]) and ufunc in [np.multiply, np.divide, np.true_divide]:
                a1, a2 = args[:2]
                b1 = a1
                b2 = a2.ndarray[..., 0]
                shape = np.broadcast(b1, b2).shape + (4,)
                result = out or np.zeros(shape)
                if isinstance(result, tuple):
                    result = result[0]
                if isinstance(result, type(self)):
                    result = result.view(np.ndarray)
                getattr(algebra, f"{ufunc.__name__}_scalar")(a1, a2.ndarray, result)
                result = type(self)(result)

            # float64[4](float64[4], float64)
            elif this_type(args[0]) and not this_type(args[1]) and ufunc in [np.multiply, np.divide, np.true_divide]:
                a1, a2 = args[:2]
                b1 = a1.ndarray[..., 0]
                b2 = a2
                shape = np.broadcast(b1, b2).shape + (4,)
                result = out or np.zeros(shape)
                if isinstance(result, tuple):
                    result = result[0]
                if isinstance(result, type(self)):
                    result = result.view(np.ndarray)
                getattr(algebra, f"scalar_{ufunc.__name__}")(a1.ndarray, a2, result)
                result = type(self)(result)
            else:
                return NotImplemented

        # float64[4](float64[4])
        elif ufunc in [
            np.negative, np.positive, np.conj, np.conjugate, np.invert,
            np.exp, np.log, np.sqrt, np.square, np.reciprocal,
        ]:
            if this_type(args[0]):
                qout = np.empty(args[0].shape) if out is None else out[0]
                getattr(algebra, ufunc.__name__)(args[0].ndarray, qout)
                result = type(self)(qout)
            else:
                return NotImplemented

        # float64[4](float64[4], float64)
        elif ufunc in [np.float_power]:
            a1, a2 = args[:2]
            b1 = a1.ndarray[..., 0]
            b2 = a2
            shape = np.broadcast(b1, b2).shape + (4,)
            result = out or np.zeros(shape)
            if isinstance(result, tuple):
                result = result[0]
            if isinstance(result, type(self)):
                result = result.view(np.ndarray)
            algebra.float_power(a1.ndarray, a2, result)
            result = type(self)(result)

        # float64(float64[4])
        elif ufunc in [np.absolute]:
            if this_type(args[0]):
                qout = np.empty(args[0].shape[:-1]) if out is None else out[0]
                algebra.absolute(args[0].ndarray, qout)
                result = qout
            else:
                return NotImplemented

        # bool(float64[4], float64[4])
        elif ufunc in [np.not_equal, np.equal, np.logical_and, np.logical_or]:
            # Note that these ufuncs are used in numerous unexpected places
            # throughout numpy, so we really need them for basic things to work
            a1, a2 = args[:2]
            b1 = a1.ndarray[..., 0]
            b2 = a2.ndarray[..., 0]
            shape = np.broadcast(b1, b2).shape
            result = out or np.zeros(shape, dtype=bool)
            if isinstance(result, tuple):
                result = result[0]
            if isinstance(result, type(self)):
                result = result.view(np.ndarray)
            getattr(algebra, ufunc.__name__)(a1.ndarray, a2.ndarray, result)

        # bool(float64[4])
        elif ufunc in [np.isfinite, np.isinf, np.isnan]:
            if this_type(args[0]):
                bout = np.empty(args[0].shape[:-1], dtype=bool) if out is None else out[0]
                getattr(algebra, ufunc.__name__)(args[0].ndarray, bout)
                result = bout
            else:
                return NotImplemented

        else:
            return NotImplemented

        if result is NotImplemented:
            return NotImplemented

        if method == 'at':
            return

        return result
