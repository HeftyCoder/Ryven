from __future__ import annotations

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
)

from qtpy.QtGui import QIcon, QDrag
from qtpy.QtCore import (
    QMimeData, 
    Qt,
    QEvent,
    QByteArray,
)

from ..GlobalAttributes import Location
from ..utils import shorten, connect_signal_event
from .EditVal_Dialog import EditVal_Dialog
from typing import TYPE_CHECKING
from json import dumps

if TYPE_CHECKING:
    from ryvencore.addons.variables import Variable
    from .VariablesListWidget import VariablesListWidget

class VarsList_VarWidget(QWidget):
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

        edit_value_action = QAction('edit value')
        edit_value_action.triggered.connect(self.action_edit_val_triggered)

        actions = [delete_action, edit_value_action]
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
