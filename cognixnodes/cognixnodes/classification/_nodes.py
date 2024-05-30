from __future__ import annotations
from cognixcore.api import Flow, Node, PortConfig
from cognixcore.config import NodeConfig
from cognixcore.config.traits import *
import os
import joblib

from sklearn.model_selection import (
    train_test_split
)

from ..core import Signal,TimeSignal,LabeledSignal,FeatureSignal


# from Orange.data import Table
# from Orange.classification import SVMLearner, LogisticRegressionLearner
# from Orange.evaluation import CrossValidation, CA, AUC
from cognixcore.config.traits import NodeTraitsConfig, NodeTraitsGroupConfig, Int, List, Instance
from .utils.scikit import (
    SVMClassifier,
    SciKitClassifier,
    RandomForestClassifier,
    LogisticRegressionClassifier,
    CrossValidation,
    KFoldClass,
    LeaveOneOutClass,
    ShuffleSplit,
    StratifiedKFoldClass)

from .utils.core import BasePredictor

class ModelNode(Node):
    """A node that outputs a model"""
    
    def __init__(self, flow: Flow, config: NodeConfig = None):
        super().__init__(flow, config)
        self.model = None
    
    def update_event(self, inp=-1):
        if self.model:
            self.set_output(0, self.model)

class SVMNode(ModelNode):
    title = 'SVM Classifier'
    version = '0.1'

    class Config(NodeTraitsConfig):
        C : float = CX_Float(1.0)
        degree: int = CX_Int(3)
        kernel: str = Enum('linear','poly','rbf','sigmoid','precomputed')
        gamma: str = Enum('scale','auto')
        gamma_float: float = CX_Float(0.0)
        selection_of_gamma: bool = Bool('gamma value from choices?')

    init_outputs = [PortConfig(label='model',allowed_data=SVMClassifier)]
    init_inputs = []

    @property
    def config(self) -> SVMNode.Config:
        return self._config

    def init(self):
        self.params = {'C':self.config.C,
                        'degree':self.config.degree,
                        'kernel':self.config.kernel,
                        'gamma':self.config.gamma if self.config.selection_of_gamma else self.config.gamma_float
                        }
        self.model = SVMClassifier(self.params)
        print(self.model)
        self.set_output(0, self.model)
    
class RandomForestNode(ModelNode):
    title = 'Random Forest Classifier'
    version = '0.1'

    class Config(NodeTraitsConfig):
        n_estimators : int = CX_Int(100,desc='the number of trees in the forest')
        criterion: str = Enum('gini','entropy','log loss',desc='the number of trees in the forest')
        max_depth: int = CX_Int(0,desc='the maximum depth of the tree')
        min_samples_split: int|float = CX_Int(2,desc='the minimum number of samples required to split an internal node')
        min_samples_leaf: int|float = CX_Int(1,desc='the minimum number of samples required to be at a leaf node')
        max_features: str = Enum('sqrt','log2',0,desc='the number of features to consider when looking for the best split')       
        max_leaf_nodes: int = CX_Int(0,desc='grow trees with max_leaf_nodes in best-first fashion')

    init_outputs = [PortConfig(label='model',allowed_data=RandomForestClassifier)]
    init_inputs = []

    @property
    def config(self) -> RandomForestNode.Config:
        return self._config

    def init(self):
        self.params = {
            'n_estimators': self.config.n_estimators,
            'criterion':self.config.criterion,
            'max_depth':self.config.max_depth if self.config.max_depth !=0 else None,
            'min_samples_split':self.config.min_samples_split,
            'min_samples_leaf':self.config.min_samples_leaf,
            'max_features':self.config.max_features if self.config.max_features !=0 else None,
            'max_leaf_nodes':self.config.max_leaf_nodes if self.config.max_leaf_nodes !=0 else None,
        }

        self.model =RandomForestClassifier(self.params)
        print(self.model)
        self.set_output(0, self.model)

class LogisticRegressionNode(ModelNode):
    title = 'Logistic Regression Classifier'
    version = '0.1'

    class Config(NodeTraitsConfig):
        penalty: str = Enum('l1','l2','elasticnet','None',desc='specify the norm of the penalty')
        tol:float = CX_Float(1e-4,desc='tolerance for stopping criteria')
        C:float = CX_Float(1.0,desc='inverse of regularization strength; must be a positive float')
        solver:str = Enum('lbfgs','liblinear','newton-cg','newton-cholesky','sag','saga',desc='algorithm to use in the optimization problem')
        max_iter:int = CX_Int(100,desc='maximum number of iterations taken for the solvers to converge')

    init_outputs = [PortConfig(label='model')]
    init_inputs = []

    @property
    def config(self) -> LogisticRegressionNode.Config:
        return self._config

    def init(self):
        self.params = {
            'penalty' : self.config.penalty,
            'tol' : self.config.tol,
            'C' : self.config.C,
            'solver' : self.config.solver,
            'max_iter' : self.config.max_iter,
        }

        self.model = LogisticRegressionClassifier(self.params)
        self.set_output(0, self.model)

class TrainNode(Node):

    title = 'Train Classifier'
    version = '0.1'
    
    class Config(NodeTraitsConfig):
        binary:bool = Bool('binary classification?',desc='if the classification is binary or multiclass')

    init_inputs = [PortConfig(label='data',allowed_data=FeatureSignal),PortConfig(label='model')]
    init_outputs = [PortConfig(label='model'),
                    PortConfig(label='train accuracy'),
                    PortConfig(label='train precision'),
                    PortConfig(label='train recall'),
                    PortConfig(label='train f1_score')]

    @property
    def config(self) -> TrainNode.Config:
        return self._config

    def init(self):

        self.signal = None
        self.classifier = None
        self.load_model = False
        self.model_exists = False

    def update_event(self, inp=-1):

        if inp == 0:self.signal = self.input(inp)
        if inp == 1 and not self.model_exists:self.classifier:SciKitClassifier = self.input(inp)

        if self.signal and self.classifier:
            self.model_exists = True

            (
                trained_model,
                train_accuracy,
                train_precision,
                train_precision,
                train_f1
            ) = self.classifier.train(self.signal, self.config.binary)
            
            self.classifier = trained_model
            
            # print(trained_model,train_accuracy,train_precision,train_precision,train_f1)
            self.set_output(0, self.classifier)
            self.set_output(1, train_accuracy)
            self.set_output(2, train_precision)
            self.set_output(3, train_precision)
            self.set_output(4, train_f1)
            


class TrainTestSplitNode(Node):
    title = 'Train Test Split'
    version = '0.1'

    class Config(NodeTraitsConfig):
        train_test_split:float= CX_Float(0.2,desc='split of data between train and test data')

    init_inputs = [PortConfig(label='data',allowed_data=FeatureSignal)]
    init_outputs = [PortConfig(label='train data',allowed_data=FeatureSignal),
                    PortConfig(label='test data',allowed_data=FeatureSignal)]

    @property
    def config(self) -> TrainTestSplitNode.Config:
        return self._config
    
    def init(self):

        self.tt_split = self.config.train_test_split
        self.model = SciKitClassifier(model = None)

    def update_event(self, inp=-1):

        signal = self.input(inp)
        
        if signal:

            train_signal,test_signal = self.model.split_data(signal,test_size=self.tt_split,random_state=1)
            self.set_output(0, train_signal)
            self.set_output(1, test_signal)


class CrossValidationNode(Node):

    title = 'Cross Validation'
    version = '0.1'
    
    class Config(NodeTraitsConfig):
        folds: int = CX_Int(5,desc='the number of folds to split data for cross validation')
        splitter_type:str = Enum('KFold','Stratified','LeaveOneOut','ShuffleSplit')
        train_test_split:float= CX_Float(0.2,desc='split of data between train and test data')
        binary:bool = Bool(desc='if the classification is binary or multiclass')

    init_inputs = [PortConfig(label='data',allowed_data=FeatureSignal),PortConfig(label='model')]
    init_outputs = [PortConfig(label='cv accuracy'),
                    PortConfig(label='cv precision'),
                    PortConfig(label='cv recall'),
                    PortConfig(label='cv f1_score')]

    @property
    def config(self) -> CrossValidationNode.Config:
        return self._config

    def init(self):

        self.signal = None
        self.model = None
        self.load_model = False

        cv_class = next((cls for name, cls in CrossValidation.subclasses.items() if self.config.splitter_type in name), None)
        self.cv_model: CrossValidation = cv_class(
            kfold=self.config.folds, 
            train_test_split = self.config.train_test_split, 
            binary_classification = self.config.binary
        )
        print(self.cv_model)
        
        self.cv_model.set_average_setting()

    def update_event(self, inp=-1):

        if inp == 0:self.signal = self.input(0)
        if inp == 1:self.model:SciKitClassifier = self.input(2)

        if self.signal and self.model:

            cv_accuracy,cv_precision,cv_precision,cv_f1 = self.cv_model.calculate_cv_score(model=self.model,f_signal=self.signal)
            
            self.set_output(0, cv_accuracy)
            self.set_output(1, cv_precision)
            self.set_output(2, cv_precision)
            self.set_output(3, cv_f1)

class SaveModel(Node):
    title = 'Save Model'
    version = '0.1'

    class Config(NodeTraitsConfig):
        filename: str = CX_String('file name',desc='the name of the model')

    init_inputs = [PortConfig(label='model'),PortConfig(label='path')]

    def init(self):

        real_path = os.path.realpath(__file__)
        dir_path = os.path.dirname(real_path).split('\\')
        self.path = ""

        for i in range(len(dir_path)-1):
            self.path = self.path + dir_path[i] + "\\"

        self.define_path = False
        self.model = None
        self.other_path = None
        self.filename = self.config.filename
        
    @property
    def config(self) -> SaveModel.Config:
        return self._config

    def stop(self):
        if self.model:
            self.model.save_model(self.path+self.filename+".joblib")

    def update_event(self, inp=-1):
        print(self.path)
            
        if inp == 0:self.model:SciKitClassifier = self.input(0)
        if inp == 1:self.other_path = self.input(1) 
        if self.other_path:self.path = self.other_path
        
            
class LoadModel(Node):
    title = 'Load Model'
    version = '0.1'

    class Config(NodeTraitsConfig):
        f: str = File('Some path',desc='path of the model to import')

    init_outputs = [PortConfig(label='model')]

    @property
    def config(self) -> LoadModel.Config:
        return self._config
    
    def init(self):
        self.path_file = self.config.f
        self.define_model = False

    def update_event(self, inp=-1):
        if not self.define_model:
            self.model = SciKitClassifier.load_model(self.path+".joblib")
            print(self.model)
            self.set_output(0, self.model)
            self.define_model = True

class TestNode(Node):
    title = 'Test Classifier'
    version = '0.1'

    init_inputs = [PortConfig(label='data',allowed_data=FeatureSignal), PortConfig(label='model')]
    init_outputs = [PortConfig(label='test accuracy'),
                    PortConfig(label='test precision'),
                    PortConfig(label='test recall'),
                    PortConfig(label='test f1_score')]
    

    def init(self):

        self.signal = None
        self.model = None
        self.load_model = None

    def update_event(self, inp=-1):

        if inp == 0:self.signal = self.input(0)
        if inp == 1:self.model:SciKitClassifier = self.input(2)

        if self.signal and self.model:
            self.model,test_accuracy,test_precision,test_recall,test_f1 = self.model.test(f_signal_test=self.signal)
            self.set_output(0, test_accuracy)
            self.set_output(1, test_precision)
            self.set_output(2, test_recall)
            self.set_output(3, test_f1)
