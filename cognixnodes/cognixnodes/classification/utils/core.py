"""Defines the base class fot classifiers of sklearn"""
from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from cognixcore import PortConfig
from abc import ABC
import numpy as np

from ...core import FeatureSignal

class BasePredictor(ABC):

    @abstractmethod
    def train(self, f_signal: FeatureSignal, binary_classification:bool):
        pass

    @abstractmethod
    def test(self, f_signal: FeatureSignal):
        pass

    @abstractmethod
    def save_model(self, path:str):
        pass

    @abstractmethod
    def load_model(self, path:str):
        pass
    

