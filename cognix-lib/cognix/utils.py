"""Useful functionality bundled in one module"""

import inspect
import sys

from typing import Callable, Any

def get_mod_classes(modname: str, to_fill: list | None = None, filter: Callable[[Any], bool] = None):
    """
    Returns a list of classes defined in the current file.
    
    The filter paramater is a function that takes the object and returns if it should be included.
    """
    
    current_module = sys.modules[modname]

    classes = to_fill if to_fill else []
    for _, obj in inspect.getmembers(current_module):
        if not (inspect.isclass(obj) and obj.__module__ == current_module.__name__):
            continue
        if filter and not filter(obj):
            continue
        classes.append(obj)

    return classes