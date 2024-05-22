"""Defines the base oof scikit classifiers and the classifiers themselves"""
from __future__ import annotations
from abc import ABC, abstractmethod
from .core import BasePredictor,CrossValidation
import numpy as np
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
)

from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import (
    cross_val_score,
    KFold,
    StratifiedKFold,
    LeaveOneOut,
    ShuffleSplit,
    train_test_split
)
import joblib

##### from .core import SignalInfo,Signal
### X_train and Y_train are to change to just a Signal object



class SciKitClassifier(BasePredictor):
    
    def __init__(self,model):
        self.model = model

    def train(self,X_train:np.ndarray,Y_train:np.ndarray,binary_classification:bool):

        average_setting = 'binary'
        if not binary_classification:
            average_setting = 'macro'

        self.model.fit(X_train,Y_train)

        y_pred = self.model.predict(X_train)
        print(y_pred)

        train_accuracy = accuracy_score(Y_train,y_pred)
        train_precision = precision_score(Y_train,y_pred,average=average_setting)
        train_recall = recall_score(Y_train,y_pred,average=average_setting)
        train_f1 = f1_score(Y_train,y_pred,average=average_setting)
        print(train_accuracy,train_precision,train_recall,train_f1)
        return self.model,train_accuracy,train_precision,train_recall,train_f1
    
    def test(self,X_test:np.ndarray,Y_test:np.ndarray):

        y_pred = self.model.predict(X_test)

        test_accuracy = accuracy_score(Y_test,y_pred)
        test_precision = precision_score(Y_test,y_pred)
        test_recall = recall_score(Y_test,y_pred)
        test_f1 = f1_score(Y_test,y_pred)
        print(test_accuracy,test_precision,test_recall,test_f1)
        return test_accuracy,test_precision,test_recall,test_f1

    def split_data(self,X:np.ndarray,Y:np.ndarray,test_size:float):

        X_train,X_test,Y_train,Y_test = train_test_split(X,Y,test_size,random_state=1)

        return X_train,X_test,Y_train,Y_test
      
    def save_model(self,path:str):
        joblib.dump(self.model,filename=path)

    def load_model(self,path:str):
        return joblib.load(path)   

class SVMClassifier(SciKitClassifier):

    def __init__(self,params:dict):
        super().__init__(model = SVC(**params))
        
class RandomForestClassifier(SciKitClassifier):

    def __init__(self,params:dict):
        super().__init__(model = RandomForestClassifier(**params))
        
class LogisticRegressionClassifier(SciKitClassifier):

    def __init__(self,params:dict):
        super().__init__(model = LogisticRegression(**params))
   
   
class CrossValidation:
    
    subclasses = {}
    
    def __init_subclass__(cls,**kwargs):
        super().__init_subclass__(**kwargs)
        cls.subclasses[cls.__name__] = cls

    def __init__(self,kfold:int,train_test_split:float,binary_classification:bool):
        self.kfold = kfold
        self.train_test_split = train_test_split
        self.binary_classification = binary_classification
        self.average_setting = ''
        self.cv_model = None

    def set_average_setting(self):
        if not self.binary_classification:
            self.average_setting = '_macro'
        
    def calculate_cv_score(self,model,X,Y):
        cv_accuracy = cross_val_score(model,X,Y,cv=self.cv_model,scoring='accuracy').mean()
        cv_precision = cross_val_score(model,X,Y,cv=self.cv_model,scoring=f'precision{self.average_setting}').mean()
        cv_recall = cross_val_score(model,X,Y,cv=self.cv_model,scoring=f'recall{self.average_setting}').mean()
        cv_f1 = cross_val_score(model,X,Y,cv=self.cv_model,scoring=f'f1{self.average_setting}').mean()

        return cv_accuracy,cv_precision,cv_recall,cv_f1
           

class KFoldClass(CrossValidation):
    
    def __init__(self,kfold:int,train_test_split:float,binary_classification:bool):
        super().__init__(kfold,train_test_split, binary_classification)
        self.cv_model = KFold(n_splits=kfold)
    
class StratifiedKFoldClass(CrossValidation):
    
    def __init__(self,kfold:int,train_test_split:float,binary_classification:bool):
        super().__init__(kfold,train_test_split, binary_classification)
        self.cv_model = StratifiedKFold(n_splits=kfold)
    
class LeaveOneOutClass(CrossValidation):
    
    def __init__(self,kfold:int,train_test_split:float,binary_classification:bool):
        super().__init__(kfold,train_test_split, binary_classification)
        self.cv_model = LeaveOneOut()
    
class ShuffleSplitClass(CrossValidation):
    
    def __init__(self,kfold:int,train_test_split:float,binary_classification:bool):
        super().__init__(kfold,train_test_split, binary_classification)
        self.cv_model = ShuffleSplit(train_size=1-train_test_split,test_size=train_test_split,n_splits=kfold)
    