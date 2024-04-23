from ryvencore import Session
from ryvencore.Flow import Flow

from .flow import CognixFlow
from .graph_player import CognixPlayer, GraphPlayer, GraphState
from enum import IntEnum, auto

class GraphActionResponse(IntEnum):
    """
    An enum indicating a response to an action for a graph requested on the Session
    """
    
    NO_GRAPH = auto()
    """No graph found to play"""
    NOT_ALLOWED = auto()
    """The action requested (play, pause, stop) is being invoked already"""
    SUCCESS = auto()
    """The action was succesful"""
        
        
class CognixSession(Session):
    """
    An extension to a ryvencore Session for CogniX.
    """
    
    _flow_base_type = CognixFlow
    
    def __init__(self, gui: bool = False, load_addons: bool = False):
        super().__init__(gui, load_addons)
        self._graphs_playing: set[GraphPlayer] = set()
    
    def graph_player(self, title: str):
        """A proxy to the graph players dictionary contained in the session"""
        flow: CognixFlow = self._flows.get(title)
        return flow.player if flow else None
    
    def create_flow(self, title: str = None, data: dict = None, 
                    player_type: type[GraphPlayer] = None, frames=30) -> Flow | None:
        """
        Creates and returns a new flow, given a graph player.
        If data is provided the title parameter will be ignored.
        """
        
        flow: CognixFlow = self._flow_base_type(session=self, title=title)
        player = player_type(flow, frames) if player_type else CognixPlayer(flow, frames)
        flow.player = player
        
        if data:
            flow.load(data)
        
        # Titles should be unique
        if not self.new_flow_title_valid(flow.title):
            return None
        
        self._flows[flow.title] = flow
        self.flow_created.emit(flow)

        return flow
    
    def play_flow(self, flow_name: str):
        
        graph = self.graph_player(flow_name)
        if not graph:
            return (GraphActionResponse.NO_GRAPH, f"No flow associated with name {flow_name}")
        
        if graph in self._graphs_playing or graph.state == GraphState.PLAYING:
            return (GraphActionResponse.NOT_ALLOWED, f"Flow {flow_name} is currently playing")
        
        if graph.state == GraphState.PAUSED:
            return (GraphActionResponse.NOT_ALLOWED, f"Flow {flow_name} is paused")
        
        # To avoid any race conditions because we may start the graph in another thread
        self._graphs_playing.add(graph)
        
        graph.play()
    
    def pause_flow(self, flow_name: str):
        
        graph = self.graph_player(flow_name)
        if not graph:
            return (GraphActionResponse.NO_GRAPH, f"No flow associated with name {flow_name}")
        
        if graph.state == GraphState.PAUSED:
            return (GraphActionResponse.NOT_ALLOWED, f"Flow {flow_name} already paused")
        
        if graph.state == GraphState.STOPPED:
            return (GraphActionResponse.NOT_ALLOWED, f"Flow {flow_name} isn't playing")
        
        graph.pause()
    
    def stop_flow(self, flow_name: str):
        
        graph = self.graph_player(flow_name)
        if not graph:
            return (GraphActionResponse.NO_GRAPH, f"No flow associated with name {flow_name}")
        
        if graph.state != GraphState.PLAYING:
            return (GraphActionResponse.NOT_ALLOWED, f"Flow {flow_name} is not playing!")
        
        graph.stop()
        
        
        
        
         