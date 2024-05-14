from ryvencore.data.built_in import *
from ryvencore import Data,PortConfig

from cognix.config.traits import *
from cognix.api import CognixNode,FrameNode

from typing import Union
import numpy as np
from traitsui.api import CheckListEditor

from pylsl import local_clock

from collections.abc import Sequence
from .utils_for_preprocessing.segmentation_helper import Buffer,find_index,find_segment

class Segmentation(CognixNode):
    title = 'Segmentation'
    version = '0.1'

    class Config(NodeTraitsConfig):
        x: float = CX_Float(-0.5)
        y: float = CX_Float(0.5)
        buffer_duration: float = CX_Float(10.0, desc = 'Duration of the buffer in seconds')
        error_margin: float = CX_Float()

    init_inputs = [PortConfig(label='data'),
                   PortConfig(label='marker')]

    init_outputs = [PortConfig(label='segment',allowed_data=ListData)]
    
    def on_start(self):
        self.buffer = Buffer(sampling_frequency = 2048.0, buffer_duration = self.config.buffer_duration, error_margin = self.config.error_margin, start_time = local_clock())
        
    def update_event(self, inp=-1):
        if not self.input(0):
            return 
        
        else:
            data = self.input(0)            
            
            samples = np.array(data.payload.samples()).T
            timestamps  = data.payload.timestamps()
            
            print('Data',timestamps[0],timestamps[-1])
            
            self.buffer.insert_data_to_buffer(samples,timestamps)
            
        if not self.input(1):
            return 
        
        marker = self.input(1)
        
        marker_sample = marker.payload.samples()
        marker_timestamp = marker.payload.timestamps()[0]
        
        print(marker_sample,marker_timestamp)
        
        if marker:
            segment = find_segment(tm = marker_timestamp, x = self.config.x, y = self.config.y, buffer_tm = self.buffer.buffer_timestamps, buffer_data= self.buffer.buffer_data, \
                    current_index = self.buffer.current_index, buffer_duration = self.config.buffer_duration, tstart = self.buffer.tstart, tend = self.buffer.tend, \
                        sampling_frequency = data.payload.stream_info().nominal_srate())
            if segment:
                print(segment)
                self.set_output_val(0,Data(segment))
            
    
class EEGChannelSelection(CognixNode):
    title = 'EEG Channel Selection'
    version = '0.1'
    
    class Config(NodeTraitsConfig):
        
        channels = ['Fp1', 'Af3', 'F7', 'F3', 'Fc1', 'Fc5', 'T7',
            'C3', 'Cp1', 'Cp5', 'P7', 'P3', 'Pz', 'Po3', 'O1', 'Oz', 'O2', 'Po4',
            'P4', 'P8', 'Cp6', 'Cp2', 'C4', 'T8', 'Fc6', 'Fc2', 'F4', 'F8', 'Af4',
            'Fp2', 'Fz', 'Cz']
        
        
        channels_selected = List(
            editor=CheckListEditor(
                values= [(channel,channel) for channel in channels],
                cols=4
            ),
            style='custom'
        )
        
    init_inputs = [PortConfig(label='data_in')]
    
    init_outputs = [PortConfig(label='data_out')]

    def on_start(self):
        self.selected_channels = self.config.channels_selected
        print(self.selected_channels)
        
    def update_event(self, inp=-1):
        if not self.input(0):
            return 
        else:
            data = np.array(self.input(0).payload.samples()).T
            channels_stream = self.input(0).stream_info().channels
            
            selected_data = np.zeros((len(self.selected_channels),data.shape(1)))
            for ch in self.selected_channels:
                selected_data[channels_stream[ch]] = data[channels_stream[ch]]
            self.set_output_val(0,Data(selected_data))
            
            
            
            
            
            
            
            
            
            