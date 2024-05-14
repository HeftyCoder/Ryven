"""Defines the various payloads from the input package"""
from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
import numpy as np

class StreamInfo(ABC):
    
    @property
    @abstractmethod
    def nominal_srate(self) -> int:
        """The nominal srate of the stream. -1 for irregular streams"""
        pass
    
    @property
    @abstractmethod
    def channel_count(self) -> int:
        pass
    
    @property
    @abstractmethod
    def stream_type(self) -> str:
        """The stream type, i.e EEG if given"""
        pass
    
    @property
    @abstractmethod
    def data_format(self) -> str:
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        pass
    
    @property
    @abstractmethod
    def channels(self) -> Mapping[str, int]:
        pass 
    
    
class StreamPayload(ABC):
    
    @property
    @abstractmethod
    def stream_info(self) -> StreamInfo:
        pass
    
    @property
    @abstractmethod
    def timestamps(self) -> Sequence[float]:
        pass
    
    @property
    @abstractmethod
    def samples(self) -> np.ndarray:
        pass