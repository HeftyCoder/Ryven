"""A collection of base widgets that are useful for showcasing Data types"""

from ..field_widgets import type_to_widget
from ..base_widgets import InspectorWidget
from ryvencore import Data
from typing import TypeVar

DataType = TypeVar('DataType', bound=Data)


class DataInspector(InspectorWidget[DataType]):
    """
    An inspector for data types
    
    Designed to change the value of a payload
    """    
    pass