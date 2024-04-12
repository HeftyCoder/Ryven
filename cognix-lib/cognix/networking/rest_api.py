from flask import Flask
from flask_restful import Api, Resource, abort
from ryvencore import Session

class FlowResource(Resource):
    
    def __init__(self, node_session: Session):
        super().__init__()
        self.node_session = node_session
    
    def get(self, title: str):
        s = self.node_session
        if self.__flow_exists(title):
            abort(404, message=f"A flow titled {title} does not exist")
        else:
            return s.title_to_flow_dict[title].data(), 200
    
    def post(self, title: str):
        pass
    
    def delete(self, title: str):
        pass
    
    def __flow_exists(self, title: str):
        return title in self.node_session.title_to_flow_dict

class RyvenRestAPI:
    """This is a class for creating a REST Api for communicating with a Ryven Session."""
    pass