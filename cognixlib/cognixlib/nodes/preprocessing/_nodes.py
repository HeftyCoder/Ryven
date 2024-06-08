from __future__ import annotations

import mne
import numpy as np

from mne_icalabel import label_components  

from cognixcore import PortConfig
from cognixcore.config.traits import *
from traitsui.api import *

from collections.abc import Sequence

from ...api.data import (
    Signal, 
    StreamSignal, 
    LabeledSignal,
    CircularBuffer
)

from ...api.mne.prep import (
    remove_trend_data,
    line_noise_removal_prep,
    referencing_prep,
    noisychannelsprep
)

class SegmentationNode(Node):
    """
    Outputs segments of a StreamSignal based on timestamps
    of a specific marker.
    """
    
    title = 'Segment'
    version = '0.1'

    class Config(NodeTraitsConfig):
        offset: tuple[float, float] = CX_Tuple(-0.5, 0.5)
        marker_name: str = CX_String('marker')
        mode: str = Enum(
            'input', 
            'buffer', 
            desc='Whether to use the input to decide buffer size (offline) or manually (online)'
        )
        buffer_duration: float = CX_Float(10.0, desc = 'Duration of the buffer in seconds', visible_when='mode=="buffer"')
        debug: bool = Bool(False, desc='debug message when data is segmented')

    init_inputs = [
        PortConfig(label='data', allowed_data=StreamSignal),
        PortConfig(
            label='marker', 
            allowed_data=StreamSignal | Sequence[tuple[str, float]]
        )
    ]

    init_outputs = [
        PortConfig(
            label='segment', 
            allowed_data = Sequence[StreamSignal] | StreamSignal
        )
    ]

    def init(self):
        self.buffer: CircularBuffer = None
        self.data_signal: StreamSignal = None
        
        self.update_dict = {
            0: self.update_data,
            1: self.update_marker
        }
        self.marker_tm_cache = np.full(shape=1000,fill_value=np.nan,dtype='float64')
        self.current_length = 0
             
    @property
    def config(self) -> SegmentationNode.Config:
        return self._config
    
    def update_event(self, inp=-1):
        
        update_result = self.update_input(inp)
        
        if not (update_result and self.buffer):
            return
        
        output_data = []
        output_timestamps =[]
        timestamps_out = 0
        
        for i in range(self.current_length):
            segment, timestamps = self.buffer.segment(
                self.marker_tm_cache[i], 
                self.config.offset
            )
            
            if isinstance(segment, np.ndarray):
                output_timestamps.append(timestamps)
                output_data.append(segment)
                timestamps_out += 1
                self.marker_tm_cache[i] = np.nan
        
        if timestamps_out!=0:
            signal = [
                StreamSignal(
                    output_timestamps[i],
                    self.data_signal.labels,
                    output_data[i], 
                    self.data_signal.info
                ) 
                for i in range(timestamps_out)
            ]
            
            if self.config.debug:
                msg = f"ERATE: {self.buffer.effective_dts} Found {len(signal)} Segments</br></br>"
                for s in signal:
                    s_dur = s.timestamps[-1] - s.timestamps[0]
                    msg += f"\t[{s.timestamps[0]} : {s.timestamps[-1]}] dur:[{s_dur}]</br>"
                self.logger.info(msg)
                
            if len(signal) == 1:
                signal = signal[0]
            
            self.current_length -= timestamps_out    
            self.set_output(0, signal)
                
    def update_input(self, inp):
        func = self.update_dict.get(inp)
        if not func:
            return False
        return func(inp)
    
    def update_data(self, inp: int):
        self.data_signal: StreamSignal = self.input(inp)
        if not self.data_signal:
            return False
        
        # create buffer if it doesn't exist
        if not self.buffer:
            
            buffer_duration = self.config.buffer_duration
            if self.config.mode == 'input':
                tms = self.data_signal.timestamps
                buffer_duration = tms[-1] - tms[0] + 0.1
                
            self.buffer = CircularBuffer(
                sampling_frequency=self.data_signal.info.nominal_srate,
                buffer_duration=buffer_duration,
                start_time=self.data_signal.timestamps[0],
                channels_count=len(self.data_signal.labels)
            )
        
        self.buffer.append(self.data_signal.data, self.data_signal.timestamps)
        return True

    def update_marker(self, inp: int):
        marker_signal = self.input(inp)        
        
        # no signal or no buffer
        if not marker_signal:
            return False
        
        timestamps = []
                        
        if isinstance(marker_signal, StreamSignal):
            timestamps = [
                ts for name, ts in zip(marker_signal.data, marker_signal.timestamps) 
                if name[0] == self.config.marker_name
            ]

        ### list of type [[marker1,timestamp1],[marker2,timestamp2]]
        elif isinstance(marker_signal, list): 
            timestamps = [
                time for marker, time in marker_signal 
                if marker == self.config.marker_name
            ]
            
        ## no markers match
        if len(timestamps) == 0:
            return False
        
        self.last_timestamps = timestamps
        
        self.marker_tm_cache[self.current_length : self.current_length + len(timestamps)] = timestamps
        self.current_length += len(timestamps)
        self.marker_tm_cache[0:self.current_length].sort()
        return True


class WindowNode(Node):
    """
    The Window Node has two functions.
    
    input:
        In the input mode, it accepts a StreamSignal as a whole
        input and attempts to segment it into windows, depending
        on the window length and overlap given.
    buffer:
        In the buffer mode, it acts as a buffer. Incoming data
        must be of type StreamSignal. Each time the node updates,
        it adds the input to the buffer and outputs the Window
        if it is detected, depending on the overlap given.
        
        In the buffer mode, it is assumed that small chunks of a 
        bigger signal are incoming to the buffer. In the case of 
        a bigger chunk, to avoid data loss, the buffer is extended
        to hold the additional data.
        
        Essentially, buffer mode is designed for real time processing.
    """
    
    title = 'Window'
    version = '0.1'

    buffer_mode = 'buffer'
    input_mode = 'input'
    
    step_mode = 'step'
    percent_mode = 'percent'
    
    class Config(NodeTraitsConfig):
        mode: str = Enum('input', 'buffer', desc='the operation mode of the Window Node')
        window_length: float = CX_Float(0.5, desc='length of the window in seconds')
        error_margin: float = CX_Float(0.01, desc='error margin for when the segment is slightly smaller than requested')
        dts_error_scale: float = Range(
            1.0, 
            3.0, 
            1.5, 
            desc="how close to the effective sample rate we want to reduce the error to"
        )
        extra_buffer: float = CX_Float(0.5, desc="initialize the buffer with extra amount of seconds")
        overlap_mode: str = Enum('none', 'step', 'percent', desc='how the segmented windows should be overlapped')
        overlap_step: float = Range(0.01, None, 0.5, exclude_high=True, desc='overlap step between the windows, in seconds')
        overlap_percent: float = Range(0.0, 0.99, desc='overlap percent between the windows')
        # the 0.99 means that at max, 100 windos can be created with a step of x * window_time
        debug: bool = Bool(False, desc='debug message when data is segmented')

        # to show the borders correctly, the scrollable must be in an outside group
        traits_view = View(
            Group(
                Group(
                    Item('mode'),
                    Item('window_length'),
                    Item('error_margin'),
                    Item('dts_error_scale'),
                    Item('extra_buffer'),
                    Item('overlap_mode'),
                    Group(
                        Item(
                            'overlap_step', 
                            label='step', 
                            visible_when='overlap_mode=="step"',
                        ),
                        Item(
                            'overlap_percent',
                            label='percent',
                            visible_when='overlap_mode=="percent"',
                        ),
                    ),
                    Item('debug'),
                ),
                label='configuration',
                scrollable=True,
            )
        )
        
    init_inputs = [
        PortConfig(
            label='in',
            allowed_data=StreamSignal | Sequence[StreamSignal]
        )
    ]
    init_outputs = [
        PortConfig(
            label='out',
            allowed_data=Sequence[StreamSignal]
        )
    ]
 
    def init(self):
        self.buffer: CircularBuffer = None
        self.current_time = 0
        self.first_window = True
    
    @property
    def config(self) -> WindowNode.Config:
        return self._config
    
    @property
    def wnd_time(self):
        return self.config.window_length
    
    @property
    def step(self):
        if self.config.overlap_mode == self.step_mode:
            step = min(self.wnd_time, self.config.overlap_step)
        elif self.config.overlap_mode == self.percent_mode:
            step = max(
                0, 
                (1-self.config.overlap_percent) * self.wnd_time 
            )
        else:
            step = self.wnd_time
        return step
        
    def update_event(self, inp=-1):
        
        data_inp: StreamSignal | Sequence[StreamSignal] = self.input(inp)
        if not data_inp:
            return
        
        mode = self.config.mode
        if mode == self.input_mode:
            self.update_input_mode(data_inp)
        elif mode == self.buffer_mode:
            self.update_buffer_mode(data_inp)    
    
    def update_buffer_mode(self, data_inp: StreamSignal):
        if not self.buffer:
            # create the window buffer
            self.buffer = CircularBuffer(
                data_inp.info.nominal_srate,
                self.config.window_length + self.config.extra_buffer,
                data_inp.timestamps[0],
                len(data_inp.labels)
            )
        
        data_dur = data_inp.duration
        self.current_time += data_dur
        # the buffer is not large enough to hold all the incoming
        # data, so we attempt to expand it
        self.buffer.append_expand(
            data_inp.data,
            data_inp.timestamps
        )
        
        result: list[StreamSignal] = []
        # check for a first window
        if self.first_window and self.current_time >= self.wnd_time:
            extra = self.current_time - self.wnd_time
            segment, tmps = self.buffer.segment_current(
                (-self.wnd_time-extra, -extra),
                self.config.error_margin,
                self.config.dts_error_scale
            )
            if segment is not None:
                result.append(
                    StreamSignal(
                        tmps,
                        data_inp.labels,
                        segment,
                        data_inp.info
                    )
                )
            
            self.current_time -= self.wnd_time + extra
            self.first_window = False
        
        # check for any residual windows by applying overlap
        
        step = self.step
        
        if not self.first_window and self.current_time >= step:
            
            offset = self.current_time - step
            self.current_time -= offset
        
            while True:
                seg, tms = self.buffer.segment_current(
                    (-offset-self.wnd_time, -offset),
                    self.config.error_margin,
                    self.config.dts_error_scale
                )
                if seg is not None:
                    result.insert(
                        1,
                        StreamSignal(
                            tms,
                            data_inp.labels,
                            seg,
                            data_inp.info,
                        )              
                    )
                    
                offset += step
                self.current_time -= offset
                
                if self.current_time <= 0:
                    break
        
        if result:
            if self.config.debug:
                msg = ''
                for s in result:
                    msg += f"WINDOW: [{s.tms[0]}-{s.tms[-1]} : {s.duration}\n"
                self.logger.debug(msg)
            self.set_output(0, result)
                
    def update_input_mode(self, data_inp: StreamSignal | Sequence[StreamSignal]):
        if isinstance(data_inp, StreamSignal):
            data_inp = [data_inp]
        
        result: list[StreamSignal] = []
        buffer = CircularBuffer.create_empty()
        
        # we're assuming data comes ordered in time
        # that means that the list of signals are segments
        # of one bigger signal
        # Reversing helps with adding the signals in order
        # since the extraction algorithm works last to first
        
        step = self.step
        msg = ''
        debug = self.config.debug
        for signal in data_inp:
            if debug:
                debug_arr: list[StreamSignal] = []
                msg += f'Signal of duration: {signal.duration}\nBegin:{signal.tms[0]}\nEnd:{signal.tms[-1]}\n\n'
                
            buffer.reset(signal.data, signal.timestamps)
            time = 0
            sig_start = signal.tms[0]
            while time <= (signal.duration - self.wnd_time + self.config.error_margin):
                
                seg, tms = buffer.segment(
                    time + sig_start,  
                    (0, self.wnd_time),
                    self.config.error_margin,
                    self.config.dts_error_scale
                )
                
                if seg is not None:
                    s_sig = StreamSignal(
                        tms,
                        signal.labels,
                        seg,
                        signal.info
                    )
                    if debug:
                        debug_arr.append(s_sig)   
                    result.append(s_sig)
                time += step
            
            if debug:
                msg += f'NUMBER OF WINDOWS: {len(debug_arr)}\n\n'
                for s in debug_arr:
                    msg += f"WINDOW: [{s.tms[0]}-{s.tms[-1]} : {s.duration}]\n"
                msg += "\n"
            
        if result:
            if self.config.debug:
                self.logger.debug(msg)
            self.set_output(0, result) 
 
class StreamSignalSelectionNode(Node):
    """
    Selects part of a stream signal based on its channels. An option
    allows for the labels given to be forced to lowercase.
    
    Typical EEG labels for a 32 cap are:
        fp1, af3, f7, f3, fc1, fc5, t7, c3, cp1, cp5, p7, p3,
        pz, po3, o1, oz, o2, po4, p4, p8, cp6, cp2, c4, t8, fc6,
        fc2, f4, f8, af4, fp2, fz, cz
    """
    
    title = 'Select Channels'
    version = '0.1'
    
    class Config(NodeTraitsConfig):
        
        labels_egg = ['Fp1', 'Af3', 'F7', 'F3', 'Fc1', 'Fc5', 'T7',
            'C3', 'Cp1', 'Cp5', 'P7', 'P3', 'Pz', 'Po3', 'O1', 'Oz', 'O2', 'Po4',
            'P4', 'P8', 'Cp6', 'Cp2', 'C4', 'T8', 'Fc6', 'Fc2', 'F4', 'F8', 'Af4',
            'Fp2', 'Fz', 'Cz'
        ]
        
        force_lowercase: bool = Bool(True)
        labels: list[str] = List(CX_Str())
    
    init_inputs = [
        PortConfig(label='in', allowed_data=StreamSignal)
    ]
    init_outputs = [
        PortConfig(label='out', allowed_data=StreamSignal)
    ]

    @property
    def config(self) -> StreamSignalSelectionNode.Config:
        return self._config
    
    def init(self):
        self.chan_inds = None
        if self.config.force_lowercase:
            self.selected_labels = set(self.config.labels)
        else:
            self.selected_labels = { label.lower() for label in self.config.labels }
        
        # these help for potential optimization
        # check _optimize_searchs
        # their values will be set to an empty "" if not
        self.start_ind: int = None
        self.stop_ind: int = None
        
    def update_event(self, inp=-1):
        
        signal: StreamSignal = self.input(inp)
        if not signal:
            return 
        
        if not self.start_ind:
            self._optimize_search(signal)
        
        if isinstance(self.start_ind, str):
            # no optimization found
            subdata = signal.data[self.chan_inds]
        else:
            subdata = signal.data[self.start_ind: self.stop_ind]
        
        subsignal = StreamSignal(
            signal.timestamps,
            self.selected_labels,
            subdata,
            signal.info,
            False
        )
        
        self.set_output(0, subsignal)
    
    def _optimize_search(self, signal: LabeledSignal):
        """
        Checks whether the selected labels are in sequence in
        the data signal (their corresponding indices are sequenced 
        integers). If they are, the selection is optimized since
        the internal numpy array is not copied.
        """
        
        # if no labels were given, choose all labels
        if not self.selected_labels:
            self.selected_labels = signal.labels
        # find the indices
        self.chan_inds = [
            signal.ldm._label_to_index[label] 
            for label in self.selected_labels 
        ]
        self.chan_inds.sort()
        # this means that we have a sequence (0, 1, 2, 3..)
        if (self.chan_inds[-1] - self.chan_inds[0] == len(self.chan_inds)):
            self.start_ind = self.chan_inds[0]
            self.stop_ind = self.chan_inds[-1]
            # make the selected labels in order
            self.selected_labels = [
                self.selected_labels[i] for i in self.chan_inds
            ]
        else:
            self.start_ind = ''
            self.stop_ind = ''
             
class FIRFilterNode(Node):
    title = 'FIR Filter'
    version = '0.1'
    
    class Config(NodeTraitsConfig):
        low_freq: float = CX_Float(desc='the low frequency of the filter')
        high_freq: float = CX_Float(desc='the high frequency of the fitler')
        filter_length_str: str = CX_String('None',desc='the length of the filterin ms')
        filter_length_int: int = CX_Int(desc='the length of the filter in samples')
        l_trans_bandwidth:float = CX_Float(0.0,desc='the width of the transition band at the low cut-off frequency in Hz')
        h_trans_bandwidth:float = CX_Float(0.0,desc='the width of the transition band at the high cut-off frequency in Hz')
        phase:str = Enum('zero','minimum','zero-double','minimum-half',desc='the phase of the filter')
        fir_window:str = Enum('hamming','hann','blackman',desc='the window to use in the FIR filter')
        fir_design:str = Enum('firwin','firwin2',desc='the design of the FIR filter')
            
    init_inputs = [PortConfig(label='data',allowed_data=StreamSignal | Sequence[StreamSignal])]
    init_outputs = [PortConfig(label='filtered data',allowed_data=StreamSignal | Sequence[StreamSignal])]
    
    @property
    def config(self) -> FIRFilterNode.Config:
        return self._config
    
    def init(self):
        self.filter_length = 'auto'
        print(self.config.filter_length_str,self.config.filter_length_int)
        if self.config.filter_length_str != 'None':
            self.filter_length = self.config.filter_length_str
        if self.config.filter_length_int != 0:
            self.filter_length = self.config.filter_length_int
                
    def update_event(self, inp=-1):
        
        signal: StreamSignal = self.input(inp)
        if not signal:
            return
        
        if not isinstance(signal,list):
            signal = [signal]
        
        list_of_filtered_sigs:Sequence = []
        for sig in signal:
            
            filtered_signal:StreamSignal = sig.copy()
        
            filtered_data = mne.filter.filter_data(
                data = sig.data,
                sfreq = sig.info.nominal_srate,
                l_freq = self.config.low_freq,
                h_freq = self.config.high_freq,
                filter_length = self.filter_length,
                l_trans_bandwidth = self.config.l_trans_bandwidth if self.config.l_trans_bandwidth!=0.0 else 'auto',
                h_trans_bandwidth = self.config.h_trans_bandwidth if self.config.h_trans_bandwidth!=0.0 else 'auto',
                n_jobs = -1,
                method = 'fir',
                phase = self.config.phase,
                fir_window = self.config.fir_window,
                fir_design = self.config.fir_design
                )
            
            filtered_signal._data = filtered_data
        
            list_of_filtered_sigs.append(filtered_signal)
        
        if len(list_of_filtered_sigs) == 1:
            self.set_output(0, list_of_filtered_sigs[0])
        else:
            self.set_output(0, list_of_filtered_sigs)
    
          
class IIRFilterNode(Node):
    title = 'IIR Filter'
    version = '0.1'
    
    class Config(NodeTraitsConfig):
        f_pass: float = CX_Float(desc='the low frequency of the filter')
        f_stop: float = CX_Float(desc='the high frequency of the fitler')
        phase:str = Enum('zero','zero-double','forward',desc='the phase of the filter')
        btype: str = Enum('bandpass','lowpass','highpass','bandstop',desc='the type of filter')
        order: int = CX_Int(desc='the order of the filter')
        ftype: str = Enum('butter','cheby1','cheby2','ellip','bessel')
        
    init_inputs = [PortConfig(label='data',allowed_data=StreamSignal | Sequence[StreamSignal])]
    init_outputs = [PortConfig(label='filtered data',allowed_data=StreamSignal | Sequence[StreamSignal])]
    
    @property
    def config(self) -> IIRFilterNode.Config:
        return self._config
    
    def init(self):
        self.params = dict(
            order = self.config.order,
            ftype = self.config.ftype
        )
                
    def update_event(self, inp=-1):
        
        signal:StreamSignal = self.input(inp)
        if not signal:
            return
        
        if not isinstance(signal,list):
            signal = [signal]
        
        
        list_of_filtered_sigs:Sequence = []
        for sig in signal:
            
            filtered_signal:StreamSignal = sig.copy()
            
            iir_params_dict = mne.filter.construct_iir_filter(
                iir_params = self.params,
                f_pass = self.config.f_pass,
                f_stop =  self.config.f_stop,
                sfreq = sig.info.nominal_srate,
                btype = self.config.btype,      
            )
            
            filtered_data = mne.filter.filter_data(
                data = sig.data,
                sfreq = sig.info.nominal_srate,
                method = 'iir',
                iir_params = iir_params_dict
                )

            print(filtered_data,sig.data)
            
            filtered_signal._data = filtered_data
            
            print(filtered_signal._data,sig.data)
            
            list_of_filtered_sigs.append(filtered_signal)
            
        # filtered_signal = LabeledSignal(
        #     signal.labels,
        #     filtered_data,
        #     signal.info    
        # )
        if len(list_of_filtered_sigs) == 1:
            self.set_output(0, list_of_filtered_sigs[0])
        else:
            self.set_output(0, list_of_filtered_sigs)
            
            
class NotchFilterNode(Node):
    title = 'Notch Filter'
    version = '0.1'
    
    class Config(NodeTraitsConfig):
        freqs:float = CX_Float(50.0,desc='set the line noise freqeuncy')
        filter_length_sec:str = CX_Str(desc='specify filter length in seconds')
        filter_length_samples:int = CX_Int(desc='specify filter length in samples')
        method:str = Enum('fir','iir','spectrum_fit',desc='the method in which the filter is created')
        mt_bandwidth: float = CX_Float(desc='the bandwidth of the multitaper windowing function in Hz')
        p_value:float = CX_Float(0.05,desc='p-value to use in F-test thresholding to determine significant sinusoidal components')
        phase: str = Enum('zero','minimum','zero-double','minimum-half',desc='phase of the filter')
        fir_window: str = Enum('hamming','hann','blackman')
        fir_design: str = Enum('firwin','firwin2')

        
    init_inputs = [PortConfig(label='data',allowed_data=StreamSignal)]
    init_outputs = [PortConfig(label='filtered data',allowed_data=LabeledSignal)]
    
    @property
    def config(self) -> NotchFilterNode.Config:
        return self._config
    
    def init(self):
        self.line_freq = self.config.freqs
        self.filter_length_input = self.config.filter_length_sec if self.config.filter_length_sec else self.config.filter_length_samples
        if not self.filter_length_input:
            self.filter_length_input = 'auto'
        self.method = self.config.method
        self.bandwidth = self.config.mt_bandwidth if self.config.mt_bandwidth else None
        self.p_value = self.config.p_value
        self.phase = self.config.phase
        self.fir_window = self.config.fir_window
        self.fir_design = self.config.fir_design
        
    def update_event(self,inp=-1):
        signal: StreamSignal = self.input(inp)
        if not signal:
            return 
        
        sampling_freq = signal.info.nominal_srate
        
        freqs = np.arange(self.line_freq,sampling_freq/2,self.line_freq)
        
        filtered_data = mne.filter.notch_filter(
            x = signal.data,
            Fs = sampling_freq,
            freqs = freqs,
            filter_length = self.filter_length_input,
            method = self.method,
            mt_bandwidth= self.bandwidth,
            p_value=self.p_value,
            n_jobs=-1,
            phase = self.phase,
            fir_window = self.fir_window,
            fir_design= self.fir_design
        )
        
        filtered_signal = LabeledSignal(
            signal.labels,
            filtered_data, 
            signal.info
        )
        self.set_output(0, filtered_signal)

# TODO CHECK CODE FROM HERE

class ResamplingNode(Node):
    title = 'Resampling Data'
    version = '0.1'
    
    class Config(NodeTraitsConfig):
        upsample_factor:float = CX_Float(1.0,desc='factor to upsample by')
        downsample_factor:float = CX_Float(1.0,desc='factor to downsample by')
        method:str = Enum('fft','polyphase',desc='resampling method to use')

    init_inputs = [PortConfig(label='data',allowed_data=Signal)]
    init_outputs = [PortConfig(label='filtered data',allowed_data=Signal)]
    
    @property
    def config(self) -> ResamplingNode.Config:
        return self._config
    
    def init(self):
        self.upsample_factor = self.config.upsample_factor
        self.downsample_factor = self.config.downsample_factor
        self.method = self.config.method
        
    def update_event(self,inp=-1):
        signal: Signal = self.input(inp)
        if not signal: 
            return
            
        resampled_data = mne.filter.resample(
            x = signal.data,
            up = self.upsample_factor,
            down = self.downsample_factor,
            n_jobs=-1,
            method = self.method
        )
        
        resampled_signal = Signal(resampled_data, None)
        self.set_output(0,resampled_signal)
          
class RemoveTrendNode(Node):
    title = 'Remove Trend from EEG'
    version = '0.1'
    
    class Config(NodeTraitsConfig):
        detrendType: str = Enum('high pass','high pass sinc','local detrend',desc='type of detrending to be performed')
        detrendCutoff:float = CX_Float(1.0,desc='the high-pass cutoff frequency to use for detrending (in Hz)')
        
    init_inputs = [PortConfig(label='data',allowed_data=StreamSignal)]
    init_outputs = [PortConfig(label='filtered data',allowed_data=Signal)]
    
    @property
    def config(self) -> RemoveTrendNode.Config:
        return self._config
    
    def init(self):
        self.detrend_type = self.config.detrendType
        self.detrend_cutoff = self.config.detrendCutoff
        
    def update_event(self,inp=-1):
        signal: StreamSignal = self.input(inp)
        if not signal:
            return 
        
        sampling_freq = signal.info.nominal_srate
                
        filtered_data = remove_trend_data(
            data = signal.data,
            sample_rate=sampling_freq,
            detrendType=self.detrend_type,
            detrendCutoff=self.detrend_cutoff
        )
        
        filtered_signal = Signal(filtered_data, None)
        self.set_output(0, filtered_signal)
    
class SignalToMNENode(Node):
    title = 'Data to MNE'
    version = '0.1'
    
    class Config(NodeTraitsConfig):
        montage:str = Enum('biosemi32','biosemi16','biosemi64','standard_1005','standard_1020') 
        
    init_inputs = [PortConfig(label='data',allowed_data=Signal)]
    init_outputs = [PortConfig(label='MNE',allowed_data=Signal)]
    
    @property
    def config(self) -> SignalToMNENode.Config:
        return self._config
    
    def init(self):
        self.montage = self.config.montage
        
    def update_event(self,inp=-1):
        signal: Signal = self.input(inp)
        if signal: 
            info = mne.create_info(
                ch_names = list(signal.info.channels.values()),
                sfreq = signal.info.nominal_srate,
                ch_types = 'eeg'
            )
            
            raw_mne = mne.io.RawArray(
                data = signal.data,
                info = info
            )
            
            montage = mne.channels.make_standard_montage(self.config.montage)
            raw_mne.set_montage(montage)
            
            self.set_output(0,raw_mne)

class MNEToSignalNode(Node):
    title = 'MNE to Signal'
    version = '0.1'
    
    init_inputs = [PortConfig(label='MNE data',allowed_data=mne.io.Raw)]
    init_outputs = [PortConfig(label='data',allowed_data=Signal)]
    
    def update_event(self,inp=-1):
        raw: mne.io.Raw = self.input(inp).load_data()
        if raw: 
            
            data = raw.get_data()
            sfreq = raw.info['sfreq']
            channels = raw.info['ch_names']
            channel_dict = {i:channels[i] for i in range(len(channels))}
            
        
            self.set_output(0,data)

class RemovalLineNoisePrepNode(Node):
    title = 'Line Noise Removal PREP'
    version = '0.1'
    
    class Config(NodeTraitsConfig):
        line_freq:float = CX_Float(50.0,desc='line noise frequency')
                
    init_inputs = [PortConfig(label='data',allowed_data=mne.io.Raw)]
    init_outputs = [PortConfig(label='filtered_data',allowed_data=mne.io.Raw)]
    
    @property
    def config(self) -> RemovalLineNoisePrepNode.Config:
        return self._config
    
    def start(self):
        self.line_freq = self.config.line_freq
        
    def update_event(self,inp=-1):
        signal: mne.io.Raw = self.input(inp).load_data()
        if signal: 
            
            filtered_data = line_noise_removal_prep(
                raw_eeg = signal,
                sfreq = signal.info['sfreq'],
                linenoise = np.arange(self.line_freq,signal.info['sfreq']/2,self.line_freq)
            )
            
            self.set_output(0,filtered_data)

class ReferencingPrepNode(Node):
    title = 'Referencing EEG Prep'
    version = '0.1'
    
    class Config(NodeTraitsConfig):
        ref_chs:str|list = CX_Str('eeg')
        reref_chs:str|list = CX_Str('eeg')
        line_freqs:float = CX_Float(50.0,desc='line noise frequency')
        max_iterations:int = CX_Int(4)
        ransac:bool = Bool()
        channel_wise:bool = Bool()
    
    init_inputs = [PortConfig(label = 'data', allowed_data= mne.io.Raw)]
    init_outputs = [PortConfig(label = 'referenced data',allowed_data = mne.io.Raw)]
    
    @property
    def config(self) -> ReferencingPrepNode.Config:
        return self._config
    
    def start(self):
        self.ref_chs = self.config.ref_chs
        self.reref_chs = self.config.reref_chs
        self.line_freqs = self.config.line_freqs
        self.max_iterations = self.config.max_iterations
        self.ransac = self.config.ransac
        self.channel_wise = self.config.channel_wise

    def update_event(self,inp=-1):
        signal: mne.io.Raw = self.input(inp).load_data()
        if signal: 
            
            sfreq = signal.info['sfreq']
            
            self.line_freqs = np.arange(self.line_freqs, sfreq/2, self.line_freqs)
            
            referenced_eeg = referencing_prep(
                raw_eeg = signal,
                ref_chs = self.ref_chs,
                reref_chs = self.reref_chs,
                line_freqs = self.line_freqs,
                max_iterations = self.max_iterations,
                ransac = self.ransac,
                channel_wise = self.channel_wise
            )
            
            self.set_output(0,referenced_eeg)

class NoisyChannelPrepNode(Node):
    title = 'Noisy Channels Prep'
    version = '0.1'
    
    init_inputs = [PortConfig(label = 'data', allowed_data= mne.io.Raw)]
    init_outputs = [PortConfig(label = 'noisy channel detected data',allowed_data = mne.io.Raw)]

    def update_event(self,inp=-1):
        signal: mne.io.Raw = self.input(inp).load_data()
        if signal: 
            
            new_eeg = noisychannelsprep(signal)
            
            self.set_output(0,new_eeg)

class InterpolateEEGNode(Node):
    title = 'Interpolate bad channels MNE'
    version = '0.1'
    
    class Config(NodeTraitsConfig):
        reset_bads:bool = Bool()
        mode:str = Enum('accurate','fast')
    
    init_inputs = [PortConfig(label = 'data', allowed_data= mne.io.Raw)]
    init_outputs = [PortConfig(label = 'interpolated data',allowed_data = mne.io.Raw)]

    @property
    def config(self) -> InterpolateEEGNode.Config:
        return self._config

    def update_event(self,inp=-1):
        signal: mne.io.Raw = self.input(inp).load_data()
        if signal: 
            
            new_eeg = signal.copy().interpolate_bads(
                reset_bads = self.config.reset_bads,
                mode = self.config.mode
            )
            
            self.set_output(0,new_eeg) 
 
 
class RepairArtifactsICANode(Node):
    title = 'Repair Artifacts with ICA'
    version = '0.1'
    
    class Config(NodeTraitsConfig):
        n_components:int = CX_Int()
        mode:str = Enum('fastica','infomax','picard')
    
    init_inputs = [PortConfig(label = 'data', allowed_data= mne.io.Raw)]
    init_outputs = [PortConfig(label = 'cleaned data',allowed_data = mne.io.Raw)]

    @property
    def config(self) -> RepairArtifactsICANode.Config:
        return self._config
    
    def start(self):
        self.n_components = self.config.n_components if self.config.n_components else None
        self.method = self.config.method

    def update_event(self,inp=-1):
        signal: mne.io.Raw = self.input(inp).load_data()
        if signal: 
            
            ica = mne.preprocessing.ICA(
                n_components=self.n_components,
                method=self.method,
                max_iter = 'auto',
                random_state=42
            )
            
            ica.fit(signal)
            ic_labels = label_components(signal,ica,method='iclabel')
            
            labels = ic_labels['labels']
            
            exclude_idx = [idx for idx,label in enumerate(labels) if label not in ['brain','other']]
            
            cleaned_signal = ica.apply(signal,exclude=exclude_idx)
            self.set_output(0,cleaned_signal) 
            
class AverageReferenceNode(Node):
    title = 'Average Rereference on EEG'
    version = '0.1'
    
    init_inputs = [PortConfig(label = 'data', allowed_data= mne.io.Raw)]
    init_outputs = [PortConfig(label = 'rereferenced data',allowed_data = mne.io.Raw)]

    def update_event(self,inp=-1):
        signal: mne.io.Raw = self.input(inp).load_data()
        if signal: 
            
            rereferenced_data = mne.set_eeg_reference(
                signal,
                ref_channels = 'average',
                copy=True
            )
            
            self.set_output(0,rereferenced_data) 