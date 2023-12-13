from ryvencore import Node, Flow
from ryvencore.InfoMsgs import InfoMsgs
from ryvencore.Base import Event
from ryvencore.Node import NodeInput, NodeOutput
from abc import ABCMeta, abstractmethod

from ryvencore.Data import Data

# the additions over normal ryven can probably be made into PRs
class CognixNode(Node, metaclass=ABCMeta):
    """The basic building block of a Cognix Graph"""
    
    def __init__(self, params):
        super().__init__(params)
        # events that ryvencore doesn't have
        self.updated = Event(int)
        self.output_changed = Event(NodeOutput, Data)
        # for type hinting...
        self.flow: Flow = self.flow
        
        from .graph_player import GraphPlayer # to avoid circular imports
        self._player: GraphPlayer = None
    
    @property
    def player(self):
        return self._player
    
    def update(self, inp=-1):
        """Overrides ryvencore to add an updated event"""
        super().update(inp)
        self.updated.emit(inp)
    
    def set_output_val(self, index: int, data: Data):
        """Overrides ryvencore to add an on_output_changed event"""
        super().set_output_val(index, data)
        self.output_changed.emit(self.outputs[index], data)
        
    def reset(self):
        """
        VIRTUAL
        This is called when the node is reset. Typically happens when the GraphPlayer
        enters GraphState.Playing state. Implement any initialization here.
        """
        pass
    
    def on_stop(self):
        pass
    
    def on_application_end(self):
        pass


class StartNode(CognixNode):
    """A node that has no inputs. It processes data only once."""
    
    def __init__(self, params):
        super().__init__(params)
        
    @abstractmethod
    def update_event(self, inp=-1):
        """This method is called only once when the graph is starting."""
        return super().update_event(inp)
        

class FrameNode(CognixNode):
    """A node which updates every frame of the Cognix Application."""
    
    def __init__(self, params):
        super().__init__(params)
        # Setting this will stop the node from updating
        self._is_finished = False
    
    @property
    def is_finished(self):
        return self._is_finished
    
    def frame_update(self):
        """Wraps the frame_update_event with internal calls."""
        self.updating.emit(-1)
        self.frame_update_event()
        
    @abstractmethod
    def frame_update_event(self):
        """Called on every frame. Data might have been passed from other nodes"""
        pass
    
    def reset(self):
        self._is_finished = False
        return super().reset()


class TransformNode(CognixNode):
    """Almost a typical ryven node. Processes data and sets the outputs."""
    
    def __init__(self, params):
        super().__init__(params)
    
    @abstractmethod
    def update_event(self, inp=-1):
        return super().update_event(inp)