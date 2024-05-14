from ryvencore.data.built_in import *
from ryvencore import Data,PortConfig

from cognix.config.traits import *
from cognix.api import CognixNode,FrameNode

from typing import Union
import numpy as np

from .utils_for_xdf import function_for_creation_of_file

class XDFwriter(CognixNode):
    title = 'XDF Writer'
    version = '0.1'
    
    init_inputs = [PortConfig()]