from ryvencore import Data,PortConfig
from cognix.api import CognixNode
from __future__ import annotations

# from Orange.data import Table
# from Orange.classification import SVMLearner, LogisticRegressionLearner
# from Orange.evaluation import CrossValidation, CA, AUC
from cognix.config.traits import NodeTraitsConfig, NodeTraitsGroupConfig, Int, List, Instance
from .utils_for_classification.core import Classifier
from cognix.config.traits import *

import traceback

class SVMTrainingNode(CognixNode):
    title = 'SVM Traning Clasifier'
    version = '0.1'

    class Config(NodeTraitsConfig):
        C : float = CX_Float(1.0)
        degree: int = CX_Int(3)
        kernel: str = Enum('linear','poly','rbf','sigmoid','precomputed')
        gamma: str = Enum('scale','auto')
        gamma_float: float = CX_Float(0.0)
        selection_of_gamma: bool = Bool('gamma value from choices?')

    init_inputs = [PortConfig(label = 'data'),PortConfig(label='class')]
    init_outputs = [PortConfig(label = 'model')]

    @property
    def config(self) -> SVMTrainingNode.Config:
        return self._config
    
    def on_start(self):
        self.params = {'C':self._config.C,
                       'degree':self._config.degree,
                       'kernel':self._config.kernel,
                       'gamma':self._config.gamma if self._config.selection_of_gamma else self._config.gamma_float
                       }
        self.classifier = Classifier(self.params,classifier_type='SVM')

    def update_event(self, inp=-1):

        x = self.input_payload(0)
        y = self.input_payload(1)
        self.classifier.train(X_train=x,Y_train=y)

    def on_stop(self):
        self.set_output_val(0,Data(self.classifier.model))
    
        
    




# class SVM_Node(CognixNode):
    
#     class Config(NodeTraitsGroupConfig):
        
#         class SubConfig(NodeTraitsConfig):
#             s = List()
#             d = Int(15)
        
#         george = Instance(SubConfig, args=())
#         john = Instance(SubConfig, args=())
    
#     config_type = Config
    
#     title = 'SVM Classifier'
#     version = '0.1'
    
#     init_inputs = [PortConfig()]
#     init_outputs = [PortConfig()]
    
#     def update_event(self, inp=-1):
#         packet = self.input(0)
#         if not packet:
#             return
#         svm = SVMLearner()
#         self.set_output_val(0, Data(svm))

# class LogisticRegressionNode(CognixNode):
    
#     title = 'Logistic Regression'
#     version = '0.1'
    
#     init_inputs = [PortConfig()]
#     init_outputs = [PortConfig()]
    
#     def update_event(self, inp=-1):
#         packet = self.input(0)
#         if not packet:
#             return
#         reg_learner = LogisticRegressionLearner()
#         self.set_output_val(0, Data(reg_learner))

# class CrossValidationNode(CognixNode):
    
#     title = 'Cross Validation'
#     version = '0.1'
    
#     init_inputs = [PortConfig(label='data'), PortConfig(label='classifier')]
#     init_outputs = [PortConfig(label='model'), PortConfig(label = 'ACC'), PortConfig(label='AUC')]
    
#     def update_event(self, inp=-1):
#         data_packet = self.input(0)
#         classifier_packet = self.input(1)
#         if not data_packet or not classifier_packet:
#             return
        
#         data = data_packet.payload
#         classifier = classifier_packet.payload
        
#         if not data or not classifier:
#             return
        
#         try:
#             cv_results = CrossValidation(data, [classifier], k=5)
#             accuracy = CA(cv_results)
#             auc = AUC(cv_results)
#         except Exception as e:
#             traceback.print_exc()
#             return
        
#         self.set_output_val(0, Data(cv_results))
#         self.set_output_val(1, Data(accuracy))
#         self.set_output_val(2, Data(auc))