"""A collection of base widgets that are useful for showcasing Data types"""

from ..flows.view import FlowView
from ..inspector import InspectorWidget, InspectedChangedEvent
from ryvencore import Data
from qtpy.QtWidgets import QWidget, QVBoxLayout

class DataInspector(InspectorWidget[Data], QWidget):
    """
    An inspector for data types
    
    Designed to change the value of a payload
    """    
    
    def __init__(self, inspected_obj: Data, flow_view: FlowView):
        QWidget.__init__(self)
        InspectorWidget.__init__(self, inspected_obj, flow_view)
        
    def on_insp_changed(self, change_event: InspectedChangedEvent[Data]):
        inspected_obj = change_event.new
        field_widget_type = self.gui_env.get_field_widget(type(inspected_obj.payload))
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        field_widget = field_widget_type(self, 'payload', label='value')
        field_widget.setContentsMargins(0, 0, 0, 0)
        self.layout().addWidget(field_widget)
        