from ryvencore import Node
from abc import ABCMeta, abstractmethod

class CognixNode(Node, metaclass=ABCMeta):
    """The basic building block of a Cognix Graph"""
    
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
    
    @abstractmethod
    def frame_update(self):
        """Called on every frame. Data might have been passed from other nodes"""
        self.updating.emit()


class TransformNode(CognixNode):
    """Almost a typical ryven node. Processes data and sets the outputs."""
    
    def __init__(self, params):
        super().__init__(params)
    
    @abstractmethod
    def update_event(self, inp=-1):
        return super().update_event(inp)