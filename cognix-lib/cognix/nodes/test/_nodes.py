from cognix.nodes import CognixNode, FrameNode
from ryvencore import PortConfig, Data
from random import randint

class TestStreamNode(FrameNode):
    
    title = "Random Int Generator"
    
    init_outputs=[
        PortConfig('value')
    ]
    
    def frame_update_event(self) -> bool:
        self.set_output_val(0, Data(randint(23, 1452)))    