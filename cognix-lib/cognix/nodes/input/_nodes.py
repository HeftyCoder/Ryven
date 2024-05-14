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
from .payloads.lsl import LSLStreamInfo,LSLStreamPayload

class LSLInput(FrameNode):
    """Test class for receiving an lsl stream"""
    
    class Config(NodeTraitsConfig):
        
        f = File('Some path')
        stream_name = CX_Str('stream_name',desc='Stream name')
        stream_type = CX_Str('stream_type',desc = 'Stream type')
        search_action = Enum('name','type',desc='Filtering of streams based of specific value')    
        processing_flag_mode = List(
            editor=CheckListEditor(
                values=
                [
                    (1, 'one'),  
                    (2, 'two'),
                    (4, 'three'),
                    (8, 'four')
                ]
            ),
            style='readonly'
        )
        # clocksync_flag = Bool()
        # dejitter_flag = Bool()
        # monotize_flag = Bool()
        # threadsage_flag = Bool()
        
    
    title = 'LSL Input'
    version = '0.0.1'
    init_outputs = [PortConfig(label='data')]
    
    def __init__(self, params):
        super().__init__(params)
        
        self.inlet: StreamInlet = None
        self.t = None
        self.force_stop = False
        
    def on_stop(self):
        import time
        print('Attempting stop!')
        
        self.force_stop = True
        if self.t:
            self.t.join()
            
        if self.inlet:
            self.inlet.close_stream()
            
        self.set_progress_value(-1,'Attempting stop!')
        time.sleep(1)
        print('Stopped stream')
        self.set_progress_value(0,'Stopped streaming')
        
    def reset(self):
        self.t = None
        self.force_stop = False
        self.inlet = None
        
    def on_start(self):
        print(self.config.processing_flag_mode)
        self.stream_name = self.config.stream_name
        self.stream_type = self.config.stream_type
        self.search_action = self.config.search_action
        self.processing_flag_mode = self.config.processing_flag_mode

        print(self.processing_flag_mode)
        
        def _search_stream():
            
            print(self.stream_name)
            
            self.progress = None
            self.progress = ProgressState(1,-1,'Searching data')
            while True:
                print('Searching data')
                
                if self.search_action == 'name':
                    results = resolve_bypred(f"name='{self.stream_name}'", 1, 3)
                if self.search_action == 'type':
                    results = resolve_bypred(f"type='{self.stream_type}'", 1, 3)
                
                if results or self.force_stop:
                    break
            
            if results:

                flags = 0
                for flag in self.processing_flag_mode:
                    flags |= flag
                                  
                print(flags)                  
                self.inlet = StreamInlet(results[0],processing_flags=flags)
                
                print('Found Stream!!')
                self.progress = None
                self.progress = ProgressState(1,1,'Streaming!')
                # self.set_output_val(0, Data(self.inlet))
            
        self.t = Thread(target=_search_stream)
        self.t.start()
    
    def frame_update_event(self):
        if not self.inlet:
            return
        data = self.inlet.pull_chunk()
        print(data)
        samples, timestamps = data
        if not timestamps:
            return
        
        ### inside of Data -> Payload
        self.set_output_val(0, Data(data))