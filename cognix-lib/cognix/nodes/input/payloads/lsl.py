"""Defines the payloads for the LSL Streams"""
from .abc import StreamInfo
from .abc import StreamPayload
from collections.abc import Mapping, Sequence
import numpy as np
from pylsl import (
    StreamInlet
)      
        
class LSLStreamInfo(StreamInfo):
    
    def __init__(self, inlet: StreamInlet):
        super().__init__()
        self._inlet = inlet
        self._info = inlet.info()
    
    def nominal_srate(self) -> int:
        return self._info.nominal_srate()
    
    def channel_count(self) -> int:
        return self._info.channel_count
    
    def stream_type(self) -> str:
        return self._info.type()
    
    def data_format(self) -> str:
        return self._info.channel_format()

    def name(self) -> str:
        return self._info.name()
    
    def channels(self) -> Mapping[str,int]:
        stream_xml = self._info.desc()
        chans_xml = stream_xml.child('channels')
        chans_xml = stream_xml.child("channels")
        chan_xml_list = []
        ch = chans_xml.child("channel")
        while ch.name() == "channel":
            chan_xml_list.append(ch)
            ch = ch.next_sibling("channel")
            
        return {
            chan_xml_list[c_index]: c_index 
            for c_index in chan_xml_list
        }

class LSLStreamPayload(StreamPayload):
    
    def __init__(self,stream_info:LSLStreamInfo,samples:np.ndarray,timestamps:Sequence[float]):
        super().__init__()
        self._stream_info = stream_info
        self._samples = samples
        self._timestamps = timestamps
        
    def stream_info(self) -> StreamInfo:
        return self._stream_info
    
    def timestamps(self) -> Sequence[float]:
        return self._timestamps
    
    def samples(self) -> np.ndarray:
        return self._samples
    
