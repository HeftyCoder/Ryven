from pylsl import resolve_stream, resolve_bypred, StreamInlet, StreamInfo
from threading import Thread
from ryvencore import NodeOutputType, Data
from ryvencore import NodeInputType, NodeOutputType
from ryvencore.data.built_in import *
from ryvencore.data.built_in.collections.abc import MutableSetData
from ryvencore import ProgressState

from cognix.api import CognixNode, FrameNode
from cognix.config.traits import *

class LSLInput(FrameNode):
    """Test class for receiving an lsl stream"""
    
    class Config(NodeTraitsConfig):
        
        f = File('Some path')
        stream_name = CX_Str('stream_name')
        some_list = List(CX_Int(54))    
    
    title = 'LSL Input'
    version = '0.0.1'
    init_outputs = [NodeOutputType(label='data')]
    
    def __init__(self, params):
        super().__init__(params)
        self.stream_name = 'eeg'
        self.inlet: StreamInlet = None
        self.t = None
        self.force_stop = False
        
    def on_stop(self):
        print('Attempting stop!')
        self.force_stop = True
        if self.t:
            self.t.join()
            
        if self.inlet:
            self.inlet.close_stream()
        print('Stopped stream')
        
    def reset(self):
        self.t = None
        self.force_stop = False
        self.inlet = None
        
    def on_start(self):
        
        def _search_stream():
            
            while True:
                print('Searching data')
                results = resolve_bypred("type='EEG'", 1, 3)
                if results or self.force_stop:
                    break
            if results:
                self.inlet = StreamInlet(results[0])
                print('Found Stream!!')
                self.set_output_val(0, Data(self.inlet))
        
        self.t = Thread(target=_search_stream)
        self.t.start()
    
    def frame_update_event(self):
        if not self.inlet:
            return
        data = self.inlet.pull_chunk()
        samples, timestamps = data
        if not timestamps:
            return
        self.set_output_val(0, Data(data))
    
class MyConfig(NodeTraitsConfig):
    
    s = CX_Int()
    parameter: int = CX_Int(245)
    li: list[int] = List(CX_Int(0))

class AnotherConfig(NodeTraitsConfig):
    
    myname: float = CX_Float()
    some_file:str = File()
    
class SomeInput(CognixNode):
    
    title = 'George'
    
    init_inputs = [
        NodeInputType(label='george', allowed_data=RealData),
        NodeInputType(label='we', allowed_data=MutableSetData)
    ]
    
    init_outputs = [
        NodeOutputType("mm", allowed_data=IntegerData),
        NodeOutputType("zz", allowed_data=ListData)
    ]
    
    class Config(NodeTraitsGroupConfig):
        
        one_config: MyConfig = CX_Instance(MyConfig)
        second_config: AnotherConfig = CX_Instance(AnotherConfig)
    
    def update(self, inp=-1):
        
        self.progress = ProgressState(1, 0.2, "Started loading")
        
        self.set_progress_value(0.3, "wersd")
        
        val = self.input_payload(inp)
        config: SomeInput.Config = self.config
        my_config: MyConfig = config.one_config
        
        self.progress = None