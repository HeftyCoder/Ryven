"""Useful functionality bundled in one module"""

import inspect
import sys

from .core import CognixNode

def get_mod_classes(modname: str, to_fill: list | None = None, base_type: type = None):
    """Returns a list of classes defined in the current file."""
    
    current_module = sys.modules[modname]

    classes = to_fill if to_fill else []
    for _, obj in inspect.getmembers(current_module):
        if not (inspect.isclass(obj) and obj.__module__ == current_module.__name__):
            continue
        if base_type and not issubclass(obj, base_type):
            continue
        classes.append(obj)

    return classes

def get_cognix_node_classes(modname: str, to_fill: list | None = None, base_type: type = None):
    """Returns a list of node types defined in the current mode"""
    return get_mod_classes(modname, to_fill, base_type=CognixNode)