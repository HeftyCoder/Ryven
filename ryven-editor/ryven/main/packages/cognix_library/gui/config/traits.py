"""
Implementations for a node config based on the 
built-in traits and traitsui implementation
"""
from __future__ import annotations
from cognix.api import NodeConfig, CognixNode
from cognix.config.traits import NodeTraitsConfig, NodeTraitsGroupConfig
from ryvencore_qt.nodes.inspector import InspectedChangedEvent

from .abc import NodeConfigInspector
from ryvencore_qt.env import inspector

from traitsui.api import View, Group, Item
from traits.observation.events import (
    TraitChangeEvent, 
    ListChangeEvent, 
    DictChangeEvent, 
    SetChangeEvent
)
from qtpy.QtWidgets import QVBoxLayout, QWidget
from ryven.gui_env import NodeGUI
from ryvencore_qt.flows.commands import DelegateCommand
from typing import TypeVar


@inspector(NodeTraitsConfig)
class NodeTraitsConfigInspector(NodeConfigInspector[NodeTraitsConfig], QWidget):
    """Basic config inspector"""
    
    #   CLASS
    @classmethod
    def create_config_changed_event(cls, node: CognixNode, gui: NodeGUI):
        
        def on_trait_changed(event):
            
            gui.flow_view.setFocus()
            def undo_redo(event, func, value):
                def _undo__redo():
                    node.config.block_change_events()
                    func(event, value)
                    node.config.allow_change_events()
                        
                return _undo__redo
            
            def undo_redo_pair(event, func, undo_val, redo_val):
                return (
                    undo_redo(event, func, undo_val),
                    undo_redo(event, func, redo_val)
                )
                
            node_id = node.global_id
            message = f'Config Change Node: {node_id}: {event}'
            
            if isinstance(event, TraitChangeEvent):
                u_pair = undo_redo_pair(event, _trait_change, event.old, event.new)
            elif isinstance(event, ListChangeEvent):
                u_pair = undo_redo_pair(
                    event, 
                    _list_change, 
                    (event.index, event.added, event.removed),
                    (event.index, event.removed, event.added)
                )
            elif isinstance(event, SetChangeEvent):
                u_pair = undo_redo_pair(
                    event,
                    _set_change,
                    (event.added, event.removed),
                    (event.removed, event.added)
                )
            else:
                u_pair = undo_redo_pair(
                    event,
                    _dict_change,
                    (event.added, event.removed),
                    (event.removed, event.added)
                )
                
            undo, redo = u_pair
            gui.flow_view.push_undo(
                DelegateCommand(
                    gui.flow_view,
                    message,
                    undo,
                    redo,
                ), True
            )
        
        return on_trait_changed
    
    
    #   INSTANCE
    def __init__(self, params: tuple[NodeTraitsConfig, NodeGUI]):
        QWidget.__init__(self)
        
        config, _ = params
        
        self.view: View = None
        self.ui = None
        NodeConfigInspector.__init__(self, params)
    
    def inspected_label(self):
        return (
            getattr(self.inspected, 'label') 
            if hasattr(self.inspected, 'label') 
            else 'Configuration'
        )
    
    def on_insp_changed(self, change_event: InspectedChangedEvent[NodeTraitsConfig]):
        
        self.setLayout(QVBoxLayout())
        self.delete_ui()
        
        inspected_obj = change_event.new
        
        if not inspected_obj:
            return
        
        self.inspected = inspected_obj
        
        gr_label = self.inspected_label()
        
        insp_traits = inspected_obj.serializable_traits()
        
        items: list[Item] = []
        for tr in insp_traits:
            internal_tr = inspected_obj.trait(tr)
            style = getattr(internal_tr, 'style', None)
            item = Item(tr, style=style) if style else Item(tr)
            items.append(item)
            
        config_group = Group (
            *items,
            label=gr_label,
            scrollable=True,
            springy=True,
        )
        
        self.view = View (
            config_group
        )
        
        if not change_event.created:
            self.load()
    
    def load(self):
        
        if not self.ui:
            self.ui = self.inspected.edit_traits(parent=self, kind='subpanel', view=self.view).control
            self.ui.setVisible(False)
            self.layout().addWidget(self.ui)
            self.ui.setVisible(True)
    
    def delete_ui(self):
        if self.ui:
            self.ui.deleteLater()
            self.ui.setParent(None)
            self.ui.setVisible(False)
            self.ui = None
                          
        
@inspector(NodeTraitsGroupConfig)
class NodeTraitsGroupConfigInspector(NodeTraitsConfigInspector):
    
    traits_view = None
    
    def on_insp_changed(self, change_event: InspectedChangedEvent[NodeTraitsConfig]):
        
        inspected_obj = change_event.new
        self.delete_ui()
        
        if not inspected_obj:
            return
        
        self.inspected = inspected_obj
        
        gr_label = self.inspected_label()
        gr_layout = (
            getattr(self.inspected, 'layout') 
            if hasattr(self.inspected, 'layout') 
            else 'tabbed'
        )
        
        insp_traits = inspected_obj.serializable_traits()
        
        items: list[Item] = []
        for tr in insp_traits:
            items.append(Item(tr, style='custom', show_label=False))
        
        self.view = View(
            Group(
                *items,
                label=gr_label,
                layout=gr_layout,
                show_border=True,
                scrollable=True,
                springy=True
            )
        )
        
        if not change_event.created:
            self.load()
    

#   ------UTIL-------

def _trait_change(event: TraitChangeEvent, value):
    setattr(event.object, event.name, value)
            
def _list_change(event: ListChangeEvent, value: tuple): # (added, removed, index)
    l: list = event.object
    index, added, removed = value
    
    del l[index:index+len(added)]
    l[index:index] = removed
            
def _set_change(event: SetChangeEvent, value: tuple): # (added, removed)
    s: set = event.object
    added, removed = value
    for r in removed:
        s.remove(r)
    s.update(added)
        
def _dict_change(event: DictChangeEvent, value: tuple): #(added, removed)
    d: dict = event.object
    added, removed = value
    for key in removed:
        del d[key]
    d.update(added)
