from abc import ABC, abstractmethod
from ryvencore import Flow, Node
from ryvencore.Base import Event
from enum import Enum, auto
from .base_nodes import CognixNode, StartNode, FrameNode

import time


class GraphState(Enum):
    PLAYING = auto()
    PAUSED = auto()
    STOPPED = auto()

 
class GraphPlayer(ABC):
    """
    A player is a class that handles the life-time of a node program.
    In ryvencore's context, the executor should always be naive.
    """
    
    def __init__(self, flow: Flow, frames: int = 30):
        super().__init__()
        self._frames = frames
        self._flow = flow
        self._state = GraphState.STOPPED
        self.__state_changed: Event = Event(GraphState)
    
    @property
    def flow(self):
        return self._flow
    
    @property
    def frames(self):
        return self._frames
    
    @frames.setter
    def frames(self, value: int):
        if self._state != GraphState.STOPPED:
            return
        self._frames = value
    
    @property
    def state(self):
        return self._state
    
    @property
    def state_event(self):
        return self.__state_changed
    
    def reset_state_event(self):
        self.__state_changed = Event(GraphState)
        
    @abstractmethod
    def play(self):
        pass
    
    @abstractmethod
    def pause(self):
        pass
    
    @abstractmethod
    def resume(self):
        pass
    
    @abstractmethod
    def stop(self):
        pass


class CognixPlayer(GraphPlayer):
    
    def __init__(self, flow: Flow, frames: int = 25):
        super().__init__(flow, frames)
        self._start_nodes: list[StartNode] = []
        self._frame_nodes: list[FrameNode] = []
        self._nodes: list[CognixNode] = []
        self._stop_flag = False
    
    def play(self):
        try:
            self.__play()
        except Exception as e:
            raise e
        finally:
            self._state = GraphState.STOPPED
    
    def __play(self):
        # gather cognix nodes
        if self._state != GraphState.STOPPED:
            return
        self._stop_flag = False
        self._state = GraphState.PLAYING
        self.__gather_nodes()
        
        for node in self._nodes:
            node.reset()
            
        for start_node in self._start_nodes:
            start_node.update()
        
        if not self._frame_nodes:
            self.__on_stop()
            self._state = GraphState.STOPPED
            return
        
        while True:
            if self._state == GraphState.PAUSED:
                time.sleep(self.frame_dur())
                continue
            elif self._stop_flag:
                break
            
            start_time = time.perf_counter()
            for node in self._frame_nodes:
                node.frame_update()
            wait_time = self.frame_dur() - time.perf_counter - start_time
            
            print(wait_time)
            if wait_time > 0:
                time.sleep(wait_time)
                
        self.__on_stop()
        self._state = GraphState.STOPPED
        
    def pause(self):
        self._state = GraphState.PAUSED
    
    def resume(self):
        if self._state == GraphState.PAUSED:
            self._state = GraphState.PLAYING
    
    def stop(self):
        if self._state != GraphState.STOPPED:
            self._stop_flag = True
    
    def has_start_nodes(self):
        return len(self._start_nodes) > 0
    
    def frame_dur(self):
        return 1 / self._frames
    
    def __gather_nodes(self):
        self._start_nodes.clear()
        self._frame_nodes.clear()
        self._nodes.clear()
        
        for node in self._flow.nodes:
            if not isinstance(node, CognixNode):
                continue
            self._nodes.append(node)
            if isinstance(node, StartNode):
                self._start_nodes.append(node)
            elif isinstance(node, FrameNode):
                self._frame_nodes.append(node)
    
    def __on_stop(self):
        for node in self._nodes:
            node.on_stop()
        self._state = GraphState.STOPPED # to remove