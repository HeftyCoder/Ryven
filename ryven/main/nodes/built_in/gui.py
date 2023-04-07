from ryven.gui_env import *

from qtpy.QtGui import QKeySequence
from qtpy.QtCore import Signal
from qtpy.QtWidgets import QLineEdit, QDialog, QDialogButtonBox, QMessageBox, QPlainTextEdit, QShortcut, QVBoxLayout


class GetVarGui(NodeGUI):
    color = '#c69a15'


class Result_Node_MainWidget(MWB, QLineEdit):
    def __init__(self, params):
        MWB.__init__(self, params)
        QLineEdit.__init__(self)

        self.setReadOnly(True)
        self.setFixedWidth(120)


    def show_val(self, new_val):
        self.setText(str(new_val))
        self.setCursorPosition(0)


class ResultGui(NodeGUI):
    main_widget_class = Result_Node_MainWidget
    main_widget_pos = 'between ports'
    color = '#c69a15'


class ValNode_MainWidget(MWB, QLineEdit):

    value_changed = Signal(object)

    def __init__(self, params):
        MWB.__init__(self, params)
        QLineEdit.__init__(self)

        # self.setFixedWidth(80)
        # self.setMinimumWidth(80)
        self.resize(120, 31)
        self.editingFinished.connect(self.editing_finished)

    def editing_finished(self):
        # self.node.update()
        self.value_changed.emit(self.get_val())

    def get_val(self):
        val = None
        try:
            val = eval(self.text())
        except Exception as e:
            val = self.text()
        return val

    def get_state(self):
        data = {'text': self.text()}
        return data

    def set_state(self, data):
        self.setText(data['text'])



class EditVal_Dialog(QDialog):
    def __init__(self, parent, init_val):
        super(EditVal_Dialog, self).__init__(parent)

        # shortcut
        save_shortcut = QShortcut(QKeySequence.Save, self)
        save_shortcut.activated.connect(self.save_triggered)

        main_layout = QVBoxLayout()

        self.val_text_edit = QPlainTextEdit()
        val_str = ''
        try:
            val_str = str(init_val)
        except Exception as e:
            msg_box = QMessageBox(QMessageBox.Warning, 'Value parsing failed',
                                  'Couldn\'t stringify value', QMessageBox.Ok, self)
            msg_box.setDefaultButton(QMessageBox.Ok)
            msg_box.exec_()
            self.reject()

        self.val_text_edit.setPlainText(val_str)

        main_layout.addWidget(self.val_text_edit)

        button_box = QDialogButtonBox()
        button_box.setStandardButtons(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        main_layout.addWidget(button_box)

        self.setLayout(main_layout)
        self.resize(450, 300)

        self.setWindowTitle('edit val')

    def save_triggered(self):
        self.accept()

    def get_val(self):
        val = self.val_text_edit.toPlainText()
        try:
            val = eval(val)
        except Exception as e:
            pass
        return val


class ValGui(NodeGUI):
    main_widget_class = ValNode_MainWidget
    style = 'small'
    color = '#c69a15'

    def initialized(self):
        self.actions['edit val via dialog'] = {'method': self.action_edit_via_dialog}

    def action_edit_via_dialog(self):
        val_dialog = EditVal_Dialog(parent=None, init_val=self.node.val)
        accepted = val_dialog.exec_()
        if accepted:
            self.main_widget().setText(str(val_dialog.get_val()))
            self.update()



class SetVarGui(NodeGUI):
    style = 'normal'
    color = '#c69a15'


export_guis(
    GetVarGui,
    ResultGui,
    ValGui,
    SetVarGui,
)
