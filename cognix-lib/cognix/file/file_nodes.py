from Orange.data import Table, Domain
from ryvencore import NodeOutputType, NodeInputType, Data
from ..base_nodes import CognixNode, FrameNode, StartNode
from threading import Thread

class DataTableNode(StartNode):
    
    title = 'Import Feature Data'
    version = '0.1'
    
    init_outputs = [NodeOutputType(label='')]
    
    def __init__(self, params):
        super().__init__(params)
        self.table_data: Table = None
    
    def update_event(self, inp=-1):
        # import sys
        # print(sys.setswitchinterval(0.0005))
        # print(1)
        # a = 0
        # for i in range(100000000):
        #     a = a + 1
        # print(2)
        self.table_data = Table('C:/Users/salok/Desktop/test_classification.csv')
        # print(3)
        self.table_data.domain.class_var = self.table_data.domain['category']
        self.set_output_val(0, Data(self.table_data))
        
class DataSelectionNode(CognixNode):
    
    title = 'Data Selection'
    version = '0.1'
    
    init_inputs = [NodeInputType()]
    init_outputs = [NodeOutputType()]
    
    def __init__(self, params):
        super().__init__(params)
        self.table_data: Table = None
        
    def update_event(self, inp=-1):
        packet = self.input(0)
        if packet is None:
            return
        
        data: Table = packet.payload
        s_features_names = ['bandpower_delta_Fp1', 'bandpower_theta_Fp1', 'bandpower_alpha_Fp1', 'bandpower_beta_Fp1', 'bandpower_gamma_Fp1']
        s_features = [data.domain[var_name] for var_name in s_features_names]
        new_domain = Domain(s_features, data.domain['category'])
        self.table_data = data.transform(new_domain)
        self.set_output_val(0, Data(self.table_data))
        

all_file_nodes = [DataTableNode, DataSelectionNode]