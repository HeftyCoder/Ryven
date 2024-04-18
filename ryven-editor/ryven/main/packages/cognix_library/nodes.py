from ryvencore import Node, NodeInputType, NodeOutputType, Data
from ryven.node_env import export_nodes, on_gui_load

from cognix.nodes.input.input_nodes import all_input_nodes, input_nodes_pkg
from cognix.nodes.file.file_nodes import all_file_nodes
from cognix.nodes.classification.classification_nodes import all_classification_nodes
from cognix.nodes.utility.util_nodes import all_util_nodes, util_pkg_name

export_nodes(all_input_nodes, sub_pkg_name=input_nodes_pkg)
export_nodes(all_file_nodes, sub_pkg_name='file')
export_nodes(all_classification_nodes, sub_pkg_name='classification')
export_nodes(all_util_nodes, sub_pkg_name=util_pkg_name)

@on_gui_load
def load_gui():
    from .gui import utility_guis