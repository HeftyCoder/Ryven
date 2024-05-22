from __future__ import annotations
from cognixcore.api import Flow, Node, PortConfig
from cognixcore.config import NodeConfig
from cognixcore.config.traits import *
import os
import joblib

from sklearn.model_selection import (
    train_test_split
)



# from Orange.data import Table
# from Orange.classification import SVMLearner, LogisticRegressionLearner
# from Orange.evaluation import CrossValidation, CA, AUC
from cognix.config.traits import NodeTraitsConfig, NodeTraitsGroupConfig, Int, List, Instance
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

    def start(self):
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

    init_outputs = [PortConfig(label='model',allowed_data=SVMClassifier)]
    init_inputs = []

    @property
    def config(self) -> RandomForestNode.Config:
        return self._config

    def start(self):
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

    init_outputs = [PortConfig(label='model',allowed_data=SVMClassifier)]
    init_inputs = []

    @property
    def config(self) -> LogisticRegressionNode.Config:
        return self._config

    def start(self):
        self.params = {
            'penalty' : self.config.penalty,
            'tol' : self.config.tol,
            'C' : self.config.C,
            'solver' : self.config.solver,
            'max_iter' : self.config.max_iter,
        }

        self.model = LogisticRegressionClassifier(self.params)
        print(self.model)
        self.set_output(0, self.model)

class TrainNode(Node):

    title = 'Train Classifier'
    version = '0.1'
    
    class Config(NodeTraitsConfig):
        binary:bool = Bool('binary classification?',desc='if the classification is binary or multiclass')

    init_inputs = [PortConfig(label='data'),PortConfig(label='class'),PortConfig(label='model',allowed_data=SciKitClassifier)]
    init_outputs = [PortConfig(label='model',allowed_data=SciKitClassifier),
                    PortConfig(label='train accuracy'),
                    PortConfig(label='train precision'),
                    PortConfig(label='train recall'),
                    PortConfig(label='train f1_score')]

    @property
    def config(self) -> TrainNode.Config:
        return self._config

    def __init__(self, params):
        super().__init__(params)

        self.data_ = []
        self.data_class = []
        self.model = None
        self.load_model = False

    def update_event(self, inp=-1):

        if inp == 0:self.data_ = self.input(0)
        if inp == 1:self.data_class = self.input(1)
        if inp == 2:self.model:SciKitClassifier = self.input(2)

        if len(self.data_)!=0 and len(self.data_class)!=0 and self.model:
            (
                trained_model,
                train_accuracy,
                train_precision,
                train_precision,
                train_f1
            ) = self.model.train(self.data_, self.data_class, self.config.binary)
            
            self.data_ = []
            self.data_class = []
            # print(trained_model,train_accuracy,train_precision,train_precision,train_f1)
            self.set_output(0, SciKitClassifier(trained_model))
            self.set_output(1, train_accuracy)
            self.set_output(2, train_precision)
            self.set_output(3, train_precision)
            self.set_output(4, train_f1)
            self.model = SciKitClassifier(trained_model)


class TrainTestSplitNode(Node):
    title = 'Train Test Split'
    version = '0.1'

    class Config(NodeTraitsConfig):
        train_test_split:float= CX_Float(0.2,desc='split of data between train and test data')

    init_inputs = [PortConfig(label='data'),PortConfig(label='class')]
    init_outputs = [PortConfig(label='train data'),
                    PortConfig(label='test data'),
                    PortConfig(label='train classes'),
                    PortConfig(label='test classes')]

    @property
    def config(self) -> TrainTestSplitNode.Config:
        return self._config
    
    def __init__(self, params):
        super().__init__(params)

        self.data_ = []
        self.data_class = []

    def update_event(self, inp=-1):

        tt_split = self.config.train_test_split
        print(tt_split)

        if inp == 0:self.data_ = self.input(0)
        if inp == 1:self.data_class = self.input(1)

        if len(self.data_)!=0 and len(self.data_class)!=0:
            print(self.data_.shape)
            print(self.data_class.shape)

            X_train,X_test,Y_train,Y_test = train_test_split(self.data_,self.data_class,test_size=tt_split,random_state=1)
            self.data_class = []
            self.set_output(0, X_train)
            self.set_output(1, X_test)
            self.set_output(2, Y_train)
            self.set_output(3, Y_test)
        else:
            return 

class CrossValidationNode(Node):

    title = 'Cross Validation'
    version = '0.1'
    
    class Config(NodeTraitsConfig):
        folds: int = CX_Int(5,desc='the number of folds to split data for cross validation')
        splitter_type:str = Enum('KFold','Stratified','LeaveOneOut','ShuffleSplit')
        train_test_split:float= CX_Float(0.2,desc='split of data between train and test data')
        binary:bool = Bool(desc='if the classification is binary or multiclass')

    init_inputs = [PortConfig(label='data'),PortConfig(label='class'),PortConfig(label='model',allowed_data=SciKitClassifier)]
    init_outputs = [PortConfig(label='cv accuracy'),
                    PortConfig(label='cv precision'),
                    PortConfig(label='cv recall'),
                    PortConfig(label='cv f1_score')]

    @property
    def config(self) -> CrossValidationNode.Config:
        return self._config

    def __init__(self, params):
        super().__init__(params)

        self.data_ = []
        self.data_class = []
        self.model = None
        self.load_model = False

    def start(self):
        cv_class = next((cls for name, cls in CrossValidation.subclasses.items() if self.config.splitter_type in name), None)
        self.cv_model: CrossValidation = cv_class(
            kfold=self.config.folds, 
            train_test_split = self.config.train_test_split, 
            binary_classification = self.config.binary
        )
        self.cv_model.average_setting()

    def update_event(self, inp=-1):

        folds = self.config.folds
        splitter = self.config.splitter_type
        train_test_split = self.config.train_test_split

        if inp == 0:self.data_ = self.input(0)
        if inp == 1:self.data_class = self.input(1)
        if inp == 2:self.model:SciKitClassifier = self.input(2)

        if len(self.data_)!=0 and len(self.data_class)!=0 and self.model:
            cv_accuracy,cv_precision,cv_precision,cv_f1 = self.cv_model.calculate_cv_score(model=self.model, X=self.data_, Y=self.data_class)
            
            self.data_class = []
            self.set_output(0, cv_accuracy)
            self.set_output(1, cv_precision)
            self.set_output(2, cv_precision)
            self.set_output(3, cv_f1)

class SaveModel(Node):
    title = 'Save Model'
    version = '0.1'

    class Config(NodeTraitsConfig):
        filename: str = CX_String('file name',desc='the name of the model')

    init_inputs = [PortConfig(label='model',allowed_data=SciKitClassifier),PortConfig(label='path')]

    def __init__(self, params):
        super().__init__(params)

        real_path = os.path.realpath(__file__)
        dir_path = os.path.dirname(real_path).split('\\')
        self.path = ""

        for i in range(len(dir_path)-1):
            self.path = self.path + dir_path[i] + "\\"

        self.define_path = False
        self.model = None
        self.file_saved = False
        
    @property
    def config(self) -> SaveModel.Config:
        return self._config

    def on_stop(self):
        self.file_saved = False

    def update_event(self, inp=-1):
        print(self.path)
        path = self.input(1)
        if path:
            self.path = path
        self.filename = self.config.filename
        print(self.filename)
        self.path += self.filename
        self.define_path = True

        if inp == 0:
            self.model:SciKitClassifier = self.input(0)
        
        if self.model and self.define_path and (not self.file_saved):
            self.model.save_model(self.path)
            self.file_saved = True
        


class LoadModel(Node):
    title = 'Load Model'
    version = '0.1'

    class Config(NodeTraitsConfig):
        path: str = CX_String('path file',desc='the path that the model is saved')

    init_inputs = [PortConfig(label='path')]
    init_outputs = [PortConfig(label='model',allowed_data=SciKitClassifier)]

    def __init__(self, flow: Flow):
        super().__init__(flow)

        self.define_path = False
        self.path = None

    @property
    def config(self) -> LoadModel.Config:
        return self._config

    def update_event(self, inp=-1):
        path = self.input(inp)
        if not path:
            path = self.config.path
        self.define_path = True
        self.path = path
        self.model = SciKitClassifier.load_model(self.path)

        print(self.model)

        self.set_output(0, SciKitClassifier(self.model))

class TestNode(Node):
    title = 'Test Classifier'
    version = '0.1'

    init_inputs = [PortConfig(label='data'), PortConfig(label='class'), PortConfig(label='model',allowed_data=SciKitClassifier)]
    init_outputs = [PortConfig(label='test accuracy'),
                    PortConfig(label='test precision'),
                    PortConfig(label='test recall'),
                    PortConfig(label='test f1_score')]
    

    def __init__(self, flow: Flow):
        super().__init__(flow)

        self.data_ = []
        self.data_class = []
        self.model = None
        self.load_model = None

    def update_event(self, inp=-1):

        if inp == 0:self.data_ = self.input(0)
        if inp == 1:self.data_class = self.input(1)
        if inp == 2:self.model:SciKitClassifier = self.input(2)

        print(self.data_,self.data_class)

        if len(self.data_)!=0 and len(self.data_class)!=0 and self.model:
            self.model,test_accuracy,test_precision,test_recall,test_f1 = self.model.test(self.data_,self.data_class)
            self.data_ = []
            self.data_class = []
            self.set_output(0, test_accuracy)
            self.set_output(1, test_precision)
            self.set_output(2, test_precision)
            self.set_output(3, test_f1)
