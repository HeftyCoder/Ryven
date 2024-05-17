from __future__ import annotations
from flask import Flask, request
from flask_restful import Api, Resource, abort, reqparse
from json import dumps, loads

from enum import IntEnum
from threading import Thread
from ryvencore.addons.variables import VarsAddon
from fastapi import FastAPI
from uvicorn import Server, Config

from ..graph_player import GraphState, GraphActionResponse
from ..models import FlowModel

from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    from ..session import CognixSession
    from ..flow import CognixFlow

class HttpStatus(IntEnum):
    OK = 200
    CREATED = 201
    BAD_REQUEST = 400
    NOT_FOUND = 404
    INTERNAL_SERVER_ERROR = 500

class CognixRestAPI:
    """Handles FastAPI app creation"""
    
    message = 'msg'
    error = 'error'
    
    def __init__(self, session: CognixSession):
        self._session = session
        self._vars_addon: VarsAddon = self.session.addons[VarsAddon.addon_name()]
        self._app = FastAPI()
    
    @property
    def session(self):
        return self._session
    
    @property
    def vars_addon(self):
        return self._vars_addon
    
    @property
    def app(self):
        return self._app
    
    def flow_exists(self, name: str):
        return not self.session.new_flow_title_valid(name)
    
    def var_exists(self, flow_name: str, name: str):
        flow = self.session.flows[flow_name]
        return self.vars_addon.var_exists(flow, name)
    
    def create_routes(self):
        
        @self.app.get("/")
        def read_root():
            return {
                self.message: "Welcome to the REST API for your Cognix Session! You can browse the docs via /docs or /redocs"
            }
        
        @self.app.get("/flows/")
        def get_flows() -> dict[str, FlowModel]:
            return {
                self.message:{
                    flow_name: FlowModel(**flow.data()) 
                    for flow_name, flow in self.session.flows.items()
                }
            }
        
        @self.app.get("/flows/{flow_name}")
        def get_flow(flow_name: str) -> FlowModel:
            
            if not self.flow_exists(flow_name):
                return None
            flow_data = self.session.flows[flow_name].data()
            return FlowModel(**flow_data)  
    
class CognixResource(Resource):
    
    def __init__(self, node_session: CognixSession):
        super().__init__()
        self.session = node_session
        self.vars_addon: VarsAddon = self.session.addons[VarsAddon.addon_name()]
    
    def flow_exists(self, name: str):
        return not self.session.new_flow_title_valid(name)
    
    def var_exists(self, flow_name: str, name: str):
        flow = self.session.flows[flow_name]
        return self.vars_addon.var_exists(flow, name)
        
class FlowResource(CognixResource):
    
    _get_args = reqparse.RequestParser()
    _available_player_actions = {'play', 'stop', 'pause', 'resume'}
    _get_args.add_argument(
        "player_action", 
        type=str, 
        help=f"Changes the state of the player. Available: {_available_player_actions}", 
        required=False,
        location='args'
    )
    
    _put_args = reqparse.RequestParser()
    _put_args.add_argument("data", type=str, help="Data in the form of json to load a flow", required=False)
    _put_args.add_argument(
        "rename", 
        type=str, 
        help="A rename of the title. This will change the current URI path", 
        required=False
    )
    _put_args.add_argument("fps", type=int, help="The fps for the Graph Player to aim for", required=False)
    
    def get(self, flow_name: str):
        s = self.session
        if not self.flow_exists(flow_name):
            abort(HttpStatus.NOT_FOUND.value, message=f"Flow {flow_name} does not exist")
        
        if not request.args:
            return s.flows[flow_name].data(), HttpStatus.OK.value
        
        args = self._get_args.parse_args()
        
        if 'player_action' in args:
            p_action = args['player_action']
            if p_action not in self._available_player_actions:
                abort(HttpStatus.BAD_REQUEST.value, message=f"No action {p_action} found. Actions: {self._available_player_actions}")
            
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
                    s.play_flow(flow_name, True, callback)
                elif p_action == 'stop':
                    s.stop_flow(flow_name, callback)
                elif p_action == 'pause':
                    s.pause_flow(flow_name, callback)
                elif p_action=='resume':
                    s.resume_flow(flow_name, callback)
            except Exception as e:
                abort(HttpStatus.INTERNAL_SERVER_ERROR.value, message=f"An exception was called when trying to {p_action} the flow.\n{e}")    
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
    
    def put(self, flow_name: str):
        args = self._put_args.parse_args()
        s = self.session
        
        data = args.get('data')
        if data:
            try:
                data = loads(data)
            except:
                abort(HttpStatus.BAD_REQUEST.value, message=f"Data given is not a JSON compatible dict")
        
        created = False
        flow: CognixFlow = None
        # Handle creation or rename
        message = ''
        
        try:
            new_title = args['rename'] if 'rename' in args else flow_name
            if not self.flow_exists(flow_name):
                created = True
                flow: CognixFlow = s.create_flow(new_title, data)
                message += f"FLOW CREATION: {new_title} was created from {data}\n"
            else:
                flow: CognixFlow = s.flows[flow_name]
                if flow_name != new_title:
                    s.rename_flow(flow, new_title)
                    message += f"FLOW RENAME: {flow_name} -> {new_title}\n"
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
    
    def delete(self, flow_name: str):
        if flow_name not in self.session.flows:
            abort(HttpStatus.BAD_REQUEST.value, message=f"Flow: {flow_name} does not exist")
        
        self.session.delete_flow(self.session.flows[flow_name])
        return f"Flow {flow_name} deleted!", HttpStatus.OK.value

class VariableResource(CognixResource):
    
    _variable_put_args = reqparse.RequestParser()
    _variable_put_args.add_argument("data", type=str, help="Data in the form of json to load a flow", required=False)
    _variable_put_args.add_argument(
        "rename", 
        type=str, 
        help="A rename of the title. This will change the current URI path", 
        required=False
    )
    _variable_put_args.add_argument("fps", type=int, help="The fps for the Graph Player to aim for", required=False)
    
    def get(self, flow_name: str, variable_name: str):
        
        if not self.flow_exists(flow_name):
            abort(HttpStatus.NOT_FOUND.value, message=f"Flow: {flow_name} does not exist")
            
        if not self.var_exists(flow_name, variable_name):
            abort(HttpStatus.NOT_FOUND.value, message=f"Variable: {variable_name} does not exist")
           
        s = self.session
        flow = self.session.flows[flow_name]
        var = self.vars_addon.var(flow, variable_name)
        return var.get(), HttpStatus.OK.value

    def put(self, flow_name: str, variable_name: str):
        
        if not self.flow_exists(flow_name):
            abort(HttpStatus.NOT_FOUND.value, message=f"Flow: {flow_name} does not exist")
           
        if not self.var_exists(flow_name, variable_name):
            abort(HttpStatus.NOT_FOUND.value, message=f"Variable: {variable_name} does not exist")
        
        
class CognixServer:
    """This is a class for creating a REST Api to communicate with a CogniX Session."""
    
    def __init__(self, session: CognixSession, api: CognixRestAPI = None):
        
        self.session = session
        self.api = api if api else CognixRestAPI(session)
        self.api.create_routes()
        
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
        
        self._server = Server(Config(self.api.app, host=host, port=port))
        def _run():
            self._server.run()
        
        print(f'PORT for Rest API: {port}')
        if not on_other_thread:
            _run()
        else:
            self._run_thread = Thread(target=_run)
            self._run_thread.setDaemon(True)
            self._run_thread.start()
    
    def shutdown(self):
        if self._server:
            self._server.should_exit = True