from __future__ import annotations

import textdistance
import json

from qtpy.QtWidgets import (
    QLineEdit, 
    QWidget, 
    QGridLayout, 
    QHBoxLayout,
    QVBoxLayout, 
    QStyleOption, 
    QStyle,
    QScrollArea,
    QTreeView,
    QSplitter,
    QAbstractItemView,
    QLabel,
)
from qtpy.QtGui import (
    QStandardItemModel, 
    QStandardItem, 
    QIcon,
    QPainter,
    QColor,
    QDrag,
    QFont,
)

from qtpy.QtCore import (
    Signal, 
    Qt, 
    QMimeData, 
    QModelIndex, 
    QSortFilterProxyModel,
)


from statistics import median
from re import escape
from ryvencore import Node
from ryvencore.base import IdentifiableGroups
from ..utils import IdentifiableGroupsModel
from ..env import GUIEnvProxy

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..session_gui import SessionGUI

#   UTIL

def dec(i: int, length: int) -> int:
    if i != 0:
        return i - 1
    else:
        return length - 1

def inc(i: int, length: int) -> int:
    if i != length - 1:
        return i + 1
    else:
        return 0


def sort_nodes(nodes):
    return sorted(nodes, key=lambda x: x.title.lower())


def sort_by_val(d: dict) -> dict:
    return {
        k: v
        for k, v in sorted(
            d.items(),
            key=lambda x: x[1]
        )
    }


def search(items: dict, text: str) -> dict:
    """performs the search on `items` under search string `text`"""
    dist = textdistance.sorensen_dice.distance

    distances = {}

    for item, tags in items.items():
        min_dist = 1.0
        for tag in tags:
            min_dist = min(min_dist, dist(text, tag))

        distances[item] = min_dist

    return sort_by_val(distances)


__text_font = QFont('Source Code Pro', 9)
__text_font.setPointSizeF(__text_font.pointSizeF() * 1.15)

def text_font():
    return __text_font


class NodeListItemWidget(QWidget):

    chosen = Signal()
    custom_focused_from_inside = Signal()

    @staticmethod
    def _create_mime_data(node: type[Node]) -> QMimeData:
        mime_data = QMimeData()
        mime_data.setData('application/json', bytes(json.dumps(
                {
                    'type': 'node',
                    'node identifier': node.id(),
                }
            ), encoding='utf-8'))
        return mime_data
    
    def __init__(self, parent, node_type: type[Node], gui_env: GUIEnvProxy):
        super(NodeListItemWidget, self).__init__(parent)

        self.custom_focused = False
        self.node_type = node_type
        self.gui_env = gui_env

        self.left_mouse_pressed_on_me = False

        # UI
        main_layout = QGridLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)

        self_ = self
        
        class NameLabel(QLineEdit):
            def __init__(self, text):
                super().__init__(text)

                self.setReadOnly(True)
                self.setFont(text_font())
            def mouseMoveEvent(self, ev):
                self_.custom_focused_from_inside.emit()
                ev.ignore()
            def mousePressEvent(self, ev):
                ev.ignore()
            def mouseReleaseEvent(self, ev):
                ev.ignore()

        name_label = NameLabel(node_type.title)
        main_layout.addWidget(name_label, 0, 0)
        
        self.setLayout(main_layout)
        self.setContentsMargins(0, 0, 0, 0)
        self.setMaximumWidth(250)

        self.setToolTip(node_type.__doc__)
        self.update_stylesheet()


    def mousePressEvent(self, event):
        self.custom_focused_from_inside.emit()
        if event.button() == Qt.LeftButton:
            self.left_mouse_pressed_on_me = True

    def mouseMoveEvent(self, event):
        if self.left_mouse_pressed_on_me:
            drag = QDrag(self)
            mime_data = NodeListItemWidget._create_mime_data(self.node_type)
            drag.setMimeData(mime_data)
            drag.exec_()

    def mouseReleaseEvent(self, event):
        self.left_mouse_pressed_on_me = False
        if self.geometry().contains(self.mapToParent(event.pos())):
            self.chosen.emit()

    def set_custom_focus(self, new_focus):
        self.custom_focused = new_focus
        self.update_stylesheet()

    def update_stylesheet(self):
        gui = self.gui_env.get_node_gui(self.node_type)
        color = gui.color if gui else '#888888'

        r, g, b = QColor(color).red(), QColor(color).green(), QColor(color).blue()

        new_style_sheet = f'''
NodeListItemWidget {{
    border: 1px solid rgba(255,255,255,150);
    border-radius: 2px;
    {(
        f'background-color: rgba(255,255,255,80);'
    ) if self.custom_focused else ''}
}}
QLabel {{
    background: transparent;
}}
QLineEdit {{
    background: transparent;
    border: none;
    padding: 2px;
}}
        '''

        self.setStyleSheet(new_style_sheet)

    def paintEvent(self, event):  # just to enable stylesheets
        o = QStyleOption()
        o.initFrom(self)
        p = QPainter(self)
        self.style().drawPrimitive(QStyle.PE_Widget, o, p, self)


#   LIST WIDGET
    
class NodeStandardItem(QStandardItem):
    """A node item for use in a model. Helpful when creating a tree view"""
    def __init__(self, node_type: type[Node], text: str = None):
        super().__init__(text)
        self.setEditable(False)
        self.setDragEnabled(True)
        self.setFont(text_font())
        self.node_type = node_type
    
    def mimeData(self):
        return NodeListItemWidget._create_mime_data(self.node_type) 
        
class NodeGroupsModel(IdentifiableGroupsModel[Node]):
    
    def __init__(self, list_widget: NodeListWidget, groups: IdentifiableGroups[Node], label="Packages", separator='.'):
        self.list_widget = list_widget
        super().__init__(groups, label, separator)
       
    def create_id_item(self, id: type[Node]):
        return NodeStandardItem(id, id.name())
     
    def create_subgroup(self, name: str, path: str) -> QStandardItem:
        item = QStandardItem(name)
        item.setFont(text_font())
        # https://specifications.freedesktop.org/icon-naming-spec/latest/ar01s04.html
        item.setIcon(QIcon.fromTheme('folder', self.list_widget.style().standardIcon(QStyle.SP_DirIcon)))
        item.setDragEnabled(False)
        item.setEditable(False)
        
        def on_item_clicked():
            group = self.groups.group(path)
            node_types = list(group.values() if group else self.groups.id_set)
            self.list_widget.make_nodes_current(node_types, path)
        
        item.setData(on_item_clicked, Qt.UserRole + 1)
        return item

    def mimeData(self, indexes):
        item: NodeStandardItem = self.itemFromIndex(indexes[0])
        return item.mimeData()
        
class NodeListWidget(QWidget):
    # SIGNALS
    escaped = Signal()
    node_chosen = Signal(object)

    def __init__(self, session_gui: SessionGUI, show_packages: bool = False):
        super().__init__()

        self.session_gui = session_gui
        self.nodes: list[type[Node]] = []
        self.package_nodes: list[type[Node]] = []  
        self.current_nodes: list[type[Node]] = []  # currently selectable nodes
        self.active_node_widget_index = -1  # index of focused node widget
        self.active_node_widget = None  # focused node widget
        self.node_widgets = {}  # Node-NodeWidget assignments
        self._node_widget_index_counter = 0

        # holds the path to the tree item
        self.node_model = NodeGroupsModel(self, self.session_gui.core_session.node_groups)
        self.show_packages: bool = show_packages
        self._setup_UI()

    def _setup_UI(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setAlignment(Qt.AlignTop)
        self.setLayout(self.main_layout)

        # splitter between packages and nodes
        splitter = QSplitter(Qt.Vertical)
        self.layout().addWidget(splitter)

        # search for the tree
        self.search_line_tree = QLineEdit(self)
        self.search_line_tree.setPlaceholderText('search packages...')
        self.search_line_tree.textChanged.connect(self.search_pkg_tree)

        # tree view
        self.pack_proxy_model: QSortFilterProxyModel = QSortFilterProxyModel()
        self.pack_proxy_model.setRecursiveFilteringEnabled(True)
        # we need qt6 for not filtering out the children if they would be filtered
        # out otherwise
        self.pack_proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.pack_tree = QTreeView()
        self.pack_tree.setModel(self.pack_proxy_model)
        self.pack_tree.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly)
        self.pack_tree.setDragEnabled(True)
        self.pack_proxy_model.setSourceModel(self.node_model)

        def on_select(index: QModelIndex):
            source_index = index.model().mapToSource(index)
            item: QStandardItem = index.model().sourceModel().itemFromIndex(source_index)
            func = item.data(Qt.UserRole + 1)
            if func != None:
                func()

        # pkg widget
        self.pkg_widget = QWidget()
        self.pkg_widget.setLayout(QVBoxLayout())
        self.pkg_widget.layout().addWidget(self.search_line_tree)
        self.pkg_widget.layout().addWidget(self.pack_tree)

        self.pack_tree.clicked.connect(on_select)

        if self.show_packages:
            splitter.addWidget(self.pkg_widget)
        
        splitter.setSizes([30])
        
        # nodes widget
        nodes_widget = QWidget()
        nodes_widget.setLayout(QVBoxLayout())
        splitter.addWidget(nodes_widget)

        # adding all stuff to the layout
        self.search_line_edit = QLineEdit(self)
        self.search_line_edit.setPlaceholderText('search for node...')
        self.search_line_edit.textChanged.connect(self._update_view)
        nodes_widget.layout().addWidget(self.search_line_edit)
        
        self.current_pack_label = QLabel('Package: None')
        self.current_pack_label.setFont(text_font())
        nodes_widget.layout().addWidget(self.current_pack_label)
        
        self.list_scroll_area = QScrollArea(self)
        self.list_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.list_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.list_scroll_area.setWidgetResizable(True)
        self.list_scroll_area.setContentsMargins(0, 0, 0, 0)

        self.list_scroll_area_widget = QWidget()
        self.list_scroll_area_widget.setContentsMargins(15, 10, 15, 10)
        self.list_scroll_area.setWidget(self.list_scroll_area_widget)

        self.list_layout = QVBoxLayout()
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setAlignment(Qt.AlignTop)
        self.list_scroll_area_widget.setLayout(self.list_layout)

        nodes_widget.layout().addWidget(self.list_scroll_area)

        self._update_view('')

        self.setStyleSheet(self.session_gui.design.node_selection_stylesheet)

        self.search_line_edit.setFocus()

    def search_pkg_tree(self, search: str):
        if search and search != '':
            # removes whitespace and escapes all special regex chars
            new_search = escape(search.strip())
            # regex that enforces the text starts with <new_search>
            self.pack_proxy_model.setFilterRegularExpression(f'^{new_search}')
            self.pack_tree.expandAll()
        else:
            self.pack_proxy_model.setFilterRegularExpression('')
            self.pack_tree.collapseAll()

    def make_nodes_current(self, pack_nodes, pkg_name: str):
        if not pack_nodes or self.package_nodes == pack_nodes:
            return
        self.package_nodes = pack_nodes
        self.current_pack_label.setText(f'Package: {pkg_name}')
        self._update_view()

    def mousePressEvent(self, event):
        # need to accept the event, so the scene doesn't process it further
        QWidget.mousePressEvent(self, event)
        event.accept()

    def keyPressEvent(self, event):
        """key controls"""

        num_items = len(self.current_nodes)

        if event.key() == Qt.Key_Escape:
            self.escaped.emit()

        elif event.key() == Qt.Key_Down:
            self._set_active_node_widget_index(inc(self.active_node_widget_index, length=num_items))
        elif event.key() == Qt.Key_Up:
            self._set_active_node_widget_index(dec(self.active_node_widget_index, num_items))

        elif event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            if len(self.current_nodes) > 0:
                self._place_node(self.active_node_widget_index)
        else:
            event.setAccepted(False)

    def wheelEvent(self, event):
        # need to accept the event, so the scene doesn't process it further
        QWidget.wheelEvent(self, event)
        event.accept()

    def refocus(self):
        """focuses the search line edit and selects the text"""
        self.search_line_edit.setFocus()
        self.search_line_edit.selectAll()

    def update_list(self, nodes):
        """update the list of available nodes"""
        self.nodes = sort_nodes(nodes)
        self._update_view('')

    def _update_view(self, search_text=''):
        nodes = self.nodes if search_text is not None and search_text != '' else self.package_nodes

        if nodes == None or len(nodes) == 0:
            nodes = self.nodes

        if len(nodes) == 0:
            return

        search_text = search_text.lower()

        # remove all node widgets

        for i in reversed(range(self.list_layout.count())):
            self.list_layout.itemAt(i).widget().setParent(None)

        self.current_nodes.clear()

        self._node_widget_index_counter = 0

        # search
        sorted_distances = search(
            items={n: [n.title.lower()] + n.tags for n in nodes}, text=search_text
        )

        # create node widgets
        cutoff = median(sorted_distances.values())
        for n, dist in sorted_distances.items():
            if search_text != '' and dist > cutoff:
                continue

            self.current_nodes.append(n)

            if self.node_widgets.get(n) is None:
                self.node_widgets[n] = self._create_node_widget(n)

            self.list_layout.addWidget(self.node_widgets[n])

        # focus on first result
        if len(self.current_nodes) > 0:
            self._set_active_node_widget_index(0)

    def _create_node_widget(self, node):
        node_widget = NodeListItemWidget(self, node, self.session_gui.gui_env)
        node_widget.custom_focused_from_inside.connect(self._node_widget_focused_from_inside)
        node_widget.setObjectName('node_widget_' + str(self._node_widget_index_counter))
        self._node_widget_index_counter += 1
        node_widget.chosen.connect(self._node_widget_chosen)

        return node_widget

    def _node_widget_focused_from_inside(self):
        index = self.list_layout.indexOf(self.sender())
        self._set_active_node_widget_index(index)

    def _set_active_node_widget_index(self, index):
        self.active_node_widget_index = index
        node_widget = self.list_layout.itemAt(index).widget()

        if self.active_node_widget:
            self.active_node_widget.set_custom_focus(False)

        node_widget.set_custom_focus(True)
        self.active_node_widget = node_widget
        self.list_scroll_area.ensureWidgetVisible(self.active_node_widget)

    def _node_widget_chosen(self):
        index = int(self.sender().objectName()[self.sender().objectName().rindex('_') + 1 :])
        self._place_node(index)

    def _place_node(self, index):
        node_index = index
        node = self.current_nodes[node_index]
        self.node_chosen.emit(node)
        self.escaped.emit()
