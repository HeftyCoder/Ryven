from traits.api import *
from traits.observation.expression import ObserverExpression, trait, anytrait
from traits.trait_base import not_false, not_event
from traits.observation._trait_change_event import TraitChangeEvent

from typing import Callable, Any
from json import loads, dumps

from .. import CognixNode, NodeConfig

#   UTIL

def __process_expression_str(c_trait: CTrait, trait_name: str, expr: str):
    
    if not c_trait:
        return None, f'{expr}.*' if expr else '*'
        
    trait_type = c_trait.trait_type
    
    if isinstance(trait_type, Instance) and issubclass(trait_type.klass, HasTraits):
        
        # it's guaranteed that if a trait_name doesnt exist,
        # an expr will and vice-versa
        if expr:
            return (
                trait_type.klass,
                f'{expr}.{trait_name}' if trait_name else expr
            )
        else:
            return trait_type.klass, trait_name
    
    elif isinstance(trait_type, (List, Set, Dict)):
        
        return_type = (
            trait_type.item_trait 
            if isinstance(trait_type, (List, Set)) 
            else trait_type.value_trait
        )
        
        if expr:
            return (
                return_type,
                f'{expr}.{trait_name}.items' if trait_name else f'{expr}.items'
            )
        else:
            return return_type, f'{trait_name}.items'
            
    return (None, None)

__item_methods: dict = {
    List: lambda expr: expr.list_items(),
    Set: lambda expr: expr.set_items(),
    Dict: lambda expr: expr.dict_items(),
}

def __process_expression_obs(c_trait: CTrait, trait_name: str, expr: ObserverExpression):
    
    if not c_trait:
        return None, expr.anytrait() if expr else anytrait()
        
    trait_type = c_trait.trait_type
    
    if isinstance(trait_type, Instance) and issubclass(trait_type.klass, HasTraits):
        
        # it's guaranteed that if a trait_name doesnt exist,
        # an expr will and vice-versa
        if expr:
            return (
                trait_type.klass,
                expr.trait(trait_name) if trait_name else expr
            )
        else:
            return trait_type.klass, trait(trait_name)
        
    elif isinstance(trait_type, (List, Set, Dict)):
        
        return_type = (
            trait_type.item_trait 
            if isinstance(trait_type, (List, Set)) 
            else trait_type.value_trait
        )
        items_method = __item_methods[type(trait_type)]
        
        if expr:
            return (
                return_type,
                items_method(expr.trait(trait_name)) if trait_name else items_method(expr)
            )
        else:
            return return_type, items_method(trait(trait_name))
        
    elif isinstance(trait_type, Set):
        
        return (
            trait_type.item_trait,
            expr.set_items() if expr else trait(trait_name).set_items()
        )
          
    elif isinstance(trait_type, Dict):
        
        return (
            trait_type.value_trait,
            expr.dict_items() if expr else trait(trait_name).dict_items()
        )    
            
    return (None, None)


__process_expression_methods: dict[type, Callable[[CTrait, str, Any], None]]= {
    str : __process_expression_str,
    ObserverExpression: __process_expression_obs,
}         

def find_expressions (
    obj: type[HasTraits] | List | Dict, 
    expr: ObserverExpression, 
    obs_exprs: list[ObserverExpression | str],
    exp_type: type[str | ObserverExpression] = ObserverExpression
):
    
    if not obj:
        return
    
    process_method = __process_expression_methods[exp_type]
    
    if isinstance(obj, type) and issubclass(obj, HasTraits):
        
        # main class filter
        new_obj, new_expr = process_method(None, None, expr)
        obs_exprs.append(new_expr)
        
        # search for additional traits in the class
        
        cls_traits = obj.class_traits(visible=not_false)
        for trait_name, c_trait in cls_traits.items():
            new_obj, new_expr = process_method(c_trait, trait_name, expr)
            find_expressions(new_obj, new_expr, obs_exprs, exp_type)
    
    elif isinstance(obj, CTrait):
        
        obs_exprs.append(expr)
        new_obj, new_expr = process_method(obj, None, expr)
        find_expressions(new_obj, new_expr, obs_exprs, exp_type)
        
        
class DefaultInstance(Instance):
    """Trait instance that is created by default"""
    
    def __init__(self, klass=None, factory=None, args=(), kw=None, 
                 allow_none=True, adapt=None, module=None, **metadata):
        super().__init__(klass, factory, args, kw, allow_none, adapt, module, **metadata)

        
class NodeTraitsConfig(NodeConfig, HasTraits):
    """
    An implementation of a Node Configuration using the traits library
    
    Based on the documentation, the traits inside this are treated as items, in
    the context of GUI generation.
    """
    
    # CLASS
    
    __s_metadata = {
        'type': not_event,
        'visible': not_false,
        'dont_save': not_false,
    }
    
    obj_exprs = None
    """Holds all the important observer expressions"""
    
    @classmethod
    def serializable_traits(cls):
        """Returns the serializable traits of this class"""
        return cls.class_traits(**cls.__s_metadata)
    
    @classmethod
    def find_trait_exprs(cls, exp_type: type[str | ObserverExpression] = ObserverExpression):
        
        """
        Finds all the observer expressions available for this node, for
        traits that are not an event, are visible and do not have the 
        dont_save metadata atrribute set to True.
        """
        cls.obj_exprs = []
        find_expressions(cls, None, cls.obj_exprs)
    
    def __init_subclass__(cls, **kwargs):
        cls.find_trait_exprs()

    # INSTANCE
    
    _node = Instance(CognixNode, visible=False)
    trait_changed_event: set = Set(visible=False)
    
    def __init__(self, node: CognixNode = None, *args, **kwargs):
        HasTraits.__init__(self, *args, **kwargs)
        NodeConfig.__init__(self, node)
        self.allow_notifications()
    
    # Traits only
    
    # @observe('*') the decorator doesn't allow removal of notifications
    def __any_trait_changed(self, event):
        """Invoked when any trait that can be saved changes"""
        
        # the HasTraits object
        for e in self.trait_changed_event:
            e(event)
    
    def allow_notifications(self):
        """Allows the invocation of events when a trait changes"""
        self.observe(self.__any_trait_changed, self.obj_exprs)
    
    def block_notifications(self):
        """Blocks the invocation of events when a trait changes"""
        self.observe(self.__any_trait_changed, self.obj_exprs, remove=True)
   
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
        return self.trait_get(**self.__s_metadata)

class NodeTraitsGroupConfig(NodeTraitsConfig):
    """
    A type meant to represent a group in traits ui.
    """  
    pass