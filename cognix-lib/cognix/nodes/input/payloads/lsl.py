"""Defines the payloads for the LSL Streams"""
from .core import SignalInfo, Signal
from collections.abc import Mapping, Sequence
import numpy as np
from pylsl import (
    StreamInlet,
    StreamInfo
)      

class LSLSignalInfo(SignalInfo):
    
    def __init__(self, lsl_info: StreamInfo):
        self._lsl_info = lsl_info
        
        stream_xml = lsl_info.desc()
        chans_xml = stream_xml.child("channels")
        chan_xml_list = []
        ch = chans_xml.child("channel")
        while ch.name() == "channel":
            chan_xml_list.append(ch)
            ch = ch.next_sibling("channel")
            
        channels =  {
            chan_xml_list[c_index]: c_index 
            for c_index in range(len(chan_xml_list))
        }
        
        super().__init__(
            nominal_srate=lsl_info.nominal_srate(),
            signal_type=lsl_info.type(),
            data_format=lsl_info.channel_format(),
            name=lsl_info.name(),
            channels=channels
        )
        
    
