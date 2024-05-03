from qtpy.QtWidgets import QVBoxLayout, QWidget, QLineEdit, QScrollArea
from qtpy.QtCore import Qt, Signal

from .VarsList_VarWidget import VarsList_VarWidget
from ..utils import connect_signal_event

from ryvencore.addons.variables import VarsAddon, Variable
from ryvencore import Flow

class VariablesListWidget(QWidget):
    """Convenience class for a QWidget to easily manage script variables of a script."""

    on_var_created_signal = Signal(Variable)
    on_var_deleted_signal = Signal(Variable)
    on_var_renamed_signal = Signal(Variable, str)
    
    def __init__(self, vars_addon: VarsAddon, flow: Flow):
        super(VariablesListWidget, self).__init__()

        self.vars_addon = vars_addon
        self.flow = flow
        
        # signals and events
        connect_signal_event(self.on_var_created_signal, self.vars_addon.var_created, self.on_var_created)
        connect_signal_event(self.on_var_deleted_signal, self.vars_addon.var_deleted, self.on_var_deleted)
        connect_signal_event(self.on_var_renamed_signal, self.vars_addon.var_renamed, self.on_var_renamed)

        self.widgets: dict[str, VarsList_VarWidget] = {}
        self.currently_edited_var = ''
        self.ignore_name_line_edit_signal = False  
        
        self.setup_UI()


    def setup_UI(self):
        main_layout = QVBoxLayout()

        self.list_layout = QVBoxLayout()
        self.list_layout.setAlignment(Qt.AlignTop)

        # list scroll area

        self.list_scroll_area = QScrollArea()
        self.list_scroll_area.setWidgetResizable(True)
        self.list_scroll_area.setContentsMargins(0, 0, 0, 0)

        w = QWidget()
        w.setContentsMargins(0, 0, 0, 0)
        w.setLayout(self.list_layout)

        self.list_scroll_area.setWidget(w)

        main_layout.addWidget(self.list_scroll_area)

        # controls

        self.new_var_name_lineedit = QLineEdit()
        self.new_var_name_lineedit.setPlaceholderText('new var\'s title')
        self.new_var_name_lineedit.returnPressed.connect(self.new_var_LE_return_pressed)

        main_layout.addWidget(self.new_var_name_lineedit)

        self.setContentsMargins(0, 0, 0, 0)
        self.setLayout(main_layout)

        self.recreate_list()


    def on_var_created(self, var: Variable):
        if var.flow == self.flow:
            w = VarsList_VarWidget(self, var)
            self.widgets[var.name] = w
            self.list_layout.addWidget(w)


    def on_var_deleted(self, var: Variable):
        if var.name in self.widgets:
            self.widgets[var.name].setParent(None)
            del self.widgets[var.name]


    def on_var_renamed(self, var: Variable, old_name: str):
        w = self.widgets[old_name]
        del self.widgets[old_name]
        self.widgets[var.name] = w
        w.set_name_text(var.name)
        
        
    def recreate_list(self):
        for w in self.widgets.values():
            w.setParent(None)
            del w

        self.widgets.clear()

        for var_name, var_sub in self.vars_addon.flow_variables[self.flow].items():
            new_widget = VarsList_VarWidget(self, self.vars_addon, self.flow, var_sub.variable)
            self.widgets[var_name] = new_widget

        self.rebuild_list()


    def rebuild_list(self):
        for w in self.widgets.values():
            w.setParent(None)

        for w in self.widgets.values():
            self.list_layout.addWidget(w)


    def new_var_LE_return_pressed(self):
        name = self.new_var_name_lineedit.text()
        if not self.vars_addon.var_name_valid(self.flow, name=name):
            return
        v = self.vars_addon.create_var(self.flow, name=name)


    def del_var(self, var):
        self.vars_addon.delete_var(self.flow, var.name)
