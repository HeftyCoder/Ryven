from __future__ import annotations
from flask import Flask, request
from flask_restful import Api, Resource, abort, reqparse
from json import dumps, loads
from enum import IntEnum
from concurrent.futures import Future, ThreadPoolExecutor
from ..graph_player import GraphState, GraphActionResponse
from threading import Thread
from waitress import create_server

from typing import TYPE_CHECKING, Any
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
    required=False,
    location='args'
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
    
    def get(self, name: str):
        s = self.session
        if not self.__flow_exists(name):
            abort(HttpStatus.NOT_FOUND.value, message=f"A flow named {name} does not exist")
            return
        
        if not request.args:
            return s.flows[name].data(), HttpStatus.OK.value
        
        args = _flow_get_args.parse_args()
        
        if 'player_action' in args:
            p_action = args['player_action']
            if p_action not in _available_player_actions:
                abort(HttpStatus.BAD_REQUEST.value, message=f"No action {p_action} found. Actions: {_available_player_actions}")
            
            # pass by reference
            result = {
                'response': None,
                'message': None,
                'finished': False
            }
            
            def callback(resp: GraphActionResponse, mess: str):
                result['response'] = resp
                result['message'] = mess
                result['finished'] = True
            
            try:    
                if p_action == 'play':    
                    s.play_flow(name, True, callback)
                elif p_action == 'stop':
                    s.stop_flow(name, callback)
                elif p_action == 'pause':
                    s.pause_flow(name, callback)
                elif p_action=='resume':
                    s.resume_flow(name, callback)
            except Exception as e:
                abort(HttpStatus.INTERNAL_SERVER_ERROR.value, message=f"An exception was called {e} when trying to {p_action} the flow")    
                # Request cannot be completed
            while not result['finished']:
                continue
            
            response: GraphActionResponse = result['response']
            message: str = result['message']
            
            if response != GraphActionResponse.SUCCESS:
                abort(
                    HttpStatus.BAD_REQUEST.value,
                    message=f"ERROR!! Response: {response} Error Message: {message}"
                )
            
            return f"OK!! {message}", HttpStatus.OK.value
    
    def put(self, name: str):
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
            new_title = args['rename'] if 'rename' in args else name
            if not self.__flow_exists(name):
                created = True
                flow: CognixFlow = s.create_flow(new_title, data)
                message += f"FLOW CREATION: {new_title} was created from {data}\n"
            else:
                flow: CognixFlow = s.flows[name]
                if name != new_title:
                    s.rename_flow(flow, new_title)
                    message += f"FLOW RENAME: {name} -> {new_title}\n"
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
    
    def delete(self, name: str):
        if name not in self.session.flows:
            abort(HttpStatus.BAD_REQUEST.value, message=f"Flow named {name} does not exist")
        
        self.session.delete_flow(self.session.flows[name])
        return f"Flow {name} deleted!", HttpStatus.OK.value
            
    def __flow_exists(self, name: str):
        return not self.session.new_flow_title_valid(name)

class CognixRestAPI:
    """This is a class for creating a REST Api to communicate with a CogniX Session."""
    
    def __init__(self, session: CognixSession):
        
        self.session = session
        self.app = Flask(__name__)
        self.api = Api(self.app)
        
        self.api.add_resource(FlowResource, '/flows/<string:name>', resource_class_kwargs={
            'node_session': session
        })
        self.run_task = None
        self._run_thread: Thread = None
        self._server = None
        """Populated only if the REST service starts in another thread"""

    def run(self, 
            host: str | None = None, 
            port: int | None = None,
            debug: bool | None = None,
            load_dotenv: bool = True,
            on_other_thread: bool = False,
            **options: Any
    ):
        if not host:
            host = '127.0.0.1'
        self._server = create_server(self.app, host=host, port = port)
        def _run():
            self._server.run()
            
        if not on_other_thread:
            _run()
        else:
            self._run_thread = Thread(target=_run)
            self._run_thread.setDaemon(True)
            self._run_thread.start()
    
    def shutdown(self):
        self._server.close()