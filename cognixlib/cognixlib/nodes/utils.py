from cognixcore.config.traits import *
from cognixcore.api import PortConfig, NodePort
from enum import IntEnum
from dataclasses import dataclass

class PortList(NodeTraitsConfig):
    
    class ListType(IntEnum):
        """
         A flag type that determines whether this list 
        generates inputs, outputs or both.
        """
        OUTPUTS = 1
        INPUTS = 2
    
    @dataclass
    class Params:
        prefix: str = ''
        suffix: str = ''
        allowed_data: type = None
        
    ports: list[str] =  List(CX_Str(), desc="dynamic ports")
    list_type: ListType = Int(ListType.INPUTS, visible=False)
    min_port_count = Int(0, visible=False) # this essentially protects from deleting static ports
    inp_params = Instance(Params, visible=False)
    out_params = Instance(Params, visible=False)
    
    @observe("ports.items", post_init=True)
    def notify_ports_change(self, event):
        if self.is_duplicate_notif(event):
            return
        
        valid_names = self.valid_names
        
        def fix_ports(
            port_list: Sequence[NodePort], 
            delete_func, 
            create_func, 
            rename_func,
            params: PortList.Params
        ):
            port_diff = len(valid_names) - len(port_list) + self.min_port_count
            if port_diff < 0:
                for i in range(abs(port_diff)):
                    if len(port_list) == self.min_port_count:
                        break
                    delete_func(len(port_list) - 1)
            else:
                for i in range(port_diff):
                    create_func(
                        PortConfig(
                            'port',
                            allowed_data=params.allowed_data
                        )
                    )
            
            for i in range(self.min_port_count, len(port_list)):
                rename_func(
                    i,
                    f"{params.prefix}{valid_names[i-self.min_port_count]}{params.suffix}"
                )
         
        if self.mods_inputs():
            fix_ports(
                self._node._inputs,
                self._node.delete_input,
                self._node.create_input,
                self._node.rename_input,
                self.inp_params
            )
               
        if self.mods_outputs():
            fix_ports(
                self._node._outputs,
                self._node.delete_output,
                self._node.create_output,
                self._node.rename_output,
                self.out_params
            )
    
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