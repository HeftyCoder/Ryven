"""Defines the core functionalities and data types for Cognix"""

from collections.abc import Mapping, Sequence
import numpy as np

class SignalInfo:
   
    def __init__(
        self, 
        nominal_srate: int, 
        signal_type: str, 
        data_format: str,
        name: str,
        channels: Mapping[str, int]
    ):
        self._nominal_srate = nominal_srate
        self._signal_type = signal_type
        self._data_format = data_format
        self._name = name
        self._channels = channels
        
    @property
    def nominal_srate(self):
        """The nominal srate of the stream. -1 for irregular streams"""
        return self._nominal_srate
    
    @property
    def channel_count(self):
        return len(self._channels)
    
    @property
    def signal_type(self):
        """The stream type, i.e EEG if given"""
        return self._signal_type
    
    @property
    def data_format(self):
        return self._data_format
    
    @property
    def name(self):
        return self._name
    
    @property
    def channels(self):
        return self._channels
    
    
class Signal:
    """
    Represents the data being passed over nodes for signal processing
    """
    
    def __init__(
        self,  
        data: np.ndarray,
        signal_info: SignalInfo 
    ):
        self._data = data
        self._info = signal_info
        
    @property
    def info(self):
        return self._info
    
    @property
    def data(self):
        return self._data
    
    def subdata(self, indexes: Sequence[int]):
        return self._data[indexes]

class TimeSignal(Signal):
    
    def __init__(self, timestamps: Sequence[float], data: np.ndarray, signal_info: SignalInfo):
        super().__init__(data, signal_info)
        self._timestamps = timestamps
    
    @property
    def timestamps(self):
        return self._timestamps