from qtpy.QtWidgets import (
    QWidget, 
    QVBoxLayout, 
    QLabel, 
    QTextEdit,
    QSplitter,
)

from qtpy.QtCore import Qt
from ryvencore import Node
from ryvencore.port import NodePort
from ..base_widgets import InspectorWidget

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .gui import NodeGUI

class NodeInspectorWidget(InspectorWidget[Node]):
    """Base class for the inspector widget of a node."""

    def __init__(self, params: tuple[Node, 'NodeGUI']):
        self.node, self.node_gui = params
        self.inspected = self.node
        self.flow_view = self.node_gui.flow_view
    
    def on_node_deleted(self):
        """Called when the node is deleted"""
        pass
    
    
class InspectorView(QWidget):
    """
    A widget that can display the inspector of the currently selected node.
    """

    def __init__(self, flow_view, parent: QWidget = None):
        super().__init__(parent=parent)
        self.node: Node = None
        self.inspector_widget: NodeInspectorWidget = None
        self.flow_view = flow_view

        self.setup_ui()
        self.flow_view.nodes_selection_changed.connect(self.set_selected_nodes)

    def setup_ui(self):
        self.setLayout(QVBoxLayout())

    def set_selected_nodes(self, nodes: list[Node]):
        if len(nodes) == 0:
            self.set_node(None)
        else:
            self.set_node(nodes[-1])

    def set_node(self, node: Node):
        """Sets a node for inspection, if it exists. Otherwise clears the inspector view"""

        if self.node == node:
            return

        if self.inspector_widget:
            self.inspector_widget.setVisible(False)
            self.inspector_widget.setParent(None)
            self.inspector_widget.unload()
            
        self.node = None
        self.inspector_widget = None

        if node is not None:
            self.node = node
            self.inspector_widget = self.node.gui.inspector_widget
            self.layout().addWidget(self.inspector_widget)
            self.inspector_widget.load()
            self.inspector_widget.setVisible(True)


class NodeInspectorDefaultWidget(NodeInspectorWidget, QWidget):
    """
    Default node inspector widget implementation.
    Can also be extended by embedding a custom widget.
    """
    
    @staticmethod
    def _big_bold_text(txt: str):
        return f'<b><bold>{txt}</bold></b>'
    
    def __init__(self, params, child: NodeInspectorWidget | None = None):
        QWidget.__init__(self)
        NodeInspectorWidget.__init__(self, params)

        self.child = child
        self.setLayout(QVBoxLayout())

        self.title_label: QLabel = QLabel()
        self.title_label.setText(
            f'<h2>{self.node.title}</h2> '
            f'<h4>id: {self.node.global_id}, pyid: {id(self.node)}</h4>'
        )
        # title
        self.layout().addWidget(self.title_label)
        
        # content splitter
        self.content_splitter = QSplitter()
        self.content_splitter.setOrientation(Qt.Orientation.Vertical)
        self.layout().addWidget(self.content_splitter)
        
        if child:
            self.content_splitter.addWidget(child)
        
        self.description_area: QTextEdit = QTextEdit()
        self.description_area.setReadOnly(True)
    
        self.content_splitter.addWidget(self.description_area)
    
    def load(self):
        self.process_description()
        super().load()
        if self.child:
            self.child.load()
    
    def unload(self):
        if self.child:
            self.child.unload()
        super().unload()
    
    def on_node_deleted(self):
        if self.child:
            self.child.on_node_deleted()
        return super().on_node_deleted()
    
    def process_description(self):
        desc = self.node.__doc__ if self.node.__doc__ and self.node.__doc__ != "" else "No description given"
        bbt = NodeInspectorDefaultWidget._big_bold_text
        
        def create_port_desc(ports: list[NodePort]):
            desc = ""
            for i in range(len(ports)):
                port = ports[i]
                label = port.label_str if port.label_str else 'No label'
                data_constr = port.allowed_data.__name__ if port.allowed_data else None
                desc += f"{i+1}) [ Label: {label}, Constraint: {data_constr} ]<br>" 
            
            if not desc:
                desc = "No ports!"
            return desc
        
        self.description_area.setText(f"""
<html>
    <body>
        {bbt('Title:')} {self.node.title}<br>
        {bbt('Version:')} {self.node.version}<br><br>
        {bbt('Description:')}<br><br>{desc}<br><br></p>
        {bbt('Inputs:')}<br><br>{create_port_desc(self.node._inputs)}<br><br>
        {bbt('Outputs:')}<br><br>{create_port_desc(self.node._outputs)}<br><br>
        
    </body>
</html>
        """)       
        