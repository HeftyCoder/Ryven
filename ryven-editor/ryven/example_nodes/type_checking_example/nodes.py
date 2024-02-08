from ryvencore import Node, NodeInputType, NodeOutputType
from ryvencore.data.built_in import *
from ryvencore.data.built_in.collections.abc import *
from ryven.node_env import export_nodes

class Producer(Node):
    
    title = 'Producer'
    
    init_outputs = [
        NodeOutputType('list', allowed_data=ListData),
        NodeOutputType('dict', allowed_data=DictData),
        NodeOutputType('int', allowed_data=IntegerData),
        NodeOutputType('complex', allowed_data=ComplexData),
        NodeOutputType('all'),
        NodeOutputType('set', allowed_data=SetData)
    ]
    
    
class Consumer(Node):
    
    title = 'Consumer'
    
    init_inputs = [
        NodeInputType('sequence', allowed_data=SequenceData),
        NodeInputType('map', allowed_data=MappingData),
        NodeInputType('int', allowed_data=IntegerData),
        NodeInputType('number', allowed_data=NumberData),
        NodeInputType('all'),
        NodeInputType('set', allowed_data=SetData_ABC)
    ]
    

export_nodes([Producer, Consumer, ])