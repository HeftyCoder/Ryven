from pylsl import (
    resolve_stream,
    resolve_bypred,
    StreamInlet, 
    StreamInfo,
    proc_clocksync , 
    proc_dejitter, 
    proc_monotonize,
    proc_none ,
    proc_threadsafe ,
    proc_ALL
)

from threading import Thread
from ryvencore import PortConfig, Data
from ryvencore.data.built_in import *
from ryvencore.data.built_in.collections.abc import MutableSetData
from ryvencore import ProgressState

from cognix.api import CognixNode, FrameNode
from cognix.config.traits import *
from traitsui.api import CheckListEditor
# from cognix.nodes.input.payloads.lsl import LSLStreamInfo
from .payloads.lsl import LSLSignalInfo, Signal

class LSLInput(FrameNode):
    """Test class for receiving an lsl stream"""
    
    class Config(NodeTraitsConfig):
        
        f: str = File('Some path')
        stream_name: str = CX_Str('stream_name',desc='Stream name')
        stream_type: str = CX_Str('stream_type',desc = 'Stream type')
        search_action: str = Enum('name','type',desc='Filtering of streams based of specific value')    
        #### configuration for buffer size of data received
        #### (define buffer) Boolean for transformation from list to np.array (if False transform else keep)
        processing_flag_mode: int = List(
            editor=CheckListEditor(
                values=
                [
                    (1, 'synchronization'),  
                    (2, 'dejitter'),
                    (4, 'monotonize'),
                    (8, 'threadsafe')
                ],
                cols=2
            ),
            style='custom'
        )

        
    
    title = 'LSL Input'
    version = '0.0.1'
    init_outputs = [PortConfig(label='data')]
    
    def __init__(self, params):
        super().__init__(params)
        
        self.inlet: StreamInlet = None
        
        self.reset()
        
    def on_stop(self):
        import time
        
        self.force_stop = True
        if self.t:
            self.t.join()
            
        if self.inlet:
            self.inlet.close_stream()
            
        self.set_progress_value(-1,'Stopping stream...')
        time.sleep(1)
        self.progress = None
        
    def reset(self):
        self.t = None
        self.force_stop = False
        self.inlet = None
        self.signal_info = None
        ### buffer = None
         
    def on_start(self):
        ### Check boolean for buffer
        self.stream_name = self.config.stream_name
        self.stream_type = self.config.stream_type
        self.search_action = self.config.search_action
        self.processing_flag_mode = self.config.processing_flag_mode
        
        flags = 0
        for flag in self.processing_flag_mode:
            flags |= flag
        print(flags)
        
        def _search_stream():
            
            print(self.stream_name)
            
            self.progress = None
            self.progress = ProgressState(1,-1,'Searching stream')
            
            while True:
                
                if self.search_action == 'name':
                    results = resolve_bypred(f"name='{self.stream_name}'", 1, 3)
                elif self.search_action == 'type':
                    results = resolve_bypred(f"type='{self.stream_type}'", 1, 3)
                
                if results or self.force_stop:
                    break
            
            if results:

                flags = 0
                for flag in self.processing_flag_mode:
                    flags |= flag
                                                                 
                self.inlet = StreamInlet(results[0],processing_flags=flags)
                self.signal_info = LSLSignalInfo(self.inlet.info())
                self.progress = ProgressState(1, 1, 'Streaming!')
            
        self.t = Thread(target=_search_stream)
        self.t.start()
    
    def frame_update_event(self):
        if not self.inlet:
            return
        
        ### If boolean is True -> pull_chunk(buffer)
        ### Else (samples) list -> np.array
        
        data = self.inlet.pull_chunk()
        samples, timestamps = data
        if not timestamps:
            return
        
        print(timestamps[0])
        
        ### samples depends on the boolean for the buffer!
        
        signal = Signal(timestamps, samples, self.signal_info)
        ### inside of Data -> Payload
        self.set_output_val(0, Data(signal))