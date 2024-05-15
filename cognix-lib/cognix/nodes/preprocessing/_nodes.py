from __future__ import annotations
from cognix.flow import CognixFlow
from ryvencore.data.built_in import *
from ryvencore import Data,PortConfig

from cognix.config.traits import *
from cognix.api import CognixNode,FrameNode

from typing import Union
import numpy as np
from traitsui.api import CheckListEditor

from pylsl import local_clock

from collections.abc import Sequence

from ..input.payloads.core import Signal
from .utils_for_preprocessing.segmentation_helper import CircularBuffer

class SegmentationNode(CognixNode):
    title = 'Segmentation'
    version = '0.1'

    class Config(NodeTraitsConfig):
        offset: tuple[float, float] = Tuple((-0.5, 0.5))
        marker_name: str = CX_String('marker')
        buffer_duration: float = CX_Float(10.0, desc = 'Duration of the buffer in seconds')
        error_margin: float = CX_Float()

    init_inputs = [PortConfig(label='data'),
                   PortConfig(label='marker')]

    init_outputs = [PortConfig(label='segment')]
    
    def __init__(self, flow: CognixFlow):
        super().__init__(flow)
        self.buffer: CircularBuffer = None
        self.update_dict = {
            0: self.update_data,
            1: self.update_marker
        }
        self.reset()
    
    @property
    def config(self) -> SegmentationNode.Config:
        return self._config
    
    def reset(self):
        self.current_timestamp = -1
        
    def update_event(self, inp=-1):
        
        update_result = self.call_update_event(inp)
        
        if update_result and self.buffer and self.current_timestamp > 0:
            segment = self.buffer.find_segment(self.current_timestamp, self.config.offset)
            self.set_output_val(0, Data(segment))
    
    def call_update_event(self, inp):
        func = self.update_dict.get(inp)
        if not func:
            return False
        return func(inp)
    
    def update_data(self, inp: int):
        data_signal: Signal = self.input_payload(inp)
        if not data_signal:
            return False
        
        # create buffer if it doesn't exist
        if not self.buffer:
            self.buffer = CircularBuffer(
                sampling_frequency=data_signal.info.nominal_srate,
                buffer_duration=self.config.buffer_duration,
                error_margin=self.config.error_margin,
                start_time=local_clock()
            )
        
        self.buffer.append(data_signal.data.T, data_signal.timestamps)
        return True

    def update_marker(self, inp: int):
        marker_signal: Signal = self.input_payload(inp)
        # no signal or no buffer
        if not marker_signal:
            return False
        
        marker_name = marker_signal.data[0]
        marker_ts = marker_signal.timestamps[0]
        # marker doesn't match
        if marker_name != self.config.marker_name:
            return False
        
        self.current_timestamp = marker_ts
        return True

  
class SignalSelectionNode(CognixNode):
    
    title = 'EEG Signal Selection'
    version = '0.1'
    
    class Config(NodeTraitsConfig):
        
        channels = ['Fp1', 'Af3', 'F7', 'F3', 'Fc1', 'Fc5', 'T7',
            'C3', 'Cp1', 'Cp5', 'P7', 'P3', 'Pz', 'Po3', 'O1', 'Oz', 'O2', 'Po4',
            'P4', 'P8', 'Cp6', 'Cp2', 'C4', 'T8', 'Fc6', 'Fc2', 'F4', 'F8', 'Af4',
            'Fp2', 'Fz', 'Cz']
        
        
        channels_selected = List(
            editor=CheckListEditor(
                values= [(channel, channel) for channel in channels],
                cols=4
            ),
            style='custom'
        )
    
    init_inputs = [PortConfig(label='data_in')]
    init_outputs = [PortConfig(label='data_out')]
    
    def __init__(self, flow: CognixFlow):
        super().__init__(flow)
        self.reset()

    @property
    def config(self) -> SignalSelectionNode.Config:
        return self._config
    
    def reset(self):
        self.chan_inds = None
        
    def on_start(self):
        self.selected_channels = set(self.config.channels_selected)
        print(self.selected_channels)
        
    def update_event(self, inp=-1):
        
        signal: Signal = self.input_payload(inp)
        if not signal:
            return 
        
        if not self.chan_inds:
            self.chan_inds = [
                index 
                for chan_name, index in signal.info.channels 
                if chan_name in self.selected_channels
            ]
        
        sub_signal = signal.data[self.chan_inds]
        self.set_output_val(0, Data(sub_signal))
            
            
            
            
            
            
            
            
            
            