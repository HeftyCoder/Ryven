from ryvencore.data.built_in import *
from ryvencore import Data,PortConfig

from cognix.config.traits import *
from cognix.api import CognixNode,FrameNode

from typing import Union
import numpy as np
from pylsl import (
    resolve_stream,
    resolve_bypred,
    StreamInlet, 
    StreamInfo,
)
import pylsl

from .utils_for_xdf.function_for_creation_of_file import creation_of_xdf
from .utils_for_xdf.utils_for_streams import Inlet,DataInlet,MarkerInlet
from .utils_for_xdf import xdfwriter
from ryvencore import ProgressState
from traitsui.api import CheckListEditor
from threading import Thread
import os

class XDFwriting(FrameNode):
    title = 'XDF Writer'
    version = '0.1'
    
    class Config(CognixNode):
        file_name = CX_Str('file name',desc='the name of the XDF file')
        file_path = CX_Str('file path',desc='the path in which the XDF type file will be saved')
        processing_flag_mode = List(
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
    
    init_inputs = [PortConfig(label='stream')]
    
    def __init__(self, params):
        super().__init__(params)
        
        self.inlet: StreamInlet = None
        self.t = None
        self.progress = None
        self.force_stop = False
        self.inlets = []
        self.formats = ['double64','float32','int32','string','int16','int8','int64']
        self.stream_id = 0
        self.infos = dict()
        
        real_path = os.path.realpath(__file__)
        dir_path = os.path.dirname(real_path).split('\\')
        self.path = ""

        for i in range(len(dir_path)-1):
            self.path = self.path + dir_path[i] + "\\"
    
        print(self.path)
        
    def on_stop(self):
        import time
                
        for i in range(len(self.inputs)):
            creation_of_xdf(self.xdfile,i,self.infos[i],None,None,False,False,True,first_time=self.timestamps[i][0][0],last_time=self.timestamps[i][-1][-1],samples_count=self.samples_count[i])  
        
        self.set_progress_value(-1,'Attempting stop!')
        time.sleep(1)
        print('Stopped stream')
        self.set_progress_value(0,'Stopped writing')
        

    def on_start(self):
        self.timestamps = [[] for _ in range(len(self.init_inputs))]
        self.samples_count = [0 for i in range(len(self.init_inputs))]
        
        path = self.path 
        if self.config.file_path != 'file path':
            path = self.config.file_path
            
        self.xdfile = xdfwriter.XDFWriter(f'{path}{self.config.file_name}.xdf',True)
        self.processing_flag_mode = self.config.processing_flag_mode
            
        self.progress = ProgressState(1,-1,'Searching stream')
        
        for i in range(len(self.init_inputs)):
            data = self.input(i)
            
            self.progress = None
            self.progress = ProgressState(1,1,'Saving Stream Metadata')
            self.start_time = pylsl.local_clock()
            
            flags = 0
            for flag in self.processing_flag_mode:
                flags |= flag
            
            info = data.payload.stream_info()
            if 'Marker' in info.stream_type:
                if info.nominal_srate() != pylsl.IRREGULAR_RATE or info.data_format() != pylsl.cf_string:
                    print('Invalid marker stream ' + info.name())
                    break
                # self.inlets.append([MarkerInlet(info,flags),self.stream_id])
                self.infos[self.stream_id] = {'stream_name':info.name(),'stream_type':info.stream_type(),'channel_count':info.channel_count(),\
                    'nominal_srate':info.nominal_srate(),'channel_format':self.formats[info.data_format()],'time_created':self.start_time}
                creation_of_xdf(self.xdfile,self.stream_id,self.infos[self.stream_id],None,None,True,False,False,0,0,0)
                self.stream_id += 1

            elif info.nominal_srate() != pylsl.IRREGULAR_RATE and info.data_format() != pylsl.cf_string:
                # self.inlets.append([DataInlet(info,flags),self.stream_id])
                self.infos[self.stream_id] = {'stream_name':info.name(),'stream_type':info.stream_type(),'channel_count':info.channel_count(),\
                    'nominal_srate':info.nominal_srate(),'channel_format':self.formats[info.data_format()],'time_created':self.start_time}
                creation_of_xdf(self.xdfile,self.stream_id,self.infos[self.stream_id],None,None,True,False,False,0,0,0)
    
                self.stream_id +=1
                              
            
    def update_event(self):
        for i in range(len(self.init_inputs)):
            data = self.input(i)
            samples = np.array(data.payload.samples())
            timestamps = np.array(data.payload.timestamps())
            if timestamps:
                self.timestamps[i].append(timestamps[0],timestamps[-1])
                self.samples_count[i] += len(timestamps)
                creation_of_xdf(self.xdfile,i,self.infos[i],samples,timestamps,False,True,False,0,0,0)

        
        
            
            