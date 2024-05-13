from __future__ import annotations
from qtpy.QtGui import QIcon, QDrag
from qtpy.QtCore import (
    QMimeData, 
    Qt,
    QEvent,
    QByteArray,
    Signal,
)
from qtpy.QtWidgets import (
    QWidget, 
    QHBoxLayout, 
    QVBoxLayout,
    QLabel, 
    QMenu, 
    QAction,
    QComboBox,
    QFrame,
    QLineEdit,
    QScrollArea,
)

from ..utils import shorten, connect_signal_event, Location
from ..util_widgets import EditVal_Dialog
from ..base_widgets import InspectorWidget

from json import dumps
from typing import Callable

from ryvencore.addons.variables import VarsAddon, Variable
from ryvencore import Flow, Data
    

class VarsItemWidget(QWidget):
    """A QWidget representing a single script variable for the VariablesListWidget."""

    def __init__(self, vars_list_widget: VariablesListWidget, var: Variable):
        super().__init__()

        self.vars_addon = var.addon
        self.flow = var.flow
        self.var = var
        self.vars_list_widget = vars_list_widget
        self.previous_var_name = ''  # for editing

        self.ignore_name_line_edit_signal = False


        # UI

        self.main_layout = main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(main_layout)
        # create icon

        variable_icon = QIcon(Location.PACKAGE_PATH+'/resources/pics/variable_picture.png')

        self.icon_label = icon_label = QLabel()
        icon_label.setFixedSize(15, 15)
        icon_label.setStyleSheet('border:none;')
        icon_label.setPixmap(variable_icon.pixmap(15, 15))
        main_layout.addWidget(icon_label)

        # content-layout
        self.content_widget = QFrame()
        self.content_widget.setFrameStyle(QFrame.StyledPanel | QFrame.Plain)
        self.content_widget.setLineWidth(1)
        self.content_widget.setLayout(QVBoxLayout())
        main_layout.addWidget(self.content_widget)
        
        #   name line edit

        self.name_line_edit = QLineEdit(self.var.name, self)
        self.name_line_edit.setPlaceholderText('name')
        self.name_line_edit.setEnabled(False)
        self.name_line_edit.editingFinished.connect(self.name_line_edit_editing_finished)

        self.content_widget.layout().addWidget(self.name_line_edit)
        
        # Data options
        s = self.flow.session
        for i in range(1):
            combo = QLabel("I CAN SHOW YOU THE WORLD")
            self.content_widget.layout().addWidget(combo)
        

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.name_line_edit.geometry().contains(event.pos()):
                self.name_line_edit_double_clicked()
                return


    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            drag = QDrag(self)
            mime_data = QMimeData()
            data_text = self.get_drag_data()
            data = QByteArray(bytes(data_text, 'utf-8'))
            mime_data.setData('text/plain', data)
            drag.setMimeData(mime_data)
            drop_action = drag.exec_()
            return


    def event(self, event):
        if event.type() == QEvent.ToolTip:
            val_str = ''
            try:
                val_str = str(self.var.get())
            except Exception as e:
                val_str = "couldn't stringify value"
            self.setToolTip('val type: '+str(type(self.var.get()))+'\nval: '+shorten(val_str, 3000, line_break=True))

        return QWidget.event(self, event)


    def contextMenuEvent(self, event):
        menu: QMenu = QMenu(self)

        delete_action = QAction('delete')
        delete_action.triggered.connect(self.action_delete_triggered)

        actions = [delete_action]
        for a in actions:
            menu.addAction(a)

        menu.exec_(event.globalPos())


    def action_delete_triggered(self):
        self.vars_list_widget.del_var(self.var)


    def action_edit_val_triggered(self):
        edit_var_val_dialog = EditVal_Dialog(self, self.var.get())
        accepted = edit_var_val_dialog.exec_()
        if accepted:
            self.var.set(edit_var_val_dialog.get_val())
            # self.vars_addon.create_var(self.flow, self.var.name, edit_var_val_dialog.get_val())


    def name_line_edit_double_clicked(self):
        self.name_line_edit.setEnabled(True)
        self.name_line_edit.setFocus()
        self.name_line_edit.selectAll()

        self.previous_var_name = self.name_line_edit.text()


    def get_drag_data(self):
        data = {'type': 'variable',
                'name': self.var.name,
                'value': self.var.get()}  # value is probably unnecessary
        data_text = dumps(data)
        return data_text


    def name_line_edit_editing_finished(self):
        if self.ignore_name_line_edit_signal:
            return

        new_name = self.name_line_edit.text()

        self.ignore_name_line_edit_signal = True
        
        rename_result = self.vars_addon.rename_var(self.flow, self.var.name, new_name)
        if not rename_result:
            self.name_line_edit.setText(self.previous_var_name)

        self.name_line_edit.setEnabled(False)
        self.ignore_name_line_edit_signal = False
    
    def set_name_text(self, name: str):
        self.ignore_name_line_edit_signal = True
        self.name_line_edit.setText(name)
        self.ignore_name_line_edit_signal = False


class VariablesListWidget(QWidget):
    """Convenience class for a QWidget to easily manage script variables of a script."""

    on_var_created_signal = Signal(Variable)
    on_var_deleted_signal = Signal(Variable)
    on_var_renamed_signal = Signal(Variable, str)
    
    def __init__(self, vars_addon: VarsAddon, flow: Flow, get_inspector: Callable[[type[Data]], type[InspectorWidget[Data]]] = None):
        super(VariablesListWidget, self).__init__()

        self.vars_addon = vars_addon
        self.flow = flow
        self.get_inspector = get_inspector
        """A callable that returns an inspector type"""
        
        # signals and events
        connect_signal_event(self.on_var_created_signal, self.vars_addon.var_created, self.on_var_created)
        connect_signal_event(self.on_var_deleted_signal, self.vars_addon.var_deleted, self.on_var_deleted)
        connect_signal_event(self.on_var_renamed_signal, self.vars_addon.var_renamed, self.on_var_renamed)

        self.widgets: dict[str, VarsItemWidget] = {}
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
            w = VarsItemWidget(self, var)
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
            new_widget = VarsItemWidget(self, self.vars_addon, self.flow, var_sub.variable)
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
