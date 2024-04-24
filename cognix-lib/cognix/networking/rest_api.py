from flask import Flask
from flask_restful import Api, Resource, abort, reqparse
from json import dumps, loads
from enum import IntEnum

from ..graph_player import GraphState, GraphActionResponse

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..session import CognixSession
    from ..flow import CognixFlow

#   GET ARGS
_flow_get_args = reqparse.RequestParser()
_available_player_actions = {'play', 'stop', 'pause', 'resume'}
_flow_get_args.add_argument(
    "player_action", 
    type=str, 
    help=f"Changes the state of the player. Available: {_available_player_actions}", 
    required=False
)
#   PUT ARGS
_flow_put_args = reqparse.RequestParser()
_flow_put_args.add_argument("data", type=str, help="Data in the form of json to load a flow", required=False)
_flow_put_args.add_argument(
    "rename", 
    type=str, 
    help="A rename of the title. This will change the current URI path", 
    required=False
)
_flow_put_args.add_argument("fps", type=int, help="The fps for the Graph Player to aim for", required=False)


class HttpStatus(IntEnum):
    OK = 200
    CREATED = 201
    BAD_REQUEST = 400
    NOT_FOUND = 404
    INTERNAL_SERVER_ERROR = 500


class FlowResource(Resource):
    
    def __init__(self, node_session: CognixSession):
        super().__init__()
        self.session = node_session
    
    def get(self, title: str):
        s = self.session
        if self.__flow_exists(title):
            abort(HttpStatus.NOT_FOUND.value, message=f"A flow named {title} does not exist")
            return
        
        args = _flow_get_args.parse_args()
        if not args:
            return dumps(s.flows[title].data()), HttpStatus.OK.value
        
        if 'player_action' in args:
            p_action = args['player_action']
            if p_action not in _available_player_actions:
                abort(HttpStatus.BAD_REQUEST.value, message=f"No action {p_action} found. Actions: {_available_player_actions}")
            
            response, message, finished = None, None, False
            def callback(resp: GraphActionResponse, mess: str):
                response = resp
                message = mess
                finished = True
            
            try:    
                if p_action == 'play':    
                    s.play_flow(title, True, callback)
                elif p_action == 'stop':
                    s.stop_flow(title, True, callback)
                elif p_action == 'pause':
                    s.pause_flow(title, True, callback)
                else:
                    s.resume_flow(title, True, callback)
                
                # Request cannot be completed
                while not finished:
                    continue
                
                if response != GraphActionResponse.SUCCESS:
                    abort(
                        HttpStatus.BAD_REQUEST.value,
                        message=f"ERROR!!\nResponse: {response}\nError Message: {message}"
                    )
                
                return f"OK!! {message}", HttpStatus.OK.value
            except Exception as e:
                abort(HttpStatus.INTERNAL_SERVER_ERROR.value, f"An exception was called {e} when trying to {p_action} the flow")    
    
    def put(self, title: str):
        args = _flow_put_args.parse_args()
        s = self.session
        
        data = args.get('data')
        if data:
            try:
                data = loads(data)
            except:
                abort(HttpStatus.BAD_REQUEST.value, message=f"Data given is not a JSON compliant dict")
        
        created = False
        flow: CognixFlow = None
        # Handle creation or rename
        message = ''
        
        try:
            new_title = args['rename'] if 'rename' in args else title
            if not self.__flow_exists(title):
                created = True
                flow: CognixFlow = s.create_flow(new_title, data)
                message += f"FLOW CREATION: {new_title} was created from {data}\n"
            else:
                flow: CognixFlow = s.flows[title]
                if title != new_title:
                    s.rename_flow(flow, new_title)
                    message += f"FLOW RENAME: {title} -> {new_title}\n"
                if data:
                    flow.load(data)
                    message += f"FLOW DATA RELOAD"
                    
            fps = args.get('fps')
            if fps:
                old_fps = flow.player.graph_time.frames
                flow.player.set_frames(fps)
                message += f"FLOW FPS CHANGE: {old_fps} -> {fps}"
        except Exception as e:
            abort(HttpStatus.BAD_REQUEST.value, message=f"{e}")
        
        status = HttpStatus.CREATED if created else HttpStatus.OK
        return message, status.value
    
    def delete(self, title: str):
        if title not in self.session.flows:
            abort(HttpStatus.BAD_REQUEST.value, f"Flow named {title} does not exist")
        
        self.session.delete_flow(self.session.flows[title])
        return f"Flow {title} deleted!", HttpStatus.OK.value
            
    def __flow_exists(self, title: str):
        return not self.session.new_flow_title_valid(title)

class CognixRestAPI:
    """This is a class for creating a REST Api to communicate with a CogniX Session."""
    pass