from qtpy.QtCore import (
    QPointF, 
    QRectF, 
    Qt, 
    QSizeF, 
    Property,
    QSize
)
from qtpy.QtWidgets import (
    QGraphicsWidget, 
    QGraphicsLinearLayout, 
    QSizePolicy, 
    QGraphicsLayoutItem, 
    QGraphicsItem,
    QGraphicsPixmapItem,
)
from qtpy.QtGui import (
    QFont, 
    QFontMetricsF, 
    QColor,
    QPixmap,
    QImage,
)
from ..FlowViewProxyWidget import FlowViewProxyWidget
from .PortItem import InputPortItem, OutputPortItem
from .GraphicsTextWidget import GraphicsTextWidget

from ...utils import get_longest_line, change_svg_color, get_resource

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .NodeGUI import NodeGUI
    from .NodeItem import NodeItem
    

class NodeItem_CollapseButton(QGraphicsWidget):
    def __init__(self, node_gui: 'NodeGUI', node_item: 'NodeItem'):
        super().__init__(parent=node_item)

        self.node_gui = node_gui
        self.node_item = node_item

        self.icon_size = QSizeF(14, 7)

        self.setGraphicsItem(self)
        self.setCursor(Qt.PointingHandCursor)


        self.collapse_pixmap = change_svg_color(
            get_resource('node_collapse_icon.svg'),
            self.node_gui.color
        )
        self.expand_pixmap = change_svg_color(
            get_resource('node_expand_icon.svg'),
            self.node_gui.color
        )


    def boundingRect(self):
        return QRectF(QPointF(0, 0), self.icon_size)

    def setGeometry(self, rect):
        self.prepareGeometryChange()
        QGraphicsLayoutItem.setGeometry(self, rect)
        self.setPos(rect.topLeft())

    def sizeHint(self, which, constraint=...):
        return QSizeF(self.icon_size.width(), self.icon_size.height())

    def mousePressEvent(self, event):
        event.accept()  # make sure the event doesn't get passed on
        self.node_item.flow_view.mouse_event_taken = True

        if self.node_item.collapsed:
            self.node_item.expand()
        else:
            self.node_item.collapse()

    # def hoverEnterEvent(self, event):

    def paint(self, painter, option, widget=None):

        # doesn't work: ...
        # painter.setRenderHint(QPainter.Antialiasing, True)
        # painter.setRenderHint(QPainter.HighQualityAntialiasing, True)
        # painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        if not self.node_item.hovered:
            return

        if self.node_item.collapsed:
            pixmap = self.expand_pixmap
        else:
            pixmap = self.collapse_pixmap

        painter.drawPixmap(
            0, 0,
            self.icon_size.width(), self.icon_size.height(),
            pixmap
        )
        
        
class NodeItem_Icon(QGraphicsWidget):
    def __init__(self, node_gui: 'NodeGUI', node_item: 'NodeItem'):
        super().__init__(parent=node_item)

        self.icon_size = QSize(20, 20) if node_gui.style == 'normal' else QSize(50, 50)

        image = QImage(node_gui.icon)
        self.pixmap = QPixmap.fromImage(image)
        # self.pixmap = change_svg_color(node.icon, node.color)


    def boundingRect(self):
        return QRectF(QPointF(0, 0), self.icon_size)

    def setGeometry(self, rect):
        self.prepareGeometryChange()
        QGraphicsLayoutItem.setGeometry(self, rect)
        self.setPos(rect.topLeft())

    def sizeHint(self, which, constraint=...):
        return QSizeF(self.icon_size.width(), self.icon_size.height())


    def paint(self, painter, option, widget=None):

        # TODO: anti aliasing for node icons
        
        # this doesn't work: ...
        # painter.setRenderHint(QPainter.Antialiasing, True)
        # painter.setRenderHint(QPainter.HighQualityAntialiasing, True)
        # painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        painter.drawPixmap(
            0, 0,
            self.icon_size.width(), self.icon_size.height(),
            self.pixmap
        )
    
    
class NodeItemWidget(QGraphicsWidget):
    """The QGraphicsWidget managing all GUI components of a NodeItem in widgets and layouts."""

    def __init__(self, node_gui: 'NodeGUI', node_item: 'NodeItem'):
        super().__init__(parent=node_item)

        self.node_gui = node_gui
        self.node_item = node_item
        self.flow_view = self.node_item.flow_view
        self.flow = self.flow_view.flow

        self.body_padding = 6
        self.header_padding = (0, 0, 0, 0)  # theme dependent and hence updated in setup_layout()!

        self.icon = NodeItem_Icon(node_gui, node_item) if node_gui.icon else None
        self.collapse_button = NodeItem_CollapseButton(node_gui, node_item)
        
        self.title_label = GraphicsTextWidget()
        self.title_label.set_font(
            QFont('Poppins', 15) if self.node_gui.style == 'normal' else
            QFont('K2D', 20, QFont.Bold, True)
        )
        
        self.main_widget_proxy: FlowViewProxyWidget = None
        if self.node_item.main_widget:
            self.main_widget_proxy = FlowViewProxyWidget(self.flow_view)
            self.main_widget_proxy.setWidget(self.node_item.main_widget)
        self.header_layout: QGraphicsWidget = None
        self.header_widget: QGraphicsWidget = None
        self.body_layout: QGraphicsLinearLayout = None
        self.body_widget: QGraphicsWidget = None
        self.inputs_layout: QGraphicsLinearLayout = None
        self.outputs_layout: QGraphicsLinearLayout = None
        self.setLayout(self.setup_layout())

    def setup_layout(self) -> QGraphicsLinearLayout:

        self.header_padding = self.node_item.session_design.flow_theme.header_padding

        #   main layout
        layout = QGraphicsLinearLayout(Qt.Vertical)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.header_widget = QGraphicsWidget()
        self.header_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.header_layout = QGraphicsLinearLayout(Qt.Horizontal)
        self.header_widget.setLayout(self.header_layout)
        
        self.header_layout.setSpacing(5)
        self.header_layout.setContentsMargins(
            *self.header_padding
        )
        
        if self.icon:
            self.header_layout.addItem(self.icon)
            self.header_layout.setAlignment(
                self.icon, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
            )

        self.header_layout.addItem(self.title_label)
        
        self.header_layout.addItem(self.collapse_button)
        self.header_layout.setAlignment(
            self.collapse_button, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight
        )
        
        layout.addItem(self.header_widget)
        layout.setAlignment(self.header_widget, Qt.AlignmentFlag.AlignHCenter)
            
        #   inputs
        self.inputs_layout = QGraphicsLinearLayout(Qt.Vertical)
        self.inputs_layout.setSpacing(2)

        #   outputs
        self.outputs_layout = QGraphicsLinearLayout(Qt.Vertical)
        self.outputs_layout.setSpacing(2)

        #   body
        self.body_widget = QGraphicsWidget()
        # self.body_widget.setContentsMargins(0, 0, 0, 0)
        self.body_layout = QGraphicsLinearLayout(Qt.Horizontal)
        self.body_layout.setContentsMargins(
            self.body_padding,
            self.body_padding,
            self.body_padding,
            self.body_padding
        )

        self.body_layout.setSpacing(4)
        self.body_layout.addItem(self.inputs_layout)
        self.body_layout.setAlignment(self.inputs_layout, Qt.AlignVCenter | Qt.AlignLeft)
        self.body_layout.addStretch()
        self.body_layout.addItem(self.outputs_layout)
        self.body_layout.setAlignment(self.outputs_layout, Qt.AlignVCenter | Qt.AlignRight)

        self.body_widget.setLayout(self.body_layout)

        # layout.addItem(self.body_layout)
        layout.addItem(self.body_widget)

        return layout

    def rebuild_ui(self):
        """Due to some really strange and annoying behaviour of these QGraphicsWidgets, they don't want to shrink
        automatically when content is removed, they just stay large, even with a Minimum SizePolicy. I didn't find a
        way around that yet, so for now I have to recreate the whole layout and make sure the widget uses the smallest
        size possible."""

        # if we don't manually remove the ports from the layouts,
        # they get deleted when setting the widget's layout to None below
        
        if self.inputs_layout.count() > 0:
            for i, inp in enumerate(self.node_item.inputs):
                self.inputs_layout.removeAt(0)
        
        if self.outputs_layout.count() > 0:
            for i, out in enumerate(self.node_item.outputs):
                self.outputs_layout.removeAt(0)
        
        self.setLayout(None)
        self.resize(self.minimumSize())
        self.setLayout(self.setup_layout())

        if self.node_item.collapsed:
            return

        for inp_item in self.node_item.inputs:
            self.add_input_to_layout(inp_item)
        for out_item in self.node_item.outputs:
            self.add_output_to_layout(out_item)

        if self.node_item.main_widget:
            self.add_main_widget_to_layout()
=
    def update_shape(self):
        
        for inp in self.node_item.inputs:
            inp.update()
        
        for out in self.node_item.outputs:
            out.update()
            
        self.node_item.session_design.flow_theme.setup_NI_title_label(
            self.title_label,
            self.isSelected(),
            self.node_item.hovered,
            self.node_gui.style,
            self.node_gui.title(),
            self.node_item.color,
        )

        # makes extended node items shrink according to resizing input widgets
        if not self.node_item.initializing:
            self.rebuild_ui()
        # strangely, this only works for small node items without this, not for normal ones

        mw = self.node_item.main_widget
        if mw is not None:  # maybe the main_widget got resized
            # self.main_widget_proxy.setMaximumSize(mw.size())

            # self.main_widget_proxy.setMaximumSize(mw.maximumSize())

            self.main_widget_proxy.setMaximumSize(QSizeF(mw.size()))
            self.main_widget_proxy.setMinimumSize(QSizeF(mw.size()))

            self.adjustSize()
            self.adjustSize()

        self.body_layout.invalidate()
        self.layout().invalidate()
        self.layout().activate()
        # very essential; repositions everything in case content has changed (inputs/outputs/widget)

        if self.node_gui.style == 'small':

            # making it recompute its true minimumWidth here
            self.adjustSize()

            if self.layout().minimumWidth() < self.title_label.size().width() + 15:
                self.layout().setMinimumWidth(self.title_label.size().width() + 15)
                self.layout().activate()

        w = self.boundingRect().width()
        h = self.boundingRect().height()
        rect = QRectF(QPointF(-w / 2, -h / 2),
                      QPointF(w / 2, h / 2))
        self.setPos(rect.left(), rect.top())

        if not self.node_gui.style == 'normal':
            if self.icon:
                self.icon.setPos(
                    QPointF(-self.icon.boundingRect().width() / 2,
                            -self.icon.boundingRect().height() / 2)
                )
                self.title_label.hide()
            else:
                self.title_label.setPos(
                    QPointF(-self.title_label.boundingRect().width() / 2,
                            -self.title_label.boundingRect().height() / 2)
                )


    def add_main_widget_to_layout(self):
        if self.node_gui.main_widget_pos == 'between ports':
            self.body_layout.insertItem(1, self.main_widget_proxy)
            self.body_layout.insertStretch(2)

        elif self.node_gui.main_widget_pos == 'below ports':
            self.layout().addItem(self.main_widget_proxy)
            self.layout().setAlignment(self.main_widget_proxy, Qt.AlignHCenter)

    def add_input_to_layout(self, inp: InputPortItem):
        if self.inputs_layout.count() > 0:
            self.inputs_layout.addStretch()
        self.inputs_layout.addItem(inp)
        self.inputs_layout.setAlignment(inp, Qt.AlignLeft)

    def insert_input_into_layout(self, index: int, inp: InputPortItem):
        self.inputs_layout.insertItem(index * 2 + 1, inp)  # *2 bcs of the stretches
        self.inputs_layout.setAlignment(inp, Qt.AlignLeft)
        if len(self.node_gui.node.inputs) > 1:
            self.inputs_layout.insertStretch(index * 2 + 1)  # *2+1 because of the stretches, too

    def remove_input_from_layout(self, inp: InputPortItem):
        self.inputs_layout.removeItem(inp)

        # just a temporary workaround for the issues discussed here:
        # https://forum.qt.io/topic/116268/qgraphicslayout-not-properly-resizing-to-change-of-content
        self.rebuild_ui()

    def add_output_to_layout(self, out: OutputPortItem):
        if self.outputs_layout.count() > 0:
            self.outputs_layout.addStretch()
        self.outputs_layout.addItem(out)
        self.outputs_layout.setAlignment(out, Qt.AlignRight)

    def insert_output_into_layout(self, index: int, out: OutputPortItem):
        self.outputs_layout.insertItem(index * 2 + 1, out)  # *2 because of the stretches
        self.outputs_layout.setAlignment(out, Qt.AlignRight)
        if len(self.node_gui.node.outputs) > 1:
            self.outputs_layout.insertStretch(index * 2 + 1)  # *2+1 because of the stretches, too

    def remove_output_from_layout(self, out: OutputPortItem):
        self.outputs_layout.removeItem(out)

        # just a temporary workaround for the issues discussed here:
        # https://forum.qt.io/topic/116268/qgraphicslayout-not-properly-resizing-to-change-of-content
        self.rebuild_ui()

    def collapse(self):
        self.body_widget.hide()
        if self.main_widget_proxy:
            self.main_widget_proxy.hide()

    def expand(self):
        self.body_widget.show()
        if self.main_widget_proxy:
            self.main_widget_proxy.show()

    def hide_unconnected_ports(self):
        for inp in self.node_item.node.inputs:
            if self.flow.connected_output(inp) is None:
                inp.hide()
        for out in self.node_item.node.outputs:
            if len(self.flow.connected_inputs(out)):
                out.hide()

    def show_unconnected_ports(self):
        for inp in self.node_item.inputs:
            inp.show()
        for out in self.node_item.outputs:
            out.show()
