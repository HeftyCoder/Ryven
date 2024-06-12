"""
This module defines ways to extract segments out of a signal based on timestamps
or simple windowing. 
"""
from ..data.signals import StreamSignal
from ..data.circ_buffer import CircularBuffer
from numpy import full, nan, float64

class SegmentFinder:
    """
    Extracts segments from a signal based on timestamps relative to
    the signal time axis
    """
    
    def __init__(self, marker_cache_length=1000):
        self.buffer: CircularBuffer = None
        self.data_signal: StreamSignal = None
        
        self.update_dict = {
            0: self.update_data,
            1: self.update_marker
        }
        self.marker_tm_cache = full(shape=marker_cache_length, fill_value=nan,dtype=float64)
        self.current_length = 0