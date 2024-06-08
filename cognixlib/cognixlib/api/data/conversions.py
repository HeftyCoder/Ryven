"""
Defines conversions between primitive types

Used for changing from numpy type to lsl type
"""

import numpy as np
from numpy import dtypes
import pylsl
from types import MappingProxyType

__np_to_lsl = {
    np.dtype(np.float32): pylsl.cf_float32,
    np.dtype(np.float64): pylsl.cf_double64,
    np.dtype(np.int8): pylsl.cf_int8,
    np.dtype(np.int16): pylsl.cf_int16,
    np.dtype(np.int32): pylsl.cf_int32,
    np.dtype(np.int64): pylsl.cf_int64,
    np.dtype(np.string_): pylsl.cf_string,
    
    'float32': pylsl.cf_float32,
    'float64': pylsl.cf_double64,
    'int8': pylsl.cf_int8,
    'int16': pylsl.cf_int16,
    'int32': pylsl.cf_int32,
    'int64': pylsl.cf_int64,
    'string': pylsl.cf_string,
}

np_to_lsl = MappingProxyType(__np_to_lsl)

__lsl_to_np = {
    pylsl.cf_float32: np.dtype(np.float32),
    pylsl.cf_double64: np.dtype(np.float64),
    pylsl.cf_int8: np.dtype(np.int8),
    pylsl.cf_int16: np.dtype(np.int16),
    pylsl.cf_int32: np.dtype(np.int32),
    pylsl.cf_int64: np.dtype(np.int64),
    pylsl.cf_string: np.dtype(np.string_),
}

lsl_to_np = MappingProxyType(__lsl_to_np)