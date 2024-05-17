"""Defines the base class fot classifiers of sklearn"""
from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
import numpy as np
import joblib
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression

from .._nodes import CognixNode, PortConfig
from abc import ABC

class BaseClassifier(ABC):
    
    @abstractmethod    
    def train(self):
        pass

class SVMClassifier(BaseClassifier):
    
    def __init__(self):
        self.model = SVC()
    
    def train(self):
        pass

class LinearRegression(BaseClassifier):
    
    def __init__(self):
        super().__init__(self)
        self.model = LogisticRegression()

class RandomForestClassifier(BaseClassifier):
    
    def __init__(self):
        super().__init__(self)
        self.model = RandomForestClassifier()
        
class SVMNode(CognixNode):
    
    init_outputs=[PortConfig('model', allowed_data=SVMClassifier)]
    
class TrainNode(CognixNode):
        
    init_inputs=[
        PortConfig('data'),
        PortConfig('model', allowed_data=BaseClassifier)
    ]
    
    def update_event(self, inp=-1):
        pass
    
class Classifier:

    def __init__(
        self,
        params: Mapping[str,int|str|float],
        classifier_type:str,
        model = None
    ):
        self.classifier_type = classifier_type
        self.params = params if params else {}
        self.model = model if model else self.initialize_model()

    def initialize_model(self):
        classifiers = {'SVM':SVC(),
                       'Random Forest': RandomForestClassifier(),
                       'Logistic Regression': LogisticRegression()}

        print(self.classifier_type,classifiers[self.classifier_type])
        if self.classifier_type in classifiers.keys():
            return classifiers[self.classifier_type].set_params(**self.params)
    
    def train(self,X_train:np.ndarray,Y_train:np.ndarray):
        self.model.fit(X_train,Y_train)
        
    def predict(self,X_test:np.ndarray):
        return self.model.predict(X_test)
    
    def save_model(self,path:str,filename:str):
        joblib.dump(self.model,path+filename)
    
    def load_model(self,path:str,filename:str):
        return joblib.load(path+filename)