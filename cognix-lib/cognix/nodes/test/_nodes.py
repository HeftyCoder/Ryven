from cognix.nodes import CognixNode, FrameNode
from ryvencore import NodeOutputType, Data
from random import randint

class TestStreamNode(FrameNode):
    
    title = "Random Int Generator"
    
    init_outputs=[
        NodeOutputType('value')
    ]
    
    def frame_update_event(self) -> bool:
        self.set_output_val(Data(randint(23, 1452)))    