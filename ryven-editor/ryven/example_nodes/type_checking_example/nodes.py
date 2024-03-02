from ryvencore import Node, NodeInputType, NodeOutputType
from ryvencore.data.built_in import *
from ryvencore.data.built_in.collections.abc import *
from ryven.node_env import export_nodes
from numbers import Number
from time import sleep
from ryvencore import ProgressState
from cognix.base_nodes import CognixNode, StartNode

class Producer(StartNode):
    
    title = 'Producer'
    
    init_outputs = [
        NodeOutputType('list', allowed_data=ListData),
        NodeOutputType('dict', allowed_data=DictData),
        NodeOutputType('int', allowed_data=IntegerData),
        NodeOutputType('complex', allowed_data=ComplexData),
        NodeOutputType('all'),
        NodeOutputType('set', allowed_data=SetData)
    ]
    
    def update_event(self, inp=-1):

        try:
            
            progress_state = ProgressState(1, 0)
            self.progress = progress_state
            
            self.set_output_val(0, ListData([1, 2, 3])) # a list of data produced

            self.set_progress_value(0.2, 'Loading Values')
            sleep(1)
            
            self.set_output_val(1, 
                DictData(
                    {
                        'george': 2,
                        'john': 3,
                        'damon': 4,
                    }
                )
            )

            self.set_progress_value(0.5, 'Setting numbers')
            sleep(3)
            
            self.set_output_val(2, IntegerData(23))

            self.set_output_val(3, ComplexData(2+3j))

            self.set_output_val(4, StringData('custom info'))
            
            self.set_progress_value(0.9, 'This is my way!')
            sleep(2)

            self.set_output_val(5, SetData({23, 4, 1, 2}))
            
            self.set_progress_value(-1, "Nothing to see here!")
            sleep(5)
            
            self.progress = None
        
        except Exception:
            import traceback
            traceback.print_exc()
            self.progress = None
        
class Consumer(CognixNode):
    
    title = 'Consumer'
    
    init_inputs = [
        NodeInputType('sequence', allowed_data=SequenceData),
        NodeInputType('map', allowed_data=MappingData),
        NodeInputType('int', allowed_data=IntegerData),
        NodeInputType('number', allowed_data=NumberData),
        NodeInputType('all'),
        NodeInputType('set', allowed_data=SetData_ABC)
    ]
    
    def update_event(self, inp=-1):
        
        seq: Sequence = self.input_payload(0)
        map: Mapping = self.input_payload(1)
        int_value: int = self.input_payload(2)
        number_value: Number = self.input_payload(3)
        custom_data = self.input_payload(4)
        set_data: Set = self.input_payload(5)
        
        # at this point, use the data received from the ports
        # to do whatever we like

export_nodes([Producer, Consumer, ])