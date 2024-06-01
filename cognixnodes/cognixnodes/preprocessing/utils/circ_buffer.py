import numpy as np
from collections.abc import Sequence

class CircularBuffer:
    """An implementation of a circular buffer for handling data and timestamps"""
    
    @classmethod
    def create(cls, data: np.ndarray, timestamps: np.ndarray):
        result = CircularBuffer(1, 1, 1, 1, False)
        result.reset(data, timestamps)
        return result
    
    @classmethod
    def create_empty(cls):
        return CircularBuffer(1, 1, 1, 1, False)
        
    def __init__(
        self,
        sampling_frequency: float, 
        buffer_duration: float, 
        start_time: float,
        channels_count: int,
        init_buffers=True
    ):
        self.nominal_srate = sampling_frequency
        self.effective_srate = 0
        self.duration = buffer_duration
        self.size = int(buffer_duration * self.nominal_srate)
        self.current_index = 0
        
        self.tloop = start_time
        self.dts = 1 / self.nominal_srate

        if init_buffers:
            self.data = np.full((channels_count,self.size), -1.0, dtype=float)
            self.timestamps = np.full(self.size, -1.0, dtype=float)
        
        # for calculating effective srate
        self.interval_count = 0
        self.total_intervals = 0
    
    def reset(self, data: np.ndarray, timestamps: np.ndarray):
        self.duration = timestamps[-1] - timestamps[0]
        self.tloop = timestamps[-1]
        self.size = len(timestamps)
        self.current_index = self.size-1
        self.effective_srate = 1/(timestamps[1] - timestamps[0])
        self.timestamps = timestamps
        self.data = data
        
    @property
    def effective_dts(self):
        if self.effective_srate == 0:
            return 0
        return 1 / self.effective_srate
        
    def append(
        self, 
        data: Sequence, 
        timestamps: Sequence[float],
        get_looped_data=False
    ) -> tuple[np.ndarray, np.ndarray] | tuple[None, None]:
        """
        Appends data and corresponding timestamps to the buffer
        
        When get_looped_data=True, it returns a tuple of (data, timestamps) 
        if the buffer has looped, else None.
        """
        ts_len = len(timestamps)
        assert data.shape[1] == ts_len, "Length of data and timestamps was not equal!"
        
        # TODO validate this later
        # Attempting to remove old timestamps influence
        
        # exponential moving average
        current_erate = len(timestamps) / (timestamps[-1] - timestamps[0])
        self.effective_srate = self.effective_srate + 0.65*(current_erate - self.effective_srate)
         
        if self.current_index + ts_len <= self.size:
            self.timestamps[self.current_index :ts_len + self.current_index] = timestamps
            self.data[:, self.current_index:ts_len + self.current_index] = data
            self.current_index += ts_len - 1
            return (None, None)
        
        else:
            extra = ts_len - (self.size - self.current_index)
            breakpoint = ts_len - extra
            
            self.timestamps[self.current_index:self.size] = timestamps[:breakpoint]
            self.data[:,self.current_index:self.size] = data[:, :breakpoint]
            
            self.timestamps[0:extra] = timestamps[breakpoint:]
            self.data[:, 0:extra] = data[:, breakpoint:]
            
            self.tloop = timestamps[breakpoint]

            looped_result = (None, None)
            # might not be needed
            if breakpoint != 0:
                #loop result
                looped_result = (
                    (self.data.copy(), self.timestamps.copy())
                    if get_looped_data else (None, None)
                )

            self.current_index = extra - 1
            
            return looped_result
    
    def find_index(self, timestamp: float):
        """Finds closest index of the buffer based on a timestamp"""

        tc = self.timestamps[self.current_index]
        tx = timestamp
        
        if (tx > tc) or ((tc - tx) > self.duration): 
            return (-1, False)

        tl = self.timestamps[0]
        index = int((tx - tl) * self.effective_srate)
        overflow = False
        if index < 0:
            index = self.size - (-index)
            overflow = True
        elif index > self.current_index:
            index = self.current_index
        
        if index >= self.size:
            index = self.size-1
        
        found_time = self.timestamps[index]
        err = found_time - timestamp
        err_margin = 2.5 * self.effective_dts
        
        if abs(err) <= err_margin:
            return index, overflow
        
        # At this point, we're pretty close to the time we want
        # but still far off from good precision. Hence, we're
        # attempting a local search close to the found index 
        # to narrow down a better index
        search_boundary = int(err / self.effective_dts)
        if search_boundary > 0:
            if index - search_boundary >=0:
                search_boundary = min(search_boundary, index)
                search_arr = self.timestamps[index-search_boundary:index]
                search_diff = np.abs(search_arr - timestamp)
                found_index = np.argmax(search_diff <= err_margin)
                if search_diff[found_index] <= err_margin:
                    index = index - search_boundary + found_index
                    
            else:
                leftover = index - search_boundary
                begin = max(self.size - leftover, self.current_index)
                search_arr = np.concatenate(
                    self.timestamps[begin:self.size],
                    self.timestamps[0, index]
                )
                search_diff = np.abs(search_arr - timestamp)
                found_index = np.argmax(search_diff <= err_margin)
                if search_diff[found_index] <= err_margin:
                    if found_index + begin < self.size:
                       index = found_index
                       overflow = True
                    else:
                       index = self.size - begin + found_index
        
        elif search_boundary < 0:
            search_boundary = min(abs(search_boundary), self.current_index)
            search_arr = self.timestamps[index:index+search_boundary]
            search_diff = search_arr - timestamp
            found_index = np.argmax(search_diff <= err_margin)
            if search_diff[found_index] <= err_margin:
                index += found_index
                                 
        return index, overflow
    
    def find_segment(self, timestamp: float, offsets: tuple[float, float]):
        """Extracts a segment of the buffer based around a timestamp and offsets"""
        x, y = offsets
        tm = timestamp
        buffer = self.data
        buffer_tm = self.timestamps
        size = self.size
        
        m_index, m_overflow = self.find_index(tm)
        x_index, x_overflow = self.find_index(tm + x)
        y_index, y_overflow = self.find_index(tm + y)   
        
        if (
            self.__invalid_indices(m_index, x_index, y_index) or 
            buffer_tm[m_index] < 0 or 
            buffer_tm[x_index] < 0 or 
            buffer_tm[y_index] < 0 or 
            x>y
        ): 
            return None, None
    
        if not (x_overflow or y_overflow) or (x_overflow and y_overflow):
            return buffer[:, x_index:y_index], buffer_tm[x_index:y_index]
    
        else:
            start, end = (x_index, y_index) if x_overflow else (y_index, x_index)
            return (
                np.concatenate((buffer[:, start:size], buffer[:, 0:end]), axis=1),
                np.concatenate((buffer_tm[start:size], buffer_tm[0:end]))
            )
    
    def __invalid_indices(self, m_index: int, x_index: int, y_index: int):
        """Checks if the indices are out of the buffer"""
        return (
            m_index < 0 or 
            x_index < 0 or 
            y_index < 0 or 
            y_index > self.size or 
            x_index > self.size or 
            m_index > self.size
        )
        
    def __print_segment(self, tm:float, x: float, y: float, start: bool, end: bool):
        buffer_tm = self.timestamps
        print(
            f"""Segment OVERFLOW:
                    Nominal: {self.nominal_srate}
                    Effective: {self.effective_srate}
                    Wanted: [{tm+x}:{tm+y}]
                    Actual: [{buffer_tm[start]}:{buffer_tm[end]}]
                    Error: [{buffer_tm[start]-tm-x}:{buffer_tm[end]-tm-y}]
        """)