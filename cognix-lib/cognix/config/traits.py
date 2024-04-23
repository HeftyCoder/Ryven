from traits.api import *
from traits.observation.expression import ObserverExpression, trait, anytrait
from traits.trait_base import not_false, not_event
from traits.observation._trait_change_event import TraitChangeEvent

from typing import Callable, Any
from json import loads, dumps

from traits.trait_type import NoDefaultSpecified

from ..nodes.abc import CognixNode
from .abc import NodeConfig

#   UTIL

def __process_expression_str(c_trait: CTrait, trait_name: str, expr: str):
    """
    Processes an ongoing string expression given a trait and its name. Extends the
    expression based on whether the trait is an Instance, a List, a Dict or a Set.
    """
    
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
    """
    Processes an ongoing object expression given a trait and its name. Extends the
    expression based on whether the trait is an Instance, a List, a Dict or a Set.
    """
    
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
    """
    Recursively searches an object to find all the possible observer
    expressions. Starting expression should be None and starting object
    should be a HasTraits.
    """
    
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
        
        
class CX_Instance(Instance):
    """Trait instance whose class parameter is instantiated by default"""
    
    def __init__(self, klass=None, factory=None, args=(), kw=None, 
                 allow_none=True, adapt=None, module=None, **metadata):
        super().__init__(klass, factory, args, kw, allow_none, adapt, module, **metadata)

_auto_enter = {
    'enter_set': True,
    'auto_set': False
}

#   These are all set so that not every keystroke creates a change event

class __CX_Interface:
    """
    This is a class helper to define Cognix trait parameters
    
    It is the first class in the inheritance chain.
    The trait class is the second class.
    """
    
    def __init__(self, default_value=NoDefaultSpecified, **metadata):
        metadata.update(_auto_enter)
        # second class is the Trait class
        self.__class__.__bases__[1].__init__(self, default_value, **metadata)
        
class CX_Int(__CX_Interface, Int):
    pass

class CX_Float(__CX_Interface, Float):
    pass

class CX_Str(__CX_Interface, Str):
    pass

class CX_Complex(__CX_Interface, Complex):
    pass

class CX_Unicode(__CX_Interface, Unicode):
    pass

class CX_String(__CX_Interface, String):
    pass

class CX_CStr(__CX_Interface, CStr):
    pass

class CX_CUnicode(__CX_Interface, CUnicode):
    pass

class CX_Password(__CX_Interface, Password):
    pass

        
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
    }
    
    __obs_exprs = None
    """Holds all the important observer expressions"""
    
    @classmethod
    def obs_exprs(cls):
        return cls.__obs_exprs
    
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
        cls.__obs_exprs = []
        find_expressions(cls, None, cls.__obs_exprs, exp_type)
    
    def __init_subclass__(cls, **kwargs):
        cls.find_trait_exprs(str)

    # INSTANCE
    # redefine them as non serializable traits
    _node = Instance(CognixNode, visible=False)
    _config_changed = Set(visible=False)
    _allow_change = List([True], visible=False)
    traits_view = None
    
    def __init__(self, node: CognixNode = None, *args, **kwargs):
        NodeConfig.__init__(self, node)        
        HasTraits.__init__(self, *args, **kwargs)
        self.allow_notifications()
    
    # Traits only
    
    def allow_notifications(self):
        """Allows the invocation of events when a trait changes"""
        self.observe(self._on_config_changed, self.__obs_exprs)

    def block_notifications(self):
        """Blocks the invocation of events when a trait changes"""
        self.observe(self._on_config_changed, self.__obs_exprs, remove=True)
   
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
            self.serializable_traits(), 
            indent=indent, skipkeys=True, 
            default=self.__encode
        )
    
    def serializable_traits(self):
        return self.trait_get(**self.__s_metadata)
    
    def __encode(self, obj):
        if not isinstance(obj, NodeTraitsConfig):
            return None
        return obj.serializable_traits()
    

class NodeTraitsGroupConfig(NodeTraitsConfig):
    """
    A type meant to represent a group in traits ui.
    """  
    pass