from ryvencore import NodeOutputType, NodeInputType, Data
from ..base_nodes import CognixNode, FrameNode, StartNode

from Orange.data import Table
from Orange.classification import SVMLearner, LogisticRegressionLearner
from Orange.evaluation import CrossValidation, CA, AUC

import traceback

class SVM_Node(CognixNode):
    
    title = 'SVM Classifier'
    version = '0.1'
    
    init_inputs = [NodeInputType()]
    init_outputs = [NodeOutputType()]
    
    def update_event(self, inp=-1):
        packet = self.input(0)
        if not packet:
            return
        svm = SVMLearner()
        self.set_output_val(0, Data(svm))

class LogisticRegressionNode(CognixNode):
    
    title = 'Logistic Regression'
    version = '0.1'
    
    init_inputs = [NodeInputType()]
    init_outputs = [NodeOutputType()]
    
    def update_event(self, inp=-1):
        packet = self.input(0)
        if not packet:
            return
        svm = LogisticRegressionLearner()
        self.set_output_val(0, Data(svm))

class CrossValidationNode(CognixNode):
    
    title = 'Cross Validation'
    version = '0.1'
    
    init_inputs = [NodeInputType(label='data'), NodeInputType(label='classifier')]
    init_outputs = [NodeOutputType(label='model'), NodeOutputType(label = 'ACC'), NodeOutputType(label='AUC')]
    
    def update_event(self, inp=-1):
        print(1)
        data_packet = self.input(0)
        classifier_packet = self.input(1)
        if not data_packet or not classifier_packet:
            return
        
        data = data_packet.payload
        classifier = classifier_packet.payload
        
        if not data or not classifier:
            return
        
        try:
            cv_results = CrossValidation(data, [classifier], k=5)
            accuracy = CA(cv_results)
            auc = AUC(cv_results)
        except Exception as e:
            traceback.print_exc()
            return
        
        self.set_output_val(0, Data(cv_results))
        self.set_output_val(1, Data(accuracy))
        self.set_output_val(2, Data(auc))

all_classification_nodes = [SVM_Node, LogisticRegressionNode, CrossValidationNode]