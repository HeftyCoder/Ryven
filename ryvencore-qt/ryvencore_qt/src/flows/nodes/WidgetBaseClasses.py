"""The base classes for node custom widgets for nodes."""

from ryvencore import Data, Node

from ..FlowCommands import Delegate_Command
from ...GUIBase import SerializableItem

from typing import Generic, TypeVar, TYPE_CHECKING

if TYPE_CHECKING:
    from .NodeItem import NodeItem
    from .NodeGUI import NodeGUI
    from ..FlowView import FlowView

class NodeMainWidget(SerializableItem):
    """Base class for the main widget of a node."""

    def __init__(self, params: tuple[Node, 'NodeItem', 'NodeGUI']):
        self.node, self.node_item, self.node_gui = params

    def update_node(self):
        self.node.update()

    def update_node_shape(self):
        self.node_item.update_shape()


class NodeInputWidget(SerializableItem):
    """Base class for the input widget of a node."""

    def __init__(self, params):
        self.input, self.input_item, self.node, self.node_gui, self.position = \
            params

    def val_update_event(self, val: Data):
        """
        *VIRTUAL*

        Called when the input's value is updated through a connection.
        This can be used to represent the value in the widget.
        The widget is disabled when the port is connected.
        """
        pass

    # API methods

    def update_node_input(self, val: Data, silent=False):
        """
        Update the input's value and update the node.
        """
        self.input.default = val
        if not silent:
            self.input.node.update(self.node.inputs.index(self.input))

    def update_node(self):
        self.node.update(self.node.inputs.index(self.input))

    def update_node_shape(self):
        self.node_gui.update_shape()


InspectType = TypeVar('InspectType')
"""A type representing an inspectable object"""

class InspectorWidget(SerializableItem, Generic[InspectType]):
    """Base class representing an inspector to view and alter the state of an object"""
    
    def __init__(self, inspected_obj: InspectType, flow_view: FlowView):
        self.inspected = inspected_obj
        self.flow_view = flow_view
    
    def set_inspected(self, inspected_obj: InspectType):
        """
        VIRTUAL
        
        This needs to be overriden, otherwise it will throw an exception.
        Allows for dynamic reseting of an editor with a different inspectable
        """
        raise NotImplementedError(f"Inspector {self.__class__} does not allow reseting the inspectable")

    def load(self):
        """Called when the inspector is loaded in any kind of gui"""
    
    def unload(self):
        """Called when the inspector is removed from its parent gui"""
        
    def push_undo(self, text: str, undo_fn, redo_fn):
        """Push an undo function to the undo stack of the flow."""
        self.flow_view.push_undo(
            Delegate_Command(
                self.flow_view,
                text=text,
                on_undo=undo_fn,
                on_redo=redo_fn,
            )
        )
    
class NodeInspectorWidget(InspectorWidget[Node]):
    """Base class for the inspector widget of a node."""

    def __init__(self, params: tuple[Node, 'NodeGUI']):
        self.node, self.node_gui = params
        self.inspected = self.node
        self.flow_view = self.node_gui.flow_view()
    
    def on_node_deleted(self):
        """Called when the node is deleted"""
        pass


class NodeViewerWidget:
    """
    Base class for the view widget of a node.
    
    A view is a detached window for interacting with the node other than the inspector.
    """

    def __init__(self, params: tuple[Node, 'NodeGUI']):
        self.node, self.node_gui = params
    
    def on_before_shown(self):
        """
        VIRTUAL
        
        Called before the viewer is shown
        """
        pass
    
    def on_after_shown(self):
        """
        VIRTUAL
        
        Called after the viewer is shown
        """
        pass
    
    def on_before_hidden(self):
        """
        VIRTUAL
        
        Called before the viewer is hidden.
        """
    
    def on_after_hidden(self):
        """
        VIRTUAL
        
        Called after the viewer is hidden.
        """
        
    def on_before_closed(self):
        """
        VIRTUAL
        
        Called before the viewer is closed
        """
        pass

    def on_after_closed(self):
        """
        VIRTUAL
        
        Called after the viewer is closed
        """
    
    def on_node_update(self, data):
        """
        VIRTUAL
        
        Called when a node is updated (the updated event).
        The developer can pass any kind of data and update the view.
        """
        pass

    def on_node_deleted(self):
        """
        VIRTUAL
        
        Called when a node is deleted
        """
        pass
        