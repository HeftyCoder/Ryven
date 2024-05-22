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
            

            
            
