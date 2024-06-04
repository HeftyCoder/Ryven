from __future__ import annotations

from cognixcore.api import (
    Node,
    FrameNode,
    Flow,
    PortConfig,
)
from cognixcore.config.traits import *

from typing import Union
import numpy as np
from pylsl import (
    resolve_stream,
    resolve_bypred,
    StreamInlet, 
    StreamInfo,
)
import pylsl

from .utils.function_for_creation_of_file import creation_of_xdf
from .utils.utils_for_streams import Inlet,DataInlet,MarkerInlet
from .utils import xdfwriter
from cognixcore import ProgressState
from traitsui.api import CheckListEditor
from threading import Thread
from ..core import Signal,StreamSignal
from ..stream import LSLSignalInfo
from collections.abc import Mapping
import os
import pyxdf
import json

class XDFWriterNode(Node):
    title = 'XDF Writer'
    version = '0.1'
    
    class Config(NodeTraitsConfig):
        directory: str = Directory(desc='the saving directory')
        default_filename: str = CX_Str("model", desc="the default file name")
        varname: str = CX_Str(
            "model", 
            desc="the file name will be extracted from this if there is a string variable"
        )
        
    init_inputs = [PortConfig(label='data stream',allowed_data=StreamSignal), PortConfig(label='marker stream',allowed_data=StreamSignal), PortConfig(label='path')]
    
    def __init__(self, flow: Flow):
        super().__init__(flow)
        
        self.inlet: StreamInlet = None
        self.t = None
        self.progress = None
        self.force_stop = False
        self.inlets = dict()
        self.formats = ['double64','float32','int32','string','int16','int8','int64']
        self.stream_id = 0
        self.create_xdf = False
        self.path = None

        dir = self.config.directory
        filename = self.var_val_get(self.config.varname) 
        if not filename or isinstance(filename, str) == False:
            filename = self.config.default_filename
            
        if dir: 
            self.path = os.path.join(dir, filename)
    
        print(self.path)
    
    @property
    def config(self) -> XDFWriterNode.Config:
        return self._config
    
    def init(self):
        self.start_time = pylsl.local_clock()
        self.write_header = [False for _ in range(len(self._inputs)-1)]
        self.timestamps = [[] for _ in range(len(self._inputs)-1)]
        self.samples_count = [0 for i in range(len(self._inputs)-1)]
    
    def stop(self):
        import time
        for i in range(len(self.inlets)):
            creation_of_xdf(self.xdfile,i,self.inlets[i],None,None,False,False,True,first_time=self.timestamps[i][0][0],last_time=self.timestamps[i][-1][-1],samples_count=self.samples_count[i])  
    
    def update_event(self,inp:int):
        
        if not self.create_xdf and self.path:

            self.xdfile = xdfwriter.XDFWriter(f'{self.path}.xdf',True)
            self.create_xdf = True
        
        if not self.write_header[inp]:

            if inp!=len(self._inputs)-1:
                signal: StreamSignal = self.input(inp)
                if not signal:
                    return False
                if 'Marker' in signal.info.signal_type and (signal.info.nominal_srate != pylsl.IRREGULAR_RATE or signal.info.data_format != pylsl.cf_string):
                        return 
                else:
                    self.inlets[inp] = {'stream_name':signal.info.name,'stream_type':signal.info.signal_type,'channel_count':len(signal.labels),\
                        'nominal_srate':signal.info.nominal_srate,'channel_format':self.formats[signal.info.data_format],'time_created':self.start_time,'channels':signal.info.channels}
                    creation_of_xdf(self.xdfile,inp,self.inlets[inp],None,None,True,False,False,0,0,0)

                self.write_header[inp] = True
        
        if inp!=len(self._inputs)-1:
            signal:Signal = self.input(inp)
            if signal.timestamps:
                samples = np.array(signal.data)
                timestamps = np.array(signal.timestamps)
                self.timestamps[inp].append([timestamps[0],timestamps[-1]])
                self.samples_count[inp] += len(timestamps)
                creation_of_xdf(self.xdfile,inp,self.inlets[inp],samples,timestamps,False,True,False,0,0,0)
        
            
class XDFImportingNode(Node):
    title = 'XDF Import'
    version = '0.1'
    
    class Config(NodeTraitsConfig):
        directory: str = Directory(desc='the saving directory')
        varname: str = CX_Str(
            "model", 
            desc="the file name will be extracted from this if there is a string variable"
        )
        lowercase_labels: bool = Bool(False, desc="if checked, makes all the incoming labels into lowercase")

    init_outputs = [PortConfig(label='streams',allowed_data=Mapping[str,StreamSignal])]
        
    @property
    def config(self) -> XDFImportingNode.Config:
        return self._config
    
    def init(self):
        
        dir = self.config.directory
        filename = self.var_val_get(self.config.varname) 
        path_file = None
        
        if filename and dir and isinstance(filename, str)!=False:
            path_file = f'{dir}/{filename}.xdf'
        
        formats = ['double64','float32','int32','string','int16','int8','int64']
        
        stream_collection = dict()
        
        print(path_file)
        
        if path_file and os.path.exists(path_file):
            streams , header = pyxdf.load_xdf(path_file)
            
            for stream in streams:
                print(stream)
                stream_name = stream['info']['name'][0]
                stream_type = stream['info']['type'][0]
                stream_channel_count = stream['info']['channel_count'][0]
                stream_srate = stream['info']['nominal_srate'][0]
                stream_format = stream['info']['channel_format'][0]
                stream_id = stream['info']['stream_id']
                stream_data = stream['time_series']
                stream_timestamps = stream['time_stamps']
                
                stream_channels = stream['info']['channels'][0]
                
                stream_channels = stream_channels.replace("'", '"')

                stream_channels = json.loads(stream_channels)

                labels = stream_channels.keys()
                cached_labels = (
                    list(labels) if not self.config.lowercase_labels
                    else [label.lower() for label in labels]
                )
                
                info = StreamInfo(
                    name = stream_name,
                    type = stream_type,
                    channel_count = stream_channel_count,
                    nominal_srate = float(stream_srate),
                    channel_format = stream_format,
                    source_id = str(stream_id)
                ) 
                
                stream_info = LSLSignalInfo(info)
                
                stream_collection[stream_name] = StreamSignal(
                    timestamps = stream_timestamps,
                    data = stream_data,
                    labels = cached_labels,
                    signal_info= stream_info
                )

            self.set_output(0,stream_collection)
        
        else:
            self.logger.error(msg='The path doesnt exist')
        
            
    def update_event(self, inp=-1):
        pass
            
                            
class SelectStreamNode(Node):
    title = 'Select Stream'
    version = '0.1' 

    class Config(NodeTraitsConfig):
        stream_name: str = CX_Str('stream name',desc='the stream name to get data')

    init_inputs = [PortConfig(label = 'streams',allowed_data=Mapping[str,StreamSignal])]
    init_outputs = [PortConfig(label = 'selected stream',allowed_data=StreamSignal)]

    @property
    def config(self) -> SelectStreamNode.Config:
        return self._config
    
    def init(self):
        self.dict_streams = None
        self.stream_name = self.config.stream_name
        
    def update_event(self, inp=-1):

        self.dict_streams = self.input(inp)

        if self.dict_streams and self.stream_name in self.dict_streams.keys():
            self.set_output(0,self.dict_streams[self.stream_name])
        
        
    

                
            
            