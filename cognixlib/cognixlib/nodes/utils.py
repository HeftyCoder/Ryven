from cognixcore.config.traits import *
from cognixcore.api import PortConfig
from cognixcore.node import Node
from traitsui.api import VGroup, VFold, ListEditor
from enum import IntEnum

class PortList(NodeTraitsConfig):
    
    class ListType(IntEnum):
        """
         A flag type that determines whether this list 
        generates inputs, outputs or both.
        """
        OUTPUTS = 1
        INPUTS = 2
        
    ports: list[str] =  List(CX_Str(), desc="dynamic ports")
    list_type: ListType = CX_Int(ListType.INPUTS, visible=False)
    min_port_count = CX_Int(0, visible=False) # this essentially protects from deleting static ports
    out_prefix = CX_Str('', visible=False)
    out_suffix = CX_Str('', visible=False)
    inp_prefix = CX_Str('', visible=False)
    inp_suffix = CX_Str('', visible=False)
    
    @observe("ports.items", post_init=True)
    def notify_ports_change(self, event):
        if self.is_duplicate_notif(event):
            return
        
        valid_names = self.valid_names
        
        outputs = self.node._outputs
        output_diff = len(valid_names) - len(outputs) + 1
        if output_diff < 0:
            for i in range(abs(output_diff)): 
                if len(outputs) == 1: # protect the first output
                    break
                self.node.delete_output(len(outputs) - 1)
        else:
            for i in range(output_diff):
                self.node.create_output(
                    PortConfig(
                        'port',
                    )
                )
        
        for i in range(1, len(outputs)):
            self.node.rename_output(i, valid_names[i-1])
    
    @property
    def valid_names(self):
        valid_names: list[str] = []
        for stream in self.ports:
            valid_s = stream.strip()
            if valid_s:
                valid_names.append(valid_s)
        return valid_names
    
    def mods_inputs(self):
        """Whether it modifies inputs"""
        return self.list_type & PortList.ListType.INPUTS == PortList.ListType.INPUTS
    
    def mods_outputs(self):
        """Whether it modifies outputs"""
        return self.list_type & PortList.ListType.OUTPUTS == PortList.ListType.OUTPUTS
    
    def mods_inp_out(self):
        """Whether it modifies both inputs and outputs"""
        return self.mods_inputs() and self.mods_outputs()
    
    traits_view = View(
        Item('ports', show_label=False)
    )