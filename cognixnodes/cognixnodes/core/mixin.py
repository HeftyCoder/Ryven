"""Defines interfaces important to various signals"""
from collections.abc import Sequence

class Timestamped:
    """An object that provides timestamp data"""
    
    def __init__(self, timestamps: Sequence[float]):
        self._timestamps = timestamps
    
    @property
    def timestamps(self):
        return self._timestamps
    
    @property
    def tms(self):
        """Shorthand for self.timestamps"""
        return self._timestamps

class Labeled:
    """An object that provides label data"""
    
    def __init__(self, labels: Sequence[str], make_lowercase=False):
        self._labels = labels
        if make_lowercase:
            self._labels = [label.lower() for label in labels]
    
    @property
    def labels(self):
        return self._labels

class StreamConfig:
    """An object that provides information about a stream"""
    
    def __init__(
        self,
        nominal_srate: int, 
        signal_type: str, 
        data_format: str, 
        name: str,
    ):
    
        self._nominal_srate = nominal_srate
        self._signal_type = signal_type
        self._data_format = data_format
        self._name = name
    
    @property
    def nominal_srate(self):
        """
        The nominal sampling rate of the stream. If a stream is irregular,
        this value won't have any meaning.
        """
        return self._nominal_srate
    
    @property
    def signal_type(self):
        return self._signal_type
    
    @property
    def data_format(self):
        """The format of data (i.e. float32 or float64)"""
        return self._data_format
    
    @property
    def name(self):
        return self._name