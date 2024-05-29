import numpy as np
from collections.abc import Sequence


def find_index(tx: float, buffer: Sequence, current_index: int, buffer_duration: float, tstart: float, tend: float, sampling_frequency:float , effective_sampling_frequency: float) -> tuple[int, bool]:
    size = int(buffer_duration * sampling_frequency)
    dts = 1/effective_sampling_frequency
    tc = buffer[current_index-1]

    if (tx > tc) or ((tc - tx) > buffer_duration): 
        return (-1,False)
    
    if tx <= tc:
        index = (
            (int((tx - tstart)/dts), False) 
            if tx >= tstart
            else (size - int((tend - tx)/dts), True)
        )
        
        extra_index = 0
        if buffer[index[0]] > 0:
            extra_index = int((tx - buffer[index[0]])/dts)
                
        new_index = (index[0] + extra_index,index[1])
        
        return new_index
    
def find_window(t_window:float,start_time_window:float,start_time_index:int,buffer_tm: Sequence, buffer_data: Sequence, current_index: int, buffer_duration: float, tstart: float, tend: float, sampling_frequency: float, effective_sampling_frequency: float):
    size = int(buffer_duration * sampling_frequency)
    
    m_index,m_overflow = find_index(tx = t_window + start_time_window,buffer=buffer_tm,current_index=current_index,buffer_duration=buffer_duration,tstart=tstart,tend=tend,sampling_frequency=sampling_frequency,effective_sampling_frequency=effective_sampling_frequency)
    
    window = np.zeros((32,1))
    timestamps = []

    if m_index < 0 or buffer_tm[m_index] < 0:
        pass
    
    else:
        
        if m_index < start_time_index:
            window = np.concatenate((buffer_data[:,start_time_index:size],buffer_data[:,0:m_index]),axis=1)
            timestamps = np.concatenate((buffer_tm[start_time_index:size],buffer_tm[0:m_index]))
        else: 
            window = buffer_data[:,start_time_index:m_index]
            timestamps = buffer_tm[start_time_index:m_index]
            
        print("SEGMENTTTTTTTTTTTTTTTTTT",buffer_tm[start_time_index],buffer_tm[m_index])
        
        start_time_index,start_time_window = m_index,t_window + start_time_window
            
    return start_time_index,start_time_window,window,timestamps

class CircularBufferWindowing:
    """An implementation of a circular buffer for handling data and timestamps"""
    
    def __init__(self, sampling_frequency:float, buffer_duration:float,start_time:float):
        self.nominal_srate = sampling_frequency
        self.effective_srate = 0
        self.buffer_duration = buffer_duration
        self.size = int(buffer_duration * self.nominal_srate)
        self.current_index = 0
        
        self.tstart = start_time
        self.tend = start_time
        self.dts = 1 / self.nominal_srate
        
        self.time_window_start = start_time
        self.index_window_start = 0

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
        
    def append(self, data: Sequence, timestamps: Sequence):
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
        return find_index(timestamp, self.buffer_data, self.current_index, self.buffer_duration, self.tstart, self.tend, self.nominal_srate ,self.nominal_srate)
    
    def find_segment(self, timestamp: float):
        """Extracts a segment of the buffer based around a timestamp and offsets"""
        
        new_index_start,new_time_start,window,timestamps = find_window(
            t_window = timestamp,
            start_time_window = self.time_window_start,
            start_time_index = self.index_window_start,
            buffer_tm = self.buffer_timestamps,
            buffer_data=self.buffer_data,
            current_index=self.current_index,
            buffer_duration=self.buffer_duration,
            tstart=self.tstart,
            tend=self.tend,
            sampling_frequency=self.nominal_srate,
            effective_sampling_frequency=self.effective_srate
        )
        
        if window.shape[1]!=1:
            self.time_window_start = new_time_start
            self.index_window_start = new_index_start
            return window,timestamps