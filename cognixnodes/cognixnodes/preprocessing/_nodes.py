from __future__ import annotations

from cognixcore import Flow, PortConfig
import mne

from cognixcore.config.traits import *
from typing import Union
import numpy as np
from traitsui.api import CheckListEditor

from pylsl import local_clock

from collections.abc import Sequence

from ..input.payloads.core import Signal
from .utils.segmentation_helper import CircularBuffer

class SegmentationNode(Node):
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
    
    def __init__(self, flow: Flow):
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
            self.set_output(0, segment)
    
    def call_update_event(self, inp):
        func = self.update_dict.get(inp)
        if not func:
            return False
        return func(inp)
    
    def update_data(self, inp: int):
        data_signal: Signal = self.input(inp)
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
        marker_signal: Signal = self.input(inp)
        # no signal or no buffer
        if not marker_signal:
            return False
        
        marker_name = marker_signal.data[0]
        marker_ts = marker_signal.timestamps[0]
        # marker doesn't match
        if marker_name != self.config.marker_name:
            return False
        print(marker_name,marker_ts)
        self.current_timestamp = marker_ts
        return True

  
class SignalSelectionNode(Node):
    
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
    
    def __init__(self, flow: Flow):
        super().__init__(flow)
        self.reset()

    @property
    def config(self) -> SignalSelectionNode.Config:
        return self._config
    
    def reset(self):
        self.chan_inds = None
        
    def start(self):
        self.selected_channels = set(self.config.channels_selected)
        print(self.selected_channels)
        
    def update_event(self, inp=-1):
        
        signal: Signal = self.input(inp)
        if not signal:
            return 
        
        if not self.chan_inds:
            self.chan_inds = [
                index 
                for chan_name, index in signal.info.channels 
                if chan_name in self.selected_channels
            ]
        
        sub_signal = signal.data[self.chan_inds]
        self.set_output(0, sub_signal)
            
            
class FIRFilterNode(Node):
    title = 'FIR Filter'
    version = '0.1'
    
    class Config(NodeTraitsConfig):
        low_freq: float = CX_Float(desc='the low frequency of the filter')
        high_freq: float = CX_Float(desc='the high frequency of the fitler')
        filter_length_str: str = CX_String(desc='the length of the filterin ms')
        filter_length_int: int = CX_Int(desc='the length of the filter in samples')
        l_trans_bandwidth:float = CX_Float(0.0,desc='the width of the transition band at the low cut-off frequency in Hz')
        h_trans_bandwidth:float = CX_Float(0.0,desc='the width of the transition band at the high cut-off frequency in Hz')
        phase:str = Enum('zero','minimum','zero-double','minimum-half',desc='the phase of the filter')
        fir_window:str = Enum('hamming','hann','blackman',desc='the window to use in the FIR filter')
        fir_design:str = Enum('firwin','firwin2',desc='the design of the FIR filter')
            
    init_inputs = [PortConfig(label='data',allowed_data=Signal)]
    init_outputs = [PortConfig(label='filtered data',allowed_data=Signal)]
    
    @property
    def config(self) -> FIRFilterNode.Config:
        return self._config
    
    def start(self):
        
        self.filter_length = 'auto'
        print(self.config.filter_length_str,self.config.filter_length_int)
        if self.config.filter_length_str:
            self.filter_length = self.config.filter_length_str
        if self.config.filter_length_int:
            self.filter_length = self.config.filter_length_int
                
    def update_event(self, inp=-1):
        
        signal:Signal = self.input(inp)
        if signal:
            filtered_signal:Signal = signal.copy()
            
            filtered_data = mne.filter.filter_data(
                data = signal.data,
                sfreq = signal.info.nominal_srate,
                l_freq = self.config.low_freq,
                h_freq = self.config.high_freq,
                filter_length = self.filter_length,
                l_trans_bandwidth = self.config.l_trans_bandwidth if self.config.l_trans_bandwidth!=0.0 else None,
                h_trans_bandwidth = self.config.h_trans_bandwidth if self.config.h_trans_bandwidth!=0.0 else None,
                n_jobs = -1,
                method = 'fir',
                phase = self.config.phase,
                fir_window = self.config.fir_window,
                fir_design = self.config.fir_design
                )

            filtered_signal.data = filtered_data
            self.set_output(0, filtered_signal)
    
          
class IIRFilterNode(Node):
    title = 'IIR Filter'
    version = '0.1'
    
    class Config(NodeTraitsConfig):
        f_pass: float = CX_Float(desc='the low frequency of the filter')
        f_stop: float = CX_Float(desc='the high frequency of the fitler')
        phase:str = Enum('zero','zero-double','forward',desc='the phase of the filter')
        btype: str = Enum('bandpass','lowpass','highpass','bandstop',desc='the type of filter')
        order: int = CX_Int(desc='the order of the filter')
        ftype: str = Enum('butter','cheby1','cheby2','ellip','bessel')
        
        
    init_inputs = [PortConfig(label='data',allowed_data=Signal)]
    init_outputs = [PortConfig(label='filtered data',allowed_data=Signal)]
    
    @property
    def config(self) -> IIRFilterNode.Config:
        return self._config
    
    def start(self):
        self.params = dict(
            order = self.config.order,
            ftype = self.config.ftype
            )
                
    def update_event(self, inp=-1):
        
        signal:Signal = self.input(inp)
        if signal:
            filtered_signal:Signal = signal.copy()
            
            iir_params_dict = mne.filter.construct_iir_filter(
                iir_params = self.params,
                f_pass = self.config.f_pass,
                f_stop =  self.config.f_stop,
                sfreq = signal.info.nominal_srate,
                type = self.config.btype,      
            )
            
            filtered_data = mne.filter.filter_data(
                data = signal.data,
                sfreq = signal.info.nominal_srate,
                method = 'iir',
                iir_params = iir_params_dict
                )

            filtered_signal.data = filtered_data
            self.set_output(0, filtered_signal)
            
            
            
            
            
            