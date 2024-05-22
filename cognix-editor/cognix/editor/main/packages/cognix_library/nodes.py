from ryven.node_env import export_nodes, on_gui_load
from cognix.nodes.packages import cognix_package

for pkg_name, pkg_types in cognix_package.items():
    export_nodes(pkg_types, sub_pkg_name=pkg_name)

@on_gui_load
def load_gui():
    
    from .gui.config import traits # basic GUI implementation
    from .gui import inspector
    from .gui import utility_guis