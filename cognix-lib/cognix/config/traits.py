from traits.api import HasTraits, Instance, Float, List
from traits.trait_base import not_false, not_event
from traits.observation._trait_change_event import TraitChangeEvent

from .. import CognixNode, NodeConfig
from json import loads, dumps


class DefaultInstance(Instance):
    """Trait instance that is created by default"""
    
    def __init__(self, klass=None, factory=None, args=(), kw=None, 
                 allow_none=True, adapt=None, module=None, **metadata):
        super().__init__(klass, factory, args, kw, allow_none, adapt, module, **metadata)

        
class NodeTraitsConfig(NodeConfig, HasTraits):
    """An implementation of a Node Configuration using the traits library"""
    
    _node = Instance(CognixNode, visible=False)
    on_trait_changed = List(visible=False)
    
    def __init__(self, node: CognixNode = None, *args, **kwargs):
        HasTraits.__init__(self, *args, **kwargs)
        NodeConfig.__init__(self, node)
        self.allow_notifications()
    
    # Traits only
    
    # @observe('*') the decorator doesn't allow removal of notifications
    def any_trait_changed(self, event: TraitChangeEvent):
        """Invoked when any trait changes"""
        
        # the HasTraits object
        for e in self.on_trait_changed:
            e(self, event)
    
    def allow_notifications(self):
        pass
    
    def block_notifications(self):
        pass
   
    def load(self, data: dict | str):
        
        if isinstance(data, str):
            data = loads(data)
            
        self._trait_change_notify(False)
        for name, value in data.items():
            try:
                trait_value = getattr(self, name)
                if isinstance(trait_value, NodeTraitsConfig):
                    trait_value.load(value)
                else:
                    setattr(self, name, value)
            except:
                continue
        
        self._trait_change_notify(True)
    
    def to_json(self, indent=1) -> str:
        return dumps(
            self.__serializable_traits(), 
            indent=indent, skipkeys=True, 
            default=self.__encode
        )
    
    def __encode(self, obj):
        if not isinstance(obj, NodeTraitsConfig):
            return None
        return obj.__serializable_traits()
    
    def __serializable_traits(self):
        return self.trait_get(type=not_event, visible=not_false, dont_save=not_false)
