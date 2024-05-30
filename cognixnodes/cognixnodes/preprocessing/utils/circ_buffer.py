import numpy as np
from collections.abc import Sequence

class CircularBuffer:
    """An implementation of a circular buffer for handling data and timestamps"""
    
    def __init__(self, sampling_frequency: float, buffer_duration: float, error_margin: float, start_time: float):
        self.nominal_srate = sampling_frequency
        self.effective_srate = 0
        self.error_margin = error_margin
        self.buffer_duration = buffer_duration
        self.size = int(buffer_duration * self.nominal_srate)
        self.current_index = 0
        
        self.tstart = start_time
        self.tend = start_time
        self.dts = 1 / self.nominal_srate

        self.buffer_data = np.full((32,self.size),-1.0,dtype=float)
        self.buffer_timestamps = np.full(self.size,-1.0,dtype=float)
        self.tc = self.buffer_timestamps[self.current_index]
        
        # for calculating effective srate
        self.total_timestamps = 0
        self.time_passed = 0
        
    @property
    def effective_dts(self):
        if self.effective_srate == 0:
            return 0
        return 1 / self.effective_srate
        
    def append(self, data: Sequence, timestamps: Sequence[float]):
        """Appends data and corresponding timestamps to the buffer"""
        assert data.shape[1] == len(timestamps), "Length of data and timestamps was not equal!"
        
        self.total_timestamps += len(timestamps)
        self.time_passed += timestamps[-1] - timestamps[0]
        self.effective_srate = self.total_timestamps / self.time_passed
            
        if self.current_index + len(timestamps) < self.size:
            self.buffer_timestamps[self.current_index:len(timestamps)+self.current_index] = timestamps
            self.buffer_data[:,self.current_index:len(timestamps)+self.current_index] = data
            self.current_index = self.current_index + len(timestamps)

        elif self.current_index + len(timestamps) == self.size:
            self.buffer_timestamps[self.current_index:self.size] = timestamps
            self.buffer_data[:,self.current_index:self.size] = data

            self.current_index = 0
            self.start_time = timestamps[-1] 
            
        else:
            index = len(timestamps) - (self.size - self.current_index)
            self.buffer_timestamps[self.current_index:self.size] = timestamps[:len(timestamps) - index]
            self.buffer_data[:,self.current_index:self.size] = data[:,:len(timestamps) - index]


            self.tstart = timestamps[len(timestamps) - index]

            self.buffer_timestamps[0:index] = timestamps[len(timestamps) - index:]
            self.buffer_data[:,0:index] = data[:,len(timestamps) - index:]

            self.current_index = index
        
        self.tend = self.buffer_timestamps[-1]
    
    def find_index(self, timestamp: float):
        """Finds closest index of the buffer based on a timestamp"""
        size = int(self.buffer_duration * self.nominal_srate)
        dts = self.effective_dts
        
        tc = self.buffer_data[self.current_index-1]
        tx = timestamp
        
        if (tx > tc) or ((tc - tx) > self.buffer_duration): 
            return (-1, False)
    
        if tx <= tc:
            index = (
                (int((tx - self.tstart)/dts), False) 
                if tx >= self.tstart
                else (size - int((self.tend - tx)/dts), True)
            )

            extra_index = 0
            if self.buffer_data[index[0]] > 0:
                extra_index = int((tx - self.buffer_data[index[0]])/dts)
        
            new_index = (index[0] + extra_index, index[1])

            return new_index
    
    def find_segment(self, timestamp: float, offsets: tuple[float, float]):
        """Extracts a segment of the buffer based around a timestamp and offsets"""
        x, y = offsets
        tm = timestamp
        buffer = self.buffer_data
        size = self.size
        
        m_index, m_overflow = self.find_index(tm)
        x_index, x_overflow = self.find_index(tm + x)
        y_index, y_overflow = self.find_index(tm + y)   

        buffer_tm = self.buffer_timestamps
        if (
            self.__invalid_indices(m_index, x_index, y_index) or 
            buffer_tm[m_index] < 0 or 
            buffer_tm[x_index] < 0 or 
            buffer_tm[y_index] < 0 or 
            x>y
        ): 
            return False, False
    
        if not (x_overflow or y_overflow) or (x_overflow and y_overflow):
            print("SEGMENTTTTTTTTTTTT",tm + x,tm,tm+y,buffer_tm[x_index],buffer_tm[m_index],buffer_tm[y_index])
            return buffer[:, x_index:y_index], buffer_tm[x_index:y_index]
    
        else:
            print("SEGMENTTTTTTTTTTTT",tm + x,tm,tm+y,buffer_tm[x_index],buffer_tm[m_index],buffer_tm[y_index])
            start, end = (x_index, y_index) if x_overflow else (y_index, x_index)
            return (
                np.concatenate((buffer[:,start:size], buffer[:, 0:end]), axis=1),
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