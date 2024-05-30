from __future__ import annotations
from random import randint
from cognixcore.config import NodeConfig
from cognixcore.flow import Flow
from sklearn import datasets
from sklearn.model_selection import train_test_split

from cognixcore import Node, FrameNode, PortConfig
from cognixcore.config.traits import *
from traitsui.api import EnumEditor

import logging
from numbers import Number
from random import randint
class TestStreamNode(FrameNode):
    
    title = "Classification Data Generator"
    version='0.1'
    
    init_outputs = [PortConfig(label='data'), PortConfig(label='class')]

    def __init__(self, params):
        super().__init__(params)
        iris = datasets.load_iris()
        self.X, self.y = iris.data, iris.target

        # self.X_train, self.X_test, self.y_train, self.y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        # print(self.X_train.shape)
    
    def frame_update_event(self) -> bool:
        self.set_output(0, self.X)
        self.set_output(1, self.y)

class TestRandomGeneratorNode(FrameNode):
    
    title = "Random Number Frame Node"
    version = "0.1"
    
    init_outputs = [PortConfig('result')]
    
    def init(self):
        self.current_time = 0
        
    def frame_update_event(self):
        
        self.current_time += self.player.delta_time
        if self.current_time >= 5:
            self.current_time = 0
            self.set_output(0, randint(10, 50))

class TestLogNode(Node):
    """A node for testing log messages!"""
    title = "Logging Test"
    version = '0.1'
    
    class Config(NodeTraitsConfig):
        
        msg_lvl: int = CX_Int(
            logging.NOTSET,
            editor=EnumEditor(
                values={
                    logging.NOTSET: "1:NOTSET",
                    logging.DEBUG: "2:DEBUG",
                    logging.INFO: "3:INFO",
                    logging.WARNING: "4:WARNING",
                    logging.ERROR: "5:ERROR",
                    logging.CRITICAL: "6:CRITICAL",    
                }
            ),
            desc="The logging level."
        )
        # TODO check why the custom style procs changes every time we enter a new letter
        # msg: str = CX_Str('some message', desc="The message to be sent", style="custom")
        msg: str = CX_Str('some message', desc="The message to be sent")
        
    @property
    def config(self) -> TestLogNode.Config:
        return self._config
    
    def start(self):
        self.logger.log(self.config.msg_lvl, self.config.msg) 
    
    def update_event(self, inp=-1):
        self.start()

class TestAddNode(Node):
    """A node for adding stuff together"""
    title = "Add Test Node"
    version = "0.1"
    
    init_inputs = [PortConfig('x'), PortConfig('y')]
    init_outputs = [PortConfig('result')]
        
    def init(self):
        self.values: dict[int, Any] = {}
    
    def update_event(self, inp=-1):
        self.values[inp] = self.input(inp)
        result = 0
        for value in self.values.values():
            result += value
        self.set_output(0, result) 
        
    
    

            

