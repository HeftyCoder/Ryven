from __future__ import annotations
from queue import Queue

from qtpy.QtCore import QObject, Signal
from qtpy.QtWidgets import QWidget, QApplication
from qtpy.QtGui import Qt

from .WidgetBaseClasses import NodeMainWidget, NodeInputWidget, NodeInspectorWidget, NodeViewerWidget
from .NodeInspector import NodeInspectorDefaultWidget
from .NodeViewer import NodeViewerDefault

from ryvencore.rc import ProgressState
from ryvencore import Node

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .NodeItem import NodeItem
    from ...SessionGUI import SessionGUI
    from ..FlowView import FlowView

class NodeGUI(QObject):
    """
    Interface class between nodes and their GUI representation.
    """

    # customizable gui attributes
    description_html: str = None
    
    main_widget_class: type[NodeMainWidget | QWidget] = None
    main_widget_pos: str = 'below ports'
    input_widget_classes: dict[str, type[NodeInputWidget | QWidget]] = {}
    inspector_widget_class: type[NodeInspectorWidget | QWidget] = NodeInspectorDefaultWidget
    wrap_inspector_in_default: bool = False
    viewer_widget_class: type[NodeViewerWidget | QWidget] = NodeViewerDefault
    
    init_input_widgets: dict = {}
    style: str = 'normal'
    color: str = '#c69a15'
    display_title: str = None
    icon: str = None

    # qt signals
    updating = Signal()
    update_error = Signal(object)
    input_added = Signal(int, object)
    output_added = Signal(int, object)
    input_removed = Signal(int, object)
    output_removed = Signal(int, object)
    update_shape_triggered = Signal()
    hide_unconnected_ports_triggered = Signal()
    show_unconnected_ports_triggered = Signal()
    progress_updated = Signal(ProgressState)
    
    def __init__(self, params: tuple[Node, SessionGUI, FlowView]):
        QObject.__init__(self)

        self.node, self.session_gui, self._flow_view = params
        self.item: NodeItem = None   # set by the node item directly after this __init__ call
        setattr(self.node, 'gui', self)

        if self.display_title is None:
            self.display_title = self.node.title

        self.input_widgets = {}     # {input: widget name}
        for i, widget_data in self.init_input_widgets.items():
            self.input_widgets[self.node._inputs[i]] = widget_data
        # using attach_input_widgets() one can buffer input widget
        # names for inputs that are about to get created
        self._next_input_widgets = Queue()

        self.error_during_update = False

        # turn ryvencore signals into Qt signals
        self.node.updating.sub(self._on_updating)
        self.node.update_error.sub(self._on_update_error)
        self.node.input_added.sub(self._on_new_input_added)
        self.node.output_added.sub(self._on_new_output_added)
        self.node.input_removed.sub(self._on_input_removed)
        self.node.output_removed.sub(self._on_output_removed)
        self.node.progress_updated.sub(self._on_progress_updated)

        # create the inspector widget
        self.inspector_widget = self.create_inspector()
        # create viewer widget
        self.viewer_widget = self.create_viewer()
        
        # init the default actions
        self.actions = self._init_default_actions()

    def create_viewer(self):
        """Creates the viewer for this node."""
        
        return (
            self.viewer_widget_class((self.node, self)) 
            if self.viewer_widget_class else None
        )
        
    def create_inspector(self):
        """Creates the inspector based on settings of the GUI."""
        
        inspector_params = (self.node, self)
        if self.wrap_inspector_in_default:
            inspector_widget = NodeInspectorDefaultWidget(
                child=self.inspector_widget_class((self.node, self)),
                params=inspector_params,
            )
        else:
            inspector_widget = self.inspector_widget_class(inspector_params)
        return inspector_widget
    
    def initialized(self):
        """
        *VIRTUAL*

        Called after the node GUI has been fully initialized.
        The Node has been created already (including all ports) and loaded.
        No connections have been made to ports of the node yet.
        """
        pass

    """
    slots
    """

    def _on_update_error(self, e):
        self.update_error.emit(e)

    def _on_updating(self, inp: int):
        # update input widget
        if inp != -1 and self.item.inputs[inp].widget is not None:
            o = self.node.flow.connected_output(self.node._inputs[inp])
            if o is not None:
                self.item.inputs[inp].widget.val_update_event(o.val)
        self.updating.emit()

    def _on_new_input_added(self, _, index, inp):
        if not self._next_input_widgets.empty():
            self.input_widgets[inp] = self._next_input_widgets.get()
        self.input_added.emit(index, inp)

    def _on_new_output_added(self, _, index, out):
        self.output_added.emit(index, out)

    def _on_input_removed(self, _, index, inp):
        self.input_removed.emit(index, inp)

    def _on_output_removed(self, _, index, out):
        self.output_removed.emit(index, out)

    def _on_progress_updated(self, progress: ProgressState):
        self.progress_updated.emit(progress)
    
    def _on_restored(self):
        """Called when a node is restored from being deleted"""
        pass
    
    def _on_deleted(self):
        """Called when a node is deleted"""
        if self.inspector_widget:
            self.inspector_widget.on_node_deleted()
            
        if self.viewer_widget:
            self.viewer_widget.on_node_deleted()
            self.hide_viewer()
        
    """
    actions
    
    TODO: move actions to ryvencore?
    """

    def _init_default_actions(self):
        """
        Returns the default actions every node should have
        """
        result = {
            'update shape': {'method': self.update_shape},
            'hide unconnected ports': {'method': self.hide_unconnected_ports},
            'change title': {'method': self.change_title},
        }
        
        if self.viewer_widget_class:
            result['toggle viewer'] = {'method': self.toggle_viewer}
        
        return result

    def _deserialize_actions(self, actions_data):
        """
        Recursively reconstructs the actions dict from the serialized version
        """

        def _transform(actions_data: dict):
            """
            Mutates the actions_data argument by replacing the method names
            with the actual methods. Doesn't modify the original dict.
            """
            new_actions = {}
            for key, value in actions_data.items():
                if key == 'method':
                    try:
                        value = getattr(self, value)
                    except AttributeError:
                        print(f'Warning: action method "{value}" not found in node "{self.node.title}", skipping.')
                elif isinstance(value, dict):
                    value = _transform(value)
                new_actions[key] = value
            return new_actions

        return _transform(actions_data)

    def _serialize_actions(self, actions):
        """
        Recursively transforms the actions dict into a JSON-compatible dict
        by replacing methods with their name. Doesn't modify the original dict.
        """

        def _transform(actions: dict):
            new_actions = {}
            for key, value in actions.items():
                if key == 'method':
                    new_actions[key] = value.__name__
                elif isinstance(value, dict):
                    new_actions[key] = _transform(value)
                else:
                    new_actions[key] = value
            return new_actions

        return _transform(actions)

    """
    serialization
    """

    def data(self):
        return {
            'actions': self._serialize_actions(self.actions),
            'display title': self.display_title,
            'inspector widget': self.inspector_widget.get_state(),
        }

    def load(self, data):
        if 'actions' in data:   # otherwise keep default
            self.actions = self._deserialize_actions(data['actions'])
        if 'display title' in data:
            self.display_title = data['display title']
        if 'special actions' in data:   # backward compatibility
            self.actions = self._deserialize_actions(data['special actions'])
        if 'inspector widget' in data:
            self.inspector_widget.set_state(data['inspector widget'])

    """
    GUI access methods
    """
    def title(self):
        return self.display_title
    
    def show_viewer(self):
        self.viewer_widget.setWindowTitle(self.title())
        self.viewer_widget.setParent(self.flow_view)
        self.viewer_widget.setWindowFlags(
            self.viewer_widget.windowFlags() |
            Qt.WindowType.WindowMinimizeButtonHint |
            Qt.WindowType.Dialog
        )
        self.viewer_widget.move(
            self.flow_view.mapToGlobal(
                self.item.pos()
            ).toPoint()
        )
        self.viewer_widget.show()
    
    def hide_viewer(self):
        self.viewer_widget.hide()
        
    def toggle_viewer(self):
        
        if self.viewer_widget.isHidden():
            self.show_viewer()
        else:
            self.hide_viewer()
            
    def set_display_title(self, t: str):
        self.display_title = t
        if self.viewer_widget:
            self.viewer_widget.setWindowTitle(self.display_title)
        self.update_shape()

    @property
    def flow_view(self):
        return self._flow_view

    def main_widget(self):
        """Returns the main_widget object, or None if the item doesn't exist (yet)"""

        return self.item.main_widget

    def attach_input_widgets(self, widget_names: list[str]):
        """Attaches the input widget to the next created input."""

        for w in widget_names:
            self._next_input_widgets.queue(w)

    def input_widget(self, index: int):
        """Returns a reference to the widget of the corresponding input"""

        return self.item.inputs[index].widget

    def session_stylesheet(self):
        return self.session_gui.design.global_stylesheet

    def update_shape(self):
        """Causes recompilation of the whole shape of the GUI item."""

        self.update_shape_triggered.emit()

    def hide_unconnected_ports(self):
        """Hides all ports that are not connected to anything."""

        del self.actions['hide unconnected ports']
        self.actions['show unconnected ports'] = {'method': self.show_unconnected_ports}
        self.hide_unconnected_ports_triggered.emit()

    def show_unconnected_ports(self):
        """Shows all ports that are not connected to anything."""

        del self.actions['show unconnected ports']
        self.actions['hide unconnected ports'] = {'method': self.hide_unconnected_ports}
        self.show_unconnected_ports_triggered.emit()

    def change_title(self):
        from qtpy.QtWidgets import QDialog, QVBoxLayout, QLineEdit

        class ChangeTitleDialog(QDialog):
            def __init__(self, title):
                super().__init__()
                self.new_title = None
                self.setLayout(QVBoxLayout())
                self.line_edit = QLineEdit(title)
                self.layout().addWidget(self.line_edit)
                self.line_edit.returnPressed.connect(self.return_pressed)

            def return_pressed(self):
                self.new_title = self.line_edit.text()
                self.accept()

        d = ChangeTitleDialog(self.display_title)
        d.exec()
        if d.new_title:
            self.set_display_title(d.new_title)
