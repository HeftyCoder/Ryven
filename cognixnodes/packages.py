"""Contains utilities and structures for loading all the nodes as a package hierarchy"""
from cognixcore.api import Node

cognix_package: dict[str, list[Node]]
"""
A container for the structure of packages in CogniX

Essentially a dictionary where keys are package name and
values are nodes. The package names can be arbitrarily nested

Example:

    pkg_one: [...]
    pkg_one.sub_pkg: [...]
    . . .
"""

# We will import the packages manually here and create the package structure
# An extension could be to dynamically search the files

from .classification import node_types as classification_node_types
from .file import node_types as file_node_types
from .input import node_types as input_node_types
from .utility import node_types as util_node_types
from .test import node_types as test_node_types
from .preprocessing import node_types as preprocessing_node_types
from .output import node_types as output_node_types
from .feature_extraction import node_types as fs_node_types

cognix_package: dict[str, list[type[Node]]] = {
    'file': file_node_types,
    'input': input_node_types,
    'util': util_node_types,
    'test': test_node_types,
    'preprocessing': preprocessing_node_types,
    'feature_extration': fs_node_types,
    'classification': classification_node_types,
    'output':output_node_types
}
