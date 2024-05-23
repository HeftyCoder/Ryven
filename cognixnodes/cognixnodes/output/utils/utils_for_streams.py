import pylsl
from pylsl import StreamInlet,local_clock
from .xdfwriter import XDFWriter
import numpy as np
from .function_for_creation_of_file import creation_of_xdf


class Inlet:
    def __init__(self,info:pylsl.StreamInfo,proc_flags:bytes):
        # proc_flags = None
        formats = ['double64','float32','int32','string','int16','int8','int64']
        self.inlet = StreamInlet(info,max_buflen=10,processing_flags=proc_flags)
        self.inlet_name = info.name()
        self.inlet_type = info.type()
        self.channel_count = info.channel_count()
        self.stream_Fs = info.nominal_srate()
        print(info.channel_format(),info.name(),info.type(),info.channel_count())
        self.channel_format = formats[info.channel_format()]
        print("Stream created with channel format : ",self.channel_format,self.channel_count)
        self.time_created = pylsl.local_clock()
    
    def update(self):
        pass
    
    def close_stream(self):
        self.inlet.close_stream()
        
class DataInlet(Inlet):
    def __init__(self,info:pylsl.StreamInfo,proc_flags:bytes):
        super().__init__(info,proc_flags)
        self.start_time = local_clock()
        
        print('Connected to outlet' + info.name() +'@'+ info.hostname())
        
    def update(self,xdfile:XDFWriter,stream_id:int,stream_infos:dict):
        max_samples = 3276 * 2
        data = np.nan * np.ones((max_samples,self.channel_count),dtype=np.float32)

        chunk,timestamps = self.inlet.pull_chunk(max_samples=max_samples,dest_obj=data)

        if timestamps:
            data = data[:len(timestamps), :]
            creation_of_xdf(xdfile,stream_id,stream_infos,data,timestamps,False,True,False)                    
      
class MarkerInlet(Inlet):
    def __init__(self,info:pylsl.StreamInfo,proc_flags:bytes):
        super().__init__(info,proc_flags)
        print("Looking for stream with type Markers")
        
        print("Reading from inlet named {} with channels".format(info.name()))
    
    def update(self,xdfile:XDFWriter,stream_id:int,stream_infos:dict):
        marker_samples,marker_timestamp = self.inlet.pull_chunk(timeout=0.0)
        if marker_timestamp:
            
            for i in range(len(marker_samples)):
                print(marker_samples[i],marker_timestamp[i])
                creation_of_xdf(xdfile,stream_id,stream_infos,marker_samples[i],[marker_timestamp[i]],False,True,False)                   
