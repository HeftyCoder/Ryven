"""Defines the base class fot classifiers of sklearn"""
from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
import numpy as np
import joblib
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression

class Classifier:

    def __init__(
        self,
        params: Mapping[str,int|str|float],
        classifier_type:str
    ):
        self.classifier_type = classifier_type
        self.params = params if params else {}
        self.model = self.initialize_model()

    def initialize_model(self):
        classifiers = {'SVM':SVC(**self.params),
                       'Random Forest': RandomForestClassifier(**self.params),
                       'Logistic Regression': LogisticRegression(**self.params)}

        if self.classifier_type in classifiers.keys():
            return classifiers[self.classifier_type]
        else:
            raise ValueError(f'Unsupported Classifier')
    
    def train(self,X_train:np.ndarray,Y_train:np.ndarray):
        self.model.fit(X_train,Y_train)
        
    def predict(self,X_test:np.ndarray):
        return self.model.predict(X_test)
    
    def save_model(self,path:str,filename:str):
        joblib.dump(self.model,path+filename)
    
    def load_model(self,path:str,filename:str):
        self.model = joblib.load(path+filename)