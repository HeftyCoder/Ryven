from cognix.nodes import CognixNode, FrameNode
from ryvencore import PortConfig, Data
from random import randint
from sklearn import datasets
from sklearn.model_selection import train_test_split
import time

class TestStreamNode(FrameNode):
    
    title = "Random Data Generator For classification"
    version='0.1'
    
    init_outputs = [PortConfig(label='data'),PortConfig(label='class')]

    def __init__(self, params):
        super().__init__(params)
        iris = datasets.load_iris()
        self.X,self.y = iris.data,iris.target

        # self.X_train, self.X_test, self.y_train, self.y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        # print(self.X_train.shape)
    
    def frame_update_event(self) -> bool:
        self.set_output_val(0, Data(self.X))
        self.set_output_val(1, Data(self.y))
        time.sleep(5)

            

