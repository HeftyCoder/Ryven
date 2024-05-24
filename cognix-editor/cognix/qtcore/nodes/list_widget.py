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
    QSplitter,
    QAbstractItemView,
    QLabel,
    QListView,
)
from qtpy.QtGui import (
    QStandardItem, 
    QIcon,
    QPainter,
    QColor,
    QDrag,
    QFont,
    QStandardItemModel,
)

from qtpy.QtCore import (
    Signal, 
    Qt, 
    QMimeData,
)


from statistics import median
from re import escape

from ..utils import IdentifiableGroupsModel
from ..util_widgets import FilterTreeView, TreeViewSearcher
from ..env import GUIEnv

from cognixcore import Node
from cognixcore.base import Identifiable, IdentifiableGroups

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

def create_node_mime(node: type[Node]) -> QMimeData:
    mime_data = QMimeData()
    mime_data.setData('application/json', bytes(json.dumps(
            {
                'type': 'node',
                'node identifier': node.identifiable().id,
            }
        ), encoding='utf-8'))
    return mime_data

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
        return create_node_mime(self.node_type) 
        
class NodeGroupsModel(IdentifiableGroupsModel[type[Node]]):
    
    def __init__(self, list_widget: NodeListWidget, groups: IdentifiableGroups[type[Node]], label="Packages", separator='.'):
        self.list_widget = list_widget
        super().__init__(groups, label, separator)
    
    def create_id_item(self, id: Identifiable[type[Node]]):
        node_type = id.info
        return NodeStandardItem(node_type, node_type.title)
     
    def create_subgroup(self, name: str, path: str) -> QStandardItem:
        item = QStandardItem(name)
        item.setFont(text_font())
        # https://specifications.freedesktop.org/icon-naming-spec/latest/ar01s04.html
        item.setIcon(QIcon.fromTheme('folder', self.list_widget.style().standardIcon(QStyle.SP_DirIcon)))
        item.setDragEnabled(False)
        item.setEditable(False)
        
        def on_item_clicked():
            group = self.groups.group(path)
            if group:
                node_types = [identifiable.info for identifiable in group.values()]
            else:
                node_types = list(self.groups.infos)
                
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

        # searchable tree view
        
        self.pack_tree = FilterTreeView(self.node_model)
        self.pack_tree.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly)
        self.pack_tree.setDragEnabled(True)
        
        self.tree_searcher = TreeViewSearcher(self.pack_tree)
        self.tree_searcher.search_bar.setPlaceholderText('search packages...')

        if self.show_packages:
            splitter.addWidget(self.tree_searcher)
        
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
