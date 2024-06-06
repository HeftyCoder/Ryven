"""Defines the core functionalities and data types for Cognix"""
from __future__ import annotations
from collections.abc import Mapping, Sequence
from .mixin import *
from sys import maxsize
from itertools import chain
import numpy as np

class SignalInfo:
    """
    A signal info carries metadata about the signal
    
    At its base form, it's a simple class with **kwargs for storing
    information. The **kwargs are stored as attribute to the instance
    of the class.
    
    """
    
    def __init__(
        self,
        **kwargs
    ):
        for key, value in kwargs.items():
            setattr(self, key, value)
        
class Signal:
    """
    Represents the data being passed over nodes for signal processing
    
    The data is a numpy array of any shape. What the shape describes 
    is left to the metadata. Some nodes may require a signal of 
    specific type, shape, etc.
    
    i.e.
    In EEG, a 2x2 shape might represent samples x channels.
    In image processing,a 2x2 shape typically represents an image.
    """
    
    @classmethod
    def concat(*signals: Signal, axis=0):
        if len(signals) == 1:
            return signals[0]
        
        datas = [
            sig.data for sig in signals
        ]
        
        data_comb = np.concatenate(datas, axis)
        
        return Signal(
            data_comb,
            signals[0].info
        )
        
    def __init__(
        self,  
        data: np.ndarray,
        signal_info: SignalInfo 
    ):
        self._data = data
        self._info = signal_info
    
    def __getitem__(self, key):
        return self.data[key]
    
    def __setitem__(self, key, newvalue):
        self.data[key] = newvalue
        
    @property
    def info(self):
        """Metadata information regarding the signal"""
        return self._info
    
    @property
    def data(self):
        return self._data

class TimeSignal(Signal, Timestamped):
    """
    Represents signal data with additional timestamps per sample
    
    The timestamps should map to the first dimension of the signal.
    
    i.e. A video stream, a single channel of EEG
    """
    
    @classmethod
    def concat(*signals: TimeSignal, axis=0):
        if len(signals) == 1:
            return signals[0]
        
        datas = [
            sig.data for sig in signals
        ]
        timetables = [
            sig.tms for sig in signals
        ]
        
        if axis==0:
            data_conc = np.concatenate(datas, 0)
            tms_concat = np.concatenate(timetables)
        else:
            for i in range(len(timetables) - 1):
                assert np.array_equal(timetables[i], timetables[i+1]), "Timestamp array must be the same accross all signals"
            
            for i in range(len(datas) - 1):
                assert datas[i].shape == datas[i+1].shape, "Datas must share the same shape"
            
            data_conc = np.concatenate(datas, 1)
            tms_concat = timetables[0]
        
        return TimeSignal(
            tms_concat,
            data_conc,
            signals[0].info
        )
                
    class DataMap:
        """
        Maps from time indices to data indices
        
        Since timestamps are row-related, there is no
        conversion between time and data indices.
        """
        def __init__(self, data: np.ndarray, timestamps: Sequence[float], info: SignalInfo):
            self.data = data
            self.timestamps = timestamps
            self.info = info
        
        def __str__(self):
            return str(self.data)
        
        def __getitem__(self, key):
            sub_data = self.data[key]
            sub_times = self.timestamps[key]
            return TimeSignal.DataMap(sub_data, sub_times, self.info)
        
        def __setitem__(self, key, value):
            self.data[key] = value
        
        def signal(self):
            """Converts the DataMap back to a TimeSignal"""
            return TimeSignal(self.data, self.timestamps, self.info)
        
    def __init__(self, timestamps: Sequence[float], data: np.ndarray, signal_info: SignalInfo):
        Signal.__init__(self, data, signal_info)
        Timestamped.__init__(self, timestamps)
        self._time_datamap = TimeSignal.DataMap(data, timestamps, signal_info)
    
    @property
    def time_datamap(self):
        """Retrieves an object with mapped indices from timestamps to data"""
        return self._time_datamap
    
    @property
    def tdm(self):
        """Shorthand for time_datamap"""
        return self.time_datamap

class LabeledSignal(Signal, Labeled):
    """
    Represents signal data that is mapped to specific labels.
    """
    
    @classmethod
    def concat(self, *signals: LabeledSignal, axis=0):
        
        if len(signals) == 1:
            return signals[0]
        
        datas = [
            sig.data for sig in signals
        ]
        label_lists = [
            sig.labels for sig in signals
        ]
        
        if axis==0:
            data_conc = np.concatenate(datas, axis=0)
            label_conc = list(chain(*label_lists))
        else:
            for i in range(len(label_lists) - 1):
                assert label_lists[i] == label_lists[i+1], "Labels must be the same for vertical concat!"
            data_con = np.concatenate(datas, axis=1)
            label_conc = label_lists[0]
        
        return LabeledSignal(
            label_conc,
            data_con,
            signals[0].info
        )
        
    class DataMap:
        """
        Maps from label indices to data indices
        
        Since labels are column-related, a conversion must be made
        between label indices and data indices.
        """
        def __init__(self, data: np.ndarray, labels: Sequence[str], info: SignalInfo):
            self.data = data
            self.labels = labels
            self.info = info
            self._label_to_index: dict[str, int] = {
                label:index for index, label in enumerate(labels)
            }
        
        def __str__(self):
            return f"{self.labels}\n{self.data}"
        
        def __getitem__(self, key):
            old_key = key
            key = self.convert_to_indices(key)
            sub_data = self.data[:, key]
            if isinstance(key, list):
                sub_labels = old_key
            else:
                sub_labels = self.labels[key]
            return LabeledSignal.DataMap(sub_data, sub_labels, self.info)
        
        def __setitem__(self, key, value):
            key = self.convert_to_indices(key)
            self.data[:, key] = value
        
        def signal(self):
            """Converts the DataMap back to a LabeledSignal"""
            return LabeledSignal(self.labels, self.data, self.info)
        
        def convert_to_indices(self, key):
            result = key
            if isinstance(key, str):
                result = self._label_to_index[key]
            elif isinstance(key, list):
                result = []
                for k in key:
                    result.append(self._label_to_index[k])
            elif isinstance(key, slice):
                start = (
                    self._label_to_index[key.start] 
                    if isinstance(key.start, str)
                    else key.start
                )
                stop = (
                    self._label_to_index[key.stop]
                    if isinstance(key.stop, str)
                    else key.stop
                )
                stop += 1
                stop = min(len(self.labels), stop)
                result = slice(start, stop)
            return result
    
    def __init__(
        self,
        labels: Sequence[str], 
        data: np.ndarray, 
        signal_info: SignalInfo,
        make_lowercase=False,
    ):
        Signal.__init__(self, data, signal_info)
        Labeled.__init__(self, labels, make_lowercase)
        self._label_datamap = LabeledSignal.DataMap(data, labels, signal_info)

    @property
    def label_datamap(self):
        """Retrieves an object with mapped indices from labels to data"""
        return self._label_datamap

    @property
    def ldm(self):
        """Shorthand for label_datamap"""
        return self.label_datamap
    
class StreamSignalInfo(SignalInfo, StreamConfig):
    """Information regard a Stream Signal"""
    def __init__(
        self,
        nominal_srate: int, 
        signal_type: str, 
        data_format: str, 
        name: str, 
        **kwargs
    ):
        SignalInfo.__init__(self, **kwargs)
        StreamConfig.__init__(
            self,
            nominal_srate,
            signal_type,
            data_format,
            name 
        )
        
class StreamSignal(TimeSignal, LabeledSignal):
    """
    Represents time signal data with additional channels / labels.
    
    In this context, a timestamp doesn't correspond to a singular unit
    of the signal, but rather multitle samples from different sources
    (devices) recorded at the same time.
    
    i.e. multiple video streams, a full EEG configuration (all channels)
    
    This object is essentially a superset of the TimeSignal class and
    will most likely be used in the majority of cases, even if there was
    only one channel / label.
    """
    
    def __init__(
        self, 
        timestamps: Sequence[float], 
        labels: Sequence[str],
        data: np.ndarray, 
        signal_info: StreamSignalInfo,
        make_lowercase=False
    ):
        TimeSignal.__init__(self, timestamps, None, None)
        LabeledSignal.__init__(self, labels, None, None, make_lowercase)
        self._data = data
        self._info = signal_info
    
    @property
    def info(self):
        return self._info

class FeatureSignal(LabeledSignal):
    """
    Represents a signal whose rows correspond to a feature
    and whose columns correspond to a feature label 
    """
    
    @classmethod
    def concat_classes(self, *signals: FeatureSignal):
        """
        Concatenates two Feature Signals based on their classes.
        The resulting signal will have the data reordered in such
        a way that a class has all its data sequentially in memory.
        
        This means that the features / labels of the signals must
        be the same, both in length and in order.
        """
        
        if len(signals) == 1:
            return signals[0]
        
        for i in range(len(signals) - 1):
            assert (signals[i].labels == signals[i+1].labels,
                   "Signal labels are not the same!")
        
        # ideally, this should be implemented in cython
        # or as an external library
        
        # extract all the available classes
        class_labels = {
            class_label
            for signal in signals
            for class_label in signal.classes
        }
        
        # We scan the data through its labels and add
        # whatever data we find to this list. In the
        # end, we'll have the data we want sorted by
        # the labels in sequence
        class_sorted_datas: list[np.ndarray] = []
        
        # the index dictionary for the classes
        class_index_dict: dict[str, tuple[int, int]] = {}
        offset = 0
        for class_label in class_labels:
            
            # final length of the current label
            label_data_len = 0
            for signal in signals:
                if class_label in signal.cdm:
                    label_data = signal.cdm[class_label].data
                    class_sorted_datas.append(label_data)
                    label_data_len += label_data.shape[0]
            
            class_index_dict[class_label] = (offset, offset + label_data_len)
            offset += label_data_len
        
        classes_data = np.concatenate(class_sorted_datas, axis=0)
        return FeatureSignal(
            signals[0].labels,
            class_index_dict,
            classes_data,
            None
        )
            
    class DataMap:
        
        def __init__(
            self,
            labels: Sequence[str],
            class_dict: dict[str, tuple[int, int]],
            data: np.ndarray,
            signal_info: SignalInfo
        ):
            self.labels = labels
            self.classes = class_dict
            self.data = data
            self.info = signal_info
        
        def get(self, key):
            try:
                return self[key]
            except:
                return None
        
        def __contains__(self, class_name):
            return class_name in self.classes    
            
        def __getitem__(self, key):
            if isinstance(key, str):
                class_range = self.classes[key]
                subclasses = {key: class_range}
                start, stop = class_range
                subdata = self.data[start:stop]
            elif isinstance(key, list):
                minstart = maxsize
                maxstop = -1
                subclasses: dict[str, tuple[int, int]] = {}
                for k in key:
                    class_range = self.classes[k]
                    subclasses[k] = class_range
                    start, stop = class_range
                    minstart = min(minstart, start)
                    maxstop = max(maxstop, stop)
                
                subdata = self.data[start:stop]
            else:
                raise KeyError(f"Incompatible Key Type. Must be {str} or {list}")
            
            return FeatureSignal.DataMap(
                self.labels,
                subclasses,
                subdata,
                self.info
            )
        
        def signal(self):
            return FeatureSignal(
                self.labels,
                self.classes,
                self.data,
                self.info
            )
            
    def __init__(
        self, 
        labels: Sequence[str],
        class_dict: dict[str, tuple[int, int]],
        data: np.ndarray, 
        signal_info: SignalInfo
    ):
        super().__init__(labels, data, signal_info)
        self.classes = class_dict
        self._class_datamap = FeatureSignal.DataMap(
            labels, 
            class_dict, 
            data, 
            signal_info
        )
    
    @property
    def class_datamap(self):
        """Map from the classes to the portion of the signal"""
        return self._class_datamap
    
    @property
    def cdm(self):
        """Shorthand for class_datamap"""
        return self._class_datamap
    