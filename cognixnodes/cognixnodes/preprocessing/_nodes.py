from __future__ import annotations

from cognixcore import Flow, PortConfig
import mne

from mne_icalabel import label_components  

from cognixcore.config.traits import *
from typing import Union
import numpy as np
from traitsui.api import CheckListEditor

from pylsl import local_clock
from collections.abc import Sequence
from sys import maxsize

from ..core import Signal, TimeSignal, StreamSignal, LabeledSignal
from .utils.circ_buffer import CircularBuffer

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
            segment, timestamps = self.buffer.find_segment(
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
        
        self.buffer.append(self.data_signal.data.T, self.data_signal.timestamps)
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
    
    buffer:
        In the buffer mode, it acts as a buffer. Incoming data
        must be of type StreamSignal. Each time the node updates,
        it adds the input to the buffer and outputs the Window
        if it is detected.
    
    segment:
        In the segment mode, it acts as a segmentation mechanism.
        Incoming data can be a StreamSignal or a list of StreamSignals.
        In its update, it will receive the data, attempt to segment it
        into the requested window size and return the results as a 
        list of StreamSignals. If the data is less than the window,
        there will be no output.
        
        This mode has an optional overlap parameter, where the resulting
        windows can be overlapped. This value is clamped to the window size.
    """
    
    title = 'Window'
    version = '0.1'

    buffer_mode = 'buffer'
    segment_mode = 'segment'
    
    class Config(NodeTraitsConfig):
        mode: str = Enum('buffer', 'segment', desc='the operation mode of the Window Node')
        window_length: float = CX_Float(0.5, desc='length of the window in seconds')
        overlap: float = CX_Float(0, visible_when='mode=="segment"', desc='overlap between the windows')
        debug: bool = Bool(False, desc='debug message when data is segmented')
    
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
    
    @property
    def config(self) -> WindowNode.Config:
        return self._config
        
    def update_event(self, inp=-1):
        
        self.data_inp: StreamSignal | Sequence[StreamSignal] = self.input(inp)
        if not self.data_inp:
            return
        
        if self.config.mode == self.buffer_mode:
            self.update_buffer_mode(self.data_inp)
        else:
            self.update_segment_mode(self.data_inp)    
    
    def update_buffer_mode(self, data_inp: StreamSignal):
        if not self.buffer:
            self.buffer = CircularBuffer(
                data_inp.info.nominal_srate,
                self.config.window_length,
                data_inp.timestamps[0],
                len(data_inp.labels)
            )
        
        # TODO if the incoming signal is bigger than the window,
        # segment it and return multiple windows :D
        data, timestamps = self.buffer.append(data_inp.data, data_inp.timestamps, True)
        if data:
            result_signal = StreamSignal(
                timestamps,
                data_inp.labels,
                data,
                data_inp.info
            )
            self.set_output(0, result_signal)
        
    def update_segment_mode(self, data_inp: StreamSignal | Sequence[StreamSignal]):
        if isinstance(data_inp, StreamSignal):
            data_inp = [data_inp]
        
        wnd_dur = self.config.window_length
        overlap = min(self.config.overlap, wnd_dur)
        results: list[StreamSignal] = []
        buffer = CircularBuffer.create_empty()
        for i in range(len(data_inp)):
            inp_signal = data_inp[i]
            inp_dur = inp_signal.tms[-1] - inp_signal.tms[0]
            
            if inp_dur < wnd_dur:
                if self.config.debug:
                    self.logger.warning(f'Incoming signal had smaller duration than Window Length')
                continue
            
            buffer.reset(inp_signal.data, inp_signal.timestamps)
            
            wnd_num = int(inp_dur / wnd_dur)
            for w in range(wnd_num):
                wnd_length = wnd_dur
                if w != wnd_num - 1:
                    wnd_length += overlap
                
                start = w*wnd_dur
                segment, times = buffer.find_segment(
                    timestamp=0,
                    offsets=(start, start + wnd_length)
                )
                
                results.append(
                    StreamSignal(
                        timestamps=times,
                        labels=inp_signal.labels,
                        data=inp_signal.data,
                        signal_info=inp_signal.info
                    )
                )
        if results:
            self.set_output(0, results) 
 
class LabeledSignalSelectionNode(Node):
    """
    Selects part of a signal based on its labels. An option
    allows for the labels given to be forced to lowercase.
    """
    
    title = 'Select Labels'
    version = '0.1'
    
    class Config(NodeTraitsConfig):
        
        labels_egg = ['Fp1', 'Af3', 'F7', 'F3', 'Fc1', 'Fc5', 'T7',
            'C3', 'Cp1', 'Cp5', 'P7', 'P3', 'Pz', 'Po3', 'O1', 'Oz', 'O2', 'Po4',
            'P4', 'P8', 'Cp6', 'Cp2', 'C4', 'T8', 'Fc6', 'Fc2', 'F4', 'F8', 'Af4',
            'Fp2', 'Fz', 'Cz'
        ]
        
        force_lowercase: bool = Bool()
        labels: list[str] = List(CX_Str())
    
    init_inputs = [
        PortConfig(label='in', allowed_data=LabeledSignal)
    ]
    init_outputs = [
        PortConfig(label='out', allowed_data=StreamSignal | LabeledSignal)
    ]

    @property
    def config(self) -> LabeledSignalSelectionNode.Config:
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
        
        signal: LabeledSignal | StreamSignal = self.input(inp)
        if not signal:
            return 
        
        if not self.start_ind:
            self._optimize_search(signal)
        
        if isinstance(self.start_ind, str):
            # no optimization found
            subdata = signal.data[self.chan_inds]
        else:
            subdata = signal.data[self.start_ind: self.stop_ind]
        
        if isinstance(signal, StreamSignal):
            subsignal = StreamSignal(
                signal.timestamps,
                self.selected_labels,
                subdata,
                signal.info,
                False
            )
        elif isinstance(signal, LabeledSignal):
            subsignal = LabeledSignal(
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
            
    init_inputs = [PortConfig(label='data',allowed_data=StreamSignal)]
    init_outputs = [PortConfig(label='filtered data',allowed_data=StreamSignal)]
    
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
        
        filtered_data = mne.filter.filter_data(
            data = signal.data,
            sfreq = signal.info.nominal_srate,
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
        
        print(filtered_data)

        filtered_signal = StreamSignal(
            signal.timestamps,
            signal.labels,
            filtered_data,
            signal.info,
            False,
        )
        
        self.set_output(0, filtered_signal)
    
          
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
        
    init_inputs = [PortConfig(label='data',allowed_data=StreamSignal)]
    init_outputs = [PortConfig(label='filtered data',allowed_data=LabeledSignal)]
    
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
        
        iir_params_dict = mne.filter.construct_iir_filter(
            iir_params = self.params,
            f_pass = self.config.f_pass,
            f_stop =  self.config.f_stop,
            sfreq = signal.info.nominal_srate,
            type = self.config.btype,      
        )
        
        filtered_data = mne.filter.filter_data(
            data = signal.data,
            sfreq = signal.info.nominal_srate,
            method = 'iir',
            iir_params = iir_params_dict
            )

        filtered_signal = LabeledSignal(
            signal.labels,
            filtered_data,
            signal.info    
        )
        
        self.set_output(0, filtered_signal)
            
            
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



from .utils.prep_pipeline_functions import remove_trend_data,line_noise_removal_prep,referencing_prep,noisychannelsprep
          
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