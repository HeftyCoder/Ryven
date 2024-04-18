from .nodes import *
from ryven.gui_env import *
from traitsui.api import View, Item, ButtonEditor, Group, InstanceEditor
from ryvencore_qt.src.flows.FlowCommands import Delegate_Command
from collections import deque
from qtpy.QtWidgets import QVBoxLayout, QWidget
from traits.observation._trait_change_event import TraitChangeEvent

class RandNodeInspector(NodeInspectorWidget, QWidget):
    
    def __init__(self, params):
        QWidget.__init__(self)
        NodeInspectorWidget.__init__(self, params)
        
        self.setLayout(QVBoxLayout())
        self.node: RandNode = self.node  # help with auto-complete
        
        g1 = Group(
                *tuple(Item(name) for name in self.config.visible_traits()),
                Item("generate", show_label=False, editor=ButtonEditor(label="Generate!")),
                label="Config",
                scrollable=True
            )
        self.view = View(
            Group(g1, 
                  show_border=True, 
                  layout='tabbed', 
                  scrollable=True,
                  label='Configuration'),
            resizable=True
        )
        
        self.ui = None
    
    @property
    def config(self):
        return self.node.config

    def load(self):
        if not self.ui:
            print('created')
            self.ui = self.config.edit_traits(parent=self, kind='subpanel', view=self.view).control
            self.ui.setVisible(False)
            self.layout().addWidget(self.ui)
            self.ui.setVisible(True)
            
        self.config.on_trait.append(self.on_trait_changed)
        self.config.on_val.append(self.on_val_changed)
    
    def unload(self):
        self.config.on_trait.remove(self.on_trait_changed)
        self.config.on_val.remove(self.on_val_changed)
    
    def on_node_deleted(self):
        if not self.ui:
            return
        self.ui.deleteLater()
        self.ui.setParent(None)
        self.ui.setVisible(False)
        self.ui = None
        
    def on_val_changed(self, prev_val, new_val):
        def undo_redo(value):
            def _undo_redo():
                self.node.set_output_val(0, Data(value))
            return _undo_redo
        
        self.push_undo(f'Update {prev_val} -> {new_val}', undo_redo(prev_val), undo_redo(new_val))
    
    def on_trait_changed(self, trait_event: TraitChangeEvent):
        print(type(trait_event))
        print(f'Trait "{trait_event.name}" changed from {trait_event.old} to {trait_event.new}')
        # otherwise an enter event for a text editor wouldn't stop text editing
        self.node_gui.flow_view().setFocus()
        if trait_event.name == trait_event.new:
            return

        def undo_redo(value):
            def _undo_redo():
                self.config.block_notifications()
                setattr(self.config, trait_event.name, value)
                if trait_event.name == 'seed':
                        self.config.ran_gen.seed = value
                self.config.allow_notifications()

            return _undo_redo

        self.push_undo(f'Config Change {trait_event.name} {trait_event.old} -> {trait_event.new}', undo_redo(trait_event.old), undo_redo(trait_event.new))

@node_gui(RandNode)
class RandNodeGUI(NodeGUI):
    inspector_widget_class = RandNodeInspector
    wrap_inspector_in_default = True
