from __future__ import annotations
from ryvencore import Flow
from .nodes import CognixNode

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .graph_player import GraphPlayer
    from .session import CognixSession

class CognixFlow(Flow):
    """
    An extension to a ryvencore Flow for CogniX.
    
    Specifically, it adds a CognixFlowPlayer for interpreting the graph.
    """
    
    _node_base_type = CognixNode
    
    def __init__(self, session: CognixSession, title: str, player: GraphPlayer = None):
        super().__init__(session, title)
        self.session = session