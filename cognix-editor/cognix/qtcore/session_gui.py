from __future__ import annotations

from qtpy.QtCore import QObject, Signal, Qt
from qtpy.QtWidgets import QWidget, QApplication

from .flows.view import FlowView
from .design import Design
from .gui_base import GUIBase
from .code_editor.codes_storage import SourceCodeStorage

from cognixcore import (
    set_complete_data_func,
    Flow,
    Session,
)

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .env import GUIEnv

class SessionGUI(GUIBase, QObject):
    """
    ryvencore-qt's Session wrapper class, implementing the GUI.
    Any session with a GUI must be created through this class.
    Access the ryvencore session through the :code:`session`
    attribute, and the GUI from the ryvencore session through the
    :code:`gui` attribute. Once instantiated, you can simply use
    the :code:`session` directly to create, rename, delete flows,
    register nodes, etc.
    """

    flow_created = Signal(object)
    flow_deleted = Signal(object)
    flow_renamed = Signal(object, str)
    flow_view_created = Signal(object, object)

    def __init__(self, gui_parent: QWidget, gui_env: GUIEnv=None):
        GUIBase.__init__(self)
        QObject.__init__(self)

        if gui_env:
            self.__gui_env = gui_env
        else:
            from .env import get_gui_env # global gui env
            self.__gui_env = get_gui_env()
        
        self.__gui_env.load_env()
            
        self.core_session = Session(gui=True, load_addons=True)
        setattr(self.core_session, 'gui', self)

        self.gui_parent = gui_parent

        # code storage
        self.wnd_light_type = 'dark'
        self.cd_storage = SourceCodeStorage(self.__gui_env)
        # flow views
        self.flow_views = {}  # {Flow : FlowView}

        # register complete_data function
        set_complete_data_func(self.get_complete_data_function(self))

        # load design
        app = QApplication.instance()
        app.setAttribute(Qt.AA_UseHighDpiPixmaps)
        Design.register_fonts()
        self.design = Design()

        # connect to session
        self.core_session.flow_created.sub(self._flow_created)
        self.core_session.flow_deleted.sub(self._flow_deleted)
        self.core_session.flow_renamed.sub(self._flow_renamed)

    @property
    def gui_env(self):
        """Utility property for accessing the global GUI environment."""
        return self.__gui_env
    
    def _flow_created(self, flow: Flow):
        """
        Builds the flow view for a newly created flow, saves it in
        self.flow_views, and emits the flow_view_created signal.
        """
        self.flow_created.emit(flow)

        self.flow_views[flow] = FlowView(
            session_gui=self,
            flow=flow,
            parent=self.gui_parent,
        )
        self.flow_view_created.emit(flow, self.flow_views[flow])

        return flow

    def _flow_deleted(self, flow: Flow):
        """
        Removes the flow view for a deleted flow from self.flow_views.
        """
        self.flow_views.pop(flow)
        self.flow_deleted.emit(flow)

    def _flow_renamed(self, flow: Flow, new_name: str):
        """
        Renames the flow view for a renamed flow.
        """
        self.flow_renamed.emit(flow, new_name)