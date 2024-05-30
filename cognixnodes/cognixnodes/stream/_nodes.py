from __future__ import annotations

from pylsl import (
    resolve_stream,
    resolve_bypred,
    StreamInlet, 
    StreamInfo,
    proc_clocksync , 
    proc_dejitter, 
    proc_monotonize,
    proc_threadsafe ,
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

from ..core import StreamSignal, StreamSignalInfo

class LSLSignalInfo(StreamSignalInfo):
    
    def __init__(self, lsl_info: StreamInfo):
        self._lsl_info = lsl_info
        
        stream_xml = lsl_info.desc()
        chans_xml = stream_xml.child("channels")
        chan_xml_list = []
        ch = chans_xml.child("channel")
        while ch.name() == "channel":
            chan_xml_list.append(ch)
            ch = ch.next_sibling("channel")
            
        self.channels: dict[str, int] =  {
            chan_xml_list[c_index].child_value('label'): c_index 
            for c_index in range(len(chan_xml_list))
        }
        
        super().__init__(
            nominal_srate=lsl_info.nominal_srate(),
            signal_type=lsl_info.type(),
            data_format=lsl_info.channel_format(),
            name=lsl_info.name(),
        )

class LSLInputNode(FrameNode):
    """An LSL Input Stream"""
    
    class Config(NodeTraitsConfig):
        
        stream_name: str = CX_Str('stream_name', desc='Stream name')
        stream_type: str = CX_Str('stream_type', desc = 'Stream type')
        search_action: str = Enum('name','type', desc='Filtering of streams based of specific value')    
        define_buffer:bool = Bool(True, desc='the creation of a buffer for the saving of the data samples')
        buffer_size: int = CX_Int(3276, desc='the size of the buffer in which the data samples are stored')
        lowercase_labels: bool = Bool(False, desc="if checked, makes all the incoming labels into lowercase")
        debug: bool = Bool(False, desc="when true, logs debug messages")

        #### configuration for buffer size of data received
        #### (define buffer) Boolean for transformation from list to np.array (if False transform else keep)
        processing_flag_mode: int = List(
            editor=CheckListEditor(
                values=
                [
                    (proc_clocksync, 'synchronization'),  
                    (proc_dejitter, 'dejitter'),
                    (proc_monotonize, 'monotonize'),
                    (proc_threadsafe, 'threadsafe')
                ],
                cols=2
            ),
            style='custom'
        )

        
    
    title = 'LSL Input'
    version = '0.1'
    init_outputs = [PortConfig(label='data', allowed_data=StreamSignal)]
    
    def __init__(self, params):
        super().__init__(params)
        
        self.inlet: StreamInlet = None
        self.formats = ['double64','float32','int32',str,'int16','int8','int64']
        # The stream won't change after initialization
        self.cached_labels: list[str] = None 
    
    @property
    def config(self) -> LSLInputNode.Config:
        return self._config
    
    def init(self):
        self.t = None
        self.force_stop = False
        self.inlet = None
        self.signal_info: LSLSignalInfo = None
        self.buffer:np.ndarray | list = None
        
        ### Check boolean for buffer
        self.buffer_size = self.config.buffer_size
        self.define_buffer = self.config.define_buffer
        self.stream_name = self.config.stream_name
        self.stream_type = self.config.stream_type
        self.search_action = self.config.search_action
        self.processing_flag_mode = self.config.processing_flag_mode
        
        self.logger.warn(f'buffer_size:{self.buffer_size},define_buffer:{self.define_buffer}')
        
        flags = 0
        for flag in self.processing_flag_mode:
            flags |= flag
        
        def _search_stream():
            
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
                                                                 
                self.inlet = StreamInlet(results[0], processing_flags=flags)
                self.signal_info = LSLSignalInfo(self.inlet.info())
                
                labels = self.signal_info.channels.keys()
                self.cached_labels = (
                    list(labels) if not self.config.lowercase_labels
                    else [label.lower() for label in labels]
                )
                
                if self.define_buffer: 
                    
                    if self.formats[self.inlet.channel_format]!=str:
                    
                        self.buffer = np.zeros(
                            (self.buffer_size * 2, int(self.inlet.channel_count)),
                            dtype=self.formats[self.inlet.channel_format]
                        )
                    
                    else:
                        
                        self.buffer = []
    
                self.progress = ProgressState(1, 1, 'Streaming!')
            
        self.t = Thread(target=_search_stream)
        self.t.start()

    def stop(self):
        
        self.force_stop = True
        if self.t:
            self.t.join()
            
        if self.inlet:
            self.inlet.close_stream()
            
        self.set_progress_value(-1,'Stopping stream...')
        self.progress = None
    
    def frame_update_event(self):
        if not self.inlet or (self.define_buffer and self.buffer is None):
            return
        
        if self.define_buffer:
            # numpy buffer used
            if self.formats[self.inlet.channel_format]!=str:
            
                _, timestamps = self.inlet.pull_chunk(max_samples=self.buffer_size * 2, dest_obj=self.buffer)
                if timestamps:
                    samples = self.buffer[:len(timestamps),:]
            # there's an issue with the str (marker) streams
            # since the marker streams are probably few, we
            # don't use the buffer
            else:
                samples, timestamps = self.inlet.pull_chunk()
                if timestamps:
                    samples = np.array(samples)
        
        else:
            samples, timestamps = self.inlet.pull_chunk()
            if timestamps:
                samples = np.array(samples)
        
        if self.config.debug and timestamps:
            self.logger.info(f'{timestamps},{samples}')
            
        if not timestamps:
            return
        
        signal = StreamSignal(
            timestamps, 
            self.cached_labels,
            samples, 
            self.signal_info
        )
        self.set_output(0, signal)

class LSLOutputNode(FrameNode):
    """An LSL Output Stream"""
    pass
