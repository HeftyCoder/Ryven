from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
import numpy as np

class Filter(ABC):
    
    @abstractmethod
    def create_filter(self):
        pass
    
    @abstractmethod
    def filtering_data(self,data:np.ndarray,sfreq:float,filter_params:Mapping[str|float|int]):
        pass
    

class FIRFilter(Filter):
    
    def __init__(self):
        
        
        