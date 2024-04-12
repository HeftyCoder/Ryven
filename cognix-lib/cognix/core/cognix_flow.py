from ryvencore import Flow
from .cognix_node import CognixNode
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .cognix_session import CognixSession

class CognixFlow(Flow):
    """
    An extension to a ryvencore Flow for CogniX.
    
    Specifically, it adds a CognixFlowPlayer for interpreting the graph.
    """
    
    _node_base_type = CognixNode

