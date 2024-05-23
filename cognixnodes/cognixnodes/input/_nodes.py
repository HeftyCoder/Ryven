from __future__ import annotations

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

from cognixcore.api import (
    Node,
    FrameNode,
    ProgressState, 
    PortConfig,
)
from cognixcore.config.traits import *
from threading import Thread
from traitsui.api import CheckListEditor

import numpy as np
# from cognix.nodes.input.payloads.lsl import LSLStreamInfo
from .payloads.lsl import LSLSignalInfo, Signal

class LSLInputNode(FrameNode):
    """Test class for receiving an lsl stream"""
    
    class Config(NodeTraitsConfig):
        
        f: str = File('Some path')
        stream_name: str = CX_Str('stream_name', desc='Stream name')
        stream_type: str = CX_Str('stream_type', desc = 'Stream type')
        search_action: str = Enum('name','type', desc='Filtering of streams based of specific value')    
        define_buffer:bool = Bool(True, desc='the creation of a buffer for the saving of the data samples')
        buffer_size: int = CX_Int(3276, desc='the size of the buffer in which the data samples are stored')

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
    init_outputs = [PortConfig(label='data', allowed_data=Signal)]
    
    def __init__(self, params):
        super().__init__(params)
        
        self.inlet: StreamInlet = None
        self.formats = ['double64','float32','int32','string','int16','int8','int64']
        self.reset()

    @property
    def config(self) -> LSLInputNode.Config:
        return self._config

    def stop(self):
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
        self.buffer = None
         
    def start(self):
        ### Check boolean for buffer
        self.buffer_size = self.config.buffer_size
        self.define_buffer = self.config.define_buffer
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
        
        if self.define_buffer:
            self.buffer = np.zeros(
                (self.buffer_size * 2, self.inlet.channel_count),
                dtype=self.formats[self.inlet.channel_format]
            )
            _,timestamps = self.inlet.pull_chunk(max_samples=self.buffer_size * 2, dest_obj=self.buffer)
            samples = self.buffer[:len(timestamps),:]
        else:
            samples,timestamps = self.inlet.pull_chunk()
            samples = np.array(samples)

        if not timestamps:
            return
        
        print(timestamps[0])
        
        signal = Signal(timestamps, samples, self.signal_info)

        self.set_output(0, signal)