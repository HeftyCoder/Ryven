from ryvencore import Session
from .flow import CognixFlow

class CognixSession(Session):
    """
    An extension to a ryvencore Session for CogniX.
    """
    
    _flow_base_type = CognixFlow