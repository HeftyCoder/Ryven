from cognixcore.config.traits import *
from cognixcore.api import PortConfig

class NameConfig(NodeTraitsConfig):
    
    streams: list[str] =  List(CX_Str(), desc="the requested for extraction stream names")

    @observe("streams.items", post_init=True)
    def notify_streams_change(self, event):
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
                        'stream',
                    )
                )
        
        for i in range(1, len(outputs)):
            self.node.rename_output(i, valid_names[i-1])
        
    @property
    def valid_names(self):
        valid_names: list[str] = []
        for stream in self.streams:
            valid_s = stream.strip()
            if valid_s:
                valid_names.append(valid_s)
        return valid_names