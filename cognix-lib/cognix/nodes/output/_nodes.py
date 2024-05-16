from __future__ import annotations
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
from ..input.payloads.core import Signal
import os

class XDFWriterNode(FrameNode):
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
    
    init_inputs = [PortConfig(label='data stream'),PortConfig(label='marker stream'),PortConfig(label='path')]
    
    def __init__(self, params):
        super().__init__(params)
        
        self.inlet: StreamInlet = None
        self.t = None
        self.progress = None
        self.force_stop = False
        self.inlets = dict()
        self.formats = ['double64','float32','int32','string','int16','int8','int64']
        self.stream_id = 0
        self.timestamps = [[] for _ in range(len(self._inputs)-1)]
        self.samples_count = [0 for i in range(len(self._inputs)-1)]

        real_path = os.path.realpath(__file__)
        dir_path = os.path.dirname(real_path).split('\\')
        self.path = ""

        for i in range(len(dir_path)-1):
            self.path = self.path + dir_path[i] + "\\"
    
        print(self.path)
    
    @property
    def config(self) -> XDFWriterNode.Config:
        return self._config
    
    def on_stop(self):
        import time
        
        for i in range(len(self._inputs)):
            creation_of_xdf(self.xdfile,i,self.inlets[i],None,None,False,False,True,first_time=self.timestamps[i][0][0],last_time=self.timestamps[i][-1][-1],samples_count=self.samples_count[i])  
        
        self.set_progress_value(-1,'Attempting stop!')
        time.sleep(1)
        print('Stopped stream')
        self.set_progress_value(0,'Stopped writing')
    
            
    def update_event(self,inp:int):
        
        if len(self.inlets) != len(self._inputs):

            path = self.input_payload(2)
            if not path:
                path = self.path

            self.xdfile = xdfwriter.XDFWriter(f'{path}{self.config.file_name}.xdf',True)

            if inp!=len(self._inputs):
                signal: Signal = self.input_payload(inp)
                if not signal:
                    return False
                if 'Marker' in signal.info.signal_type and (signal.info.nominal_srate != pylsl.IRREGULAR_RATE or signal.info.data_format != pylsl.cf_string):
                        return 
                else:
                    self.inlets[inp] = {'stream_name':signal.info.name,'stream_type':signal.info.signal_type,'channel_count':signal.info.channel_count,\
                        'nominal_srate':signal.info.nominal_srate,'channel_format':self.formats[signal.info.data_format],'time_created':self.start_time}
                    creation_of_xdf(self.xdfile,inp,self.inlets[inp],None,None,True,False,False,0,0,0)
        
        if inp!=len(self._inputs):
            signal:Signal = self.input_payload(inp)
            if signal.timestamps:
                samples = np.array(signal.data)
                timestamps = np.array(signal.timestamps)
                self.timestamps[inp].append(timestamps[0],timestamps[-1])
                self.samples_count[inp] += len(timestamps)
                creation_of_xdf(self.xdfile,inp,self.inlets[inp],samples,timestamps,False,True,False,0,0,0)
        
            
            