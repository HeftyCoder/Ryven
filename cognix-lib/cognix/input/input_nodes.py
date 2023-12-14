from ..base_nodes import CognixNode, FrameNode
from pylsl import resolve_stream, resolve_bypred, StreamInlet, StreamInfo
from threading import Thread
from ryvencore import NodeOutputType, Data

class LSLInput(FrameNode):
    """Test class for receiving an lsl stream"""
    
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
                self.inlet = results[0]
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
    

all_input_nodes = [LSLInput,]
input_nodes_pkg = 'input'