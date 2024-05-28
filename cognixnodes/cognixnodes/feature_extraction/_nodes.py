from __future__ import annotations

from ..input.payloads.core import Signal
import mne

from cognixcore.api import (
    Flow, 
    Node, 
    FrameNode, 
    PortConfig,
)
from cognixcore.config.traits import *

import numpy as np
from traitsui.api import CheckListEditor
from collections.abc import Sequence
from .utils.fbscp_func import FBCSP_binary
from .utils.stats_helper import *

class FBSCPBinaryNode(Node):
    title = 'FBCSP Binary'
    version = '0.1'
    
    class Config(NodeTraitsConfig):
        n_windows: int = CX_Int(2,desc='the number of windows used for FBSCP')
        n_features: int = CX_Int(4,desc='the number of features to create')
        freq_bands: str = CX_Str('4-40',desc='the frequency range in Hz in which the FBSCP functions -')
        freq_bands_split: int = CX_Int(10,desc='how to split the frequency band')
        filter_order:int = CX_Int(3,desc='the order of the filter')
    
    init_inputs = [PortConfig(label='data',allowed_data=Signal)]
    init_outputs = [PortConfig(label='features')]
    
    @property
    def config(self) -> FBSCPBinaryNode.Config:
        return self._config 
        
    def start(self):
        self.frequency_bands = self.config.freq_bands.split('-')
        if len(self.frequency_bands) != 2:
            self.frequency_bands = None
        else:
            self.frequency_bands = [int(_) for _ in self.frequency_bands]
            
        self.freq_splits = self.config.freq_bands_split if self.config.freq_bands_split else None
        
    def update_event(self, inp=-1):
        signal: Signal = self.input(inp)
        if signal:
            features = signal.copy()
            
            fbscp_fs = FBCSP_binary(
                data_dict = signal.data,
                fs = signal.info.nominal_srate,
                n_w = self.config.n_windows,
                n_features = self.config.n_features,
                n_freq_bands = self.frequency_bands,
                n_splits_freq = self.freq_splits,
                filter_order = self.config.filter_order,
            )
            
            features_extracted = fbscp_fs.extract_features()
            
            print(features_extracted)
            
            self.set_output(0, features_extracted)
            
class PSDMultitaperNode(Node):
    title = 'Power Spectral Density with Multitaper'
    version = '0.1'


    class Config(NodeTraitsConfig):
        fmin: float = CX_Float(0.0,desc='the lower-bound on frequencies of interest')
        fmax: float = CX_Float(desc='the upper-bound on frequencies of interest')
        bandwidth: float = CX_Float(desc='the frequency bandwidth of the multi-taper window funciton in Hz')
        normalization: str = Enum('full','length',desc='normalization strategy')
        output = str = Enum('power','complex')

    init_inputs = [PortConfig(label='data',allowed_data=Signal)]
    init_outputs = [PortConfig(label='psds'),PortConfig(label='freqs')]

    @property
    def config(self) -> PSDMultitaperNode.Config:
        return self._config

    def start(self):
        self.fmin = self.config.fmin

        self.fmax = np.inf
        if self.config.fmax: self.fmax = self.config.fmax

        self.bandwidth = None
        if self.config.bandwidth: self.bandwidth = self.config.bandwidth

        self.normalization = self.config.normalization

        self.output = self.config.output

    def update_event(self, inp=-1):
        signal:Signal =self.input_payload(inp)
        if signal:
            features = signal.copy()

            psds,freqs,_ = mne.time_frequency.psd_array_multitaper(
                x = signal.data,
                sfreq = signal.info.nominal_srate,
                fmin = self.fmin,
                fmax = self.fmax,
                bandwidth= self.bandwidth,
                normalization= self.normalization,
                output = self.output,
                n_jobs= -1
            )

            self.set_output(0,psds)
            self.set_output(1,freqs)



class PSDWelchNode(Node):
    title = 'Power Spectral Density with Multitaper'
    version = '0.1'


    class Config(NodeTraitsConfig):
        fmin: float = CX_Float(0.0,desc='the lower-bound on frequencies of interest')
        fmax: float = CX_Float(desc='the upper-bound on frequencies of interest')
        n_fft: int = CX_Int(256, desc='The length of FFT used')
        n_overlap: int = CX_Int(0, desc='the number of points of overlap between segments')
        n_per_seg: int = CX_Int(desc='length of each Welch segment')
        average: str = Enum('mean','median','none',desc='how to average the segments')
        output = str = Enum('power','complex')

    init_inputs = [PortConfig(label='data',allowed_data=Signal)]
    init_outputs = [PortConfig(label='psds'),PortConfig(label='freqs')]

    @property
    def config(self) -> PSDWelchNode.Config:
        return self._config

    def start(self):
        self.fmin = self.config.fmin

        self.fmax = np.inf
        if self.config.fmax: self.fmax = self.config.fmax

        self.n_fft = self.config.n_fft

        self.n_overlap = self.config.n_overlap

        self.n_per_seg = None
        if self.config.n_per_seg: self.n_per_seg = self.config.n_per_seg

        self.average = self.config.average if self.config.average!= 'none' else None

        self.output = self.config.output

    def update_event(self, inp=-1):
        signal:Signal =self.input_payload(inp)
        if signal:
            features = signal.copy()

            psds,freqs,_ = mne.time_frequency.psd_array_welch(
                x = signal.data,
                sfreq = signal.info.nominal_srate,
                fmin = self.fmin,
                fmax = self.fmax,
                n_fft= self.n_fft,
                n_overlap= self.n_overlap,
                n_per_seg= self.n_per_seg,
                n_jobs= -1,
                output= self.output,
                window = 'hamming'
            )

            self.set_output(0,psds)
            self.set_output(1,freqs)



class MorletTFNode(Node):
    title = 'Time-Frequency Representetion Morlet'
    version = '0.1'

    class Config(NodeTraitsConfig):
        n_cycles: int = CX_Int(7,desc='number of cycles in the wavelet')
        zero_mean: bool = Bool()
        use_fft: bool = Bool()
        output = str = Enum('complex','power','phase','avg_power','itc','avg_power_itc')

    init_inputs = [PortConfig(label='data',allowed_data=Signal),PortConfig(label='freqs')]
    init_outputs = [PortConfig(label='out')]

    @property
    def config(self) -> MorletTFNode.Config:
        return self._config

    def start(self):
        self.n_cycles = self.config.n_cycles
        self.zero_mean = self.config.zero_mean
        self.use_fft = self.config.use_fft
        self.output = self.config.output

    def update_event(self, inp=-1):
        if inp == 0: signal:Signal =self.input_payload(inp)
        if inp == 1: freqs = self.input_payload(inp)
        if signal and freqs:
            features = signal.copy()

            out = mne.time_frequency.tfr_array_morlet(
                data = signal.data,
                sfreq = signal.info.nominal_srate,
                freqs = freqs,
                n_cycles = self.n_cycles,
                zero_mean = self.zero_mean,
                use_fft = self.use_fft,
                output = self.output
            )

            self.set_output(0,out)



class MultitaperTFNode(Node):
    title = 'Time-Frequency Representetion Multitaper'
    version = '0.1'


    class Config(NodeTraitsConfig):
        n_cycles: int = CX_Int(7,desc='number of cycles in the wavelet')
        zero_mean: bool = Bool()
        use_fft: bool = Bool()
        time_bandwidth: float = CX_Float(4.0,desc='product between the temporal window length (in seconds) and the full frequency bandwidth (in Hz).')
        output = str = Enum('complex','power','phase','avg_power','itc','avg_power_itc')

    init_inputs = [PortConfig(label='data',allowed_data=Signal),PortConfig(label='freqs')]
    init_outputs = [PortConfig(label='out')]

    @property
    def config(self) -> MultitaperTFNode.Config:
        return self._config

    def start(self):
        self.n_cycles = self.config.n_cycles
        self.zero_mean = self.config.zero_mean
        self.time_bandwidth = self.config.time_bandwidth if self.config.time_bandwidth >= 2.0 else 4.0
        self.use_fft = self.config.use_fft
        self.output = self.config.output

    def update_event(self, inp=-1):
        if inp == 0: signal:Signal =self.input_payload(inp)
        if inp == 1: freqs = self.input_payload(inp)
        if signal and freqs:
            features = signal.copy()

            out = mne.time_frequency.tfr_array_multitaper(
                data = signal.data,
                sfreq = signal.info.nominal_srate,
                freqs = freqs,
                n_cycles= self.n_cycles,
                zero_mean= self.zero_mean,
                time_bandwidth= self.time_bandwidth,
                use_fft= self.use_fft,
                output= self.output,
                n_jobs= -1
            )

            self.set_output(0,out)



class StockwellTFNode(Node):
    title = 'Time-Frequency Representetion Stockwell Transform'
    version = '0.1'

    class Config(NodeTraitsConfig):
        fmin: float = CX_Float(desc='the lower-bound on frequencies of interest')
        fmax: float = CX_Float(desc='the upper-bound on frequencies of interest')
        n_fft: int = CX_Int(desc='the length of the windows used for FFT')
        width: float = CX_Float(1.0,desc='the width of the Gaussian Window')
        return_itc: bool = Bool()

    init_inputs = [PortConfig(label='data',allowed_data=Signal),PortConfig(label='freqs')]
    init_outputs = [PortConfig(label='st_power'),PortConfig(label='itc'),PortConfig(label='freqs')]

    @property
    def config(self) -> StockwellTFNode.Config:
        return self._config

    def start(self):
        self.fmin = self.config.fmin if self.config.fmin else None
        self.fmax = self.config.fmax if self.config.fmax else None
        self.n_fft = self.config.n_fft if self.config.n_fft else None
        self.width = self.config.width
        self.return_itc = self.config.return_itc

    def update_event(self, inp=-1):
        if inp == 0: signal:Signal =self.input_payload(inp)
        if inp == 1: freqs = self.input_payload(inp)
        if signal and freqs:
            features = signal.copy()

            st_power,itc,freqs = mne.time_frequency.tfr_array_stockwell(
                data = signal.data,
                sfreq = signal.info.nominal_srate,
                fmin = self.fmin,
                fmax= self.fmax,
                n_fft= self.n_fft,
                width = self.width,
                return_itc= self.return_itc,
                n_jobs= -1
            )

            if self.return_itc:
                self.set_output(1,itc)
            self.set_output(0,st_power)
            self.set_output(2,freqs)



class CWTNode(Node):
    title = 'Continuous Wavelet Transform'
    version = '0.1'

    class Config(NodeTraitsConfig):
        use_fft: bool = Bool(desc='use fft for convolutions')
        mode: str = Enum('same','valid','full',desc='convention for convolution')

    init_inputs = [PortConfig(label='data',allowed_data=Signal),PortConfig(label='wavelets')]
    init_outputs = [PortConfig(label='output')]

    @property
    def config(self) -> CWTNode.Config:
        return self._config

    def start(self):
        self.use_fft = self.config.use_fft
        self.mode = self.config.mode

    def update_event(self, inp=-1):
        if inp == 0: signal:Signal =self.input_payload(inp)
        if inp == 1: ws = self.input_payload(inp)
        if signal and ws:
            features = signal.copy()

            output = mne.time_frequency.tfr.cwt(
                X = signal.data,
                Ws = ws,
                use_fft = self.use_fft,
                mode = self.mode
            )

            self.set_output(0,output)



class STFTNode(Node):
    title = 'Short Time Fourier Transform'
    version = '0.1'

    class Config(NodeTraitsConfig):
        wsize: int = CX_Int(4,desc='length of the STFT window in samples(must be a multiple of 4)')
        tstep: int = CX_Int(2,desc='step between successive windows in samples')

    init_inputs = [PortConfig(label='data',allowed_data=Signal)]
    init_outputs = [PortConfig(label='output')]

    @property
    def config(self) -> CWTNode.Config:
        return self._config

    def start(self):
        self.wsize = self.config.wsize
        self.tstep = self.config.tstep

    def update_event(self, inp=-1):
        signal:Signal = self.input_payload(inp)
        if signal:
            features = signal.copy()

            output = mne.time_frequency.stft(
                x = signal.data,
                wsize = self.wsize,
                tstep = self.tstep
            )

            self.set_output(0,output)



class ISTFTode(Node):
    title = 'Inverse Short Time Fourier Transform'
    version = '0.1'

    class Config(NodeTraitsConfig):
        Tx: int = CX_Int(4,desc='length of the STFT window in samples(must be a multiple of 4)')
        tstep: int = CX_Int(2,desc='step between successive windows in samples')

    init_inputs = [PortConfig(label='data',allowed_data=Signal)]
    init_outputs = [PortConfig(label='output')]

    @property
    def config(self) -> ISTFTode.Config:
        return self._config

    def start(self):
        self.Tx = self.config.Tx if self.config.Tx else None
        self.tstep = self.config.tstep

    def update_event(self, inp=-1):
        signal:Signal = self.input_payload(inp)
        if signal:
            features = signal.copy()

            output = mne.time_frequency.istft(
                X = signal.data,
                tstep = self.tstep,
                Tx = self.Tx
            )

            self.set_output(0,output)



class FourierCSDNode(Node):
    title = 'Cross-spectral density with Fourier Transform'
    version = '0.1'


    class Config(NodeTraitsConfig):
        fmin: float = CX_Float(0.0,desc='the lower-bound on frequencies of interest')
        fmax: float = CX_Float(desc='the upper-bound on frequencies of interest')
        t0: float = CX_Float(0,desc='time of the first sample relative to the onset of the epoch (in sec)')
        tmin: float = CX_Float(desc='minimum time instant to consider, in seconds')
        tmax: float = CX_Float(desc='maximum time instant to consider, in seconds')
        n_fft: int = CX_Int(desc='length of the fft')

    init_inputs = [PortConfig(label='data',allowed_data=Signal)]
    init_outputs = [PortConfig(label='csd')]

    @property
    def config(self) -> FourierCSDNode.Config:
        return self._config

    def start(self):
        self.fmin = self.config.fmin
        self.fmax = self.config.fmax if self.config.fmax else np.inf
        self.t0 = self.config.t0
        self.tmin = self.config.tmin if self.config.tmin else None
        self.tmax = self.config.tmax if self.config.tmax else None
        self.nfft = self.config.n_fft if self.config.n_fft else None

    def update_event(self, inp=-1):
        if inp == 0: signal:Signal =self.input_payload(inp)
        if signal:
            features = signal.copy()

            out = mne.time_frequency.csd_array_fourier(
                X = signal.data,
                sfreq = signal.info.nominal_srate,
                t0 = self.t0,
                fmin= self.fmin,
                fmax = self.fmax,
                tmin = self.tmin,
                tmax = self.tmax,
                ch_names = signal.info.channels.values(),
                n_fft= self.nfft,
                n_jobs= -1
            )

            self.set_output(0,out)



class MultitaperCSDNode(Node):
    title = 'Cross-spectral density with Multitaper Transform'
    version = '0.1'


    class Config(NodeTraitsConfig):
        fmin: float = CX_Float(0.0,desc='the lower-bound on frequencies of interest')
        fmax: float = CX_Float(desc='the upper-bound on frequencies of interest')
        t0: float = CX_Float(0,desc='time of the first sample relative to the onset of the epoch (in sec)')
        tmin: float = CX_Float(desc='minimum time instant to consider, in seconds')
        tmax: float = CX_Float(desc='maximum time instant to consider, in seconds')
        n_fft: int = CX_Int(desc='length of the fft')
        bandwidth:float = CX_Float(desc='the bandwidth of the multitaper windowing function in Hz')

    init_inputs = [PortConfig(label='data',allowed_data=Signal)]
    init_outputs = [PortConfig(label='csd')]

    @property
    def config(self) -> MultitaperCSDNode.Config:
        return self._config

    def start(self):
        self.fmin = self.config.fmin
        self.fmax = self.config.fmax if self.config.fmax else np.inf
        self.t0 = self.config.t0
        self.tmin = self.config.tmin if self.config.tmin else None
        self.tmax = self.config.tmax if self.config.tmax else None
        self.nfft = self.config.n_fft if self.config.n_fft else None
        self.bandwidth = self.config.bandwidth if self.config.bandwidth else None

    def update_event(self, inp=-1):
        if inp == 0: signal:Signal =self.input_payload(inp)
        if signal:
            features = signal.copy()

            out = mne.time_frequency.csd_array_multitaper(
                X = signal.data,
                sfreq = signal.info.nominal_srate,
                t0 = self.t0,
                fmin= self.fmin,
                fmax = self.fmax,
                tmin = self.tmin,
                tmax = self.tmax,
                ch_names = signal.info.channels.values(),
                n_fft= self.nfft,
                bandwidth = self.bandwidth,
                n_jobs= -1
            )

            self.set_output(0,out)



class MorletCSDNode(Node):
    title = 'Cross-spectral density with Multitaper Transform'
    version = '0.1'


    class Config(NodeTraitsConfig):
        t0: float = CX_Float(0,desc='time of the first sample relative to the onset of the epoch (in sec)')
        tmin: float = CX_Float(desc='minimum time instant to consider, in seconds')
        tmax: float = CX_Float(desc='maximum time instant to consider, in seconds')
        use_fft:bool = Bool()
        n_cycles: float = CX_Float(7,desc='number of cycles in the wavelet')

    init_inputs = [PortConfig(label='data',allowed_data=Signal),PortConfig(label='freqs')]
    init_outputs = [PortConfig(label='csd')]

    @property
    def config(self) -> MorletCSDNode.Config:
        return self._config

    def start(self):
        self.t0 = self.config.t0
        self.tmin = self.config.tmin if self.config.tmin else None
        self.tmax = self.config.tmax if self.config.tmax else None
        self.use_fft = self.config.use_fft
        self.n_cycles = self.config.n_cycles if self.config.n_cycles else None

    def update_event(self, inp=-1):
        if inp == 0: signal:Signal =self.input_payload(inp)
        if inp == 1: freqs = self.input_payload(inp)
        if signal and freqs:
            features = signal.copy()

            out = mne.time_frequency.csd_array_morlet(
                X = signal.data,
                sfreq= signal.info.nominal_srate,
                frequencies= freqs,
                ch_names= signal.info.channels.values(),
                t0 = self.t0,
                tmin = self.tmin,
                tmax = self.tmax,
                use_fft= self.use_fft,
                n_cycles= self.n_cycles,
                n_jobs= -1
            )

            self.set_output(0,out)


class MeanNode(Node):
    title = 'Mean'
    version = '0.1'
    
    init_inputs = [PortConfig(label='data',allowed_data=Signal)]
    init_outputs = [PortConfig(label='features')]
    
    def start(self):
        classes = list(Statistics.subclasses.values())
        self.func = self.stats_selected[0]
        self.features = np.zeros((32,1))
    
    def update_event(self, inp=-1):
        signal:Signal =self.input_payload(inp)
        if signal:
            data = signal.data
            func = self.func(data)
            feature = func.calculate_stat()
            self.features[:,0] = feature
            self.set_output(0,self.features)
            
class VarNode(Node):
    title = 'Variance'
    version = '0.1'
    
    init_inputs = [PortConfig(label='data',allowed_data=Signal)]
    init_outputs = [PortConfig(label='features')]
    
    def start(self):
        classes = list(Statistics.subclasses.values())
        self.func = self.stats_selected[1]
        self.features = np.zeros((32,1))
    
    def update_event(self, inp=-1):
        signal:Signal =self.input_payload(inp)
        if signal:
            data = signal.data
            func = self.func(data)
            feature = func.calculate_stat()
            self.features[:,0] = feature
            self.set_output(0,self.features)
            
class StdNode(Node):
    title = 'Standard deviation'
    version = '0.1'
    
    init_inputs = [PortConfig(label='data',allowed_data=Signal)]
    init_outputs = [PortConfig(label='features')]
    
    def start(self):
        classes = list(Statistics.subclasses.values())
        self.func = self.stats_selected[2]
        self.features = np.zeros((32,1))
    
    def update_event(self, inp=-1):
        signal:Signal =self.input_payload(inp)
        if signal:
            data = signal.data
            func = self.func(data)
            feature = func.calculate_stat()
            self.features[:,0] = feature
            self.set_output(0,self.features)
            
class PTPNode(Node):
    title= 'Peak-to-Peak Value'
    version = '0.1'
    
    init_inputs = [PortConfig(label='data',allowed_data=Signal)]
    init_outputs = [PortConfig(label='features')]
    
    def start(self):
        classes = list(Statistics.subclasses.values())
        self.func = self.stats_selected[3]
        self.features = np.zeros((32,1))
    
    def update_event(self, inp=-1):
        signal:Signal =self.input_payload(inp)
        if signal:
            data = signal.data
            func = self.func(data)
            feature = func.calculate_stat()
            self.features[:,0] = feature
            self.set_output(0,self.features)
            
class SkewNode(Node):
    title = 'Skewness'
    version = '0.1'
    
    init_inputs = [PortConfig(label='data',allowed_data=Signal)]
    init_outputs = [PortConfig(label='features')]
    
    def start(self):
        classes = list(Statistics.subclasses.values())
        self.func = self.stats_selected[4]
        self.features = np.zeros((32,1))
    
    def update_event(self, inp=-1):
        signal:Signal =self.input_payload(inp)
        if signal:
            data = signal.data
            func = self.func(data)
            feature = func.calculate_stat()
            self.features[:,0] = feature
            self.set_output(0,self.features)
            
class KurtNode(Node):
    title = 'Kurtosis'
    version = '0.1'
    
    init_inputs = [PortConfig(label='data',allowed_data=Signal)]
    init_outputs = [PortConfig(label='features')]
    
    def start(self):
        classes = list(Statistics.subclasses.values())
        self.func = self.stats_selected[5]
        self.features = np.zeros((32,1))
    
    def update_event(self, inp=-1):
        signal:Signal =self.input_payload(inp)
        if signal:
            data = signal.data
            func = self.func(data)
            feature = func.calculate_stat()
            self.features[:,0] = feature
            self.set_output(0,self.features)
            
class RMSNode(Node):
    title = 'RMS value'
    version = '0.1'
    
    init_inputs = [PortConfig(label='data',allowed_data=Signal)]
    init_outputs = [PortConfig(label='features')]
    
    def start(self):
        classes = list(Statistics.subclasses.values())
        self.func = self.stats_selected[6]
        self.features = np.zeros((32,1))
    
    def update_event(self, inp=-1):
        signal:Signal =self.input_payload(inp)
        if signal:
            data = signal.data
            func = self.func(data)
            feature = func.calculate_stat()
            self.features[:,0] = feature
            self.set_output(0,self.features)
                       
class MobilityNode(Node):
    title = 'Hjorth Mobility'
    version = '0.1'
    
    init_inputs = [PortConfig(label='data',allowed_data=Signal)]
    init_outputs = [PortConfig(label='features')]
    
    def start(self):
        classes = list(Statistics.subclasses.values())
        self.func = self.stats_selected[7]
        self.features = np.zeros((32,1))
    
    def update_event(self, inp=-1):
        signal:Signal =self.input_payload(inp)
        if signal:
            data = signal.data
            func = self.func(data)
            feature = func.calculate_stat()
            self.features[:,0] = feature
            self.set_output(0,self.features)
               
class ComplexityNode(Node):
    title = 'Hjorth Complexity'
    version = '0.1'
    
    init_inputs = [PortConfig(label='data',allowed_data=Signal)]
    init_outputs = [PortConfig(label='features')]
    
    def start(self):
        classes = list(Statistics.subclasses.values())
        self.func = self.stats_selected[8]
        self.features = np.zeros((32,1))
    
    def update_event(self, inp=-1):
        signal:Signal =self.input_payload(inp)
        if signal:
            data = signal.data
            func = self.func(data)
            feature = func.calculate_stat()
            self.features[:,0] = feature
            self.set_output(0,self.features)
                  
class Quantile75thNode(Node):
    title = '75th quantile'
    version = '0.1'
    
    init_inputs = [PortConfig(label='data',allowed_data=Signal)]
    init_outputs = [PortConfig(label='features')]
    
    def start(self):
        classes = list(Statistics.subclasses.values())
        self.func = self.stats_selected[9]
        self.features = np.zeros((32,1))
    
    def update_event(self, inp=-1):
        signal:Signal =self.input_payload(inp)
        if signal:
            data = signal.data
            func = self.func(data)
            feature = func.calculate_stat()
            self.features[:,0] = feature
            self.set_output(0,self.features)
             
class Quantile25thNode(Node):
    title = '25th quantile'
    version = '0.1'
    
    init_inputs = [PortConfig(label='data',allowed_data=Signal)]
    init_outputs = [PortConfig(label='features')]
    
    def start(self):
        classes = list(Statistics.subclasses.values())
        self.func = self.stats_selected[10]
        self.features = np.zeros((32,1))
    
    def update_event(self, inp=-1):
        signal:Signal =self.input_payload(inp)
        if signal:
            data = signal.data
            func = self.func(data)
            feature = func.calculate_stat()
            self.features[:,0] = feature
            self.set_output(0,self.features)
                        
class StatisticsNode(Node):
    title = 'Basic Statistics'
    version = '0.1'

    class Config(NodeTraitsConfig):
        stats_selected: int = List(
            editor = CheckListEditor(
                values = [
                    (0,'mean'),
                    (1,'var'),
                    (2,'std'),
                    (3,'ptp'),
                    (4,'skewness'),
                    (5,'kurtosis'),
                    (6,'rms'),
                    (7,'mobility'),
                    (8,'complexity'),
                    (9,'75th quantile'),
                    (10,'25th quantile')
                ],
                cols=2
            ),
            style='custom'
        )

    init_inputs = [PortConfig(label='data',allowed_data=Signal)]
    init_outputs = [PortConfig(label='features')]

    @property
    def config(self) -> StatisticsNode.Config:
        return self._config
    
    def start(self):
        self.stats_selected = self.config.stats_selected
        classes = list(Statistics.subclasses.values())
        self.funcs = [classes[_] for _ in self.stats_selected]
        self.features = np.zeros((32,len(self.stats_selected)))
    
    def update_event(self, inp=-1):
        signal:Signal =self.input_payload(inp)
        if signal:
            data = signal.data
            for index,func in enumerate(self.funcs):
                func = func(data)
                feature = func.calculate_stat()
                self.features[:,index] = feature

            self.set_output(0,self.features)
            
class ApproximateEntopyNode(Node):
    title = 'Approximate Entropy'
    version = '0.1'
    
    init_inputs = [PortConfig(label='data',allowed_data=Signal)]
    init_outputs = [PortConfig(label='features')]
    
    def update_event(self, inp=-1):
        signal:Signal = self.input_payload(inp)
        if signal:
            data = signal.data
            feature = univariate.compute_app_entropy(data)
            self.set_output(0,feature)

class SampleEntropyNode(Node):
    title = 'Sample Entropy'
    version = '0.1'
    
    init_inputs = [PortConfig(label='data',allowed_data=Signal)]
    init_outputs = [PortConfig(label='features')]
    
    def update_event(self, inp=-1):
        signal:Signal = self.input_payload(inp)
        if signal:
            data = signal.data
            feature = univariate.compute_samp_entropy(data)
            self.set_output(0,feature)
            
class SVDEntropyNode(Node):
    title = 'SVD Entropy'
    version = '0.1'
    
    class Config(NodeTraitsConfig):
        tau: int = CX_Int(2,desc='the delay (number of samples)')
    
    init_inputs = [PortConfig(label='data',allowed_data=Signal)]
    init_outputs = [PortConfig(label='features')]
    
    @property
    def config(self) -> SVDEntropyNode.Config:
        return self._config
    
    def update_event(self, inp=-1):
        signal:Signal = self.input_payload(inp)
        if signal:
            data = signal.data
            feature = univariate.compute_svd_entropy(data=data,tau=self.config.tau)
            self.set_output(0,feature)
            
class WaveletEnergyNode(Node):
    title = 'Wavelet Transform Energy'
    version = '0.1'
    
    class Config(NodeTraitsConfig):
        wavelet_name:str = Enum('haar', 'db1', 'db2', 'db3', 'db4', 'db5', 'db6', 'db7', 'db8', 'db9', 'db10','morl','cmorl','gaus1', 'gaus2', 'gaus3', 'gaus4', 'gaus5', 'gaus6', 'gaus7', 'gaus8',desc='the wavelet name from which we calculate the wavelet coefficients and their energy')
    
    init_inputs = [PortConfig(label='data',allowed_data=Signal)]
    init_outputs = [PortConfig(label='features')]
        
    @property
    def config(self) -> WaveletEnergyNode.Config:
        return self._config 
    
    def update_event(self, inp=-1):
        signal:Signal = self.input_payload(inp)
        if signal:
            data = signal.data
            feature = univariate.compute_wavelet_coef_energy(data,wavelet_name=self.config.wavelet_name)
            self.set_output(0,feature)
            
class PLVNode(Node):
    title = 'Phase Locking Value (PLV)'
    version = '0.1'
    
    class Config(NodeTraitsConfig):
        include_diagonal: bool = Bool()
        
    init_inputs = [PortConfig(label='data',allowed_data=Signal)]
    init_outputs = [PortConfig(label='features')]
        
    @property
    def config(self) -> PLVNode.Config:
        return self._config 
    
    def update_event(self, inp=-1):
        signal:Signal = self.input_payload(inp)
        if signal:
            data = signal.data
            feature = bivariate.compute_phase_lock_val(data,include_diag=self.config.include_diagonal)
            self.set_output(0,feature)

class CorrelationNode(Node):
    title = 'Pearson Correlation (time-domain)'
    version = '0.1'
    
    class Config(NodeTraitsConfig):
        include_diagonal: bool = Bool()
        return_eigenvalues: bool = Bool()
        
    init_inputs = [PortConfig(label='data',allowed_data=Signal)]
    init_outputs = [PortConfig(label='features')]
        
    @property
    def config(self) -> CorrelationNode.Config:
        return self._config 
    
    def update_event(self, inp=-1):
        signal:Signal = self.input_payload(inp)
        if signal:
            data = signal.data
            feature = bivariate.compute_time_corr(data,with_eigenvalues=self.config.return_eigenvalues,include_diag=self.config.include_diagonal)
            self.set_output(0,feature)

class CorrelationSpectralNode(Node):
    title = 'Pearson Correlation (time-domain)'
    version = '0.1'
    
    class Config(NodeTraitsConfig):
        include_diagonal: bool = Bool()
        return_eigenvalues: bool = Bool()
        psd_method:str = Enum('welch','multitaper','fft')
        
    init_inputs = [PortConfig(label='data',allowed_data=Signal)]
    init_outputs = [PortConfig(label='features')]
        
    @property
    def config(self) -> CorrelationSpectralNode.Config:
        return self._config 
    
    def update_event(self, inp=-1):
        signal:Signal = self.input_payload(inp)
        if signal:
            data = signal.data
            feature = bivariate.compute_spect_corr(
                sfreq= signal.info.nominal_srate,
                data = data,
                with_eigenvalues= self.config.return_eigenvalues,
                include_diag= self.config.include_diagonal,
                psd_method= self.config.psd_method
            )
            self.set_output(0,feature)

class PowerSpectrumNode(Node):
    title = 'Power Spectrum'
    version = '0.1'
    
    class Config(NodeTraitsConfig):
        fmin: float = CX_Float(0.0,desc='minimum frequency for the calculation of the power spectrum')
        fmax: float = CX_Float(100.0,desc='maximum frequency for the calculation of the power spectrum')
        n_splits: int = CX_Int(5,desc='number of splits in the specified range of frequencies')
        normalization: bool = Bool()
        psd_method: str = Enum('welch','multitaper','fft',desc='method to calculate the power spectrum')
        log_calculation: bool = Bool()
        
        
    init_inputs = [PortConfig(label='data',allowed_data=Signal)]
    init_outputs = [PortConfig(label='features')]
    
    @property
    def config(self) -> PowerSpectrumNode.Config:
        return self._config
    
    def start(self):
        self.fmin = self.config.fmin if self.config.fmin else None
        self.fmax = self.config.fmax if self.config.fmax else None
        self.n_splits = self.config.n_splits if self.config.n_splits else None

        if not self.fmin or not self.fax or not self.n_splits:
            self.freq_bands = np.array([0.5, 4., 8., 13., 30., 100.])
        else:
            self.freq_bands = np.linspace(self.fmin,self.fmax,self.n_splits)
        
        self.normalization = self.config.normalization
        self.psd_method = self.config.psd_method
        self.log_calculation = self.config.log_calculation
    
    def update_event(self, inp=-1):
        signal:Signal = self.input_payload(inp)
        if signal:
            feature = univariate.compute_pow_freq_bands(
                data = signal.data,
                sfreq = signal.info.nominal_srate,
                freq_bands = self.freq_bands,
                normalize = self.normalization,
                psd_method= self.psd_method,
                log = self.log_calculation
            )
            
            self.set_output(0,feature)


