
if __name__ != '__main__':
    exit()

from traits.api import *
from traitsui.api import *

class Test(HasTraits):
    
    show: bool = Bool()
    item = Int(0, desc="George", visible_when='self.test()')

    def test():
        return False
    
view = View(
    Group(
        Item('show'),
        Item('item', visible_when='show==test()')
    )
)

a = Test()
a.configure_traits(view=view)
