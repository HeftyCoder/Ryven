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

class FBSCPNode(Node):
    title = 'Filter Bank Common Spatial Patterns'
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
    def config(self) -> FBSCPNode.Config:
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
            
class PSDMultitaperNode(CognixNode):
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

    def on_start(self):
        self.fmin = self._config.fmin 
        
        self.fmax = np.inf
        if self._config.fmax: self.fmax = self._config.fmax    
        
        self.bandwidth = None
        if self._config.bandwidth: self.bandwidth = self._config.bandwidth   
        
        self.normalization = self._config.normalization
        
        self.output = self._config.output
        
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
                        
            self.set_output_val(0,Data(psds))
            self.set_output_val(1,Data(freqs))
         

            
class PSDWelchNode(CognixNode):
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

    def on_start(self):
        self.fmin = self._config.fmin 
        
        self.fmax = np.inf
        if self._config.fmax: self.fmax = self._config.fmax    
        
        self.n_fft = self._config.n_fft  
        
        self.n_overlap = self._config.n_overlap  
        
        self.n_per_seg = None
        if self._config.n_per_seg: self.n_per_seg = self._config.n_per_seg   
        
        self.average = self._config.average if self._config.average!= 'none' else None
        
        self.output = self._config.output
        
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
                        
            self.set_output_val(0,Data(psds))
            self.set_output_val(1,Data(freqs))
         
       
class MorletTFNode(CognixNode):
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

    def on_start(self):
        self.n_cycles = self._config.n_cycles
        self.zero_mean = self._config.zero_mean
        self.use_fft = self._config.use_fft
        self.output = self._config.output
        
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
                        
            self.set_output_val(0,Data(out))

       
class MultitaperTFNode(CognixNode):
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

    def on_start(self):
        self.n_cycles = self._config.n_cycles
        self.zero_mean = self._config.zero_mean
        self.time_bandwidth = self._config.time_bandwidth if self._config.time_bandwidth >= 2.0 else 4.0 
        self.use_fft = self._config.use_fft
        self.output = self._config.output
        
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
            
            self.set_output_val(0,Data(out))
            
            
class StockwellTFNode(CognixNode):
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

    def on_start(self):
        self.fmin = self._config.fmin if self._config.fmin else None
        self.fmax = self._config.fmax if self._config.fmax else None
        self.n_fft = self._config.n_fft if self._config.n_fft else None
        self.width = self._config.width
        self.return_itc = self._config.return_itc
        
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
                self.set_output_val(1,Data(itc))
            self.set_output_val(0,Data(st_power))
            self.set_output_val(2,Data(freqs))

class CWTNode(CognixNode):
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

    def on_start(self):
        self.use_fft = self._config.use_fft
        self.mode = self._config.mode
        
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
            
            self.set_output_val(0,Data(output))
            
class STFTNode(CognixNode):
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

    def on_start(self):
        self.wsize = self._config.wsize
        self.tstep = self._config.tstep
        
    def update_event(self, inp=-1):
        signal:Signal = self.input_payload(inp)
        if signal:
            features = signal.copy()

            output = mne.time_frequency.stft(
                x = signal.data,
                wsize = self.wsize,
                tstep = self.tstep
            )

            self.set_output_val(0,Data(output))
            
class ISTFTode(CognixNode):
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

    def on_start(self):
        self.Tx = self._config.Tx if self._config.Tx else None
        self.tstep = self._config.tstep 
        
    def update_event(self, inp=-1):
        signal:Signal = self.input_payload(inp)
        if signal:
            features = signal.copy()
            
            output = mne.time_frequency.istft(
                X = signal.data,
                tstep = self.tstep,
                Tx = self.Tx
            )
            
            self.set_output_val(0,Data(output))
            
       
class FourierCSDNode(CognixNode):
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

    def on_start(self):
        self.fmin = self._config.fmin 
        self.fmax = self._config.fmax if self._config.fmax else np.inf 
        self.t0 = self._config.t0
        self.tmin = self._config.tmin if self._config.tmin else None
        self.tmax = self._config.tmax if self._config.tmax else None
        self.nfft = self._config.n_fft if self._config.n_fft else None
        
        
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
            
            self.set_output_val(0,Data(out))
            
class MultitaperCSDNode(CognixNode):
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

    def on_start(self):
        self.fmin = self._config.fmin 
        self.fmax = self._config.fmax if self._config.fmax else np.inf 
        self.t0 = self._config.t0
        self.tmin = self._config.tmin if self._config.tmin else None
        self.tmax = self._config.tmax if self._config.tmax else None
        self.nfft = self._config.n_fft if self._config.n_fft else None
        self.bandwidth = self._config.bandwidth if self._config.bandwidth else None
        
        
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
            
            self.set_output_val(0,Data(out))

class MorletCSDNode(CognixNode):
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

    def on_start(self):
        self.t0 = self._config.t0
        self.tmin = self._config.tmin if self._config.tmin else None
        self.tmax = self._config.tmax if self._config.tmax else None
        self.use_fft = self._config.use_fft
        self.n_cycles = self._config.n_cycles if self._config.n_cycles else None
        
        
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
            
            self.set_output_val(0,Data(out))