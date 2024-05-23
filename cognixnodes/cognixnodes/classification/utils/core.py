"""Defines the base class fot classifiers of sklearn"""
from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from cognixcore import PortConfig
from abc import ABC
import numpy as np

##### from .core import SignalInfo,Signal
### X_train and Y_train are to change to just a Signal object

class BasePredictor(ABC):

    @abstractmethod
    def train(self,X_train:np.ndarray,Y_train:np.ndarray,binary_classification:bool):
        pass

    @abstractmethod
    def test(self,X_test:np.ndarray,Y_test:np.ndarray):
        pass

    @abstractmethod
    def save_model(self,path:str):
        pass

    @abstractmethod
    def load_model(self,path:str):
        pass
    

