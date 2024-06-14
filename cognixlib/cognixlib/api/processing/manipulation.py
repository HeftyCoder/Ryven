"""
This module defines ways to extract segments out of a signal based on timestamps
or simple windowing. 
"""
from ..data.signals import TimeSignal, StreamSignal
from ..data.circ_buffer import CircularBuffer
from numpy import full, nan, float64, ndarray
from collections.abc import Sequence, Iterable
from abc import ABC, abstractmethod

class SegmentFinder(ABC):
    """
    Extracts segments from a signal based on marker timestamps relative to
    the signal time axis. Multiple markers can be used.
    """
    
    class TimestampCache:
        
        def __init__(self, cache_length=1000):
            self.current_length = 0
            self._cache = full(shape=cache_length, fill_value=nan,dtype=float64)
            self._buffer: CircularBuffer = None
        
        def append(self, tmps: float | Sequence[float] | ndarray):
            if isinstance(tmps, (Sequence, ndarray)):
                l_t = len(tmps)
                self._cache[self.current_length:self.current_length + l_t] = tmps
                self.current_length += l_t
            else:
                self._cache[self.current_length + 1] = tmps
                self.current_length += 1
        
        def sort(self):
            self._cache[0:self.current_length].sort()
        
        def segment(self, offset: tuple[float, float], data_ref: TimeSignal):
            output_data: Sequence[TimeSignal] = []
            cl = self.current_length
            
            for i in range(cl):
                segment, timestamps = self._buffer.segment(
                    self._cache[i],
                    offset,
                )
                
                if segment is not None:
                    self.current_length -= 1
                    new_sig = data_ref.copy(False)
                    new_sig.data = segment
                    new_sig.timestamps = timestamps
                    output_data.append(new_sig)
            
            return output_data
            
    def __init__(
        self, 
        marker_names: Iterable[str],
        marker_cache_length=1000,
    ):
        self._data_ref: TimeSignal = None
        self._marker_tm_cache = {
            m_name: SegmentFinder.TimestampCache(marker_cache_length)
            for m_name in marker_names
        }
    
    @abstractmethod
    def update_data(self, data_signal: TimeSignal):
        pass

    def update_markers(self, marker_signal: TimeSignal | Sequence[tuple[str, float]]):        
        
        changed_caches: set[SegmentFinder.TimestampCache] = set()
                 
        for i in range(len(marker_signal)):
            if isinstance(marker_signal, TimeSignal):
                m_name = marker_signal.data[i]
                tms = marker_signal.timestamps[i]
            else:
                m_name, tms = marker_signal
            
            if m_name in self._marker_tm_cache:
                m_cache = self._marker_tm_cache[m_name]
                changed_caches.add(m_cache)
                tms = marker_signal.timestamps[i]
                m_cache.append(tms)

        if not changed_caches:
            return False
        for cache in changed_caches:
            cache.sort()
        return True

    def segments(self, offset: tuple[float, float]):
        result: dict[str, list[TimeSignal]] = {}
        if not self._data_ref:
            return result
        
        for m_name, cache in self._marker_tm_cache.items():
            t_signals = cache.segment(offset, self._data_ref)
            if t_signals:
                result[m_name] = t_signals
        
        return result            

class SegmentFinderOffline(SegmentFinder):
    
    def __init__(
        self, 
        marker_names: Iterable[str], 
        marker_cache_length=1000,
        data: TimeSignal=None
    ):
        super().__init__(marker_names, marker_cache_length)
        if data:
            self.update_data(data)
    
    def update_data(self, data_signal: TimeSignal):
        self._data_ref = data_signal
        self._buffer = CircularBuffer.create(
            data_signal.data,
            data_signal.timestamps,
        )
        
class SegmentFinderOnline(SegmentFinder):
    
    def __init__(
        self, 
        marker_names: Iterable[str], 
        marker_cache_length=1000,
        buffer_dur=0.0,
        nominal_srate=-1,
        data_signal: TimeSignal = None
    ):
        super().__init__(marker_names, marker_cache_length)
        self.set_buffer_info(buffer_dur, nominal_srate)
        self._buffer: CircularBuffer = None
        
        if data_signal:
            self.update_data(data_signal)
    
    def set_buffer_info(self, buffer_dur: float, srate: int):
        self._buffer_dur = buffer_dur
        self._nominal_srate = srate
        
    def update_data(
        self, 
        data_signal: TimeSignal
    ):        
        
        if not self._buffer:
            self._data_ref = data_signal
            self._buffer = CircularBuffer(
                sampling_frequency=self._nominal_srate,
                buffer_duration=self._buffer_dur,
                start_time=data_signal.timestamps[0],
                channels_count=len(data_signal.data.shape[1])
            )
        else:
            self._buffer.append(data_signal.data, data_signal.timestamps)
    
    def is_buffer_init(self):
        return self._buffer is not None
    