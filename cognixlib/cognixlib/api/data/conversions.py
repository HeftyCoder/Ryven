"""
Defines conversions between primitive types

Used for changing from numpy type to lsl type
"""

import numpy as np
import pylsl
from types import MappingProxyType

__np_to_lsl = {
    np.float32: pylsl.cf_float32,
    np.float64: pylsl.cf_double64,
    np.int8: pylsl.cf_int8,
    np.int16: pylsl.cf_int16,
    np.int32: pylsl.cf_int32,
    np.int64: pylsl.cf_int64,
    np.string_: pylsl.cf_string,
    
    'float32': pylsl.cf_float32,
    'float64': pylsl.cf_double64,
    'int8': pylsl.cf_int8,
    'int16': pylsl.cf_int16,
    'int32': pylsl.cf_int32,
    'int64': pylsl.cf_int64,
    'string': pylsl.cf_string
}

np_to_lsl = MappingProxyType(__np_to_lsl)