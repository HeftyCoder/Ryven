from ryvencore import Session, Flow

from .flow import CognixFlow
from .graph_player import CognixPlayer, GraphPlayer, GraphState, GraphActionResponse
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Callable
from .networking.rest_api import CognixServer

        
class CognixSession(Session):
    """
    An extension to a ryvencore Session for CogniX.
    """
    
    _flow_base_type = CognixFlow
    
    def __init__(self, gui: bool = False, load_addons: bool = False):
        super().__init__(gui, load_addons)
        self._graphs_playing: set[GraphPlayer] = set()
        self._flow_executor = ThreadPoolExecutor(thread_name_prefix="flow_execution_")
        self._flow_to_future: dict[str, Future] = {}
        self._rest_api = CognixServer(self)
    
    @property
    def rest_api(self):
        return self._rest_api
    
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
        player = player_type(flow, frames) if player_type else CognixPlayer(frames)
        
        if data:
            flow.load(data)
        
        flow.player = player
        player.flow = flow
        
        # Titles should be unique
        if not self.new_flow_title_valid(flow.title):
            return None
        
        self._flows[flow.title] = flow
        self.flow_created.emit(flow)

        return flow
    
    def play_flow(self, flow_name: str, on_other_thread=False, callback: Callable[[GraphActionResponse, str], None] = None):
        """Plays the flow through the graph player"""
        
        graph_player = self.graph_player(flow_name)
        if not graph_player:
            callback(GraphActionResponse.NO_GRAPH, f"No flow associated with name {flow_name}")
            return
        
        if graph_player in self._graphs_playing or graph_player.state == GraphState.PLAYING:
            callback(GraphActionResponse.NOT_ALLOWED, f"Flow {flow_name} is currently playing")
            return
        
        if graph_player.state == GraphState.PAUSED:
            callback(GraphActionResponse.NOT_ALLOWED, f"Flow {flow_name} is paused")
            return
        
        # To avoid any race conditions because we may start the flow in another thread
        self._graphs_playing.add(graph_player)
        if callback:
            graph_player.graph_events.sub_event(
                GraphState.PLAYING,
                lambda: callback(GraphActionResponse.SUCCESS, f"Flow {flow_name} is playing!"),
                one_off=True
            )
        
        if not on_other_thread:
            self.__play_flow(flow_name, graph_player)
        else:
            play_task = self._flow_executor.submit(self.__play_flow, flow_name, graph_player)
            self._flow_to_future[flow_name] = play_task
            
    
    def __play_flow(self, flow_name: str, graph_player: GraphPlayer):
        if graph_player not in self._graphs_playing:
            self._graphs_playing.add(graph_player)
        try:
            graph_player.play()
        except Exception as e:
            raise e
        finally:
            self._graphs_playing.remove(graph_player)
            # handles the case where we have threads
            if flow_name in self._flow_to_future:
                del self._flow_to_future[flow_name]
            

    def pause_flow(self, flow_name: str, callback: Callable[[GraphActionResponse, str], None] = None):
        """Pauses the graph player"""
        
        graph = self.graph_player(flow_name)
        if not graph and callback:
            callback(GraphActionResponse.NO_GRAPH, f"No flow associated with name {flow_name}")
            return
        
        if graph.state == GraphState.PAUSED and callback:
            callback(GraphActionResponse.NOT_ALLOWED, f"Flow {flow_name} already paused")
            return
        
        if graph.state == GraphState.STOPPED and callback:
            callback(GraphActionResponse.NOT_ALLOWED, f"Flow {flow_name} isn't playing")
            return
        
        if callback:
            graph.graph_events.sub_event(
                GraphState.PAUSED, 
                lambda: callback(GraphActionResponse.SUCCESS, f"Flow {flow_name} has paused"),
                one_off=True
            )
        
        graph.pause()
    
    def resume_flow(self, flow_name: str, callback: Callable[[GraphActionResponse, str], None] = None):
        
        graph = self.graph_player(flow_name)
        if not graph and callback:
            callback(GraphActionResponse.NO_GRAPH, f"No flow associated with name {flow_name}")
            return

        if graph.state != GraphState.PAUSED and callable:
            callback(GraphActionResponse.NO_GRAPH, f"Flow {flow_name} is not paused")
            return

        if callback:
            graph.graph_events.sub_event(
                GraphState.PLAYING,
                lambda: callback(GraphActionResponse.SUCCESS, f"Flow {flow_name} resumted"),
                one_off=True
            )
        
        graph.resume()
    
    def stop_flow(self, flow_name: str, callback: Callable[[GraphActionResponse, str], None] = None):
        """Stops the graph player"""
        
        graph = self.graph_player(flow_name)
        if not graph and callback:
            callback(GraphActionResponse.NO_GRAPH, f"No flow associated with name {flow_name}")
            return
        
        if graph.state != GraphState.PLAYING and callback:
            callback(GraphActionResponse.NOT_ALLOWED, f"Flow {flow_name} is not playing!")
            return
        
        if callback:
            graph.graph_events.sub_event(
                GraphState.STOPPED,
                lambda: callback(GraphActionResponse.SUCCESS, f"Flow {flow_name} has stopped"),
                one_off=True
            )
            
        graph.stop()
    
    def shutdown(self):
        
        # shut down any players
        for flow_title in self.flows.keys():
            self.stop_flow(flow_title)
        
        self._flow_executor.shutdown()
        
        # shut down the rest api
        self.rest_api.shutdown()
        
        
        
        
        
         